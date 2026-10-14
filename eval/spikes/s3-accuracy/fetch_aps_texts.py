"""E5 input: fetch Curia DE text fields for the 298 APS-gold affairs from ws.parlament.ch OData (robots 404 = allowed,
per S2). One process, polite.py (UA hackapertus-research/0.1, >=1.2 s gap, fail closed on 429/5xx). 20 IDs per request."""
import gzip, json, os, sys, urllib.parse
sys.path.insert(0, '/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s2-oracles/scripts')
import polite
D2 = '/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s2-oracles/data'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'aps_curia_texts_de.jsonl.gz')
os.makedirs(os.path.dirname(OUT), exist_ok=True)
SEL = "ID,Language,BusinessShortNumber,Title,SubmittedText,ReasonText,Description,InitialSituation"
o2c = {}
for l in gzip.open(f'{D2}/oracle_curia.jsonl.gz', 'rt'):
    r = json.loads(l); o2c[r['opd_affair_id']] = r['curia_id']
aps = [json.loads(l) for l in open(f'{D2}/aps_gold_sample.jsonl')]
ids = sorted({o2c[a['opd_affair_id']] for a in aps if a['opd_affair_id'] in o2c})
print('aps', len(aps), 'curia ids', len(ids), flush=True)
rows = []
for i in range(0, len(ids), 20):
    chunk = ids[i:i + 20]
    f = "Language eq 'DE' and (" + " or ".join(f"ID eq {x}" for x in chunk) + ")"
    url = "https://ws.parlament.ch/odata.svc/Business?$format=json&$select=" + SEL + "&$filter=" + urllib.parse.quote(f)
    while url:
        d = polite.get_json(url, timeout=120)["d"]
        res = d["results"] if isinstance(d, dict) else d
        for r in res:
            r.pop("__metadata", None); rows.append(r)
        url = d.get("__next") if isinstance(d, dict) else None
    print(i, len(rows), flush=True)
with gzip.open(OUT, 'wt') as fo:
    for r in rows: fo.write(json.dumps(r, ensure_ascii=False) + '\n')
print('DONE', len(rows))
