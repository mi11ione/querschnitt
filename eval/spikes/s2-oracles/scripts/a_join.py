"""Task A: join Curia Business rows (DE/FR/IT) to OPD CHE affairs; write oracle_curia.jsonl.gz and print stats."""
import collections
import datetime as dt
import gzip
import json
import re

D = "/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s2-oracles/data"
CLEAN_FROM = "2024-11-06"  # BFH Space last modified 2024-11-05 -> strictly after


def ms_date(s):
    m = re.match(r"/Date\((-?\d+)", s or "")
    return dt.datetime.utcfromtimestamp(int(m.group(1)) / 1000).date().isoformat() if m else None


cur = {}  # ID -> merged record
for lang in ("de", "fr", "it"):
    for line in gzip.open(f"{D}/curia_business_{lang}.jsonl.gz", "rt"):
        r = json.loads(line)
        c = cur.setdefault(r["ID"], {"curia_id": r["ID"], "short_number": r["BusinessShortNumber"],
                                     "submitted": ms_date(r["SubmissionDate"]), "type": r["BusinessTypeAbbreviation"],
                                     "dept": r["ResponsibleDepartmentAbbreviation"], "tags_by_lang": {}, "titles": {}})
        c["titles"][lang] = r["Title"]
        c["tags_by_lang"][lang] = [int(t) for t in (r["Tags"] or "").split("|") if t.strip()]
print("curia distinct IDs", len(cur), "rows per lang",
      {l: sum(1 for c in cur.values() if l in c["titles"]) for l in ("de", "fr", "it")})
tag_inconsistent = sum(1 for c in cur.values() if len({tuple(sorted(v)) for v in c["tags_by_lang"].values()}) > 1)
print("IDs whose tag set differs across languages", tag_inconsistent)

tags = json.load(open(f"{D}/curia_tags.json"))
tagname = {l.lower(): {t["ID"]: t["TagName"] if "TagName" in t else t.get("Name") for t in v} for l, v in tags.items()}

texts = collections.defaultdict(set)
for i, line in enumerate(gzip.open("/Users/mi11ion/Desktop/hackapertus/gegenprobe/track_2a/data/census/texts.tsv.gz", "rt")):
    if i == 0:
        continue
    p = line.rstrip("\n").split("\t")
    if p[1] == "CHE" and p[3] in ("Eingereichter Text", "Texte déposé", "Testo depositato") and p[5] not in ("", "0"):
        texts[int(p[2])].add(p[3])

opd = {}
for line in gzip.open("/Users/mi11ion/Desktop/hackapertus/spikes/data/raw/opd/affairs.ndjson.gz", "rt"):
    a = json.loads(line)
    if a["body_key"] == "CHE" and (a["external_id"] or "").isdigit():
        opd[int(a["external_id"])] = a
print("OPD CHE affairs with numeric external_id", len(opd))

out, stats = [], collections.Counter()
num_mismatch = []
for cid, c in cur.items():
    a = opd.get(cid)
    stats["curia_total"] += 1
    if not a:
        stats["curia_not_in_opd"] += 1
        continue
    if a["number"] != c["short_number"]:
        num_mismatch.append((cid, a["number"], c["short_number"]))
    t = c["tags_by_lang"].get("de") or c["tags_by_lang"].get("fr") or c["tags_by_lang"].get("it") or []
    out.append({"opd_affair_id": a["id"], "curia_id": cid, "short_number": c["short_number"], "submitted": c["submitted"],
                "type": c["type"], "dept": c["dept"], "tags": t, "titles": c["titles"],
                "has_text_on_disk": a["id"] in texts, "clean_pool": (c["submitted"] or "") >= CLEAN_FROM})
print("joined", len(out), "of", len(cur), f"({len(out) / len(cur):.1%}); number mismatches", len(num_mismatch), num_mismatch[:5])
opd_since2000 = [a for a in opd.values() if (a["begin_date"] or "") >= "2000-01-01"]
joined_ids = {o["curia_id"] for o in out}
print("OPD CHE (numeric ext id) begin>=2000:", len(opd_since2000), "covered by curia rows:",
      sum(1 for a in opd_since2000 if int(a["external_id"]) in joined_ids))
print("examples", [(o["opd_affair_id"], o["curia_id"], o["short_number"]) for o in out[:3]])
with gzip.open(f"{D}/oracle_curia.jsonl.gz", "wt") as f:
    for o in out:
        f.write(json.dumps(o, ensure_ascii=False) + "\n")

tagged = [o for o in out if o["tags"]]
print("tagged", len(tagged), f"{len(tagged) / len(out):.1%}")
k = collections.Counter(len(o["tags"]) for o in out)
print("labels per affair", sorted(k.items()), "mean (tagged)", round(sum(len(o["tags"]) for o in tagged) / len(tagged), 2))
freq = collections.Counter(t for o in tagged for t in o["tags"])
print("label freq:", [(tagname["de"].get(t, t), n) for t, n in freq.most_common()])
yr = collections.defaultdict(lambda: [0, 0])
for o in out:
    y = (o["submitted"] or "????")[:4]
    yr[y][0] += 1
    yr[y][1] += bool(o["tags"])
print("year: n/tagged", {y: tuple(v) for y, v in sorted(yr.items())})
tri = [o for o in tagged if all(o["titles"].get(l) for l in ("de", "fr", "it"))]
print("tagged w/ all 3 titles", len(tri), "and submitted text in census", sum(o["has_text_on_disk"] for o in tri))
print("types (tagged)", collections.Counter(o["type"] for o in tagged).most_common(14))
cp = [o for o in tagged if o["clean_pool"]]
print("CLEAN POOL (submitted >=", CLEAN_FROM, ") tagged:", len(cp), "| per lang title:",
      {l: sum(1 for o in cp if o["titles"].get(l)) for l in ("de", "fr", "it")},
      "| with census text", sum(o["has_text_on_disk"] for o in cp),
      "| untagged in window", sum(1 for o in out if o["clean_pool"] and not o["tags"]))
print("clean pool types", collections.Counter(o["type"] for o in cp).most_common(12))
print("clean pool label freq", [(tagname["de"].get(t, t), n) for t, n in collections.Counter(t for o in cp for t in o["tags"]).most_common()])
json.dump({"tagname": tagname}, open(f"{D}/curia_tagnames.json", "w"), ensure_ascii=False, indent=1)
