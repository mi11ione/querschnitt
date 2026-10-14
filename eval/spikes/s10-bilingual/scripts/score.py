"""S10 scoring (PREREG S10). No model calls. Reader / kappa / Wilson logic reused from S6 score.py.
Inputs (s10 folder): ann_A.tsv, ann_B.tsv, optional ann_C.tsv (tie-break; only items where A and B first choices differ),
format `<id>\\t<first code>\\t<optional second code>` ('0' = no policy topic); key.jsonl.
Gold = A first choice if A == B, else C first choice (if ann_C has it), else pending (excluded, counted).
Outputs: accuracy of Apertus DE / FR / pooled top-1 vs gold (Wilson), paired bootstrap differences (2,000 resamples, stratified
by canton, seed 20261014); DE-FR top-1 agreement and 'please check' (disagreement) share over all items (no gold needed);
accuracy when the languages agree vs disagree; per canton; by shown language; kappa A-B. Because the sample is 70 per canton,
pooled figures are given unweighted and frame-weighted (canton weights = S10 frame sizes from sample_meta.json).
Usage: python3 -I score.py [--dir D] [--out score.json]     python3 -I score.py --c-template  (writes packet/ann_C_TEMPLATE.tsv)"""
import json, os, sys, math, random, collections

S10 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALID = {'1.1.1.', '1.1.2.', '1.1.3.', '1.1.4.', '1.1.5.', '1.2.', '1.3.', '1.4.1.', '1.4.2.', '1.4.3.', '1.5.', '1.6.1.',
         '1.6.2.', '1.6.3.', '1.6.4.', '1.7.1.', '1.7.2.', '1.7.3.', '1.7.4.', '1.8.1.', '1.8.2.', '1.8.3.', '2.0.1.', '2.0.2.', '0'}
CANTONS = ('BE', 'FR', 'VS')
SYS = ('de', 'fr', 'pooled')
NB, SEED = 2000, 20261014


def norm(c):
    c = (c or '').strip()
    if not c: return None
    if c in ('0', '0.', 'none', 'kein'): return '0'
    if not c.endswith('.'): c += '.'
    if c not in VALID: raise SystemExit(f'invalid code {c!r}')
    return c


def read_ann(path):
    out = {}
    for l in open(path, encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        if not p[0].strip() or p[0].startswith('#'): continue
        first = norm(p[1] if len(p) > 1 else '')
        if first is None: continue
        out[p[0].strip()] = (first, norm(p[2]) if len(p) > 2 else None)
    return out


def wilson(k, n, z=1.96):
    if n == 0: return (float('nan'), float('nan'))
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 3), round(c + h, 3))


def kappa(x, y):
    n = len(x)
    if n == 0: return float('nan')
    po = sum(a == b for a, b in zip(x, y)) / n
    cx, cy = collections.Counter(x), collections.Counter(y)
    pe = sum(cx[k] * cy[k] for k in set(cx) | set(cy)) / (n * n)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else float('nan')


def prop(rows, f):
    k = sum(1 for r in rows if f(r)); n = len(rows)
    return dict(n=n, k=k, p=round(k / n, 3) if n else None, ci=wilson(k, n))


def weighted(rows, f, W):
    """frame-weighted proportion: sum_c W_c * mean_c(f) / sum W over cantons present."""
    num = den = 0.0
    for c in CANTONS:
        rc = [r for r in rows if r['canton'] == c]
        if rc: num += W[c] * sum(1 for r in rc if f(r)) / len(rc); den += W[c]
    return num / den if den else float('nan')


def boot(rows, stats, W, seed=SEED):
    """stratified (by canton) paired bootstrap; stats: name -> (rows -> value). Returns name -> (lo, hi) 95% percentile."""
    rng = random.Random(seed); by = {c: [r for r in rows if r['canton'] == c] for c in CANTONS}
    vals = collections.defaultdict(list)
    for _ in range(NB):
        rs = [x for c in CANTONS for x in (rng.choices(by[c], k=len(by[c])) if by[c] else [])]
        for nm, fn in stats.items(): vals[nm].append(fn(rs))
    out = {}
    for nm, v in vals.items():
        v = sorted(x for x in v if x == x)
        out[nm] = (round(v[int(0.025 * len(v))], 3), round(v[min(len(v) - 1, int(0.975 * len(v)))], 3)) if v else None
    return out


def hit(s): return lambda r: r[f'apertus_{s}'] == r['gold']


def main():
    args = sys.argv[1:]
    D = args[args.index('--dir') + 1] if '--dir' in args else S10
    outp = args[args.index('--out') + 1] if '--out' in args else f'{D}/score.json'
    key = {json.loads(l)['oid']: json.loads(l) for l in open(f'{S10}/key.jsonl')}
    W = {c: json.load(open(f'{S10}/sample_meta.json'))['counts'][f'{c}:eligible'] for c in CANTONS}
    allrows = list(key.values())
    out = {'weights_frame': W}

    # ---- no-gold quantities: DE-FR agreement and 'please check' share (all items)
    ng = dict(agree_all=prop(allrows, lambda r: r['agree']),
              agree_weighted=round(weighted(allrows, lambda r: r['agree'], W), 4),
              please_check_all=prop(allrows, lambda r: not r['agree']),
              please_check_weighted=round(weighted(allrows, lambda r: not r['agree'], W), 4),
              please_check_by_canton={c: prop([r for r in allrows if r['canton'] == c], lambda r: not r['agree']) for c in CANTONS})
    ng['please_check_weighted_ci'] = boot(allrows, {'w': lambda rs: weighted(rs, lambda r: not r['agree'], W)}, W)['w']
    out['no_gold'] = ng
    print('## No gold needed')
    print(f"DE-FR top-1 agreement {ng['agree_all']}   please-check share {ng['please_check_all']}  weighted {ng['please_check_weighted']} {ng['please_check_weighted_ci']}")
    for c, d in ng['please_check_by_canton'].items(): print(f"  please-check {c}: {d}")

    if '--c-template' in args or not (os.path.exists(f'{D}/ann_A.tsv') and os.path.exists(f'{D}/ann_B.tsv')):
        if '--c-template' in args:
            A, B = read_ann(f'{D}/ann_A.tsv'), read_ann(f'{D}/ann_B.tsv')
            dis = sorted(o for o in set(A) & set(B) if A[o][0] != B[o][0])
            cp = f'{D}/packet/ann_C_TEMPLATE.tsv' if os.path.isdir(f'{D}/packet') else f'{D}/ann_C_TEMPLATE.tsv'
            open(cp, 'w').write("".join(f"{o}\t\t\n" for o in dis))
            print(f'ann_C_TEMPLATE.tsv: {len(dis)} ids where A and B first choices differ')
        else:
            print('\n(no ann_A.tsv / ann_B.tsv yet: gold-based metrics TO MEASURE)')
        json.dump(out, open(outp, 'w'), indent=1); return

    A, B = read_ann(f'{D}/ann_A.tsv'), read_ann(f'{D}/ann_B.tsv')
    C = read_ann(f'{D}/ann_C.tsv') if os.path.exists(f'{D}/ann_C.tsv') else {}
    both = sorted(set(A) & set(B) & set(key))
    rows, pending = [], 0
    for o in both:
        a1, b1 = A[o][0], B[o][0]
        gold = a1 if a1 == b1 else (C[o][0] if o in C else None)
        if gold is None: pending += 1
        rows.append(dict(key[o], a1=a1, b1=b1, gold=gold, gold_src='AB' if a1 == b1 else ('C' if gold else 'pending')))
    g = [r for r in rows if r['gold']]
    out['annotators'] = dict(n_A=len(A), n_B=len(B), n_C=len(C), both=len(both), AB_agree=prop(rows, lambda r: r['a1'] == r['b1']),
                             kappa_AB=kappa([r['a1'] for r in rows], [r['b1'] for r in rows]),
                             gold_n=len(g), gold_from_C=sum(r['gold_src'] == 'C' for r in rows), pending=pending)
    print(f"\n## Annotators: {out['annotators']}")

    acc = {s: prop(g, hit(s)) for s in SYS}
    accw = {s: round(weighted(g, hit(s), W), 4) for s in SYS}
    stats = {f'w_{s}': (lambda s: lambda rs: weighted(rs, hit(s), W))(s) for s in SYS}
    for x, y in (('de', 'fr'), ('pooled', 'de'), ('pooled', 'fr')):
        stats[f'diff_{x}-{y}'] = (lambda x, y: lambda rs: (sum(hit(x)(r) for r in rs) - sum(hit(y)(r) for r in rs)) / len(rs))(x, y)
        stats[f'wdiff_{x}-{y}'] = (lambda x, y: lambda rs: weighted(rs, hit(x), W) - weighted(rs, hit(y), W))(x, y)
    bs = boot(g, stats, W)
    out['accuracy'] = {s: dict(acc[s], weighted=accw[s], weighted_ci=bs[f'w_{s}']) for s in SYS}
    out['paired_diff'] = {}
    for x, y in (('de', 'fr'), ('pooled', 'de'), ('pooled', 'fr')):
        d = (acc[x]['k'] - acc[y]['k']) / len(g) if g else float('nan')
        out['paired_diff'][f'{x}-{y}'] = dict(diff=round(d, 3), ci=bs[f'diff_{x}-{y}'], weighted=round(accw[x] - accw[y], 4),
                                             weighted_ci=bs[f'wdiff_{x}-{y}'],
                                             only_x_right=sum(hit(x)(r) and not hit(y)(r) for r in g),
                                             only_y_right=sum(hit(y)(r) and not hit(x)(r) for r in g))
    print('\n## Accuracy vs gold (n, k, acc, Wilson | frame-weighted, stratified bootstrap)')
    for s in SYS: print(f"  {s:7s} {out['accuracy'][s]}")
    print('## Paired differences (stratified bootstrap 2,000)')
    for k, v in out['paired_diff'].items(): print(f'  {k:10s} {v}')

    strata = [('languages agree', lambda r: r['agree']), ('languages disagree (please check)', lambda r: not r['agree'])] + \
             [(f'canton={c}', (lambda c: lambda r: r['canton'] == c)(c)) for c in CANTONS] + \
             [(f'shown={l}', (lambda l: lambda r: r['shown_lang'] == l)(l)) for l in ('de', 'fr')]
    out['strata'] = {}
    print('\n## Strata (acc DE | FR | pooled)')
    for nm, f in strata:
        rs = [r for r in g if f(r)]
        out['strata'][nm] = {s: prop(rs, hit(s)) for s in SYS}
        if nm.startswith('canton='): out['strata'][nm]['de_fr_agree'] = prop([r for r in allrows if f(r)], lambda r: r['agree'])
        print(f"  {nm:36s} n={len(rs):3d}  " + '  '.join(f"{s} {out['strata'][nm][s]['p']} {out['strata'][nm][s]['ci']}" for s in SYS))
    conf = collections.Counter((r['apertus_de'], r['apertus_fr']) for r in g if not r['agree'])
    out['disagree_pairs_de_fr'] = [[a, b, n] for (a, b), n in conf.most_common(10)]
    json.dump(out, open(outp, 'w'), indent=1, default=list)
    print('\nwrote', outp)


if __name__ == '__main__':
    main()
