"""Step-1 check: (i) prompt bytes for the 30 DVS items vs S3 (S3 input = dvs.json fields), (ii) fresh uncached e6a call vs S3 raw e6a."""
import sys, json, math, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/Users/mi11ion/Desktop/hackapertus/bern/ideation2/lib')
from common import *
import pai
I = {x['id']: x for x in json.load(open(f'{HERE}/items_cache.json'))}
D = json.load(open(f'{S3}/data/dvs.json'))['pos']
s3raw = {json.loads(l)['oid']: json.loads(l) for l in open(f'{S3}/raw/e6a.jsonl')}
rows = []
for x in D:
    s3u, s3p = build_prompt(x['title_lang'], x['title'], x['title_long'], 'a')
    it = I[x['opd_affair_id']]
    u, p = build_prompt(it['lang'], it['title'], it['title_long'], 'a')
    same = (u.encode() == s3u.encode() and p == s3p)
    ch, meta = pai.chat([{"role": "user", "content": u}, {"role": "assistant", "content": p}], model=MODEL, max_tokens=1,
                        tag='bern2-s8-check', tag_cap_usd=0.05, nocache=True, logprobs=True, top_logprobs=20,
                        continue_final_message=True, add_generation_prompt=False)
    d = pai.read_codes(ch, ["A", "B"]); pa, pb = math.exp(d.get('A', -50)), math.exp(d.get('B', -50))
    py = pa / (pa + pb); ref = s3raw[x['opd_affair_id']]['p_yes']
    rows.append(dict(oid=x['opd_affair_id'], in_window=it['in_window'], prompt_equal=same, lang=it['lang'], s3_lang=x['title_lang'],
                     p_yes=py, s3_p_yes=ref, absdiff=abs(py - ref), fp=meta['resp'].get('system_fingerprint'), served=meta['resp'].get('model')))
json.dump(rows, open(f'{HERE}/check_dvs.json', 'w'), indent=1)
eq = [r for r in rows if r['prompt_equal']]
print('prompt bytes equal', len(eq), '/', len(rows))
print('max |dp| on equal', max(r['absdiff'] for r in eq), 'n within 1e-3', sum(r['absdiff'] <= 1e-3 for r in eq))
print('max |dp| all', max(r['absdiff'] for r in rows), 'fps', {r['fp'] for r in rows}, {r['served'] for r in rows})
for r in rows:
    if not r['prompt_equal'] or r['absdiff'] > 1e-3: print(r)
