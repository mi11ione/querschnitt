"""Static export for the app and the open data files (docs/CONTRACT.md §3):

    python -m querschnitt.export --run runs/main --inputs ../data/inputs.jsonl.gz --out app/data [--since 2025-01-01]

Writes meta.json, bodies.json, affairs.json (columnar), detail/<id // 1000>.json, scheme_aps.json and, for the open
topics file, topics.jsonl.gz (CONTRACT §1 rows). Only affairs whose steps are complete get topic values; the scored
share is reported per parliament."""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import re
import time
from pathlib import Path

from . import prompts as P
from .calibrate import Calibration
from .compose import VERSION, decide, read_run, topic_rows
from .data import load_bodies, level, parl_name
from .engine import Engine
from .examples import ExamplePool
from .scheme import APS, adhoc, flat, named_schemes

ROOT = Path(__file__).resolve().parents[2]
NAMED_IDS = set()
KW = re.compile(json.loads((ROOT / "eval/kw_digitalisierung.json").read_text())["kw"], re.I)


def kw_text(x):
    t, tl = x["title"], x["title_long"]
    return t[:400] + ("\n" + tl[:400] if tl and tl != t else "")


def jdump(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
    tmp.rename(p)


def run(args):
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    extra = [tuple(e.split(":")) for e in args.extra]   # BODY:FROM:TO — a parliament's own scheme with its labelled years
    NAMED_IDS.update(s["id"] for s in named_schemes())
    lock, rows = read_run(*[Path(r) for r in args.run.split(",")])
    eng = Engine(None, ExamplePool.load(ROOT / "data/eval/aps_pool.jsonl"))
    topics = [adhoc("digitalisierung")]
    calib = Calibration.load(ROOT / "eval/calibration.json") if (ROOT / "eval/calibration.json").exists() else None
    B = load_bodies(Path(args.opd))
    first_year = collections.defaultdict(lambda: "9999")
    X = []
    with gzip.open(args.inputs, "rt") as f:
        for line in f:
            x = json.loads(line)
            if x["date"] and x["date"][:4] >= "1800":   # a few OPD dates are typos (e.g. 0209)
                first_year[x["body"]] = min(first_year[x["body"]], x["date"][:4])
            if x["date"] and (args.since <= x["date"] <= args.until or
                              any(x["body"] == b and lo <= x["date"] <= hi for b, lo, hi in extra)):
                X.append(x)
    X.sort(key=lambda x: (x["date"], x["id"]), reverse=True)
    cols = collections.defaultdict(list)
    detail = collections.defaultdict(dict)
    cov = collections.defaultdict(collections.Counter)
    months = collections.defaultdict(collections.Counter)
    tfile = gzip.open(out / "topics.jsonl.gz.tmp", "wt") if args.topics_file else None
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    n_dec = collections.Counter()
    n_extra = 0
    gold_own = {}   # a parliament's own labels where published openly (Basel-Stadt OGD 100086, CC BY 4.0): number → code
    bsf = ROOT.parent / "data/manual/bs_100086.csv"
    if bsf.exists():
        import csv
        bs = next((s_ for s_ in named_schemes() if s_["id"] == "bs-themen"), None)
        if bs:
            by_name = {o["name"]["de"]: o["code"].split(":", 1)[1] for o in bs["options"]}
            for r in csv.DictReader(open(bsf, encoding="utf-8-sig"), delimiter=";"):
                gold_own[("BS", r["Signatur"])] = [by_name.get(r["Thema 1"]), by_name.get(r["Thema 2"]) if r["Thema 2"] else None]
    for x in X:
        d = decide(x, rows, eng.ch1_prompt, topics)
        if not (args.since <= x["date"] <= args.until) and not any(k in NAMED_IDS for k in d):
            continue   # extra ranges carry only the affairs scored with the parliament's own scheme
        a = d.get("aps"); g = d.get("adhoc/digitalisierung")
        in_slice = args.since <= x["date"] <= args.until
        n_extra += not in_slice
        c = cov[x["body"]] if in_slice else collections.Counter()   # extra-range affairs stay out of slice totals
        c["n"] += 1; c["scored"] += bool(a); c["dig"] += bool(g); c["title_only"] += not x["text"]
        c["check"] += bool(a and a["lane"] == "please_check")
        if in_slice:
            months[x["body"]][x["date"][:7]] += 1
            n_dec["aps"] += bool(a); n_dec["dig"] += bool(g)
        trows = topic_rows(x, d, lock, calib.apply if calib else None, now)
        ar = sorted((r for r in trows if r["scheme"] == "aps" and r["level"] == 1), key=lambda r: r["rank"])
        ch_p = (ar[0]["p"] if ar[0]["p"] is not None else ar[0]["p_raw"]) if ar else None   # the API row's p, nothing else
        for k, v in (("id", x["id"]), ("body", x["body"]), ("date", x["date"]), ("type_h", x["type_h"] or x["type"]), ("type", x["type"]), ("type_h_fr", x.get("type_h_fr") or ""),
                     ("state", x["state"]), ("lang", x["text_lang"] or x["lang"]), ("title", x["title"]), ("party", x["party"]),
                     ("submitter", x["submitter"]), ("stype", x["submitter_type"]),
                     ("ch", a["ch"] if a else None), ("ch_p", round(ch_p, 3) if ch_p is not None else None),
                     ("lane", (a["lane"] == "please_check") * 1 if a else None),
                     ("subs", [1000 * APS.sub_index[s][0] + APS.sub_index[s][1] for s, _ in a["subs"]] if a else []),
                     ("dig_p", round(g["p"], 3) if g else None), ("dig_flag", int(g["flag"]) if g else None),
                     ("dig_lane", int(g["lane"] == "please_check") if g else None), ("kw", int(bool(KW.search(kw_text(x))))),
                     ("be", d["be-directorates"]["code"].split(":")[1] if d.get("be-directorates") else None),
                     ("be_lane", (d["be-directorates"]["lane"] == "please_check") * 1 if d.get("be-directorates") else None),
                     ("bi", (a["bilingual"]["lane"] == "please_check") * 1 if (a and a.get("bilingual")) else None),
                     ("own", next(([k, v["code"].split(":", 1)[1], int(v["lane"] == "please_check")] for k, v in d.items()
                                   if k in NAMED_IDS), None)),
                     ("own_gold", gold_own.get((x["body"], x["number"])))):
            cols[k].append(v)
        detail[x["id"] // 1000][x["id"]] = dict(
            title_long=x["title_long"], text=x["text"][:1500], text_src=x["text_src"], url=x["url"], number=x["number"],
            alt_lang=x.get("alt_lang"), title_alt=x.get("title_alt") or None, title_long_alt=x.get("title_long_alt") or None,
            n_signers=x["n_signers"], dept=x["dept"],
            aps=dict(reads={str(i): [round(a["R1"][i], 3)] + ([round(a["R2"][i], 3)] if a.get("R2") else [])
                               for i in sorted(range(25), key=lambda i: -(a["P"][i]))[:6]},
                     read_names=["Reihenfolge A", "Reihenfolge B"] if a.get("R2") else ["Reihenfolge A"],
                     rank=a["rank"], conf_raw=round(a["conf"], 4), p=[r["p"] for r in ar], p_raw=[r["p_raw"] for r in ar],
                     p_step=[round(a["P"][i], 4) for i in a["rank"]], lane=a["lane"],
                     subs=[[s, round(p, 4)] for s, p in a["subs"]], readings=a["n_readings"], examples=a.get("examples"),
                     pids=a["pids"], evidence=a.get("evidence"), bilingual=a.get("bilingual")) if a else None,
            be=d.get("be-directorates"),
            dig=dict(p=round(g["p"], 4), p_a=round(g["p_a"], 4), p_b=None if g["p_b"] is None else round(g["p_b"], 4),
                     lane=g["lane"], evidence=g.get("evidence")) if g else None,
            build=lock["fp"], model=lock["model"])
        if tfile:
            for r in trows:
                tfile.write(json.dumps(r, ensure_ascii=False) + "\n")
    if tfile:
        tfile.close()
        (out / "topics.jsonl.gz.tmp").rename(out / "topics.jsonl.gz")
    jdump(out / "affairs.json", dict(n=len(cols["id"]), cols=cols))
    for k, v in detail.items():
        jdump(out / "detail" / f"{k}.json", v)
    bodies = []
    for key, c in sorted(cov.items(), key=lambda kv: -kv[1]["n"]):
        b = B.get(key) or {}
        fed = key == "CHE"
        bodies.append(dict(key=key, name_de="Bundesversammlung" if fed else parl_name(key, B, "de"),
                           name_fr="Assemblée fédérale" if fed else parl_name(key, B, "fr"), place_de=b.get("name_de"), place_fr=b.get("name_fr"),
                           level=level(key, B), canton=b.get("canton_key") or (key if len(key) == 2 else None), lang=b.get("lang"),
                           n_affairs=c["n"], n_scored=c["scored"], n_dig=c["dig"], n_check=c["check"],
                           title_only_share=round(c["title_only"] / c["n"], 3), covered_from=first_year[key],
                           n_by_month=dict(sorted(months[key].items()))))
    jdump(out / "bodies.json", bodies)
    jdump(out / "scheme_aps.json", dict(
        chapters=[dict(i=i, code=APS.codes[i], de=APS.short(i, "de"), fr=APS.short(i, "fr"), it=APS.short(i, "it")) for i in range(25)],
        subtopics={str(1000 * i + j): dict(code=APS.sub_codes[i][j], de=APS.subs_de[i][j], ch=i) for i in range(24) for j in range(len(APS.subs_de[i]))},
        topics=[dict(id=t["id"], names=t["names"], aliases=t.get("aliases", [])) for t in topics],
        schemes=[dict(id="be-directorates", body="BE", title=flat("be-directorates")["title"],
                      options=[dict(code=o["code"].split(":")[1], abbr=o["abbr"], name=o["name"]) for o in flat("be-directorates")["options"]]
                      + [dict(code="none", abbr={"de": "—", "fr": "—"}, name=flat("be-directorates")["none"]["name"])])]
                + [dict(id=s["id"], body=s.get("body"), kind="named", title=s["title"],
                        options=[dict(code=o["code"].split(":", 1)[1], name=o["name"]) for o in s["options"]]
                        + [dict(code=s["none"]["code"].split(":", 1)[1], name=s["none"]["name"])]) for s in named_schemes()]))
    tot = sum(c["n"] for c in cov.values())
    meta = dict(generated_at=now, version=VERSION, model=lock["model"], build=lock["fp"], build_short=lock["fp"][-8:],
                since=args.since, until=min(X[0]["date"], time.strftime("%Y-%m-%d")) if X else None,
                n_future_dated=sum(1 for x in X if x["date"] > time.strftime("%Y-%m-%d")), affairs=tot, parliaments=len(cov),
                scored=n_dec["aps"], scored_share=round(n_dec["aps"] / tot, 4) if tot else 0, dig_scored=n_dec["dig"],
                please_check=sum(c["check"] for c in cov.values()), calibration=bool(calib),
                extra=dict(ranges=args.extra, affairs=n_extra))
    nl = ROOT / "runs/nightly/last.json"
    if nl.exists():
        meta["nightly"] = json.loads(nl.read_text())
    jdump(out / "meta.json", meta)
    pf = ROOT / "eval/pruefstand_app.json"
    if pf.exists():
        (out / "pruefstand.json").write_text(pf.read_text())
    print(json.dumps(meta, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=",".join(str(ROOT / "runs" / r) for r in ("main", "side", "ev", "s20") if (ROOT / "runs" / r / "state.json").exists()))
    ap.add_argument("--inputs", default=str(ROOT.parent / "data/inputs.jsonl.gz"))
    ap.add_argument("--opd", default=str(ROOT.parent / "data/opd-new"))
    ap.add_argument("--out", default=str(ROOT / "app/data"))
    ap.add_argument("--since", default="2025-01-01")
    ap.add_argument("--until", default="9999")
    ap.add_argument("--extra", nargs="*", default=["BS:2019-01-01:2024-12-31"],
                    help="BODY:FROM:TO ranges added to the slice (Basel-Stadt's labelled years for its own scheme, S20/S21)")
    ap.add_argument("--topics-file", dest="topics_file", action="store_true", default=True, help="write the open topics file (default)")
    ap.add_argument("--no-topics-file", dest="topics_file", action="store_false", help="skip the open topics file")
    run(ap.parse_args(argv))


if __name__ == "__main__":
    main()
