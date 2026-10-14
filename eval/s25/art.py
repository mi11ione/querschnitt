"""S25 step 3: article route. For OPD aps_affair article ids that have a Wayback capture (redirects 301/302) and whose
OPD affair is not excluded, read the archived redirect's Location (no redirect following) to get the APS process id; if
that process id is not already a candidate, record a capture row for it in extra_cands.json (fetch.py picks these up).
Network: web.archive.org only (polite.py gate: robots, UA, >=1.2 s, fail closed on 429/5xx)."""
import collections, gzip, json, os, re, sys, urllib.error, urllib.parse, urllib.request
sys.path.insert(0, "/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s2-oracles/scripts")
import polite  # noqa: E402
HERE = os.path.dirname(os.path.abspath(__file__))
polite.LOG = f"{HERE}/robots_log.jsonl"
B = "/Users/mi11ion/Desktop/hackapertus/bern"; S9D = f"{B}/ideation2/spikes/s9-aps/data"
links = collections.defaultdict(set)
for l in gzip.open("/Users/mi11ion/Desktop/hackapertus/gegenprobe/track_2a/.work/opd/external_links.ndjson.gz", "rt"):
    d = json.loads(l)
    if d.get("type_harmonized_en") == "aps_affair":
        links[d["external_id"]].add(d["affair_id"])
EX = ({json.loads(l)["opd_affair_id"] for l in open(f"{S9D}/aps_ext.jsonl")}
      | {json.loads(l)["opd_affair_id"] for l in open(f"{B}/ideation/spikes/s2-oracles/data/aps_gold_sample.jsonl")}
      | {x["oid"] for x in json.load(open(f"{S9D}/items.json"))} | {x["oid"] for x in json.load(open(f"{S9D}/mem_ideation1.json"))}
      | {json.loads(l)["oid"] for l in open(f"{B}/querschnitt/data/eval/aps_pool.jsonl")})
art = collections.defaultdict(list)
for f in ("articles", "fr_articles"):
    for r in json.load(open(f"{HERE}/cdx/{f}.json"))[1:]:
        m = re.search(r"/articles/(\d+)$", r[0])
        if m and m.group(1) in links and links[m.group(1)] - EX:
            art[m.group(1)].append(r)
proc_ids = set()
for f in ("de_prozesse", "fr_prozesse"):
    for r in json.load(open(f"{HERE}/cdx/{f}.json"))[1:]:
        m = re.search(r"/prozesse/(\d+)", r[0])
        if m and r[2] == "200": proc_ids.add(m.group(1))

class NoRedir(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None
opener = urllib.request.build_opener(NoRedir)
def head_location(url):
    if not polite.allowed(url): raise polite.Blocked(url)
    polite._wait("web.archive.org")
    req = urllib.request.Request(url, headers={"User-Agent": polite.UA, "Accept-Encoding": "identity"})
    import time
    for attempt, delay in enumerate((5, 10, 20, None)):
        try:
            with opener.open(req, timeout=60) as r: return r.status, r.headers.get("Location")
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500: raise polite.Blocked(f"{e.code} {url}")
            return e.code, e.headers.get("Location")
        except urllib.error.URLError:
            if delay is None: raise
            time.sleep(delay); polite._wait("web.archive.org")

out, log = {}, []
for aid, rows in sorted(art.items()):
    r = max(rows, key=lambda r: r[1])
    url = f"https://web.archive.org/web/{r[1]}id_/{r[0]}"
    loc, hops = None, 0
    while hops < 3:
        st, loc = head_location(url); hops += 1
        if not loc: break
        loc = urllib.parse.urljoin(url, loc)
        if urllib.parse.urlsplit(loc).netloc != "web.archive.org":
            loc = None; break                      # never leave web.archive.org
        if "/prozesse/" in loc: break
        url = loc
    m = re.search(r"/web/(\d+)(?:id_)?/(https?://[^#?]*/prozesse/(\d+)[^#?]*)", loc or "")
    log.append({"article_id": aid, "affairs": sorted(links[aid]), "status": st, "location": loc})
    if m and m.group(3) not in proc_ids:
        out[m.group(3)] = [m.group(2), m.group(1), "200", "text/html"]
    print(aid, st, (loc or "")[:120], flush=True)
json.dump(out, open(f"{HERE}/extra_cands.json", "w"))
json.dump(log, open(f"{HERE}/art_log.json", "w"))
print("articles", len(art), "new process ids", len(out))
