"""Task A/E: fetch Curia text fields for the clean test pool (submitted >= 2024-11-06), DE/FR/IT, monthly windows."""
import datetime as dt, gzip, json, os, sys, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import polite
D = "/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s2-oracles/data"
B = "https://ws.parlament.ch/odata.svc/"
SEL = "ID,Language,BusinessShortNumber,Title,SubmittedText,ReasonText,Description,InitialSituation"
def months():
    x = dt.date(2024, 11, 6)
    end = dt.date(2026, 11, 1)
    while x < end:
        nx = dt.date(x.year + (x.month == 12), x.month % 12 + 1, 1)
        yield x.isoformat(), nx.isoformat()
        x = nx
for lang in sys.argv[1:] or ("DE", "FR", "IT"):
    out = f"{D}/curia_cleanpool_texts_{lang.lower()}.jsonl.gz"
    if os.path.exists(out):
        continue
    rows = []
    for a, b in months():
        f = f"Language eq '{lang}' and SubmissionDate ge datetime'{a}T00:00:00' and SubmissionDate lt datetime'{b}T00:00:00'"
        url = B + "Business?$format=json&$orderby=ID&$select=" + SEL + "&$filter=" + urllib.parse.quote(f)
        while url:
            d = polite.get_json(url, timeout=180)["d"]
            res = d["results"] if isinstance(d, dict) else d
            for r in res:
                r.pop("__metadata", None)
                rows.append(r)
            url = d.get("__next") if isinstance(d, dict) else None
        print(lang, a, len(rows), flush=True)
    with gzip.open(out + ".part", "wt") as fo:
        for r in rows:
            fo.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.rename(out + ".part", out)
print("DONE")
