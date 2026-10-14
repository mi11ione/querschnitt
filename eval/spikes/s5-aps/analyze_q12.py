"""Q1 (APS chapters with subtopic descriptions) and Q2 (joint L2 over top-k chapters) -> q12.json"""
import json, os, sys, math, random, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import APS, L2_GOLD, load, l1_probs, q2_chapters, S3, RAW5, OUT5, APS_CODES, SUBS, wilson  # noqa
import s1lib

R = {}
def kwchs(a, tru):
    return {APS_CODES.index(k.replace('-', '.') + '.') for k in (a['keyword_chapters'] or {})
            if k.replace('-', '.') + '.' in APS_CODES} | {tru}

def paired_prop(a, b, n=2000, seed=3):
    rng = random.Random(seed); m = len(a); d = []
    for _ in range(n):
        idx = [rng.randrange(m) for _ in range(m)]; d.append(sum(a[i] - b[i] for i in idx) / m)
    d.sort(); return (round(d[int(.025 * n)], 3), round(d[int(.975 * n) - 1], 3))

def geo2(pa, pb):
    out = {}
    for o in pa:
        if o not in pb: continue
        g = [math.exp((math.log(max(x, 1e-12)) + math.log(max(y, 1e-12))) / 2) for x, y in zip(pa[o], pb[o])]
        s = sum(g); out[o] = [v / s for v in g]
    return out

e5a = {o: r['p'] for o, r in load(f'{S3}/raw/e5a.jsonl', 'oid').items()}
e5b = {o: r['p'] for o, r in load(f'{S3}/raw/e5b.jsonl', 'oid').items()}
q1a = {o: r['p'] for o, r in load(f'{RAW5}/q1a.jsonl', 'oid').items()}
q1b = {o: r['p'] for o, r in load(f'{RAW5}/q1b.jsonl', 'oid').items()}
V = {'S3 E5 names, identity': e5a, 'S3 E5 names, permuted': e5b, 'S3 E5 names, 2-order avg (geo, S3)': geo2(e5a, e5b),
     '(a) names+subtopics, identity': q1a, '(a) names+subtopics, permuted': q1b,
     '(c) names+subtopics, 2-order avg (arith)': {o: [(x + y) / 2 for x, y in zip(q1a[o], q1b[o])] for o in q1a if o in q1b},
     '(c) names+subtopics, 2-order avg (geo)': geo2(q1a, q1b)}
common = sorted(set.intersection(*(set(v) for v in V.values())))
top1 = lambda p: max(range(25), key=lambda i: p[i])
Q1 = {'n_common': len(common)}
hits = {}
for name, P in V.items():
    res = {}
    for grp, f in (('all', lambda a: True), ('strong', lambda a: a['join_quality'] != 'slug_only'),
                   ('weak', lambda a: a['join_quality'] == 'slug_only')):
        os_ = [o for o in common if f(APS[o])]; t1 = t3 = kw = 0
        for o in os_:
            p = V[name][o]; order = sorted(range(25), key=lambda i: -p[i]); tru = APS_CODES.index(APS[o]['chapter_code'])
            t1 += order[0] == tru; t3 += tru in order[:3]; kw += order[0] in kwchs(APS[o], tru)
        n = len(os_)
        res[grp] = dict(n=n, top1=round(t1 / n, 3), ci1=wilson(t1, n), top3=round(t3 / n, 3), ci3=wilson(t3, n), kw=round(kw / n, 3))
    hits[name] = [top1(P[o]) == APS_CODES.index(APS[o]['chapter_code']) for o in common]
    res['top2'] = round(sum(APS_CODES.index(APS[o]['chapter_code']) in sorted(range(25), key=lambda i: -P[o][i])[:2] for o in common) / len(common), 3)
    Q1[name] = res
base = 'S3 E5 names, 2-order avg (geo, S3)'
Q1['paired_top1_vs_E5avg'] = {n: paired_prop(hits[n], hits[base]) for n in V if n != base}
Q1['agree_q1a_q1b'] = sum(top1(q1a[o]) == top1(q1b[o]) for o in common)
Q1['agree_e5a_e5b'] = sum(top1(e5a[o]) == top1(e5b[o]) for o in common)
conf = collections.Counter()
P = V['(c) names+subtopics, 2-order avg (arith)']
for o in common:
    tru = APS_CODES.index(APS[o]['chapter_code']); pr = top1(P[o])
    if pr != tru: conf[(s1lib.CH_DE[tru], s1lib.CHAPTERS['de'][pr][:28])] += 1
Q1['top_confusions_c'] = [f'{a} -> {b}: {n}' for (a, b), n in conf.most_common(6)]
rows = list(load(f'{RAW5}/q1a.jsonl', 'oid').values()) + list(load(f'{RAW5}/q1b.jsonl', 'oid').values())
Q1['builds'] = dict(collections.Counter(f"{r['rec']['model']}|{r['rec']['fp']}" for r in rows))
Q1['pt_per_call'] = round(sum(r['rec']['pt'] for r in rows) / len(rows), 1)
Q1['min_mass'] = min(r['mass'] for r in rows)
R['Q1'] = Q1

# ---------------------------------------------------------------- Q2
e5t = load(f'{S3}/raw/e5t.jsonl', 'oid')
ok_t = {o for o, r in e5t.items() if r['top_name'] == APS[o]['subtopic_name']}   # L2 right given true chapter (S3)
gold = {o: (L2_GOLD[o], APS[o]['subtopic_name']) for o in L2_GOLD}
n2 = len(gold)
Q2 = {'n': n2, 'within_top_chapter': {}}
for name in ('S3 E5 names, 2-order avg (geo, S3)', '(c) names+subtopics, 2-order avg (arith)', '(c) names+subtopics, 2-order avg (geo)'):
    P = V[name]
    right = [o for o in gold if top1(P[o]) == gold[o][0]]
    e2e = sum(o in ok_t for o in right)
    Q2['within_top_chapter'][name] = dict(chapter_top1=round(len(right) / n2, 3), e2e=round(e2e / n2, 3), ci=wilson(e2e, n2), k=e2e)
ra, rb = load(f'{RAW5}/q2a.jsonl', 'oid'), load(f'{RAW5}/q2b.jsonl', 'oid')
if ra:
    l1name = next(iter(ra.values()))['l1']; P1 = l1_probs(l1name)
    def sub_scores(rows, o):
        r = rows[o]; return {tuple(op): r['p'][i] for i, op in enumerate(r['opts'])}, r['p'][-1]
    def evaluate(scorefn, ids):
        h_sub = h_ch = 0; nonetop = 0
        for o in ids:
            sc, pn = scorefn(o)
            best = max(sc, key=sc.get)
            h_sub += best == gold[o]; h_ch += best[0] == gold[o][0]
            nonetop += pn > max(sc.values())
        n = len(ids)
        return dict(n=n, e2e=round(h_sub / n, 3), ci=wilson(h_sub, n), k=h_sub, chapter_top1=round(h_ch / n, 3), ci_ch=wilson(h_ch, n),
                    none_top=nonetop)
    ids = [o for o in gold if o in ra and (not rb or o in rb)]
    cover = sum(gold[o][0] in ra[o]['chs'] for o in ids)
    Q2['l1'] = l1name; Q2['gold_chapter_in_shown'] = (cover, round(cover / len(ids), 3), wilson(cover, len(ids)))
    Q2['n_chapters_shown'] = dict(collections.Counter(len(ra[o]['chs']) for o in ids))
    Q2['mean_options'] = round(sum(len(ra[o]['opts']) for o in ids) / len(ids), 1)
    Q2['joint_order_a'] = evaluate(lambda o: sub_scores(ra, o), ids)
    if rb:
        Q2['joint_order_b'] = evaluate(lambda o: sub_scores(rb, o), ids)
        def avg(o):
            a, pa = sub_scores(ra, o); b, pb = sub_scores(rb, o)
            return {k: (a[k] + b[k]) / 2 for k in a}, (pa + pb) / 2
        Q2['joint_2order_avg'] = evaluate(avg, ids)
        Q2['agree_a_b'] = sum(max(sub_scores(ra, o)[0], key=sub_scores(ra, o)[0].get) == max(sub_scores(rb, o)[0], key=sub_scores(rb, o)[0].get) for o in ids)
        joint = avg
    else:
        joint = lambda o: sub_scores(ra, o)
    # derived: product with the L1 chapter prior, p(sub) * p(ch)^beta (beta fixed, not tuned)
    for beta in (0.5, 1.0):
        def prod(o, beta=beta):
            sc, pn = joint(o); return {k: v * (P1[o][k[0]] ** beta) for k, v in sc.items()}, 0.0
        Q2[f'joint_x_L1prior_beta{beta}'] = evaluate(prod, ids)
    # paired: joint (best) vs within-top-chapter on the same L1
    wt = [top1(P1[o]) == gold[o][0] and o in ok_t for o in ids]
    jt = [max(joint(o)[0], key=joint(o)[0].get) == gold[o] for o in ids]
    Q2['paired_joint_vs_withintop_sameL1'] = paired_prop(jt, wt)
    wt5 = [top1(V['S3 E5 names, 2-order avg (geo, S3)'][o]) == gold[o][0] and o in ok_t for o in ids]
    Q2['paired_joint_vs_S3_0435'] = paired_prop(jt, wt5)
    jc = [max(joint(o)[0], key=joint(o)[0].get)[0] == gold[o][0] for o in ids]
    lc = [top1(P1[o]) == gold[o][0] for o in ids]
    Q2['chapter_L1_top1_same_items'] = round(sum(lc) / len(ids), 3)
    Q2['paired_chapter_joint_vs_L1'] = paired_prop(jc, lc)
    Q2['chapter_joint_vs_L1_flips'] = dict(gain=sum(a and not b for a, b in zip(jc, lc)), loss=sum(b and not a for a, b in zip(jc, lc)))
    # chapter accuracy on the 35 subtopic-gold-free affairs is not measured (no Q2 call); see results.md
    rows = list(ra.values()) + list(rb.values())
    Q2['builds'] = dict(collections.Counter(f"{r['rec']['model']}|{r['rec']['fp']}" for r in rows))
    Q2['pt_per_call'] = round(sum(r['rec']['pt'] for r in rows) / len(rows), 1)
    Q2['min_mass'] = min(r['mass'] for r in rows)
R['Q2'] = Q2
json.dump(R, open(f'{OUT5}/q12.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(R, ensure_ascii=False, indent=1))
