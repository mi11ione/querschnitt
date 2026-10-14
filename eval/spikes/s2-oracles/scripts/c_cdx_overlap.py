"""Task C: overlap of OPD aps_affair article ids / CHE numbers with Wayback CDX captures (local, no network)."""
import collections, gzip, json, re
D = "/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s2-oracles/data"
links = {}
for l in gzip.open("/Users/mi11ion/Desktop/hackapertus/gegenprobe/track_2a/.work/opd/external_links.ndjson.gz", "rt"):
    d = json.loads(l)
    if d.get("type_harmonized_en") == "aps_affair":
        links.setdefault(d["external_id"], []).append(d["affair_id"])
print("aps links: article ids", len(links), "affairs", sum(len(v) for v in links.values()))
che = {}
for l in gzip.open("/Users/mi11ion/Desktop/hackapertus/spikes/data/raw/opd/affairs.ndjson.gz", "rt"):
    a = json.loads(l)
    if a["body_key"] == "CHE":
        che[a["number"]] = a["id"]
aps_aff = {a for v in links.values() for a in v}
art = collections.defaultdict(list)
for f in ("articles_id", "fr_articles_id"):
    for row in json.load(open(f"{D}/raw_cdx/{f}.json"))[1:]:
        if len(row) == 4:
            m = re.search(r"/articles/(\d+)", row[0])
            if m: art[m.group(1)].append(row)
print("CDX article ids captured", len(art), "status", collections.Counter(r[2] for v in art.values() for r in v))
hit = set(art) & set(links)
print("OPD aps article ids with an /articles/<id> capture:", len(hit))
proc = {}
for f in ("prozesse", "fr_prozesse"):
    for row in json.load(open(f"{D}/raw_cdx/{f}_prefix.json" if f == "prozesse" else f"{D}/raw_cdx/{f}.json"))[1:]:
        if len(row) != 4 or row[0].endswith(".pdf") or row[3] != "text/html" or row[2] != "200":
            continue
        m = re.search(r"/prozesse/(\d+)(?:-([^?#/]*))?", row[0])
        if m: proc.setdefault(m.group(1), []).append(row)
print("process ids with 200 html capture", len(proc))
# slug -> curia number: '...-mo-09-3719' / 'brg-20-090' / 'pa-iv-12-345' / 'mcf-10476'
num_re = re.compile(r"-(\d{2})-(\d{3,4})$")
joined = {}
for pid, rows in proc.items():
    for r in rows:
        slug = re.search(r"/prozesse/\d+-?([^?#/]*)", r[0]).group(1)
        m = num_re.search(slug)
        if m:
            n = f"{m.group(1)}.{m.group(2)}"
            if n in che:
                joined[pid] = (n, che[n], r)
                break
print("process ids whose slug ends in a Curia number present in OPD CHE:", len(joined))
print("  of which OPD affair has an aps link:", sum(1 for v in joined.values() if v[1] in aps_aff))
json.dump({"article_hits": sorted(hit), "proc_joined": joined}, open(f"{D}/raw_cdx/overlap.json", "w"))
