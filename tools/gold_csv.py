"""Gold CSVs for `make eval` from existing human labels (no new labelling):
  data/eval/gold_aps_s9.csv   1,357 held-out federal affairs with the APS editors' chapter (S9; oid = OPD affair id)
  data/eval/gold_dvs30.csv    the 30 digitalisation affairs on DVS's public page (S15 key, dvs = true): a positives list
Usage: python tools/gold_csv.py [ideation2/spikes dir]"""
import csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SP = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "ideation2/spikes"
out = ROOT / "data/eval"; out.mkdir(parents=True, exist_ok=True)
items = json.load(open(SP / "s9-aps/data/items.json"))
with open(out / "gold_aps_s9.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["affair_id", "scheme", "code", "year", "source"])
    for x in sorted(items, key=lambda x: x["oid"]):
        w.writerow([x["oid"], "aps", "aps:" + x["chapter_code"], x["year"], "APS editors (S9 held-out, " + x["join_quality"] + ")"])
dvs = [json.loads(l) for l in open(SP / "s15-judgecheck/key.jsonl") if l.strip()]
with open(out / "gold_dvs30.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["affair_id", "source"])
    for x in sorted((x for x in dvs if x["dvs"]), key=lambda x: x["oid"]):
        w.writerow([x["oid"], "DVS public list (S15)"])
print(len(items), "APS rows;", sum(x["dvs"] for x in dvs), "DVS rows")
