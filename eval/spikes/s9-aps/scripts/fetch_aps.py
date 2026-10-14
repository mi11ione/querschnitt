"""S9 step 1a: fetch the remaining slug-joined APS process captures (Wayback id_ raw), parse chapter + main subtopic exactly
as ideation-1 s2-oracles/scripts/c_aps_fetch.py (regexes copied verbatim), join_quality as in ideation 1.
Excludes the 298 ideation-1 pages (by process id) and their affairs (by OPD affair id). Same shuffle seed as c_aps_fetch.
Polite: s2-oracles polite.py (RFC 9309 robots via robots9309, one UA, >=1.2 s/host, fail closed on 429/5xx); log -> our data/."""
import collections, gzip, html as H, json, os, random, re, sys, time
S2 = "/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s2-oracles"
sys.path.insert(0, f"{S2}/scripts")
import polite  # noqa: E402
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
polite.LOG = f"{HERE}/data/robots_log.jsonl"
D = f"{S2}/data"
OUT = f"{HERE}/data/aps_ext.jsonl"

links = collections.defaultdict(set)
for l in gzip.open("/Users/mi11ion/Desktop/hackapertus/gegenprobe/track_2a/.work/opd/external_links.ndjson.gz", "rt"):
    d = json.loads(l)
    if d.get("type_harmonized_en") == "aps_affair":
        links[d["affair_id"]].add(d["external_id"])
joined = json.load(open(f"{D}/raw_cdx/overlap.json"))["proc_joined"]
old = [json.loads(l) for l in open(f"{D}/aps_gold_sample.jsonl")]
old_p = {x["aps_process_id"] for x in old}; old_a = {x["opd_affair_id"] for x in old}
keys = sorted(joined)
random.Random(20261013).shuffle(keys)
keys = [k for k in keys if k not in old_p and joined[k][1] not in old_a]
done = set()
if os.path.exists(OUT):
    done = {json.loads(l)["aps_process_id"] for l in open(OUT)}
print("todo", len([k for k in keys if k not in done]), "of", len(keys), flush=True)
n_ok = n_try = n_err = 0; t0 = time.time()
with open(OUT, "a") as fo:
    for pid in keys:
        if pid in done:
            continue
        num, opd_id, row = joined[pid]
        cap = f"https://web.archive.org/web/{row[1]}id_/{row[0]}"
        n_try += 1; t = time.time()
        try:
            st, b = polite.get(cap, timeout=60, retries=2)
        except polite.Blocked as e:
            print("BLOCKED", e, flush=True); break
        except Exception as e:
            n_err += 1; print("ERR", pid, repr(e)[:120], flush=True); continue
        h = b.decode("utf-8", "replace")
        rec = {"opd_affair_id": opd_id, "curia_number": num, "aps_process_id": pid, "capture_url": cap,
               "capture_ts": row[1], "http": st, "secs": round(time.time() - t, 2)}
        ch = re.search(r'topic-(\d+(?:-\d+)*) topic-tag"><i></i><h3><a href="[^"]*chapters%5B%5D=([\d.]+)">([^<]+)</a>', h)
        sub = re.search(r'topic-tag subtopic"><h4><a href="[^"]*keywords%5B%5D=(\d+)">([^<]+)</a>', h)
        arts = sorted(set(re.findall(r'<a name="article-(\d+)"', h)), key=int)
        nrs = collections.Counter(x.strip() for x in re.findall(r"Gesch(?:ä|&auml;)ftsnr\.</dt>\s*<dd>([^<]+)</dd>", h))
        kw_topics = collections.Counter(re.findall(r'label-keyword topic-(\d+-\d+(?:-\d+)?)', h))
        rec.update({
            "chapter_code": ch.group(2) if ch else None,
            "chapter_name": H.unescape(ch.group(3)).strip() if ch else None,
            "subtopic_id": sub.group(1) if sub else None,
            "subtopic_name": H.unescape(sub.group(2)).strip() if sub else None,
            "aps_article_ids": arts,
            "aps_article_id": next((a for a in arts if a in links.get(opd_id, ())), None),
            "page_geschaeftsnr_top": nrs.most_common(1)[0][0] if nrs else None,
            "number_confirmed": bool(nrs) and nrs.most_common(1)[0][0] == num,
            "opd_has_aps_link": opd_id in links,
            "opd_link_in_page": any(a in links.get(opd_id, ()) for a in arts),
            "keyword_chapters": dict(kw_topics),
        })
        rec["join_quality"] = ("aps_link_in_page" if rec["opd_link_in_page"] else
                               "geschaeftsnr_on_page" if rec["number_confirmed"] else "slug_only")
        n_ok += bool(rec["chapter_code"])
        fo.write(json.dumps(rec, ensure_ascii=False) + "\n"); fo.flush()
        if n_try % 25 == 0:
            print(f"{n_try} tried, {n_ok} with chapter, {n_err} err, {(time.time() - t0) / n_try:.2f}s/item", flush=True)
        if n_try == 50 and n_ok < 15:
            print("poor yield, stopping", flush=True); break
print(f"DONE tried {n_try} ok {n_ok} err {n_err} in {time.time() - t0:.0f}s", flush=True)
