"""Offline hybrids (no calls): M1 single-code probs + generative list + kNN memory prior. Tuned on dev, scored on test."""
import json, sys, os, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import *
R = {ph: load(ph) for ph in ('e1d', 'e2d', 'e3a', 'e3b', 'e1m', 'e3m')}
G = lambda c: set(BY[c]['gold'])
knn = {}
for it in ITEMS:
    nb = it['lang']['de']['nb'][:5]; tot = sum(n['score'] for n in nb) or 1
    sc = {t: 0.0 for t in TAGS}
    for n in nb:
        for t in n['tags']: sc[t] += n['score'] / tot
    knn[it['curia_id']] = sc
def m1p(a, b=None):
    P = avg_geo(R[a], R[b]) if b and R[b] else pvec(R[a])
    return {c: as_scores(p) for c, p in P.items()}
def genw(ph, c):
    labs = R[ph][c]['labels']; return {t: (1.0 if t in labs[:3] else 0.0) for t in TAGS}
out = {}
for m1name, (a, b), gph in [('E1d', ('e1d', None), 'e1m'), ('E1d+E2d avg', ('e1d', 'e2d'), 'e1m'), ('E3a', ('e3a', None), 'e3m'),
                            ('E3 avg', ('e3a', 'e3b'), 'e3m')]:
    if b and not R[b] or len(R[b] if b else R[a]) < 300: continue
    P = m1p(a, b)
    best = None
    for al, be, ga in itertools.product((0.4, 0.6, 0.8, 1.0), (0.0, 0.1, 0.2, 0.3), (0.0, 0.2, 0.4)):
        S = {c: {t: al * P[c][t] + be * genw(gph, c)[t] + ga * knn[c][t] for t in TAGS} for c in P}
        for rule, grid in GRID.items():
            for x in grid:
                d = prf([(G(c), dec(S[c], rule, x)) for c in DEV])['micro']
                if best is None or d > best[0]: best = (d, al, be, ga, rule, x)
    d, al, be, ga, rule, x = best
    S = {c: {t: al * P[c][t] + be * genw(gph, c)[t] + ga * knn[c][t] for t in TAGS} for c in P}
    pairs = [(G(c), dec(S[c], rule, x)) for c in TEST]
    m = prf(pairs)
    # simple union rule: M1 top1 + generative first-3
    up = [(G(c), dec(P[c], 'topk', 1) | set(R[gph][c]['labels'][:3])) for c in TEST]; um = prf(up)
    bthr = [(G(c), dec({**{t: 0.0 for t in TAGS}, **{int(k): v for k, v in BY[c]['bfh'].items()}}, 'thr', 0.25)) for c in TEST]
    out[m1name] = dict(weights=(al, be, ga), rule=f'{rule}@{x}', dev=round(d, 3), test={k: round(v, 3) for k, v in m.items()},
                       ci=boot(pairs), ci_macro=boot(pairs, 'macro'), d_vs_bfh=paired_boot(pairs, bthr), d_macro_vs_bfh=paired_boot(pairs, bthr, 'macro'),
                       avg_pred=round(sum(len(p) for _, p in pairs) / len(pairs), 2),
                       union_top1_gen3={k: round(v, 3) for k, v in um.items()}, union_ci=boot(up))
    print(m1name, json.dumps(out[m1name]))
json.dump(out, open(f'{OUT}/hybrid.json', 'w'), indent=1)

# per-label F1 on test: best hybrid (last design in loop with full data) vs BFH thr 0.25
def perlabel(pairs):
    out = {}
    for t in TAGS:
        tp = sum(t in p and t in g for g, p in pairs); fp = sum(t in p and t not in g for g, p in pairs); fn = sum(t in g and t not in p for g, p in pairs)
        if tp + fn: out[lname(t, 'de')] = (round(2 * tp / (2 * tp + fp + fn), 2) if tp else 0.0, tp + fn)
    return out
name = 'E3 avg' if 'E3 avg' in out else 'E3a'
al, be, ga = out[name]['weights']; rule, x = out[name]['rule'].split('@'); x = float(x)
a, b = ('e3a', 'e3b') if name == 'E3 avg' else ('e3a', None)
P = m1p(a, b)
S = {c: {t: al * P[c][t] + be * genw('e3m', c)[t] + ga * knn[c][t] for t in TAGS} for c in P}
hp = perlabel([(G(c), dec(S[c], rule, x)) for c in TEST])
bp = perlabel([(G(c), dec({**{t: 0.0 for t in TAGS}, **{int(k): v for k, v in BY[c]['bfh'].items()}}, 'thr', 0.25)) for c in TEST])
gap = sorted(((hp[k][0] - bp[k][0], k, hp[k][0], bp[k][0], hp[k][1]) for k in hp), key=lambda z: z[0])
print('per-label (gap, label, apertus, bfh, n_gold):'); [print(g) for g in gap]
json.dump(dict(design=name, gap=gap), open(f'{OUT}/perlabel.json', 'w'), ensure_ascii=False, indent=0)
