"""`querschnitt` command line.

    querschnitt build-inputs --export data/opd --out data/inputs.jsonl.gz
    querschnitt run --inputs data/inputs.jsonl.gz --out runs/main [batch options]     (wraps querschnitt.batch)
    querschnitt load [--topics topics.jsonl.gz] [--inputs data/inputs.jsonl.gz] [--if-empty]
    querschnitt serve [--host 127.0.0.1] [--port 8000]
    querschnitt delta --since yesterday [--plan] [--no-fetch] [--no-model]
    querschnitt nightly --at 02:30                                                      (delta once a day, forever)
    querschnitt topics-file --out out/topics.jsonl.gz       (the store's current machine rows, for the Hop loader)
    querschnitt eval GOLD.csv [--scheme adhoc/digitalisierung] [--out result.json]
    querschnitt scheme-eval THEIR.csv|xlsx [--id COL] [--label COL] [--n 200] [--examples 5] [--cap 2]   (make scheme-eval)
    querschnitt metrics | export

Paths default to the environment: QS_DB / QS_PG_DSN (store), QS_INPUTS (data/inputs.jsonl.gz), QS_EXPORT_DIR
(data/opd), QS_RUN_DIR (runs/main), QS_PROFILE (full | lite), QS_STEPS (batch steps for the full profile), QS_TOPICS_OUT
(the topics file a delta writes; lite default out/topics.jsonl.gz). Nightly steps: full
`ch sub yn bi ev` (chapter, subtopic read-back, ad-hoc topics, the German/French readings of bilingual parliaments, evidence
quote); lite `ch sub` (the measured chapter design: chapter read back from the subtopic; no ad-hoc topics, no quote).
Lite in OpenParlData's Postgres: the store's own tables are `qs_*`, beside OPD's `topics`, which only the Hop loader
(upstream/hop) writes, from the topics file each delta writes."""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import os
import sys
import time
from pathlib import Path

from .store import ROOT, Store, metrics_line, parse_ts


def env_path(key: str, default: str) -> Path:
    p = Path(os.environ.get(key) or default)
    return p if p.is_absolute() else ROOT / p


# ---------------------------------------------------------------- compose (lead's module; file writer if it has one)
def compose_rows(run: Path, inputs: Path, ids: set[int] | None, topics: list[str]) -> list[dict]:
    """Topic rows for `ids` from the run's step rows: compose.decide + compose.topic_rows with eval/calibration.json
    where it exists and was fitted on the run's build (topic_rows picks the map, so these rows equal the export's)."""
    from . import compose as C
    from .engine import Engine
    from .examples import ExamplePool
    from .scheme import adhoc
    lock, rows = C.read_run(run)
    pool_p = ROOT / "data/eval/aps_pool.jsonl"
    eng = Engine(None, ExamplePool.load(pool_p) if pool_p.exists() else None)
    calib = None
    if (ROOT / "eval/calibration.json").exists():
        from .calibrate import Calibration
        calib = Calibration.load(ROOT / "eval/calibration.json")
    T = [adhoc(t) for t in topics]
    out = []
    with gzip.open(inputs, "rt") as f:
        for line in f:
            a = json.loads(line)
            if ids is not None and a["id"] not in ids:
                continue
            dec = C.decide(a, rows, eng.ch1_prompt, T)
            if len(dec) <= 1:
                continue
            out += C.topic_rows(a, dec, lock, calib)
    return out


# ---------------------------------------------------------------- delta
SINGLES = ("affairs", "bodies", "contributors")


def fetch_exports(export: Path, plan: bool = False) -> dict:
    """Download the export files data.build reads when the published index says they changed (created / size)."""
    from . import net
    idx = net.get_json(net.EXPORTS + "index.json")
    state_p = export / ".qs_fetch.json"
    state = json.loads(state_p.read_text()) if state_p.exists() else {}
    jobs = []
    for f in idx["files"]:
        if f["type"] == "single" and f["entity"] in SINGLES:
            jobs.append((f["filename"], f["url"], f["size"], f.get("created")))
        elif f["type"] == "split" and f["entity"] == "texts":
            jobs += [("texts/" + g["filename"], g["url"], g["size"], g.get("created")) for g in f["files"]]
    todo = [j for j in jobs if state.get(j[0]) != [j[2], j[3]] or not (export / j[0]).exists()]
    out = dict(index_generated=idx.get("generated_at"), files=len(jobs), changed=len(todo), bytes=sum(j[2] for j in todo),
               docs={g["filename"]: g["url"] for f in idx["files"] if f["entity"] == "docs" for g in f.get("files", [])})
    if plan:
        return out
    for fn, url, size, created in todo:
        net.download(url, export / fn)
        state[fn] = [size, created]
        state_p.write_text(json.dumps(state, indent=0))
    (export / "index.json").write_text(json.dumps(idx))
    return out


def changed_affairs(export: Path, since: dt.datetime, known: dict[int, str]) -> tuple[set[int], set[str], set[int]]:
    """(new to the store or begun since `since`, their bodies, updated since `since`). Documents are streamed for the
    first set only: OPD refreshes `updated_at` broadly (82,995 affairs between 10 and 11 Oct 2026), so updated-only
    affairs are rebuilt from titles, texts and the documents already on disk."""
    from .net import ndjson
    s = since.isoformat()[:19]
    ids, bodies, upd = set(), set(), set()
    for a in ndjson(export / "affairs.ndjson.gz"):
        if a["id"] not in known or (a.get("begin_date") or "")[:19] >= s:
            ids.add(a["id"]); bodies.add(a["body_key"])
        elif (a.get("updated_at") or "")[:19] >= s:
            upd.add(a["id"])
    return ids, bodies, upd


def build_touched(export: Path, prev: Path, touched: set[int], out: Path, work: Path) -> dict:
    """Inputs for the touched affairs only (data.build over a filtered view of the export: their affairs and documents,
    the full bodies, contributors and texts files), merged into the previous inputs file. Memory follows the delta, not
    the corpus (a full rebuild holds every document head: 4.8 GB peak RSS on the 11 Oct export)."""
    import shutil
    from . import data
    from .net import ndjson
    v = work / "export-view"
    shutil.rmtree(v, ignore_errors=True); v.mkdir(parents=True)
    for f in ("bodies.ndjson.gz", "contributors.ndjson.gz", "texts"):
        (v / f).symlink_to((export / f).resolve())
    with gzip.open(v / "affairs.ndjson.gz", "wt") as o:
        for a in ndjson(export / "affairs.ndjson.gz"):
            if a["id"] in touched:
                o.write(json.dumps(a, ensure_ascii=False) + "\n")
    docs = export / "docs_slim.jsonl.gz"
    with gzip.open(v / "docs_slim.jsonl.gz", "wt") as o:
        if docs.exists():
            for d in ndjson(docs):
                if d["a"] in touched:
                    o.write(json.dumps(d, ensure_ascii=False) + "\n")
    part = work / "inputs-touched.jsonl.gz"
    st = data.build(v, part, docs_path=v / "docs_slim.jsonl.gz")
    with gzip.open(out, "wt") as o:
        with gzip.open(prev, "rt") as f:
            for line in f:
                if json.loads(line)["id"] not in touched:
                    o.write(line)
        with gzip.open(part, "rt") as f:
            for line in f:
                o.write(line)
    shutil.rmtree(v, ignore_errors=True); part.unlink(missing_ok=True)
    return st


def fetch_docs(export: Path, urls: dict[str, str], bodies: set[str], ids: set[int]) -> int:
    """Stream docs_<body>.ndjson.gz for the touched bodies and append the slim rows of the touched affairs to
    docs_slim.jsonl.gz (the format of tools/stream_docs.py; duplicates are harmless to data.pick_doc)."""
    from . import net
    from .data import clean
    n = 0
    with gzip.open(export / "docs_slim.jsonl.gz", "at") as o:
        for b in sorted(bodies):
            url = urls.get(f"docs_{b}.ndjson.gz")
            if not url:
                continue
            for d in net.stream_ndjson(url):
                if d.get("affair_id") not in ids or not d.get("text"):
                    continue
                t = clean(d["text"])
                if len(t) <= 200:
                    continue
                o.write(json.dumps(dict(id=d["id"], a=d["affair_id"], b=d["body_key"], name=d.get("name"), cat=d.get("category_harmonized"),
                                        cat_raw=d.get("category_de") or d.get("category_fr") or d.get("category_it"), lang=d.get("language"),
                                        date=(d.get("date") or "")[:10], url=d.get("url"), url_oparl=d.get("url_oparl"), n=len(t),
                                        head=t[:2000]), ensure_ascii=False) + "\n")
                n += 1
            time.sleep(1.5)
    return n


def ledger_usd(p: Path) -> float:
    if not p.exists():
        return 0.0
    tot = 0.0
    for line in p.read_text().splitlines():
        try:
            tot += json.loads(line)["usd"]
        except (ValueError, KeyError):
            pass
    return tot


NIGHTLY_STEPS = ("ch", "sub", "yn", "bi", "ev")   # the export's rows: lanes from bi, quotes from ev (the batch default is ch sub yn)
LITE_STEPS = ("ch", "sub")                        # the chapter as measured (S16/S25 and eval/calibration.json read back from sub)


def delta(a) -> dict:
    """Nightly: fresh export → inputs → new/changed affairs (input hash) → batch → topic rows → store → one line."""
    from . import data
    from .scheme import adhoc_topics
    t0 = time.time()
    st = Store()
    export, inputs, run = env_path("QS_EXPORT_DIR", a.export or "data/opd"), env_path("QS_INPUTS", a.inputs or "data/inputs.jsonl.gz"), \
        env_path("QS_RUN_DIR", a.run_dir or "runs/main")
    lite = (os.environ.get("QS_PROFILE") or a.profile) == "lite"
    since = parse_ts(a.since)
    log = dict(since=since.isoformat(), profile="lite" if lite else "full")
    if a.fetch:
        export.mkdir(parents=True, exist_ok=True)
        f = fetch_exports(export, plan=a.plan)
        log["fetch"] = {k: v for k, v in f.items() if k != "docs"}
        if a.plan:
            print(json.dumps(log, indent=1)); return log
    known = {r["id"]: r["input_hash"] for r in st.all("SELECT id, input_hash FROM qs_affairs")}
    ids, bodies, upd = changed_affairs(export, since, known)
    log.update(new_or_begun=len(ids), bodies=len(bodies), updated_only=len(upd))
    if a.fetch and ids:
        log["docs_rows"] = fetch_docs(export, f["docs"], bodies, ids)
    tmp = inputs.with_name(inputs.name.replace(".jsonl.gz", ".new.jsonl.gz"))
    docs = export / "docs_slim.jsonl.gz"
    if inputs.exists() and not a.full_rebuild:
        log["build"] = build_touched(export, inputs, ids | upd, tmp, run.parent / "delta-work")
    else:
        log["build"] = data.build(export, tmp, docs_path=docs if docs.exists() else Path("/nonexistent"))
    scope = os.environ.get("QS_SCOPE_SINCE", "2025-01-01")
    rowhash = {r["affair_id"]: r["input_hash"] for r in st.all(
        "SELECT affair_id, input_hash FROM qs_topics WHERE provenance = 'inferred' AND valid_to IS NULL AND scheme = 'aps' AND level = 1 AND rank = 1")}
    adds, n_new = [], 0
    with gzip.open(tmp, "rt") as fh:
        for line in fh:
            x = json.loads(line)
            i, h = x["id"], x["input_hash"]
            if i not in known:                                   # new to the store
                if x["date"] >= scope:
                    adds.append((i, h, "new")); n_new += 1
            elif known[i] is not None and known[i] != h:          # changed since it was loaded
                if x["date"] >= scope or i in rowhash:
                    adds.append((i, h, "changed"))
            elif known[i] is None and i in rowhash and rowhash[i] not in (None, h):
                adds.append((i, h, "changed"))                   # loaded from the static export, scored on an older input
    os.replace(tmp, inputs)
    st.load_affairs(inputs)
    st.queue_add(adds)
    pend_before = st.pending()
    log.update(new_affairs=n_new, queued=len(adds), pending_before=pend_before)
    topics = [] if lite else adhoc_topics()
    usd0 = ledger_usd(run / "ledger.jsonl")
    rows_in, build, n_scored, t_model = 0, None, 0, None
    Q = st.queue()
    todo = []
    if Q and a.model:
        dates = {r["id"]: r["date"] for r in st.affairs(list(Q)).values()}
        todo = sorted(Q, key=lambda i: (dates.get(i) or "", i), reverse=True)[: a.max_affairs or None]
    if todo and (run / "PID").exists():
        try:
            os.kill(int((run / "PID").read_text()), 0)
            raise SystemExit(f"{run}: a batch is running there (PID file); the delta never shares a live run dir")
        except (ProcessLookupError, ValueError):
            pass
    if todo:
        t_model = time.time()
        run.mkdir(parents=True, exist_ok=True)
        idf = run / f"delta-{dt.date.today().isoformat()}.ids"
        idf.write_text("\n".join(map(str, todo)) + "\n")
        from . import batch
        steps = list(LITE_STEPS) if lite else (os.environ.get("QS_STEPS") or "").split() or list(NIGHTLY_STEPS)
        log["steps"] = steps
        args = ["run", "--inputs", str(inputs), "--out", str(run), "--ids", str(idf), "--conc", str(a.conc),
                "--max-rate", str(a.max_rate), "--since", "0000", "--topics", *topics, "--steps", *steps]
        try:
            batch.main(args)
        except SystemExit as e:
            log["batch"] = f"stopped: {e}"
        if (run / "state.json").exists():
            rows = compose_rows(run, inputs, set(todo), topics)
            res = st.load_topics(rows)
            rows_in = res["inserted"]; log["load"] = res
            build = json.loads((run / "state.json").read_text())["lock"]["fp"]
        n_scored = st.queue_drain()
        t_model = time.time() - t_model
    usd = ledger_usd(run / "ledger.jsonl") - usd0
    pending = st.pending()
    wall = time.time() - t0
    log.update(todo=len(todo), scored=n_scored, pending_after=pending, drain_s=round(t_model, 1) if t_model is not None else None)
    st.log_run("delta", affairs=len(todo), rows=rows_in, wall_s=round(wall, 1), usd=round(usd, 6), pending=pending, build=build,
               note=json.dumps(log, ensure_ascii=False)[:4000])
    m = st.metrics()
    line = metrics_line(m) + f" · queue {pend_before} → {pending}" + (f" · drain {t_model / 60:.1f} min" if t_model is not None else "")
    log["line"] = line
    print(line, flush=True)
    out = Path(a.topics_out) if getattr(a, "topics_out", None) else \
        env_path("QS_TOPICS_OUT", "out/topics.jsonl.gz") if (lite or os.environ.get("QS_TOPICS_OUT")) else None
    if out:                                   # the hand-off to OPD: upstream/hop/load_topics.hwf loads this file into `topics`
        log["topics_file"] = dict(path=str(out), rows=st.write_topics_file(out))
        print(f"topics file {out}: {log['topics_file']['rows']:,} current machine rows", flush=True)
    if a.last:
        write_last(Path(a.last), export, log, a.model, rows_in, usd, m)
    return log


def write_last(p: Path, export: Path, log: dict, model: bool, rows_in: int, usd: float, m: dict):
    """runs/nightly/last.json, the app's «letzte Nacht»: a pass without the endpoint starts the night; the model pass
    after it completes the same record (otherwise the model pass starts a fresh one)."""
    today = time.strftime("%Y-%m-%d")
    old = json.loads(p.read_text()) if p.exists() else {}
    cont = model and old.get("date") == today and "pending_after_cut" in old and old.get("pending_after_drain") is None
    L = old if cont else dict(date=today, new_affairs=0, new_rows=0, usd=0.0, scored=0, pending_after_cut=None,
                              pending_after_drain=None, drain_minutes=None)
    idx = export / "index.json"
    L["opd_export_generated"] = json.loads(idx.read_text()).get("generated_at") if idx.exists() else L.get("opd_export_generated")
    L["new_affairs"] += log["new_affairs"]; L["new_rows"] += rows_in; L["usd"] = round(L["usd"] + usd, 6)
    if model:
        L.update(scored=L["scored"] + log["scored"], pending_after_drain=log["pending_after"],
                 drain_minutes=round(log["drain_s"] / 60, 1) if log["drain_s"] is not None else 0.0)
    else:
        L["pending_after_cut"] = log["pending_after"]
    L.update(pending=m["pending"], unscored_in_scope=m["unscored_in_scope"])
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp"); tmp.write_text(json.dumps(L, indent=1)); os.replace(tmp, p)


def nightly(a):
    """Run `delta --since yesterday` once a day at --at (local time), forever; one log line per night."""
    while True:
        h, m = map(int, a.at.split(":"))
        now = dt.datetime.now()
        nxt = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if nxt <= now:
            nxt += dt.timedelta(days=1)
        print(f"{now:%Y-%m-%d %H:%M} next delta at {nxt:%Y-%m-%d %H:%M}", flush=True)
        time.sleep((nxt - now).total_seconds())
        try:
            delta(a)
        except Exception as e:  # noqa: BLE001 — logged; the next night retries
            print(f"{dt.datetime.now():%Y-%m-%d %H:%M} delta failed: {e!r}", flush=True)
            try:
                Store().log_run("delta", note=f"failed: {e!r}"[:4000])
            except Exception:  # noqa: BLE001
                pass


def shipped_data() -> tuple[str | None, list[str], Path | None]:
    """(inputs, [topics], static export dir) for `make run`: the full local data if present, else the app's static
    export, else the test sample (80 OPD affairs with synthetic rows marked model=fixture)."""
    inp, top = env_path("QS_INPUTS", "data/inputs.jsonl.gz"), ROOT / "data/topics.jsonl.gz"
    if inp.exists() and top.exists():
        return str(inp), [str(top)], None
    exp = ROOT / "app/data"
    if (exp / "affairs.json").exists() and (exp / "topics.jsonl.gz").exists():
        return None, [str(exp / "topics.jsonl.gz")], exp
    fx = ROOT / "tests/fixtures"
    return str(fx / "inputs_sample.jsonl"), [str(fx / "topics_sample.jsonl")], None


# ---------------------------------------------------------------- editor decisions → examples
def adhoc_dir() -> Path:
    """The ad-hoc topic files (QS_ADHOC_DIR overrides, as for Neues Thema's save)."""
    return Path(os.environ.get("QS_ADHOC_DIR") or ROOT / "src/querschnitt/schemes/adhoc")


def examples_cmd(argv):
    """querschnitt examples --topic digitalisierung | --all [--dry-run]
    Reads the current confirmed/rejected rows of `adhoc/<topic>` from the store and writes them into
    schemes/adhoc/<topic>.yaml as `examples` ({affair_id, title, match, by, at}). From the next run on, each yes/no prompt
    for that topic shows the four most similar decided affairs (the S8 P8.5 loop shape; rows change prompt id and are
    re-scored, never mixed)."""
    import yaml
    ap = argparse.ArgumentParser(prog="querschnitt examples")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--topic")
    g.add_argument("--all", action="store_true", help="every ad-hoc topic with confirmed decisions (the nightly runs this)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if a.all:
        st = Store()
        topics = sorted({r["scheme"].split("/", 1)[1] for r in st.all(   # the pattern as a parameter: '%' is psycopg's placeholder
            "SELECT DISTINCT scheme FROM qs_topics WHERE scheme LIKE ? AND provenance = 'confirmed' AND valid_to IS NULL", ("adhoc/%",))})
        for t in topics:
            if (adhoc_dir() / f"{t}.yaml").exists():
                examples_cmd(["--topic", t] + (["--dry-run"] if a.dry_run else []))
        if not topics:
            print("no confirmed decisions on ad-hoc topics")
        return
    st = Store(); sch = f"adhoc/{a.topic}"
    rows = st.all("SELECT t.affair_id, t.code, t.status, t.confirmed_by, t.confirmed_at, a.title FROM qs_topics t "
                  "JOIN qs_affairs a ON a.id = t.affair_id WHERE t.scheme = ? AND t.valid_to IS NULL AND t.provenance = 'confirmed'", (sch,))
    ex = {}
    for r in rows:
        yes = r["code"].endswith(":yes")
        match = yes if r["status"] == "confirmed" else (not yes)
        ex[r["affair_id"]] = dict(affair_id=r["affair_id"], title=r["title"], match=match, by=r["confirmed_by"], at=str(r["confirmed_at"]))
    p = adhoc_dir() / f"{a.topic}.yaml"
    doc = yaml.safe_load(p.read_text())
    old = {e.get("affair_id"): e for e in doc.get("examples") or [] if isinstance(e, dict)}
    old.update(ex)
    doc["examples"] = list(old.values())
    print(f"{sch}: {len(ex)} decisions in the store → {len(doc['examples'])} examples in {p.name}"
          f" ({sum(e['match'] for e in doc['examples'])} yes, {sum(not e['match'] for e in doc['examples'])} no)")
    if not a.dry_run:
        p.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=300))


# ---------------------------------------------------------------- main
def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "run":                       # pass-through to the resumable batch runner
        from . import batch
        return batch.main(argv)
    if argv and argv[0] == "export":                    # the lead's static export, its own options
        from . import export
        return export.main(argv[1:])
    if argv and argv[0] == "eval":
        from . import evaluate
        return evaluate.main(argv[1:])
    if argv and argv[0] == "scheme-eval":              # a partner's labels -> their own scheme file -> a scored test
        from . import scheme_eval
        return scheme_eval.main(argv[1:])
    if argv and argv[0] == "examples":                  # editor decisions → the topic file's examples (used from the next run)
        return examples_cmd(argv[1:])
    if argv and argv[0] == "export":                    # pass-through to the static export (its own flags)
        from . import export
        return export.main(argv[1:])
    ap = argparse.ArgumentParser(prog="querschnitt", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build-inputs", help="OPD export dir → inputs.jsonl.gz")
    b.add_argument("--export", default=os.environ.get("QS_EXPORT_DIR", "data/opd"))
    b.add_argument("--out", default=os.environ.get("QS_INPUTS", "data/inputs.jsonl.gz"))
    b.add_argument("--docs", help="docs_slim.jsonl.gz (default: <export>/docs_slim.jsonl.gz)")
    sub.add_parser("run", help="the corpus batch (querschnitt run --help)")
    sub.add_parser("eval", help="score a labelled CSV (querschnitt eval --help)")
    sub.add_parser("scheme-eval", help="a partner's labels as their own scheme, scored (querschnitt scheme-eval --help)")
    l = sub.add_parser("load", help="topic rows and affair summaries → store")
    l.add_argument("--topics", nargs="*", default=[])
    l.add_argument("--inputs")
    l.add_argument("--if-empty", action="store_true", help="only when the store has no rows (make run)")
    l.add_argument("--auto", action="store_true", help="the shipped data: data/{inputs,topics}.jsonl.gz, else app/data "
                   "(static export), else the test sample")
    s = sub.add_parser("serve", help="the API (+ app/ at /)")
    s.add_argument("--host", default=os.environ.get("QS_HOST", "127.0.0.1"))
    s.add_argument("--port", type=int, default=int(os.environ.get("QS_PORT", "8000")))
    for name in ("delta", "nightly"):
        d = sub.add_parser(name, help="nightly export delta" if name == "delta" else "delta once a day")
        d.add_argument("--since", default="yesterday")
        d.add_argument("--export"); d.add_argument("--inputs"); d.add_argument("--run-dir")
        d.add_argument("--profile", default="full", choices=["full", "lite"])
        d.add_argument("--plan", action="store_true", help="robots + index only: print what would be downloaded")
        d.add_argument("--no-fetch", dest="fetch", action="store_false", help="use the export files on disk")
        d.add_argument("--no-model", dest="model", action="store_false", help="inputs and affairs only, no batch")
        d.add_argument("--max-affairs", type=int)
        d.add_argument("--full-rebuild", action="store_true", help="rebuild every input (first night; ~5 GB RAM peak)")
        d.add_argument("--last", help="write/complete the night's summary JSON (runs/nightly/last.json)")
        d.add_argument("--conc", type=int, default=int(os.environ.get("QS_CONC", "3")))
        d.add_argument("--max-rate", type=float, default=float(os.environ.get("QS_MAX_RATE", "1.0")))
        d.add_argument("--topics-out", help="write the topics file for the Hop loader here after the load (env QS_TOPICS_OUT; "
                       "lite default out/topics.jsonl.gz, full: only when given)")
        if name == "nightly":
            d.add_argument("--at", default=os.environ.get("QS_NIGHTLY_AT", "02:30"))
    tf = sub.add_parser("topics-file", help="the store's current machine rows as the topics file the Hop loader reads")
    tf.add_argument("--out", default=str(env_path("QS_TOPICS_OUT", "out/topics.jsonl.gz")))
    sub.add_parser("metrics", help="print the /metrics line")
    sub.add_parser("export", help="static export for the app (app/data/)")
    a = ap.parse_args(argv)

    if a.cmd == "build-inputs":
        from . import data
        exp = Path(a.export)
        print(json.dumps(data.build(exp, Path(a.out), docs_path=Path(a.docs) if a.docs else None), indent=1))
    elif a.cmd == "load":
        st = Store()
        if a.if_empty and st.one("SELECT COUNT(*) AS n FROM qs_topics")["n"]:
            print(f"store {st.kind} has rows; nothing loaded (--if-empty)"); return
        t0 = time.time(); n_aff, res = 0, dict(inserted=0)
        if a.auto and not (a.inputs or a.topics):
            a.inputs, a.topics, exp = shipped_data()
            if exp:
                n_aff = st.load_affairs_export(exp); print(f"affairs {n_aff:,} ← {exp} (static export)")
        if a.inputs:
            n_aff = st.load_affairs(a.inputs); print(f"affairs {n_aff:,} ← {a.inputs}")
        for p in a.topics:
            res = st.load_topics(p); print(f"topics ← {p}: {res}")
        if a.auto and (ROOT / "app/data/bodies.json").exists():
            print(f"parliaments {st.load_bodies_json(ROOT / 'app/data/bodies.json')} ← app/data/bodies.json")
        st.log_run("load", affairs=n_aff, rows=res["inserted"], wall_s=round(time.time() - t0, 1), pending=st.pending(),
                   note=json.dumps(dict(inputs=a.inputs, topics=a.topics)))
        print(metrics_line(st.metrics()))
    elif a.cmd == "serve":
        from .api import serve
        serve(a.host, a.port)
    elif a.cmd == "delta":
        delta(a)
    elif a.cmd == "nightly":
        nightly(a)
    elif a.cmd == "metrics":
        print(metrics_line(Store().metrics()))
    elif a.cmd == "topics-file":
        out = Path(a.out)
        print(f"topics file {out}: {Store().write_topics_file(out):,} current machine rows")
    elif a.cmd == "export":
        try:
            from . import export  # the lead's module
        except ImportError:
            sys.exit("export: not built yet (querschnitt.export is written by the engine workstream)")
        return export.main(argv[1:])


if __name__ == "__main__":
    sys.exit(main())
