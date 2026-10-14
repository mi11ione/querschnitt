"""Verification: on 20 of the ideation-1 297 APS items, (1) our D0 identity-order payload (item built by our build_items.make
from S3's Curia DE file + our q1_prompt) equals S5's payload (S5 item from s3 aps.json + s5lib.q1_prompt, assembled as
gw.chat line 63 does) byte for byte, using the bytes pai actually POSTs; (2) p from a fresh pai call reproduces S5 raw q1a
within 1e-3 (max abs diff over 25 chapters)."""
import json, os, random, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s9lib, pai
from s9lib import S3, S5, DATA, RAW
from build_items import make, oracle, texts, opd_titles
sys.path.insert(0, S5)
import s5lib  # stub gw already in sys.modules (s9lib)
urllib.request.urlopen = s9lib._orig

APS = {a['opd_affair_id']: a for a in json.load(open(f'{S3}/data/aps.json'))}
q1a = s9lib.load(f'{S5}/raw/q1a.jsonl')
oids = sorted(APS); random.Random(9).shuffle(oids); oids = oids[:20]
old = {}
for l in open(f'{s9lib.S2D}/aps_gold_sample.jsonl'):
    r = json.loads(l); old[r['opd_affair_id']] = r       # last wins, as S3
O = oracle(); opd = opd_titles(set()); t3 = texts(f'{S3}/data/aps_curia_texts_de.jsonl.gz')
sent = []
_real = urllib.request.urlopen
def spy(req, *a, **k):
    sent.append(req.data); return _real(req, *a, **k)
pai.urllib.request.urlopen = spy
rows = []
for o in oids:
    _, L = make(old[o], O, opd, t3, {})
    mine_item = L['de']
    u, p = s9lib.q1_prompt(mine_item, list(range(25)))
    us, ps = s5lib.q1_prompt(APS[o], list(range(25)))
    s5_payload = dict(model=s5lib.MODEL, messages=[{"role": "user", "content": us}, {"role": "assistant", "content": ps}],
                      max_tokens=1, temperature=0.0, continue_final_message=True, add_generation_prompt=False, logprobs=True,
                      top_logprobs=20)
    n0 = len(sent)
    d, rec = s9lib.m1(u, p, 'bern2-s9-verify', s9lib.CODES)
    mine_bytes = sent[n0] if len(sent) > n0 else None
    pv = s9lib.probs_from_codes(d, list(range(25)))
    diff = max(abs(x - y) for x, y in zip(pv, q1a[o]['p']))
    rows.append(dict(oid=o, bytes_equal=mine_bytes == json.dumps(s5_payload).encode(), sent=mine_bytes is not None,
                     max_abs_diff_p=diff, fp=rec['fp'], model=rec['model'], cached=rec['cached']))
    print(rows[-1], flush=True)
res = dict(n=len(rows), bytes_equal=sum(r['bytes_equal'] for r in rows), within_1e3=sum(r['max_abs_diff_p'] <= 1e-3 for r in rows),
           max_diff=max(r['max_abs_diff_p'] for r in rows), fps=sorted({r['fp'] for r in rows}), rows=rows)
json.dump(res, open(f'{os.path.dirname(DATA)}/verify_s5.json', 'w'), indent=1)
print({k: v for k, v in res.items() if k != 'rows'})
