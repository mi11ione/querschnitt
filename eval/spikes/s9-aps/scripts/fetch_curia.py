"""S9 step 1b: Curia OData DE + FR text fields for every S9 candidate affair (slug-joined, not ideation-1), same fields as
ideation-1 s3-accuracy/fetch_aps_texts.py, extended to FR. 20 IDs per request, polite.py (robots 404 = allow all, logged).
Curia ID from oracle_curia (opd_affair_id -> curia_id); else derived from the number (YY.NNNN -> 19|20YY*10^4 + NNNN)."""
import gzip, json, os, random, sys, urllib.parse
S2 = "/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s2-oracles"
sys.path.insert(0, f"{S2}/scripts")
import polite  # noqa: E402
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
polite.LOG = f"{HERE}/data/robots_log.jsonl"
D = f"{S2}/data"
SEL = "ID,Language,BusinessShortNumber,Title,SubmittedText,ReasonText,Description,InitialSituation"
o2c = {}
for l in gzip.open(f"{D}/oracle_curia.jsonl.gz", "rt"):
    r = json.loads(l); o2c[r["opd_affair_id"]] = r["curia_id"]
joined = json.load(open(f"{D}/raw_cdx/overlap.json"))["proc_joined"]
old = [json.loads(l) for l in open(f"{D}/aps_gold_sample.jsonl")]
old_p = {x["aps_process_id"] for x in old}; old_a = {x["opd_affair_id"] for x in old}

def derive(num):
    yy, n = num.split("."); return int(("19" if int(yy) >= 90 else "20") + yy) * 10000 + int(n)

ids = sorted({o2c.get(v[1]) or derive(v[0]) for k, v in joined.items() if k not in old_p and v[1] not in old_a})
print("curia ids", len(ids), flush=True)
for lang in ("DE", "FR"):
    out = f"{HERE}/data/curia_texts_{lang.lower()}.jsonl"
    have = {json.loads(l)["ID"] for l in open(out)} if os.path.exists(out) else set()
    asked = f"{HERE}/data/curia_asked_{lang.lower()}.json"
    done_ids = set(json.load(open(asked))) if os.path.exists(asked) else set()
    todo = [i for i in ids if i not in have and i not in done_ids]
    print(lang, "todo", len(todo), flush=True)
    for i in range(0, len(todo), 20):
        chunk = todo[i:i + 20]
        f = f"Language eq '{lang}' and (" + " or ".join(f"ID eq {x}" for x in chunk) + ")"
        url = "https://ws.parlament.ch/odata.svc/Business?$format=json&$select=" + SEL + "&$filter=" + urllib.parse.quote(f)
        rows = []
        while url:
            d = polite.get_json(url, timeout=120)["d"]
            res = d["results"] if isinstance(d, dict) else d
            for r in res:
                r.pop("__metadata", None); rows.append(r)
            url = d.get("__next") if isinstance(d, dict) else None
        with open(out, "a") as fo:
            for r in rows: fo.write(json.dumps(r, ensure_ascii=False) + "\n")
        done_ids |= set(chunk); json.dump(sorted(done_ids), open(asked, "w"))
        if (i // 20) % 10 == 0: print(lang, i, len(rows), flush=True)
print("DONE", flush=True)
