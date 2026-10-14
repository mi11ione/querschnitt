#!/usr/bin/env python3
"""Freeze the Prüfstand items into data/ (run once; the frozen files are what run.py reads).

    python3 upstream/eval-task/build_items.py [--s9 PATH] [--s8 PATH]

data/aps_s9.jsonl.gz   1,357 federal affairs: the exact inputs of S9/S16 (Curia Vista title, long title, submitted text
                       in German and French), the APS editors' chapter (= data/eval/gold_aps_s9.csv, checked here) and the
                       five labelled examples S9 retrieved for each item (BM25 over the 1,654-affair pool, the item itself
                       left out; frozen because tie order depends on pool order)
data/dvs30.jsonl       the 30 affairs on the public DVS "digitalisation" page: the exact inputs of S8 (title, long title,
                       language), all positives (= data/eval/gold_dvs30.csv, checked here)
data/MANIFEST.json     sha256 of every frozen file
Default source paths are the hackapertus working tree (ideation2/spikes/s9-aps, s8-dvs)."""
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--s9", default=str(BERN / "ideation2/spikes/s9-aps/data/items.json"))
    ap.add_argument("--s8", default=str(BERN / "ideation2/spikes/s8-dvs/items_cache.json"))
    ap.add_argument("--neighbours", default=str(BERN / "ideation2/spikes/s9-aps/data/d3_neighbours.json"))
    a = ap.parse_args(argv)
    out = HERE / "data"; out.mkdir(exist_ok=True)

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
    with gzip.GzipFile(p1, "wb", mtime=0) as f:
        f.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode())

    pos = [int(r["affair_id"]) for r in csv.DictReader(open(ROOT / "data/eval/gold_dvs30.csv"))]
    cache = {x["id"]: x for x in json.load(open(a.s8))}
    p2 = out / "dvs30.jsonl"
    p2.write_text("".join(json.dumps(dict(id=i, body=cache[i]["body"], level=cache[i]["level"], lang=cache[i]["lang"],
                                          title=cache[i]["title"], title_long=cache[i]["title_long"], gold=1),
                                     ensure_ascii=False) + "\n" for i in pos))
    pool = ROOT / "data/eval/aps_pool.jsonl"
    man = dict(files={p.name: sha(p) for p in (p1, p2)}, example_pool={str(pool.relative_to(ROOT)): sha(pool)},
               sources=dict(aps_s9=str(Path(a.s9).relative_to(BERN)) if str(a.s9).startswith(str(BERN)) else a.s9,
                            dvs30=str(Path(a.s8).relative_to(BERN)) if str(a.s8).startswith(str(BERN)) else a.s8),
               counts=dict(aps_s9=len(rows), dvs30=len(pos)))
    (out / "MANIFEST.json").write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps(man, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
