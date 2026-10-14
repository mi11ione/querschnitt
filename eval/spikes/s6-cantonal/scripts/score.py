"""S6 Part B scoring. No LLM calls.
Inputs (s6 folder): ann_A.tsv, ann_B.tsv  (`<id>\\t<chapter code e.g. 1.7.2.>\\t<optional second code>`; '0' = no policy topic),
key.jsonl (opaque id -> affair + Apertus outputs). Usage: python3 -I score.py [ann_A ann_B out.json]  -> prints tables, writes ../score.json
- Cohen kappa A vs B on the first choice (25 categories).
- Strict gold: A and B agree on the first choice. Lenient gold: the A set {1st, 2nd} and the B set overlap; gold = overlap.
- Apertus top-1 (final: L1 -> joint L2 chapter), L1 top-1 and L1 top-3 accuracy vs strict / lenient gold, overall and by
  level, language, text vs title-only, and by the abstention signal.
- Annotator-Apertus agreement (raw + kappa on the first choice) next to annotator-annotator agreement."""
import json, os, sys, math, collections

S6 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALID = {'1.1.1.', '1.1.2.', '1.1.3.', '1.1.4.', '1.1.5.', '1.2.', '1.3.', '1.4.1.', '1.4.2.', '1.4.3.', '1.5.', '1.6.1.',
         '1.6.2.', '1.6.3.', '1.6.4.', '1.7.1.', '1.7.2.', '1.7.3.', '1.7.4.', '1.8.1.', '1.8.2.', '1.8.3.', '2.0.1.', '2.0.2.', '0'}


def norm(c):
    c = (c or '').strip()
    if not c: return None
    if c in ('0', '0.', 'none', 'kein'): return '0'
    if not c.endswith('.'): c += '.'
    if c not in VALID: raise SystemExit(f'invalid code {c!r}')
    return c


def read_ann(path):
    out = {}
    for ln, l in enumerate(open(path, encoding='utf-8')):
        p = l.rstrip('\n').split('\t')
        if not p[0].strip() or p[0].startswith('#'): continue
        first = norm(p[1] if len(p) > 1 else '')
        if first is None: continue   # unannotated row
        second = norm(p[2]) if len(p) > 2 else None
        out[p[0].strip()] = (first, second)
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


def acc(rows, hit):
    k = sum(1 for r in rows if hit(r)); n = len(rows)
    return dict(n=n, k=k, acc=round(k / n, 3) if n else None, ci=wilson(k, n))


def main():
    key = {json.loads(l)['oid']: json.loads(l) for l in open(f'{S6}/key.jsonl')}
    pa, pb = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else (f'{S6}/ann_A.tsv', f'{S6}/ann_B.tsv')
    outp = sys.argv[3] if len(sys.argv) > 3 else f'{S6}/score.json'
    A, B = read_ann(pa), read_ann(pb)
    both = sorted(set(A) & set(B) & set(key))
    print(f'items: key {len(key)}, A {len(A)}, B {len(B)}, both {len(both)}')
    rows = []
    for o in both:
        k = key[o]; sa = {c for c in A[o] if c}; sb = {c for c in B[o] if c}
        rows.append(dict(k, a1=A[o][0], b1=B[o][0], sa=sa, sb=sb, strict=A[o][0] if A[o][0] == B[o][0] else None,
                         lenient=(sa & sb) or None,
                         stratum_conf=('second order run' if k['second_order_run'] else 'first order p>=0.9')))
    out = {}
    # annotator-annotator vs annotator-Apertus
    ag = dict(
        A_vs_B=dict(raw=acc(rows, lambda r: r['a1'] == r['b1']), kappa=kappa([r['a1'] for r in rows], [r['b1'] for r in rows]),
                    any_overlap=acc(rows, lambda r: bool(r['sa'] & r['sb']))),
        A_vs_Apertus=dict(raw=acc(rows, lambda r: r['a1'] == r['apertus_final']),
                          kappa=kappa([r['a1'] for r in rows], [r['apertus_final'] for r in rows]),
                          apertus_in_set=acc(rows, lambda r: r['apertus_final'] in r['sa'])),
        B_vs_Apertus=dict(raw=acc(rows, lambda r: r['b1'] == r['apertus_final']),
                          kappa=kappa([r['b1'] for r in rows], [r['apertus_final'] for r in rows]),
                          apertus_in_set=acc(rows, lambda r: r['apertus_final'] in r['sb'])))
    out['agreement'] = ag
    print('\n## Agreement (first choice)')
    for nm, d in ag.items():
        print(f"{nm:14s} raw {d['raw']['acc']} {d['raw']['ci']}  kappa {d['kappa']}  " +
              ' '.join(f"{x} {d[x]['acc']}" for x in d if x not in ('raw', 'kappa')))
    strict = [r for r in rows if r['strict']]; len_ = [r for r in rows if r['lenient']]
    out['gold_sizes'] = dict(strict=len(strict), lenient=len(len_), n=len(rows))
    print(f"\ngold: strict {len(strict)}/{len(rows)}, lenient {len(len_)}/{len(rows)}")
    metrics = {
        'final_top1': (lambda r: r['apertus_final'] == r['strict'], lambda r: r['apertus_final'] in r['lenient']),
        'l1_top1': (lambda r: r['apertus_l1_top1'] == r['strict'], lambda r: r['apertus_l1_top1'] in r['lenient']),
        'l1_top3': (lambda r: r['strict'] in r['apertus_top3'], lambda r: bool(set(r['apertus_top3']) & r['lenient'])),
    }
    strata = [('all', lambda r: True)] + \
             [(f'level={v}', (lambda v: lambda r: r['level'] == v)(v)) for v in ('cantonal', 'communal')] + \
             [(f'lang={v}', (lambda v: lambda r: r['lang'] == v)(v)) for v in ('de', 'fr', 'it')] + \
             [('text', lambda r: not r['title_only']), ('title-only', lambda r: r['title_only'])] + \
             [('L1 first order p>=0.9', lambda r: not r['second_order_run']), ('L1 second order run', lambda r: r['second_order_run']),
              ('orders disagree', lambda r: r['order_disagree'] is True)]
    out['accuracy'] = {}
    print('\n## Apertus accuracy vs consensus gold (strict | lenient)')
    print(f"{'stratum':24s} " + ' '.join(f"{m:>26s}" for m in metrics))
    for sn, sf in strata:
        rs, rl = [r for r in strict if sf(r)], [r for r in len_ if sf(r)]
        d = {m: dict(strict=acc(rs, fs), lenient=acc(rl, fl)) for m, (fs, fl) in metrics.items()}
        out['accuracy'][sn] = d
        print(f"{sn:24s} " + ' '.join(f"{str(d[m]['strict']['acc']):>6s} (n{d[m]['strict']['n']:>3d}) | {str(d[m]['lenient']['acc']):>6s} (n{d[m]['lenient']['n']:>3d})"
                                      for m in metrics))
    # confusions vs strict gold
    conf = collections.Counter((r['strict'], r['apertus_final']) for r in strict if r['strict'] != r['apertus_final'])
    out['top_confusions_gold_to_apertus'] = [[g, p, n] for (g, p), n in conf.most_common(10)]
    print('\ntop confusions (gold -> Apertus):', out['top_confusions_gold_to_apertus'])
    json.dump(out, open(outp, 'w'), indent=1, default=list)


if __name__ == '__main__':
    main()
