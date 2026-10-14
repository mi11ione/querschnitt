"""Lead's offline check: selective second order (only when identity top p < tau) vs always 2 orders. No calls."""
import json, os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import APS, load, RAW5, APS_CODES, wilson  # noqa
q1a = {o: r['p'] for o, r in load(f'{RAW5}/q1a.jsonl', 'oid').items()}
q1b = {o: r['p'] for o, r in load(f'{RAW5}/q1b.jsonl', 'oid').items()}
com = sorted(set(q1a) & set(q1b))
def geo(x, y):
    g = [math.exp((math.log(max(a, 1e-12)) + math.log(max(b, 1e-12))) / 2) for a, b in zip(x, y)]; s = sum(g); return [v / s for v in g]
t1 = lambda p: max(range(25), key=lambda i: p[i])
out = {}
for tau in (0.8, 0.9, 0.95, 0.99, 1.01):
    hit = 0; second = 0; t3 = 0
    for o in com:
        pa = q1a[o]
        if max(pa) >= tau: p = pa
        else: p = geo(pa, q1b[o]); second += 1
        tru = APS_CODES.index(APS[o]['chapter_code'])
        hit += t1(p) == tru; t3 += tru in sorted(range(25), key=lambda i: -p[i])[:3]
    out[str(tau)] = dict(n=len(com), second_share=round(second / len(com), 3), top1=round(hit / len(com), 3), ci=wilson(hit, len(com)), top3=round(t3 / len(com), 3))
print(json.dumps(out, indent=1)); json.dump(out, open('selective.json', 'w'), indent=1)
