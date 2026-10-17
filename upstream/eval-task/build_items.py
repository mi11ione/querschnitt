#!/usr/bin/env python3
"""Freeze the Prüfstand items into data/ (run once; the frozen files are what run.py reads).

    python3 upstream/eval-task/build_items.py [--splits aps_s9 dvs30 heldout_s25] [--s9 PATH] [--s8 PATH] [--inputs PATH]

data/aps_s9.jsonl.gz   1,357 federal affairs: the exact inputs of S9/S16 (Curia Vista title, long title, submitted text
                       in German and French), the APS editors' chapter (= data/eval/gold_aps_s9.csv, checked here) and the
                       five labelled examples S9 retrieved for each item (BM25 over the 1,654-affair pool, the item itself
                       left out; frozen because tie order depends on pool order)
data/aps_heldout_s25.jsonl.gz
                       927 federal affairs never used while designing (pre-registered S25, eval/PREREG-BUILD.md
                       2026-10-14 20:20): the production inputs the shipped run sent on 14 Oct (title, long title, up to
                       1,500 characters of text in the affair's language, from ../data/inputs.jsonl.gz; for the 40 whose
                       document text was rebuilt on 16 Oct to start at the title, the untrimmed document head the model saw,
                       from the OPD docs export), the APS editors' chapter (= eval/s25/items.jsonl, ids = eval/s25/ids.txt)
                       and the five APS-labelled examples the shipped engine retrieves (ExamplePool over data/eval/aps_pool.jsonl,
                       German federal affairs only; none of the 927 is in the pool, checked here). With --s25-run, every
                       chapter prompt is checked against the prompt ids of the stored S25 rows.
data/dvs30.jsonl       the 30 affairs on the public DVS "digitalisation" page: the exact inputs of S8 (title, long title,
                       language), all positives (= data/eval/gold_dvs30.csv, checked here)
data/MANIFEST.json     sha256 of every frozen file
Default source paths: the vendored S9 and S8 files in eval/spikes/ (byte-identical to ideation2/spikes/s9-aps, s8-dvs) and,
for heldout_s25, the production inputs and the OPD docs export in the working tree's data/ (outside the repo).
MANIFEST.json keeps the entries of the splits not rebuilt."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BERN = ROOT.parent


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p) -> str:
    """A source path relative to the repository root (`../` = the working tree around it)."""
    p = Path(p).resolve()
    if p.is_relative_to(ROOT):
        return str(p.relative_to(ROOT))
    return "../" + str(p.relative_to(BERN)) if p.is_relative_to(BERN) else str(p)


def build_s9(a, out: Path) -> tuple[Path, int]:
    gold = {int(r["affair_id"]): r["code"] for r in csv.DictReader(open(ROOT / "data/eval/gold_aps_s9.csv"))}
    items = json.load(open(a.s9))
    nb = {int(k): v for k, v in json.load(open(a.neighbours)).items()}
    rows = []
    for it in sorted(items, key=lambda x: int(x["oid"])):
        oid = int(it["oid"]); code = "aps:" + it["chapter_code"]
        assert gold[oid] == code, (oid, gold[oid], code)
        rows.append(dict(id=oid, curia_number=it.get("curia_number"), year=int(it["year"]), period=it.get("period"),
                         join_quality=it.get("join_quality"), gold_chapter=int(it["chapter"]), gold_code=code,
                         gold_subtopic=it.get("subtopic_name") if str(it.get("sub_gold")) == "True" else None,
                         de={k: it["de"].get(k) or "" for k in ("title", "title_long", "text")},
                         fr={k: (it.get("fr") or {}).get(k) or "" for k in ("title", "title_long", "text")},
                         examples=[dict(id=int(x["oid"]), title=x["title"], chapter=int(x["chapter"])) for x in nb[oid]]))
    assert len(rows) == len(gold) == 1357, len(rows)
    p1 = out / "aps_s9.jsonl.gz"
    write_gz(p1, rows)
    return p1, len(rows)


def write_gz(p: Path, rows: list[dict]):
    with gzip.GzipFile(p, "wb", mtime=0) as f:
        f.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode())


def build_dvs(a, out: Path) -> tuple[Path, int]:
    pos = [int(r["affair_id"]) for r in csv.DictReader(open(ROOT / "data/eval/gold_dvs30.csv"))]
    cache = {x["id"]: x for x in json.load(gzip.open(a.s8, "rt") if a.s8.endswith(".gz") else open(a.s8))}
    p2 = out / "dvs30.jsonl"
    p2.write_text("".join(json.dumps(dict(id=i, body=cache[i]["body"], level=cache[i]["level"], lang=cache[i]["lang"],
                                          title=cache[i]["title"], title_long=cache[i]["title_long"], gold=1),
                                     ensure_ascii=False) + "\n" for i in pos))
    return p2, len(pos)


def build_s25(a, out: Path) -> tuple[Path, int]:
    sys.path.insert(0, str(ROOT / "src"))
    from querschnitt import prompts as P
    from querschnitt.examples import ExamplePool
    gold = {}
    for line in open(a.s25):
        r = json.loads(line); gold[int(r["oid"])] = r
    ids = [int(l) for l in open(Path(a.s25).with_name("ids.txt")) if l.strip()]
    assert ids == list(gold) and len(ids) == 927, (len(ids), len(gold))
    pool = ROOT / "data/eval/aps_pool.jsonl"
    pool_ids = {int(json.loads(l)["oid"]) for l in open(pool) if l.strip()}
    assert not pool_ids & set(gold), "an S25 item is in the example pool"
    ex_pool = ExamplePool.load(pool)
    A = {}
    with gzip.open(a.inputs, "rt") as f:
        for line in f:
            x = json.loads(line)
            if x["id"] in gold:
                A[x["id"]] = x
    assert set(A) == set(gold), sorted(set(gold) - set(A))[:5]
    # the text the model saw on 14 Oct: inputs rebuilt on 16 Oct (QS_TRIM_DOCS=1, documents start at the title) carry a
    # trimmed document text; the S25 run read the untrimmed head (data.py with QS_TRIM_DOCS=0: head[:1500])
    from querschnitt.data import trim_to_title
    want = {int(x["text_src"].split(":")[1]): o for o, x in A.items() if x.get("text_kind") == "doc"}
    heads = {}
    with gzip.open(a.docs, "rt") as f:
        for line in f:
            i = int(line[7:line.index(",")]) if line.startswith('{"id": ') else None
            if i in want:
                heads[want[i]] = json.loads(line)["head"]
    assert len(heads) == len(want), (len(heads), len(want))
    n_untrimmed = 0
    for o, h in heads.items():
        assert trim_to_title(h, A[o]["title"])[:1500] == A[o]["text"], o      # the input is the trimmed form of this head
        if h[:1500] != A[o]["text"]:
            A[o] = dict(A[o], text=h[:1500]); n_untrimmed += 1
    rows_run = None
    if a.s25_run:
        from querschnitt.compose import read_run
        rows_run = read_run(Path(a.s25_run))[1]
    rows = []
    for o in sorted(gold):
        x, g = A[o], gold[o]
        assert x["level"] == "federal" and x["body"] == "CHE", o
        yr = int(("19" if g["curia_number"][:2] >= "50" else "20") + g["curia_number"][:2])
        ver = {x["lang"]: dict(title=x["title"], title_long=x["title_long"], text=x["text"] or "")}
        if x.get("alt_lang") in ("de", "fr"):
            ver[x["alt_lang"]] = dict(title=x["title_alt"], title_long=x["title_long_alt"], text="")
        empty = dict(title="", title_long="", text="")
        ex = ex_pool.neighbours(x) if x["lang"] == "de" else []        # the engine: examples for German federal affairs
        row = dict(id=o, curia_number=g["curia_number"], year=yr,
                   period="pre-2010" if yr < 2010 else "2010-19" if yr < 2020 else "2020+", join_quality=g["join_quality"],
                   gold_chapter=int(g["chapter"]), gold_code="aps:" + g["chapter_code"], gold_subtopic=g.get("subtopic_name"),
                   lang=x["lang"], de=ver.get("de", empty), fr=ver.get("fr", empty),
                   examples=[dict(id=int(e["oid"]), title=e["title"], chapter=int(e["chapter"])) for e in ex],
                   aps_process_id=g["aps_process_id"], aps_capture=g["capture_url"], text_src=x.get("text_src"))
        rows.append(row)
        if rows_run is not None:          # the chapter prompt the shipped engine sent (examples on the first code order)
            inp = dict(id=o, lang=x["lang"], **row[x["lang"]])
            u, p = (P.chapter_prompt_examples(inp, list(range(25)), [(e["title"], e["chapter"]) for e in row["examples"]])
                    if row["examples"] else P.chapter_prompt(inp, list(range(25))))
            assert P.pid(u, p) in rows_run, ("prompt not in the S25 rows", o)
    p3 = out / "aps_heldout_s25.jsonl.gz"
    write_gz(p3, rows)
    print(f"heldout_s25: {len(rows)} items, {sum(bool(r['examples']) for r in rows)} with examples, "
          f"{n_untrimmed} untrimmed document heads restored, prompts checked against the S25 rows: {rows_run is not None}")
    return p3, len(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", nargs="*", default=["aps_s9", "dvs30", "heldout_s25"], choices=["aps_s9", "dvs30", "heldout_s25"])
    ap.add_argument("--s9", default=str(ROOT / "eval/spikes/s9-aps/data/items.json"))
    ap.add_argument("--s8", default=str(ROOT / "eval/spikes/s8-dvs/items_cache.json.gz"))
    ap.add_argument("--neighbours", default=str(ROOT / "eval/spikes/s9-aps/data/d3_neighbours.json"))
    ap.add_argument("--s25", default=str(ROOT / "eval/s25/items.jsonl"))
    ap.add_argument("--inputs", default=str(BERN / "data/inputs.jsonl.gz"), help="production inputs (one row per affair)")
    ap.add_argument("--docs", default=str(BERN / "data/opd-new/docs_slim.jsonl.gz"), help="OPD docs export (document heads)")
    ap.add_argument("--s25-run", help="the S25 run dir (runs/s25): check every chapter prompt against its stored prompt ids")
    a = ap.parse_args(argv)
    out = HERE / "data"; out.mkdir(exist_ok=True)
    mp = out / "MANIFEST.json"
    man = json.loads(mp.read_text()) if mp.exists() else dict(files={}, example_pool={}, sources={}, counts={})
    built = {}
    if "aps_s9" in a.splits:
        built["aps_s9"] = (*build_s9(a, out), rel(a.s9))
    if "dvs30" in a.splits:
        built["dvs30"] = (*build_dvs(a, out), rel(a.s8))
    if "heldout_s25" in a.splits:
        built["heldout_s25"] = (*build_s25(a, out), f"{rel(a.s25)}; inputs {rel(a.inputs)}; document heads {rel(a.docs)}")
    for k, (p, n, src) in built.items():
        man["files"][p.name] = sha(p); man["sources"][k] = src; man["counts"][k] = n
    pool = ROOT / "data/eval/aps_pool.jsonl"
    man["example_pool"] = {str(pool.relative_to(ROOT)): sha(pool)}
    mp.write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps(man, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
