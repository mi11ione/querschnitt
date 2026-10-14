"""S25 step 4 (no network): rebuild items.jsonl + ids.txt from fetched.jsonl. Fills/joins Curia numbers against the newer
OPD snapshot bern/data/opd-new (CHE only): (i) curia_number for joined affairs missing from the older snapshot fetch.py used,
(ii) pages with exactly one Geschäftsnr. not in the older snapshot -> join_quality geschaeftsnr_on_page. Same exclusions
(S5/ideation-1, S9 fetched + items, example pool), 24 APS chapters only, one row per OPD affair (newest process id first)."""
import gzip, json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
B = "/Users/mi11ion/Desktop/hackapertus/bern"; S9D = f"{B}/ideation2/spikes/s9-aps/data"
APS_CODES = ['1.1.1.', '1.1.2.', '1.1.3.', '1.1.4.', '1.1.5.', '1.2.', '1.3.', '1.4.1.', '1.4.2.', '1.4.3.', '1.5.', '1.6.1.',
             '1.6.2.', '1.6.3.', '1.6.4.', '1.7.1.', '1.7.2.', '1.7.3.', '1.7.4.', '1.8.1.', '1.8.2.', '1.8.3.', '2.0.1.', '2.0.2.']
EX = ({json.loads(l)["opd_affair_id"] for l in open(f"{S9D}/aps_ext.jsonl")}
      | {json.loads(l)["opd_affair_id"] for l in open(f"{B}/ideation/spikes/s2-oracles/data/aps_gold_sample.jsonl")}
      | {x["oid"] for x in json.load(open(f"{S9D}/items.json"))} | {x["oid"] for x in json.load(open(f"{S9D}/mem_ideation1.json"))}
      | {json.loads(l)["oid"] for l in open(f"{B}/querschnitt/data/eval/aps_pool.jsonl")})
num2id, id2num = {}, {}
for l in gzip.open(f"{B}/data/opd-new/affairs.ndjson.gz", "rt"):
    if '"body_key":"CHE"' not in l:
        continue
    a = json.loads(l)
    num2id.setdefault(a["number"], a["id"]); id2num[a["id"]] = a["number"]
R = {}
for l in open(f"{HERE}/fetched.jsonl"):
    r = json.loads(l); R[r["aps_process_id"]] = r
n_new = 0
for r in R.values():
    if r["oid"] is None and r["join_quality"] is None and r["page_geschaeftsnr_top"] and r["page_geschaeftsnr_top"] in num2id:
        r["oid"], r["join_quality"] = num2id[r["page_geschaeftsnr_top"]], "geschaeftsnr_on_page"; n_new += 1
    if r["oid"] and not r["curia_number"]:
        r["curia_number"] = id2num.get(r["oid"])
out, seen = [], set()
for pid in sorted(R, key=lambda p: -int(p)):
    r = R[pid]
    if not r["oid"] or r["oid"] in EX or r["oid"] in seen or r["chapter_code"] not in APS_CODES or r["oid"] not in id2num:
        continue
    seen.add(r["oid"])
    out.append({"oid": r["oid"], "curia_number": r["curia_number"], "aps_process_id": pid, "capture_url": r["capture_url"],
                "capture_ts": r["capture_ts"], "chapter_code": r["chapter_code"], "chapter": APS_CODES.index(r["chapter_code"]),
                "chapter_name": r["chapter_name"], "subtopic_id": r["subtopic_id"], "subtopic_name": r["subtopic_name"],
                "join_quality": r["join_quality"]})
with open(f"{HERE}/items.jsonl", "w") as f:
    for x in out: f.write(json.dumps(x, ensure_ascii=False) + "\n")
with open(f"{HERE}/ids.txt", "w") as f:
    for x in out: f.write(f"{x['oid']}\n")
print("fetched", len(R), "new joins via opd-new", n_new, "items", len(out))
