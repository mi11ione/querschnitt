"""Q4 candidate verification on Curia (dev 100 / test 200). Candidates = top-6 labels of S3 E3 2-order arith average;
p(yes) = mean over the two answer orders (q4a yes=A, q4b yes=B). Thresholds tuned on dev micro-F1. -> q4.json"""
import json, os, sys, math, collections, statistics
sys.path.insert(0, '/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s3-accuracy')
import analyze as A3
from s3lib import prf, boot, paired_boot, wilson, LABELS, NL, TAGS

OUT = os.path.dirname(os.path.abspath(__file__)); RAW5 = os.path.join(OUT, 'raw')
def rows(ph):
    p = f'{RAW5}/{ph}.jsonl'
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
ra, rb = rows('q4a'), rows('q4b')
ya = {(r['cid'], r['tag_id']): r['p_yes'] for r in ra}; yb = {(r['cid'], r['tag_id']): r['p_yes'] for r in rb}
e3a, e3b = A3.load('e3a'), A3.load('e3b')
E3 = {c: A3.as_scores([(x + y) / 2 for x, y in zip(e3a[c]['p'], e3b[c]['p'])]) for c in e3a}
cands = {c: sorted(E3[c], key=E3[c].get, reverse=True)[:6] for c in E3}
complete = lambda c, Y: all((c, t) in Y for t in cands[c])
DEV = [c for c in A3.DEV if complete(c, ya) and complete(c, yb)]
TEST = [c for c in A3.TEST if complete(c, ya) and complete(c, yb)]
G = lambda c: set(A3.BY[c]['gold'])
def py2(c, t): return (ya[(c, t)] + yb[(c, t)]) / 2

TAUS = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98, 0.99, 0.995, 0.998, 0.999]
def dec_v1(c, tau, py=py2): return {t for t in cands[c] if py(c, t) >= tau}
def dec_v2(c, tau, py=py2): return {cands[c][0]} | dec_v1(c, tau, py)
def dec_v3(c, x, py=py2):
    lam, tau = x; return {t for t in cands[c] if lam * py(c, t) + (1 - lam) * E3[c][t] >= tau} or {cands[c][0]}
def tune(fn, grid):
    best = max(grid, key=lambda x: prf([(G(c), fn(c, x)) for c in DEV])['micro'])
    pairs = [(G(c), fn(c, best)) for c in TEST]; m = prf(pairs)
    return dict(param=best, micro=round(m['micro'], 3), ci=boot(pairs), macro=round(m['macro'], 3), ci_macro=boot(pairs, 'macro'),
                P=round(m['P'], 3), R=round(m['R'], 3), avg_pred=round(sum(len(p) for _, p in pairs) / len(pairs), 2)), pairs

Q = dict(n_dev=len(DEV), n_test=len(TEST))
ng = sum(len(G(c)) for c in TEST)
Q['cand_recall_top6_test'] = round(sum(len(set(cands[c]) & G(c)) for c in TEST) / ng, 3)
res, P = {}, {}
res['V1 verified (p_yes>=tau), 2 orders'], P['v1'] = tune(dec_v1, TAUS)
res['V2 E3 top-1 + verified, 2 orders'], P['v2'] = tune(dec_v2, TAUS)
res['V3 fused lam*p_yes+(1-lam)*p_E3, 2 orders'], P['v3'] = tune(dec_v3, [(l, t) for l in (0.25, 0.5, 0.75, 0.9) for t in (0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)])
V3GRID = [(l, t) for l in (0.25, 0.5, 0.75, 0.9) for t in (0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)]
res['V3 fused, single order (yes=A only)'], P['v3a'] = tune(lambda c, x: dec_v3(c, x, py=lambda c, t: ya[(c, t)]), V3GRID)
res['V2 single order (yes=A only)'], P['v2a'] = tune(lambda c, x: dec_v2(c, x, py=lambda c, t: ya[(c, t)]), TAUS)
res['V2 single order (yes=B only)'], P['v2b'] = tune(lambda c, x: dec_v2(c, x, py=lambda c, t: yb[(c, t)]), TAUS)
# references on the same test items
ev = A3.evaluate(E3, ids_dev=DEV, ids_test=TEST); k = A3.best_rule(ev)
P['e3'] = ev['_pairs'][k.split('@')[0]]; m = ev[k]
res[f'ref S3 E3 2-order avg ({k})'] = dict(micro=m['micro'], ci=m['ci_micro'], macro=m['macro'], ci_macro=m['ci_macro'], P=m['P'], R=m['R'], avg_pred=m['avg_pred'])
bfh = {it['curia_id']: {int(k): v for k, v in it['bfh'].items()} for it in A3.ITEMS}
P['bfh'] = [(G(c), A3.dec(bfh[c], 'thr', 0.25)) for c in TEST]; m = prf(P['bfh'])
res['ref BFH Omikuji thr 0.25'] = dict(micro=round(m['micro'], 3), ci=boot(P['bfh']), macro=round(m['macro'], 3), ci_macro=boot(P['bfh'], 'macro'),
                                       P=round(m['P'], 3), R=round(m['R'], 3), avg_pred=round(sum(len(p) for _, p in P['bfh']) / len(P['bfh']), 2))
Q['results'] = res
Q['paired'] = {f'{a} vs {b}': dict(d_micro=paired_boot(P[a], P[b]), d_macro=paired_boot(P[a], P[b], 'macro'))
               for a in ('v1', 'v2', 'v3') for b in ('e3', 'bfh')}
# order agreement and calibration of p_yes by rank
keys = [k for k in ya if k in yb]
Q['order_agree@0.5'] = round(sum((ya[k] >= .5) == (yb[k] >= .5) for k in keys) / len(keys), 3)
byrank = collections.defaultdict(lambda: [0, 0, 0.0])
for c in TEST:
    for r_, t in enumerate(cands[c]):
        b = byrank[r_]; b[0] += 1; b[1] += t in G(c); b[2] += py2(c, t)
Q['by_rank_test'] = {r_: dict(n=b[0], gold_rate=round(b[1] / b[0], 3), mean_pyes=round(b[2] / b[0], 3)) for r_, b in sorted(byrank.items())}
allr = ra + rb
Q['builds'] = dict(collections.Counter(f"{r['rec']['model']}|{r['rec']['fp']}" for r in allr))
Q['calls'] = len(allr); Q['pt_per_call'] = round(statistics.mean(r['rec']['pt'] for r in allr), 1)
Q['usd_total'] = round(sum(r['rec']['usd'] for r in allr), 4)
Q['pt_per_affair_verif_2orders'] = round(12 * Q['pt_per_call'], 0)
json.dump(Q, open(f'{OUT}/q4.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(Q, ensure_ascii=False, indent=1))
