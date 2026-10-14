"""Offline: does adding Apertus (E3a M1 probs) to BFH scores help? w tuned on dev, scored on test."""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import *
G = lambda c: set(BY[c]['gold'])
P = {c: as_scores(p) for c, p in pvec(load('e3a')).items()}
bfh = {c: {**{t: 0.0 for t in TAGS}, **{int(k): v for k, v in BY[c]['bfh'].items()}} for c in BY}
best = None
for w in (0.0, 0.1, 0.2, 0.3, 0.5, 0.7):
    S = {c: {t: bfh[c][t] + w * P[c][t] for t in TAGS} for c in P}
    for rule, grid in GRID.items():
        for x in grid + [0.35, 0.45, 0.6]:
            d = prf([(G(c), dec(S[c], rule, x)) for c in DEV])['micro']
            if best is None or d > best[0]: best = (d, w, rule, x)
d, w, rule, x = best
S = {c: {t: bfh[c][t] + w * P[c][t] for t in TAGS} for c in P}
pairs = [(G(c), dec(S[c], rule, x)) for c in TEST]
bthr = [(G(c), dec(bfh[c], 'thr', 0.25)) for c in TEST]
res = dict(w=w, rule=f'{rule}@{x}', test={k: round(v, 3) for k, v in prf(pairs).items()}, ci=boot(pairs),
           d_vs_bfh=paired_boot(pairs, bthr), d_macro=paired_boot(pairs, bthr, 'macro'))
print(json.dumps(res)); json.dump(res, open(f'{OUT}/ensemble_bfh.json', 'w'))
