"""S25 step 2: fetch Wayback id_ captures of APS process pages NOT fetched by ideation-1 (aps_gold_sample) or S9
(aps_ext), newest process id first; parse chapter + main subtopic with the S9 / c_aps_fetch regexes (verbatim); join to
OPD CHE affairs via (a) APS article anchors on the page that OPD links as aps_affair, (b) the page's Geschäftsnr., (c) a
Curia number at the end of the slug. Resumable: every fetched pid goes to fetched.jsonl; raw pages to raw_pages.jsonl.gz.
Network: web.archive.org only, via ideation-1 polite.py. Stops at MAX qualifying new affairs or when candidates run out."""
import collections, gzip, html as H, json, os, re, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "spikes", "s2-oracles", "scripts"))  # vendored polite.py
import polite  # noqa: E402
HERE = os.path.dirname(os.path.abspath(__file__))
polite.LOG = f"{HERE}/robots_log.jsonl"
ROOT = os.path.dirname(os.path.dirname(HERE))  # repository root
WS = os.path.dirname(os.path.dirname(ROOT))  # workspace above the repo: OPD export copies used at fetch time (not in the repo)
S2D, S9D = f"{ROOT}/eval/spikes/s2-oracles/data", f"{ROOT}/eval/spikes/s9-aps/data"  # vendored
MAX = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
RAW_CAP = 95 * 2**20
APS_CODES = ['1.1.1.', '1.1.2.', '1.1.3.', '1.1.4.', '1.1.5.', '1.2.', '1.3.', '1.4.1.', '1.4.2.', '1.4.3.', '1.5.', '1.6.1.',
             '1.6.2.', '1.6.3.', '1.6.4.', '1.7.1.', '1.7.2.', '1.7.3.', '1.7.4.', '1.8.1.', '1.8.2.', '1.8.3.', '2.0.1.', '2.0.2.']

# OPD: aps_affair links (article id -> affair ids, affair id -> article ids), CHE number -> affair id
art2aff, links = collections.defaultdict(set), collections.defaultdict(set)
for l in gzip.open(f"{WS}/gegenprobe/track_2a/.work/opd/external_links.ndjson.gz", "rt"):
    d = json.loads(l)
    if d.get("type_harmonized_en") == "aps_affair":
        art2aff[d["external_id"]].add(d["affair_id"]); links[d["affair_id"]].add(d["external_id"])
che = {}
for l in gzip.open(f"{WS}/spikes/data/raw/opd/affairs.ndjson.gz", "rt"):
    if '"body_key":"CHE"' not in l:
        continue
    a = json.loads(l)
    che[a["number"]] = a["id"]

# exclusions: S5/ideation-1 (297/298), S9 (all fetched + items), example pool
ext = [json.loads(l) for l in open(f"{S9D}/aps_ext.jsonl")]
old = [json.loads(l) for l in open(f"{S2D}/aps_gold_sample.jsonl")]
EX_P = {x["aps_process_id"] for x in ext} | {x["aps_process_id"] for x in old}
EX_A = ({x["opd_affair_id"] for x in ext} | {x["opd_affair_id"] for x in old}
        | {x["oid"] for x in json.load(open(f"{S9D}/items.json"))}
        | {x["oid"] for x in json.load(open(f"{S9D}/mem_ideation1.json"))}
        | {json.loads(l)["oid"] for l in open(f"{ROOT}/data/eval/aps_pool.jsonl")})

# candidates: latest 200 text/html capture per process id, DE path preferred over /fr/
proc = collections.defaultdict(list)
for f in ("de_prozesse", "fr_prozesse"):
    for r in json.load(open(f"{HERE}/cdx/{f}.json"))[1:]:
        if len(r) < 4 or r[2] != "200" or r[3] != "text/html" or ".pdf" in r[0]:
            continue
        m = re.search(r"/prozesse/(\d+)(?:-([^?#/.]*))?/?$", r[0])
        if m:
            proc[m.group(1)].append(r)
num_re = re.compile(r"-(\d{2})-(\d{3,4})$")
def slugnum(rows):
    for r in rows:
        m = num_re.search(re.search(r"/prozesse/\d+-?([^?#/]*)", r[0]).group(1))
        if m and f"{m.group(1)}.{m.group(2)}" in che:
            return f"{m.group(1)}.{m.group(2)}"
cands = []
for pid, rows in proc.items():
    if pid in EX_P:
        continue
    sn = slugnum(rows)
    if sn and che[sn] in EX_A:
        continue
    best = max(rows, key=lambda r: ("/fr/" not in r[0], r[1]))
    cands.append((pid, best, sn))
if os.path.exists(f"{HERE}/extra_cands.json"):          # article route (art.py): process ids found via redirects
    have = {c[0] for c in cands}
    for pid, row in json.load(open(f"{HERE}/extra_cands.json")).items():
        if pid not in have and pid not in EX_P:
            cands.append((pid, row, slugnum([row])))
cands.sort(key=lambda c: -int(c[0]))

FET, ITEMS = f"{HERE}/fetched.jsonl", f"{HERE}/items.jsonl"
done = {}
if os.path.exists(FET):
    for l in open(FET):
        try: r = json.loads(l); done[r["aps_process_id"]] = r
        except ValueError: pass
def qualifies(r):
    return r.get("oid") and r["oid"] not in EX_A and r.get("chapter_code") in APS_CODES

def write_items():
    seen, out = set(), []
    for pid, _, _ in cands:
        r = done.get(pid)
        if r and qualifies(r) and r["oid"] not in seen:
            seen.add(r["oid"])
            out.append({k: r[k] for k in ("oid", "curia_number", "aps_process_id", "capture_url", "capture_ts", "chapter_code",
                                          "chapter", "chapter_name", "subtopic_id", "subtopic_name", "join_quality")})
    with open(ITEMS + ".tmp", "w") as f:
        for x in out: f.write(json.dumps(x, ensure_ascii=False) + "\n")
    os.replace(ITEMS + ".tmp", ITEMS)
    with open(f"{HERE}/ids.txt", "w") as f:
        for x in out: f.write(f"{x['oid']}\n")
    return len(out)

n_q = write_items()
print("candidates", len(cands), "done", len(done), "qualifying", n_q, flush=True)
n_try = n_err = 0; t0 = time.time()
with open(FET, "a") as fo:
    for pid, row, sn in cands:
        if n_q >= MAX:
            break
        if pid in done:
            continue
        cap = f"https://web.archive.org/web/{row[1]}id_/{row[0]}"
        n_try += 1; t = time.time()
        try:
            st, b = polite.get(cap, timeout=60, retries=2)
        except polite.Blocked as e:
            print("BLOCKED", e, flush=True); break
        except Exception as e:
            n_err += 1; print("ERR", pid, repr(e)[:120], flush=True)
            if n_err > 30 and n_err > n_try / 4: print("too many errors, stopping", flush=True); break
            continue
        h = b.decode("utf-8", "replace")
        if os.path.exists(f"{HERE}/raw_pages.jsonl.gz") is False or os.path.getsize(f"{HERE}/raw_pages.jsonl.gz") < RAW_CAP:
            with gzip.open(f"{HERE}/raw_pages.jsonl.gz", "at") as gz:
                gz.write(json.dumps({"pid": pid, "capture_url": cap, "http": st, "html": h}, ensure_ascii=False) + "\n")
        rec = {"aps_process_id": pid, "capture_url": cap, "capture_ts": row[1], "http": st, "secs": round(time.time() - t, 2)}
        # --- verbatim from ideation-1 c_aps_fetch.py / S9 fetch_aps.py ---
        ch = re.search(r'topic-(\d+(?:-\d+)*) topic-tag"><i></i><h3><a href="[^"]*chapters%5B%5D=([\d.]+)">([^<]+)</a>', h)
        sub = re.search(r'topic-tag subtopic"><h4><a href="[^"]*keywords%5B%5D=(\d+)">([^<]+)</a>', h)
        arts = sorted(set(re.findall(r'<a name="article-(\d+)"', h)), key=int)
        nrs = collections.Counter(x.strip() for x in re.findall(r"Gesch(?:ä|&auml;)ftsnr\.</dt>\s*<dd>([^<]+)</dd>", h))
        kw_topics = collections.Counter(re.findall(r'label-keyword topic-(\d+-\d+(?:-\d+)?)', h))
        # --- end verbatim ---
        top = nrs.most_common(1)[0][0] if nrs else None
        linked = sorted({a for x in arts for a in art2aff.get(x, ())})
        oid_nr = che.get(top) if top else None
        oid = jq = None
        if linked:
            if oid_nr in linked:
                oid, jq = oid_nr, "aps_link_in_page"
            elif len(linked) == 1:
                oid, jq = linked[0], "aps_link_in_page"
            else:
                jq = "aps_link_ambiguous"
        elif oid_nr:
            oid, jq = oid_nr, "geschaeftsnr_on_page"
        elif sn:
            oid, jq = che[sn], "slug_only"
        num = next((n for n, i in che.items() if i == oid), None) if oid else None
        rec.update({
            "oid": oid, "curia_number": num, "join_quality": jq, "opd_linked_affairs": linked,
            "chapter_code": ch.group(2) if ch else None,
            "chapter": APS_CODES.index(ch.group(2)) if ch and ch.group(2) in APS_CODES else None,
            "chapter_name": H.unescape(ch.group(3)).strip() if ch else None,
            "subtopic_id": sub.group(1) if sub else None,
            "subtopic_name": H.unescape(sub.group(2)).strip() if sub else None,
            "aps_article_ids": arts, "page_geschaeftsnr_top": top, "slug_number": sn,
            "keyword_chapters": dict(kw_topics),
        })
        done[pid] = rec
        fo.write(json.dumps(rec, ensure_ascii=False) + "\n"); fo.flush()
        if qualifies(rec):
            n_q = write_items()
        if n_try % 25 == 0:
            print(f"{n_try} tried, {n_q} qualifying, {n_err} err, {(time.time() - t0) / n_try:.2f}s/item, pid {pid}", flush=True)
n_q = write_items()
print(f"DONE tried {n_try} qualifying {n_q} err {n_err} in {time.time() - t0:.0f}s", flush=True)
