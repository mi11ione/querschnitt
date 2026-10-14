"""Task C: fetch <=300 Wayback captures of APS process pages that join to OPD CHE affairs; extract chapter + main subtopic."""
import collections
import gzip
import html as H
import json
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import polite  # noqa: E402

D = "/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s2-oracles/data"
MAX = int(sys.argv[1]) if len(sys.argv) > 1 else 300

links = collections.defaultdict(set)  # opd affair id -> aps article ids
for l in gzip.open("/Users/mi11ion/Desktop/hackapertus/gegenprobe/track_2a/.work/opd/external_links.ndjson.gz", "rt"):
    d = json.loads(l)
    if d.get("type_harmonized_en") == "aps_affair":
        links[d["affair_id"]].add(d["external_id"])

joined = json.load(open(f"{D}/raw_cdx/overlap.json"))["proc_joined"]
keys = sorted(joined)
random.Random(20261013).shuffle(keys)
out_path = f"{D}/aps_gold_sample.jsonl"
done = set()
if os.path.exists(out_path):
    done = {json.loads(l)["aps_process_id"] for l in open(out_path)}
n_ok = n_try = 0
t0 = time.time()
with open(out_path, "a") as fo:
    for pid in keys:
        if n_try + len(done) >= MAX:
            break
        if pid in done:
            continue
        num, opd_id, row = joined[pid]
        cap = f"https://web.archive.org/web/{row[1]}id_/{row[0]}"
        n_try += 1
        t = time.time()
        try:
            st, b = polite.get(cap, timeout=60, retries=2)
        except polite.Blocked as e:
            print("BLOCKED", e, flush=True)
            break
        except Exception as e:
            print("ERR", pid, e, flush=True)
            continue
        h = b.decode("utf-8", "replace")
        rec = {"opd_affair_id": opd_id, "curia_number": num, "aps_process_id": pid, "capture_url": cap,
               "capture_ts": row[1], "http": st, "secs": round(time.time() - t, 2)}
        top = re.search(r'<div class="topics">(.*?)</div>\s*</div>', h, re.S)
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
        if rec["chapter_code"]:
            n_ok += 1
        fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fo.flush()
        if n_try % 25 == 0:
            print(f"{n_try} tried, {n_ok} with chapter, {(time.time() - t0) / n_try:.2f}s/item", flush=True)
        if n_try == 50 and n_ok < 15:
            print("poor yield, stopping", flush=True)
            break
print(f"DONE tried {n_try} ok {n_ok} in {time.time() - t0:.0f}s", flush=True)
