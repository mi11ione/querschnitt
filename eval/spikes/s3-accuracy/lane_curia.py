"""Lead's offline check: Curia test top-1 by 'two readings agree/disagree' (E3 memory, identity vs permuted). No calls."""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A
a = A.load('e3a'); b = A.load('e3b')
pa = A.pvec(a); pb = A.pvec(b); avg = A.avg_arith(pa, pb)
ids = [c for c in A.TEST if c in pa and c in pb]
top = lambda p: max(range(len(p)), key=lambda i: p[i])
res = {'agree': [0, 0], 'disagree': [0, 0]}
for c in ids:
    k = 'agree' if top(pa[c]) == top(pb[c]) else 'disagree'
    hit = bool(A.top1_set(avg[c]) & set(A.BY[c]["gold"]))
    res[k][0] += 1; res[k][1] += hit
out = {k: dict(n=v[0], top1_prec=round(v[1] / v[0], 3), ci=A.wilson(v[1], v[0])) for k, v in res.items()}
err = {k: v[0] - v[1] for k, v in res.items()}; out['errors'] = err; out['n'] = len(ids)
print(json.dumps(out, indent=1)); json.dump(out, open('lane_curia.json', 'w'), indent=1)
