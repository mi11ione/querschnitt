"""Lead's offline check: APS chapter precision at coverage (always-two-orders geo avg), human gold (APS editors via Wayback). No calls."""
import json, os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import APS, load, RAW5, APS_CODES, wilson  # noqa
q1a = {o: r['p'] for o, r in load(f'{RAW5}/q1a.jsonl', 'oid').items()}
q1b = {o: r['p'] for o, r in load(f'{RAW5}/q1b.jsonl', 'oid').items()}
rows = []
for o in set(q1a) & set(q1b):
    g = [math.exp((math.log(max(a, 1e-12)) + math.log(max(b, 1e-12))) / 2) for a, b in zip(q1a[o], q1b[o])]; s = sum(g); p = [v / s for v in g]
    top = max(range(25), key=lambda i: p[i]); agree = max(range(25), key=lambda i: q1a[o][i]) == max(range(25), key=lambda i: q1b[o][i])
    rows.append((p[top], top == APS_CODES.index(APS[o]['chapter_code']), agree))
rows.sort(key=lambda x: -x[0]); n = len(rows); out = {'n': n}
for cov in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5):
    k = round(cov * n); s = rows[:k]; h = sum(x[1] for x in s)
    out[f'cov{cov}'] = dict(k=k, p_min=round(s[-1][0], 3), prec=round(h / k, 3), ci=wilson(h, k))
ag = [x for x in rows if x[2]]; dis = [x for x in rows if not x[2]]
out['orders_agree'] = dict(n=len(ag), acc=round(sum(x[1] for x in ag) / len(ag), 3), ci=wilson(sum(x[1] for x in ag), len(ag)))
out['orders_disagree'] = dict(n=len(dis), acc=round(sum(x[1] for x in dis) / len(dis), 3), ci=wilson(sum(x[1] for x in dis), len(dis)))
print(json.dumps(out, indent=1)); json.dump(out, open('chapter_coverage.json', 'w'), indent=1)

# lead: max-probability threshold at the same coverage as the 'readings agree' lane
k = out['orders_agree']['n']; s = rows[:k]; h = sum(x[1] for x in s)
out['maxprob_same_coverage'] = dict(k=k, prec=round(h / k, 3), ci=wilson(h, k), errors_flagged=sum(1 for x in rows[k:] if not x[1]), errors_total=sum(1 for x in rows if not x[1]))
print(out['maxprob_same_coverage']); json.dump(out, open('chapter_coverage.json', 'w'), indent=1)
