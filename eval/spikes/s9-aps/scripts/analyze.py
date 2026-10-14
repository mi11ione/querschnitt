"""S9 analysis -> results.json + results.md (re-runnable at any n). No network, no model calls.
Chapter vectors (25 = 24 APS chapters + none):
  D0 = geometric mean of d0a (identity) and d0b (S1 permutation)  [pre-registered]
  D1 = chapter of argmax_sub p_joint(sub) * P_arith(chapter) over the shown subtopics (none excluded), P_arith = arithmetic mean
       of d0a, d0b (S5 rule, beta = 1); chapter ranking for top-3: shown chapters by their best product score, then the other
       chapters in D0-arithmetic order; confidence = share of the normalised product mass on the chosen chapter
  D2 = mean of probabilities of d0a, d0b, d2fr                    [pre-registered: "averaged (mean of probabilities)"]
  D3 = geometric mean of d3m and d0b (same combiner as D0, identity call replaced by the memory call)
Intervals: Wilson 95% for proportions, paired bootstrap (2,000 resamples, percentile) for differences."""
import collections, json, math, os, random, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s9lib import DATA, RAW, HERE, SUBS, CH_DE, BUILD, geo2, load, s1lib, pai
wilson = lambda k, n: list(s1lib.wilson(k, n))
R = {'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
items = {it['oid']: it for it in json.load(open(f'{DATA}/items.json'))}
raw = {ph: load(f'{RAW}/{ph}.jsonl') for ph in ('d0a', 'd0b', 'd1', 'd2fr', 'd3m')}
fps = collections.Counter((ph, r['rec']['model'], r['rec']['fp']) for ph, rr in raw.items() for r in rr.values())
R['builds'] = [dict(phase=a, model=b, fp=c, n=n) for (a, b, c), n in sorted(fps.items())]
R['offbuild_rows'] = sum(1 for _ in open(f'{RAW}/offbuild.jsonl')) if os.path.exists(f'{RAW}/offbuild.jsonl') else 0
R['spend_usd'] = {k: round(v, 4) for k, v in pai._read_ledger()[1].items() if k.startswith('bern2-s9-')}
R['spend_total_usd'] = round(sum(R['spend_usd'].values()), 4)
R['min_mass'] = {ph: (min(r['mass'] for r in rr.values()) if rr else None) for ph, rr in raw.items()}
R['pt_mean'] = {ph: (round(sum(r['rec']['pt'] for r in rr.values()) / len(rr), 1) if rr else None) for ph, rr in raw.items()}

def order(p): return sorted(range(len(p)), key=lambda i: -p[i])

D0, PA = {}, {}
for o in items:
    if o in raw['d0a'] and o in raw['d0b']:
        a, b = raw['d0a'][o]['p'], raw['d0b'][o]['p']
        D0[o] = geo2(a, b); PA[o] = [(x + y) / 2 for x, y in zip(a, b)]

def joint_scores(o, prior):
    r = raw['d1'][o]; sc = {}
    for i, (c, s) in enumerate(r['opts']):
        sc[(c, s)] = r['p'][i] * prior[c]
    return sc

def d1_like(o, prior, rank_rest):
    sc = joint_scores(o, prior); tot = sum(sc.values()) or 1
    best = max(sc, key=sc.get)
    chbest = {}
    for (c, s), v in sc.items(): chbest[c] = max(chbest.get(c, 0), v)
    rk = sorted(chbest, key=lambda c: -chbest[c]); rk += [c for c in order(rank_rest) if c not in rk]
    conf = sum(v for (c, s), v in sc.items() if c == best[0]) / tot
    subs_rank = sorted(sc, key=lambda k: -sc[k])
    return dict(ch=best[0], rank=rk, conf=conf, sub=best, subs=subs_rank)

D1 = {o: d1_like(o, PA[o], PA[o]) for o in D0 if o in raw['d1']}
D2 = {o: [(x + y + z) / 3 for x, y, z in zip(raw['d0a'][o]['p'], raw['d0b'][o]['p'], raw['d2fr'][o]['p'])]
      for o in D0 if o in raw['d2fr']}
D3 = {o: geo2(raw['d3m'][o]['p'], raw['d0b'][o]['p']) for o in D0 if o in raw['d3m']}

def pred(design, o):
    """-> (top1, rank list, confidence)"""
    if design == 'D1':
        x = D1[o]; return x['ch'], x['rank'], x['conf']
    p = {'D0': D0, 'D2': D2, 'D3': D3}[design][o]; rk = order(p); return rk[0], rk, p[rk[0]]

AV = {'D0': set(D0), 'D1': set(D1), 'D2': set(D2), 'D3': set(D3)}
R['n'] = {k: len(v) for k, v in AV.items()}
R['n_items_built'] = len(items)

def paired(a, b, n=2000, seed=9):
    rng = random.Random(seed); m = len(a); d = []
    for _ in range(n):
        idx = [rng.randrange(m) for _ in range(m)]; d.append(sum(a[i] - b[i] for i in idx) / m)
    d.sort(); return [round(d[int(.025 * n)], 4), round(d[int(.975 * n) - 1], 4)]

def acc_block(design, ids):
    ids = sorted(ids); n = len(ids)
    if not n: return dict(n=0)
    t1 = sum(pred(design, o)[0] == items[o]['chapter'] for o in ids)
    t3 = sum(items[o]['chapter'] in pred(design, o)[1][:3] for o in ids)
    return dict(n=n, top1=round(t1 / n, 4), top1_k=t1, top1_ci=wilson(t1, n), top3=round(t3 / n, 4), top3_k=t3, top3_ci=wilson(t3, n))

# ---------------- primary: chapter top-1 / top-3 per design, paired vs D0 on common items
R['chapter'] = {}
for d in ('D0', 'D1', 'D2', 'D3'):
    common = sorted(AV[d] & AV['D0'])
    blk = acc_block(d, common)
    if d != 'D0' and common:
        h = [pred(d, o)[0] == items[o]['chapter'] for o in common]; h0 = [pred('D0', o)[0] == items[o]['chapter'] for o in common]
        g = [items[o]['chapter'] in pred(d, o)[1][:3] for o in common]; g0 = [items[o]['chapter'] in pred('D0', o)[1][:3] for o in common]
        blk.update(D0_top1_same_items=round(sum(h0) / len(common), 4), diff_top1=round((sum(h) - sum(h0)) / len(common), 4),
                   diff_top1_ci=paired(h, h0), diff_top3=round((sum(g) - sum(g0)) / len(common), 4), diff_top3_ci=paired(g, g0),
                   flips=dict(gain=sum(a and not b for a, b in zip(h, h0)), loss=sum(b and not a for a, b in zip(h, h0))))
        lo = blk['diff_top1_ci'][0]; blk['wins'] = lo > 0
    R['chapter'][d] = blk
# all-design common set
allc = sorted(AV['D0'] & AV['D1'] & AV['D2'] & AV['D3'])
R['chapter_all_designs_common'] = {d: acc_block(d, allc) for d in ('D0', 'D1', 'D2', 'D3')}
winners = [d for d in ('D1', 'D2', 'D3') if R['chapter'][d].get('wins')]
R['winners'] = winners
best = max(('D1', 'D2', 'D3'), key=lambda d: (R['chapter'][d].get('diff_top1', -9) if R['chapter'][d].get('n') else -9))
R['best_design'] = best

# ---------------- baselines on D0 items
ids0 = sorted(AV['D0'])
gold_c = collections.Counter(items[o]['chapter'] for o in ids0)
maj = gold_c.most_common(1)[0][0] if ids0 else None
majorder = [c for c, _ in gold_c.most_common()] + [c for c in range(24) if c not in gold_c]
KW = json.load(open(f'{DATA}/keywords_frozen.json'))
kw = {int(c): v['keywords'] for c, v in KW['chapters'].items()}
def kw_pred(o):
    it = items[o]['de']; txt = ' '.join((it['title'], it['title_long'], it['text'])).lower()
    sc = {c: sum(w in txt for w in kw[c]) for c in range(24)}
    m = max(sc.values()); tied = [c for c in range(24) if sc[c] == m]
    return min(tied, key=majorder.index), m
kmp = {o: kw_pred(o) for o in ids0}
k_maj = sum(items[o]['chapter'] == maj for o in ids0); k_kw = sum(kmp[o][0] == items[o]['chapter'] for o in ids0)
n0 = len(ids0)
R['baselines'] = dict(n=n0, majority_chapter=CH_DE[maj] if maj is not None else None,
                      majority_top1=round(k_maj / n0, 4) if n0 else None, majority_ci=wilson(k_maj, n0),
                      keyword_top1=round(k_kw / n0, 4) if n0 else None, keyword_ci=wilson(k_kw, n0),
                      keyword_zero_match=sum(kmp[o][1] == 0 for o in ids0),
                      keyword_file_sha256=open(f'{DATA}/keywords_frozen.json.sha256').read().strip(), keyword_frozen_utc=KW['frozen_utc'])

# ---------------- strata
def strata(design, ids):
    out = {}
    for name, f in (('pre-2010', lambda it: it['period'] == 'pre-2010'), ('2010-19', lambda it: it['period'] == '2010-19'),
                    ('2020+', lambda it: it['period'] == '2020+'),
                    ('join strong', lambda it: it['join_quality'] != 'slug_only'), ('join slug_only', lambda it: it['join_quality'] == 'slug_only')):
        out[name] = acc_block(design, [o for o in ids if f(items[o])])
    return out
R['strata'] = {d: strata(d, sorted(AV[d] & AV['D0'])) for d in ('D0', best)}

# ---------------- subtopic end to end (items with a main subtopic among the 190 and a d1 row)
sub_ids = sorted(o for o in AV['D1'] if items[o]['sub_gold'])
def d0_within(o):
    sc = joint_scores(o, [1.0] * 25); c0 = pred('D0', o)[0]
    return sorted(sc, key=lambda k: (k[0] != c0, -sc[k]))   # subtopics of D0's chapter first (empty if not shortlisted)
def sub_eval(fn, ids):
    n = len(ids); t1 = t3 = 0
    for o in ids:
        g = (items[o]['chapter'], items[o]['subtopic_name']); rk = fn(o)
        t1 += rk[0] == g; t3 += g in rk[:3]
    return dict(n=n, top1=round(t1 / n, 4) if n else None, top1_k=t1, top1_ci=wilson(t1, n), top3=round(t3 / n, 4) if n else None,
                top3_k=t3, top3_ci=wilson(t3, n))
R['subtopic'] = {'D1 (joint L2 x D0-arith prior, beta=1) [pre-registered pipeline]': sub_eval(lambda o: D1[o]['subs'], sub_ids),
                 'joint L2 alone (no prior) [derived]': sub_eval(lambda o: sorted(joint_scores(o, [1] * 25), key=lambda k: -joint_scores(o, [1] * 25)[k]), sub_ids),
                 'D0 chapter top-1 -> best joint-L2 subtopic within it [derived]': sub_eval(lambda o: d0_within(o), sub_ids)}
for d, V in (('D2', D2), ('D3', D3)):
    ids = [o for o in sub_ids if o in V]
    R['subtopic'][f'joint L2 x {d} chapter vector [derived, exploratory]'] = sub_eval(lambda o: d1_like(o, V[o], V[o])['subs'], ids)
R['subtopic_gold_chapter_in_shortlist'] = (lambda k, n: dict(k=k, n=n, share=round(k / n, 4) if n else None, ci=wilson(k, n)))(
    sum(items[o]['chapter'] in raw['d1'][o]['chs'] for o in AV['D1']), len(AV['D1']))

# ---------------- lanes (D0 orders agree / disagree)
def lanes(design, ids):
    out = {}
    for name, f in (('orders agree', True), ('orders disagree', False)):
        L = [o for o in ids if (order(raw['d0a'][o]['p'])[0] == order(raw['d0b'][o]['p'])[0]) == f]
        k = sum(pred(design, o)[0] == items[o]['chapter'] for o in L)
        out[name] = dict(n=len(L), share=round(len(L) / len(ids), 4) if ids else None, share_ci=wilson(len(L), len(ids)),
                         precision=round(k / len(L), 4) if L else None, k=k, ci=wilson(k, len(L)))
    return out
R['lanes'] = {d: lanes(d, sorted(AV[d] & AV['D0'])) for d in ('D0', best)}

# ---------------- reliability + coverage-precision
def reliability(design, ids):
    bins = [[] for _ in range(10)]
    for o in ids:
        t, _, c = pred(design, o); bins[min(9, int(c * 10))].append((c, t == items[o]['chapter']))
    rows, ece, N = [], 0.0, len(ids)
    for i, b in enumerate(bins):
        if not b: rows.append(dict(bin=f'{i/10:.1f}-{(i+1)/10:.1f}', n=0)); continue
        conf = sum(x for x, _ in b) / len(b); acc = sum(y for _, y in b) / len(b); ece += len(b) / N * abs(acc - conf)
        rows.append(dict(bin=f'{i/10:.1f}-{(i+1)/10:.1f}', n=len(b), mean_p=round(conf, 4), acc=round(acc, 4), ci=wilson(sum(y for _, y in b), len(b))))
    cov = []
    srt = sorted(ids, key=lambda o: -pred(design, o)[2])
    for c in (0.5, 0.7, 0.9, 1.0):
        k = max(1, round(c * len(srt))); sel = srt[:k]; h = sum(pred(design, o)[0] == items[o]['chapter'] for o in sel)
        cov.append(dict(coverage=c, n=k, threshold_p=round(pred(design, sel[-1])[2], 4), precision=round(h / k, 4), k=h, ci=wilson(h, k)))
    return dict(bins=rows, ece=round(ece, 4), coverage_precision=cov)
R['reliability'] = {d: reliability(d, sorted(AV[d] & AV['D0'])) for d in ('D0', best) if AV[d]}

# ---------------- exploratory combination (only if D1 and D2 both win)
if 'D1' in winners and 'D2' in winners:
    ids = sorted(AV['D1'] & AV['D2'])
    comb = {o: d1_like(o, D2[o], D2[o]) for o in ids}
    h = [comb[o]['ch'] == items[o]['chapter'] for o in ids]; h0 = [pred('D0', o)[0] == items[o]['chapter'] for o in ids]
    R['exploratory_D1xD2'] = dict(label='EXPLORATORY (not pre-registered as a hypothesis)', n=len(ids), top1=round(sum(h) / len(ids), 4),
                                  ci=wilson(sum(h), len(ids)), diff_vs_D0=round((sum(h) - sum(h0)) / len(ids), 4), diff_ci=paired(h, h0))
else:
    R['exploratory_D1xD2'] = 'not computed: D1 and D2 do not both win'

R['data'] = dict(items=len(items), period=dict(collections.Counter(it['period'] for it in items.values())),
                 join=dict(collections.Counter(it['join_quality'] for it in items.values())),
                 sub_gold=sum(it['sub_gold'] for it in items.values()), chapters_present=len({it['chapter'] for it in items.values()}),
                 de_text=sum(bool(it['de']['text']) for it in items.values()), fr_text=sum(bool(it['fr']['text']) for it in items.values()))
json.dump(R, open(f'{HERE}/results.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps({k: R[k] for k in ('n', 'chapter', 'baselines', 'winners', 'spend_total_usd')}, ensure_ascii=False, indent=1))
