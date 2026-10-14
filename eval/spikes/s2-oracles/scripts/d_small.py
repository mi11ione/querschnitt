"""Task D: join CAP Swiss federal reports and Swissvotes to OPD CHE affairs (local)."""
import collections, csv, gzip, json, re
D = "/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s2-oracles/data"
che = {}
for l in gzip.open("/Users/mi11ion/Desktop/hackapertus/spikes/data/raw/opd/affairs.ndjson.gz", "rt"):
    a = json.loads(l)
    if a["body_key"] == "CHE":
        che[a["number"]] = (a["id"], a["type_harmonized_en"], (a["begin_date"] or "")[:4])
rows = list(csv.DictReader(open(f"{D}/raw_cap/switzerland_government.csv", encoding="utf-8")))
j = [r for r in rows if r["source"].strip() in che]
print("CAP rows", len(rows), "joined", len(j), f"{len(j)/len(rows):.1%}")
print(" unjoined by decade", collections.Counter(r["year"][:3] + "0s" for r in rows if r["source"].strip() not in che))
print(" joined OPD types", collections.Counter(che[r["source"].strip()][1] for r in j))
print(" majortopics", len({r["majortopic"] for r in rows}), "unjoined examples", [r["source"] for r in rows if r["source"].strip() not in che][:8])
out = [{"opd_affair_id": che[r["source"].strip()][0], "short_number": r["source"].strip(), "year": r["year"],
        "cap_major": r["majortopic"], "cap_sub": r["subtopic"], "title_fr": r["description"]} for r in j]
with gzip.open(f"{D}/oracle_cap.jsonl.gz", "wt") as f:
    for o in out: f.write(json.dumps(o, ensure_ascii=False) + "\n")
sv = list(csv.DictReader(open(f"{D}/raw_swissvotes/swissvotes_dataset.csv", encoding="utf-8-sig"), delimiter=";"))
nums = [(r["anr"], r["gesch_nr"].strip()) for r in sv]
has = [n for n in nums if n[1] and n[1] != "."]
jj = [n for n in has if n[1] in che]
print("Swissvotes rows", len(sv), "with gesch_nr", len(has), "joined OPD CHE", len(jj), "examples", has[:3], [n for n in has if n[1] not in che][:5])
print(" with d1e1", sum(1 for r in sv if r["d1e1"].strip() not in ("", ".")), "with anneepolitique link", sum(1 for r in sv if r["anneepolitique"].strip() not in ("", ".")))
