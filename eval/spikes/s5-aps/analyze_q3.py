"""Q3 language pooling (no new calls): S3 raw e3a (DE, E3 design, identity order) and e4fra (FR, same design) on the
Curia clean-pool items with real FR title+text. Rules tuned on the 88 FR dev items, reported on the 186 FR test items.
-> q3.json"""
import json, os, sys, math
sys.path.insert(0, '/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s3-accuracy')
import analyze as A3   # S3 metrics / decoding (rules tuned on dev), nothing executed at import
from s3lib import prf, boot, paired_boot, wilson, LABELS, NL, TAGS

OUT = os.path.dirname(os.path.abspath(__file__))
de, deb, fr = A3.load('e3a'), A3.load('e3b'), A3.load('e4fra')
ids = [c for c in fr if c in de]
dev = [c for c in A3.DEV if c in ids]; test = [c for c in A3.TEST if c in ids]
builds = {f'{m}|{f}': n for (m, f), n in A3.builds(de, deb, fr).items()}

def geo(rows_list, c):
    lv = []
    for rs in rows_list:
        p = rs[c]['p']; fl = min(math.log(x) for x in p if x > 0) - 1
        lv.append([math.log(x) if x > 0 else fl for x in p])
    g = [math.exp(sum(v) / len(v)) for v in zip(*lv)]; s = sum(g); return [x / s for x in g]
def arith(rows_list, c):
    return [sum(v) / len(v) for v in zip(*(rs[c]['p'] for rs in rows_list))]

designs = {
    'DE only (e3a, 1 call)': {c: de[c]['p'] for c in ids},
    'FR only (e4fra, 1 call)': {c: fr[c]['p'] for c in ids},
    'DE+FR pooled, arith mean of probs (2 calls)': {c: arith([de, fr], c) for c in ids},
    'DE+FR pooled, sum of log-probs (2 calls)': {c: geo([de, fr], c) for c in ids},
    'ref: DE 2 orders arith (e3a+e3b, 2 calls)': {c: arith([de, deb], c) for c in ids},
    'DE 2 orders + FR, arith (3 calls)': {c: arith([de, deb, fr], c) for c in ids},
}
res = dict(n_dev=len(dev), n_test=len(test), builds=builds, designs={})
pairs_best = {}
for name, P in designs.items():
    ev = A3.evaluate({c: A3.as_scores(p) for c, p in P.items()}, ids_dev=dev, ids_test=test)
    s = A3.summary(ev); k = A3.best_rule(ev)
    pairs_best[name] = ev['_pairs'][k.split('@')[0]]
    res['designs'][name] = dict(rule=s['rule'], micro=s['micro'], ci=s['ci'], macro=s['macro'], ci_macro=s['ci_macro'],
                                P=s['P'], R=s['R'], avg_pred=s['avg_pred'], top1_prec=s['top1_prec'], top3_recall=s['top3_recall'][0],
                                top2=ev['top2']['micro'])
    # top-1 agreement DE vs FR
t1 = lambda p: max(range(NL), key=lambda j: p[j])
res['top1_agree_de_fr_test'] = sum(t1(de[c]['p']) == t1(fr[c]['p']) for c in test)
# paired differences (best dev-tuned rule each) vs DE only, and top-1 precision differences (paired bootstrap)
import random
base = 'DE only (e3a, 1 call)'
res['paired_vs_DE_only'] = {n: dict(d_micro=paired_boot(pairs_best[n], pairs_best[base])) for n in designs if n != base}
def top1_hits(P): return [LABELS[t1(P[c])] in A3.BY[c]['gold'] for c in test]
def paired_prop(a, b, n=2000, seed=3):
    rng = random.Random(seed); m = len(a); d = []
    for _ in range(n):
        idx = [rng.randrange(m) for _ in range(m)]; d.append(sum(a[i] - b[i] for i in idx) / m)
    d.sort(); return (round(d[int(.025 * n)], 3), round(d[int(.975 * n) - 1], 3))
hb = top1_hits(designs[base])
for n in designs:
    if n != base: res['paired_vs_DE_only'][n]['d_top1'] = paired_prop(top1_hits(designs[n]), hb)
hd2 = top1_hits(designs['ref: DE 2 orders arith (e3a+e3b, 2 calls)'])
res['pooled_arith_vs_DE2orders'] = dict(d_top1=paired_prop(top1_hits(designs['DE+FR pooled, arith mean of probs (2 calls)']), hd2),
                                        d_micro=paired_boot(pairs_best['DE+FR pooled, arith mean of probs (2 calls)'],
                                                            pairs_best['ref: DE 2 orders arith (e3a+e3b, 2 calls)']))
json.dump(res, open(f'{OUT}/q3.json', 'w'), ensure_ascii=False, indent=1)
for n, d in res['designs'].items():
    print(f"{n:46s} {d['rule']:13s} micro {d['micro']:.3f} {d['ci']} macro {d['macro']:.3f} top1 {d['top1_prec']} top2 {d['top2']}")
print('agree', res['top1_agree_de_fr_test'], '/', len(test))
print(json.dumps(res['paired_vs_DE_only'], indent=0)); print(res['pooled_arith_vs_DE2orders']); print(builds)
