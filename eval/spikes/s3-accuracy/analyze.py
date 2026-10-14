"""S3 analysis -> analysis.json + printed tables. Usage: python3 -I analyze.py"""
import json, os, sys, math, collections, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s3lib import *  # noqa
import s1lib

ITEMS = json.load(open(f'{DATA}/curia300.json')); BY = {it['curia_id']: it for it in ITEMS}
DEV = [it['curia_id'] for it in ITEMS if it['split'] == 'dev']
TEST = [it['curia_id'] for it in ITEMS if it['split'] == 'test']
A = {}
NONE_IDX = NL - 1
TIDX = {t: i for i, t in enumerate(LABELS)}

def load(phase, keyf='cid'):
    p = f'{RAW}/{phase}.jsonl'
    if not os.path.exists(p): return {}
    return {json.loads(l)[keyf]: json.loads(l) for l in open(p)}

def builds(*rowsets):
    c = collections.Counter()
    for rs in rowsets:
        for r in rs.values(): c[(r['rec']['model'], r['rec']['fp'])] += 1
    return c

# ------------------------------------------------------------------ decoding
def as_scores(p):  # p: label-index prob vector -> {tag: prob} (none excluded)
    return {LABELS[i]: p[i] for i in range(NL - 1)}
def top1_set(p):
    i = max(range(NL), key=lambda j: p[j]); return set() if i == NONE_IDX else {LABELS[i]}
def dec(scores, rule, x):
    s = sorted(scores, key=scores.get, reverse=True)
    if rule == 'thr': return {t for t in s if scores[t] >= x}
    if rule == 'top1+thr': return {s[0]} | {t for t in s if scores[t] >= x}
    if rule == 'topk': return set(s[:x])
    if rule == 'rel': return {t for t in s if scores[t] >= x * scores[s[0]]}
    raise ValueError(rule)
GRID = {'thr': [0.005, 0.01, 0.02, 0.03, 0.05, 0.075, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5],
        'top1+thr': [0.005, 0.01, 0.02, 0.03, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5],
        'rel': [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5]}

def evaluate(S, ids_dev=None, ids_test=None, name=''):
    """S: {cid: {tag: score}} -> metrics on test with rules tuned on dev."""
    ids_dev = ids_dev or [c for c in DEV if c in S]; ids_test = ids_test or [c for c in TEST if c in S]
    G = lambda c: set(BY[c]['gold'])
    out = dict(n_dev=len(ids_dev), n_test=len(ids_test))
    for rule, grid in GRID.items():
        best = max(grid, key=lambda x: prf([(G(c), dec(S[c], rule, x)) for c in ids_dev])['micro'])
        pairs = [(G(c), dec(S[c], rule, best)) for c in ids_test]
        m = prf(pairs); out[f'{rule}@{best}'] = dict({k: round(v, 3) for k, v in m.items()}, ci_micro=boot(pairs),
                                                     ci_macro=boot(pairs, 'macro'), avg_pred=round(sum(len(p) for _, p in pairs) / len(pairs), 2))
        out.setdefault('_pairs', {})[rule] = pairs
    for k in (1, 2, 3):
        pairs = [(G(c), dec(S[c], 'topk', k)) for c in ids_test]
        out[f'top{k}'] = {kk: round(v, 3) for kk, v in prf(pairs).items()}
    hits = sum(bool(dec(S[c], 'topk', 1) & G(c)) for c in ids_test)
    out['top1_precision'] = (round(hits / len(ids_test), 3), wilson(hits, len(ids_test)))
    r3 = sum(len(dec(S[c], 'topk', 3) & G(c)) for c in ids_test); ng = sum(len(G(c)) for c in ids_test)
    out['top3_recall'] = (round(r3 / ng, 3), wilson(r3, ng))
    any3 = sum(bool(dec(S[c], 'topk', 3) & G(c)) for c in ids_test)
    out['top3_any_hit'] = round(any3 / len(ids_test), 3)
    return out

def best_rule(ev):
    ks = [k for k in ev if '@' in k]; return max(ks, key=lambda k: ev[k]['micro'])

def summary(ev):
    k = best_rule(ev); m = ev[k]
    return dict(rule=k, micro=m['micro'], ci=m['ci_micro'], macro=m['macro'], ci_macro=m['ci_macro'], P=m['P'], R=m['R'],
                avg_pred=m['avg_pred'], top1_prec=ev['top1_precision'], top3_recall=ev['top3_recall'], n=ev['n_test'],
                thr=(ev[[x for x in ev if x.startswith('thr@')][0]]['micro'], [x for x in ev if x.startswith('thr@')][0]))

def pvec(rows):
    return {c: r['p'] for c, r in rows.items()}
def avg_arith(pa, pb):
    return {c: [(x + y) / 2 for x, y in zip(pa[c], pb[c])] for c in pa if c in pb}
def avg_geo(ra, rb):
    """mean of per-label log-probs (censored codes = min observed logprob - 1), renormalised"""
    out = {}
    for c in ra:
        if c not in rb: continue
        lv = []
        for r in (ra[c], rb[c]):
            fl = min(math.log(x) for x in r['p'] if x > 0) - 1
            lv.append([math.log(x) if x > 0 else fl for x in r['p']])
        g = [math.exp((a + b) / 2) for a, b in zip(*lv)]; s = sum(g); out[c] = [x / s for x in g]
    return out

def agreement(pa, pb, ids):
    ids = [c for c in ids if c in pa and c in pb]
    t = lambda p: max(range(NL), key=lambda j: p[j])
    agree = sum(t(pa[c]) == t(pb[c]) for c in ids)
    hi = [c for c in ids if max(pa[c]) >= 0.9]
    ah = sum(t(pa[c]) == t(pb[c]) for c in hi)
    return dict(n=len(ids), agree=agree, rate=round(agree / len(ids), 3), ci=wilson(agree, len(ids)),
                n_hi=len(hi), agree_hi=ah, rate_hi=round(ah / len(hi), 3) if hi else None, ci_hi=wilson(ah, len(hi)))

def costs(*rowsets):
    pts = [r['rec']['pt'] for rs in rowsets for r in rs.values()]; usd = sum(r['rec']['usd'] for rs in rowsets for r in rs.values())
    n = len(rowsets[0])
    return dict(calls=len(pts), mean_pt_per_call=round(statistics.mean(pts), 1),
                pt_per_affair=round(sum(pts) / n, 1), usd_per_1000=round(1000 * usd / n, 4))

def coverage_curve(P, ids):
    t = lambda p: max(range(NL), key=lambda j: p[j])
    rows = sorted(((max(P[c]), LABELS[t(P[c])] in BY[c]['gold']) for c in ids if c in P), reverse=True)
    n = len(rows); out = []
    for cov in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5):
        k = max(1, round(cov * n)); h = sum(x[1] for x in rows[:k])
        out.append(dict(coverage=cov, n=k, p_min=round(rows[k - 1][0], 4), precision=round(h / k, 3), ci=wilson(h, k)))
    return out

def strip(ev):
    return {k: v for k, v in ev.items() if k != '_pairs'}

if __name__ == '__main__':
    R = {ph: load(ph) for ph in ('e1n', 'e1d', 'e2n', 'e2d', 'e3a', 'e3b')}
    A['builds_e1_e3'] = {f'{m}|{f}': n for (m, f), n in builds(*[r for r in R.values() if r]).items()}
    D = {}
    if R['e1n']: D['E1 names (id)'] = pvec(R['e1n'])
    if R['e1d']: D['E1 names+desc (id)'] = pvec(R['e1d'])
    if R['e2n']: D['E2 names (perm B)'] = pvec(R['e2n'])
    if R['e2d']: D['E2 names+desc (perm B)'] = pvec(R['e2d'])
    if R['e1n'] and R['e2n']:
        D['E2 names avg-geo'] = avg_geo(R['e1n'], R['e2n']); D['E2 names avg-arith'] = avg_arith(pvec(R['e1n']), pvec(R['e2n']))
        A['E2_agree_names'] = agreement(pvec(R['e1n']), pvec(R['e2n']), DEV + TEST)
    if R['e1d'] and R['e2d']:
        D['E2 desc avg-geo'] = avg_geo(R['e1d'], R['e2d']); D['E2 desc avg-arith'] = avg_arith(pvec(R['e1d']), pvec(R['e2d']))
        A['E2_agree_desc'] = agreement(pvec(R['e1d']), pvec(R['e2d']), DEV + TEST)
    if R['e3a']: D['E3 memory (id)'] = pvec(R['e3a'])
    if R['e3b']: D['E3 memory (perm B)'] = pvec(R['e3b'])
    if R['e3a'] and R['e3b']:
        D['E3 memory avg-geo'] = avg_geo(R['e3a'], R['e3b']); D['E3 memory avg-arith'] = avg_arith(pvec(R['e3a']), pvec(R['e3b']))
        A['E3_agree'] = agreement(pvec(R['e3a']), pvec(R['e3b']), DEV + TEST)
    EV = {}
    D = {k: v for k, v in D.items() if sum(c in v for c in TEST) >= 20 and sum(c in v for c in DEV) >= 20}
    for name, P in D.items():
        EV[name] = evaluate({c: as_scores(p) for c, p in P.items()})
    # BFH on identical items
    bfh = {it['curia_id']: {int(k): v for k, v in it['bfh'].items()} for it in ITEMS}
    for t in TAGS:
        for c in bfh: bfh[c].setdefault(t, 0.0)
    EV['BFH Omikuji (own scores)'] = evaluate(bfh)
    pairs = [(set(BY[c]['gold']), dec(bfh[c], 'thr', 0.25)) for c in TEST]
    m = prf(pairs); A['BFH_thr0.25_test'] = dict({k: round(v, 3) for k, v in m.items()}, ci_micro=boot(pairs), ci_macro=boot(pairs, 'macro'))
    # kNN memory-only baseline (no LLM)
    for lang in ('de',):
        knn = {}
        for it in ITEMS:
            nb = it['lang'][lang]['nb'][:5]; tot = sum(n['score'] for n in nb) or 1
            sc = {t: 0.0 for t in TAGS}
            for n in nb:
                for t in n['tags']: sc[t] += n['score'] / tot
            knn[it['curia_id']] = sc
        EV[f'kNN-5 memory only ({lang}, no LLM)'] = evaluate(knn)
    # late fusion with the kNN memory prior (no extra tokens): alpha*LLM + (1-alpha)*kNN, alpha and rule tuned on dev
    knn = {it['curia_id']: None for it in ITEMS}
    for it in ITEMS:
        nb = it['lang']['de']['nb'][:5]; tot = sum(n['score'] for n in nb) or 1
        sc = {t: 0.0 for t in TAGS}
        for n in nb:
            for t in n['tags']: sc[t] += n['score'] / tot
        knn[it['curia_id']] = sc
    A['fusion_alpha'] = {}
    for name in [k for k in list(D) if 'avg-geo' in k or k.startswith('E1 names+desc')]:
        best = None
        for al in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
            S = {c: {t: al * as_scores(p)[t] + (1 - al) * knn[c][t] for t in TAGS} for c, p in D[name].items()}
            devm = max(prf([(set(BY[c]['gold']), dec(S[c], r, x)) for c in DEV if c in S])['micro'] for r, g in GRID.items() for x in g)
            if best is None or devm > best[0]: best = (devm, al, S)
        A['fusion_alpha'][name] = best[1]
        EV[f'{name} + kNN fusion (a={best[1]})'] = evaluate(best[2])
    # multi-label generative variants: predicted set = generated code list (optionally truncated to first k, k tuned on dev)
    A['gen'] = {}
    for ph in ('e1m', 'e3m'):
        rows = load(ph)
        if sum(c in rows for c in TEST) < 20: continue
        G = lambda c: set(BY[c]['gold'])
        kbest = max((1, 2, 3, 4), key=lambda k: prf([(G(c), set(rows[c]['labels'][:k])) for c in DEV if c in rows])['micro'])
        res = {}
        for k in (1, 2, 3, 4, kbest):
            pairs = [(G(c), set(rows[c]['labels'][:k])) for c in TEST if c in rows]
            m = prf(pairs); res[f'first{k}'] = dict({kk: round(v, 3) for kk, v in m.items()}, ci_micro=boot(pairs), ci_macro=boot(pairs, 'macro'))
        res['k_dev'] = kbest
        ts = [c for c in TEST if c in rows]
        h = sum(bool(rows[c]['labels'][:1]) and rows[c]['labels'][0] in G(c) for c in ts)
        res['top1_precision'] = (round(h / len(ts), 3), wilson(h, len(ts)))
        res['mean_len'] = round(sum(len(rows[c]['labels']) for c in ts) / len(ts), 2)
        res['len_dist'] = dict(collections.Counter(len(rows[c]['labels']) for c in ts))
        res['n'] = len(ts); res['unparsed'] = sum(not r['labels'] for r in rows.values())
        res['pairs_full'] = None
        A['gen'][ph] = res
        if len(ts) == len(TEST):
            pr = [(G(c), set(rows[c]['labels'])) for c in TEST]
            bthr = [(G(c), dec(bfh[c], 'thr', 0.25)) for c in TEST]
            res['d_micro_vs_BFH025'] = paired_boot(pr, bthr); res['d_macro_vs_BFH025'] = paired_boot(pr, bthr, 'macro')
        res.pop('pairs_full')
        print(ph, json.dumps(res))
    A['E_summary'] = {k: summary(v) for k, v in EV.items()}
    # paired differences vs BFH (best rule of each, test)
    bp = EV['BFH Omikuji (own scores)']['_pairs'][best_rule(EV['BFH Omikuji (own scores)']).split('@')[0]]
    bthr = [(set(BY[c]['gold']), dec(bfh[c], 'thr', 0.25)) for c in TEST]
    A['paired_vs_BFH'] = {}
    for k, ev in EV.items():
        if k.startswith('BFH'): continue
        pr = ev['_pairs'][best_rule(ev).split('@')[0]]
        if len(pr) == len(bthr):
            A['paired_vs_BFH'][k] = dict(d_micro_vs_thr025=paired_boot(pr, bthr), d_macro_vs_thr025=paired_boot(pr, bthr, 'macro'))
    # costs
    A['costs'] = {ph: costs(r) for ph, r in R.items() if r}
    # E7 coverage-precision (test)
    A['E7'] = {k: coverage_curve(D[k], TEST) for k in D}
    A['E7']['BFH'] = None
    # BFH coverage curve on its own top-1 score
    rows = sorted(((max(bfh[c].values()), max(bfh[c], key=bfh[c].get) in BY[c]['gold']) for c in TEST), reverse=True)
    out = []
    for cov in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5):
        k = round(cov * len(rows)); h = sum(x[1] for x in rows[:k])
        out.append(dict(coverage=cov, n=k, p_min=round(rows[k - 1][0], 4), precision=round(h / k, 3), ci=wilson(h, k)))
    A['E7']['BFH'] = out
    A['EV'] = {k: strip(v) for k, v in EV.items()}
    json.dump(A, open(f'{OUT}/analysis.json', 'w'), ensure_ascii=False, indent=1)
    for k, v in A['E_summary'].items():
        print(f"{k:34s} {v['rule']:14s} microF1 {v['micro']:.3f} {v['ci']} macro {v['macro']:.3f} P {v['P']:.3f} R {v['R']:.3f} "
              f"k̄ {v['avg_pred']} top1P {v['top1_prec'][0]} top3R {v['top3_recall'][0]} thr {v['thr']}")
    print('BFH thr0.25 test', A['BFH_thr0.25_test'])
    for k in ('E2_agree_names', 'E2_agree_desc', 'E3_agree'):
        if k in A: print(k, A[k])
    print(json.dumps(A['paired_vs_BFH'], indent=0)[:3000])
    print(json.dumps(A['costs']))
    print('builds', A['builds_e1_e3'])
