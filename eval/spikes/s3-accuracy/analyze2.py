"""S3 analysis for E4 (languages), E5 (APS), E6 (Digitalisierung + free generation) -> analysis2.json"""
import json, os, sys, math, collections, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s3lib import *  # noqa
import s1lib
from analyze import load, as_scores, dec, evaluate, summary, avg_geo, pvec, builds, BY, DEV, TEST, NONE_IDX, agreement, coverage_curve, best_rule, strip

B = {}
ITEMS = json.load(open(f'{DATA}/curia300.json'))
APS_CODES = ['1.1.1.', '1.1.2.', '1.1.3.', '1.1.4.', '1.1.5.', '1.2.', '1.3.', '1.4.1.', '1.4.2.', '1.4.3.', '1.5.', '1.6.1.',
             '1.6.2.', '1.6.3.', '1.6.4.', '1.7.1.', '1.7.2.', '1.7.3.', '1.7.4.', '1.8.1.', '1.8.2.', '1.8.3.', '2.0.1.', '2.0.2.']

def design_P(prefix_a, prefix_b):
    ra, rb = load(prefix_a), load(prefix_b)
    if ra and rb: return avg_geo(ra, rb), ra, rb
    return (pvec(ra) if ra else {}), ra, rb

# ---------------- E4
E4_RULE = os.environ.get('S3_E4_RULE')  # e.g. "top1+thr@0.1" from the DE best design
de_P, *_ = design_P(os.environ.get('S3_DE_A', 'e3a'), os.environ.get('S3_DE_B', 'e3b'))
B['E4'] = {}
langP = {'de': de_P}
for lang in ('fr', 'it'):
    P, ra, rb = design_P(f'e4{lang}a', f'e4{lang}b')
    if not P: continue
    langP[lang] = P
    B['E4'][lang] = dict(builds={f'{m}|{f}': n for (m, f), n in builds(ra, rb).items()},
                         eval=summary(evaluate({c: as_scores(p) for c, p in P.items()})))
    sub = set(P)
    B['E4'][lang]['de_same_items'] = summary(evaluate({c: as_scores(p) for c, p in de_P.items() if c in sub}))
    # cross-language agreement on test items present in both (top-1 identical; Jaccard of predicted sets with DE rule)
    rule, x = (E4_RULE or 'top1+thr@0.1').split('@'); x = float(x)
    ids = [c for c in TEST if c in P and c in de_P]
    t = lambda p: max(range(NL), key=lambda j: p[j])
    same = sum(t(P[c]) == t(de_P[c]) for c in ids)
    jac = []
    for c in ids:
        a = dec(as_scores(P[c]), rule, x); b = dec(as_scores(de_P[c]), rule, x)
        jac.append(len(a & b) / len(a | b) if a | b else 1.0)
    B['E4'][lang]['agree_vs_de'] = dict(n=len(ids), top1_same=same, rate=round(same / len(ids), 3), ci=wilson(same, len(ids)),
                                        mean_jaccard=round(sum(jac) / len(jac), 3), rule=f'{rule}@{x}')
    B['E4'][lang]['cost'] = dict(pt_per_affair=round(sum(r['rec']['pt'] for rs in (ra, rb) for r in rs.values()) / len(ra), 1))
    if lang == 'fr' and 'it' in langP: pass

# ---------------- E5
A5 = {a['opd_affair_id']: a for a in json.load(open(f'{DATA}/aps.json'))}
ra, rb = load('e5a', 'oid'), load('e5b', 'oid')
if ra:
    B['E5'] = {'builds': {f'{m}|{f}': n for (m, f), n in builds(ra, rb).items()}}
    def avgp(o):
        if o in rb:
            la = [math.log(max(x, 1e-12)) for x in ra[o]['p']]; lb = [math.log(max(x, 1e-12)) for x in rb[o]['p']]
            g = [math.exp((x + y) / 2) for x, y in zip(la, lb)]; s = sum(g); return [v / s for v in g]
        return ra[o]['p']
    variants = {'identity': lambda o: ra[o]['p'], 'avg2': avgp}
    if rb: variants['permuted'] = lambda o: rb[o]['p']
    for vn, f in variants.items():
        res = {}
        for grp, filt in (('all', lambda a: True), ('strong', lambda a: a['join_quality'] != 'slug_only'),
                          ('weak', lambda a: a['join_quality'] == 'slug_only'), ('with_text', lambda a: a['has_curia_text'])):
            os_ = [o for o in ra if filt(A5[o]) and (vn == 'identity' or o in rb)]
            top1 = top3 = anykw = 0
            for o in os_:
                p = f(o); order = sorted(range(25), key=lambda i: -p[i]); tru = APS_CODES.index(A5[o]['chapter_code'])
                top1 += order[0] == tru; top3 += tru in order[:3]
                kws = {APS_CODES.index(k.replace('-', '.') + '.') for k in (A5[o]['keyword_chapters'] or {}) if k.replace('-', '.') + '.' in APS_CODES} | {tru}
                anykw += order[0] in kws
            n = len(os_)
            res[grp] = dict(n=n, top1=round(top1 / n, 3), ci1=wilson(top1, n), top3=round(top3 / n, 3), ci3=wilson(top3, n),
                            top1_in_any_keyword_chapter=round(anykw / n, 3))
        B['E5'][vn] = res
    if rb:
        B['E5']['agree_id_vs_perm'] = sum(max(range(25), key=lambda i: ra[o]['p'][i]) == max(range(25), key=lambda i: rb[o]['p'][i]) for o in rb)
    # L2
    rt = load('e5t', 'oid')
    if rt:
        ok = [o for o, r in rt.items() if r['top_name'] == A5[o]['subtopic_name']]
        n = len(rt)
        B['E5']['L2_given_true'] = dict(n=n, acc=round(len(ok) / n, 3), ci=wilson(len(ok), n),
                                       mean_nsub=round(sum(len(s1lib.SUBS[r['ch']]) for r in rt.values()) / n, 1))
        # given predicted chapter: same prompt as e5t when prediction is right; wrong chapter => subtopic wrong by construction
        best = 'avg2' if rb else 'identity'; f = variants[best]
        right = [o for o in rt if max(range(25), key=lambda i: f(o)[i]) == rt[o]['ch']]
        e2e = sum(o in ok for o in right)
        B['E5']['L2_given_pred'] = dict(variant=best, n=n, chapter_right=len(right), l2_right_given_chapter_right=e2e,
                                       acc_conditional=round(e2e / len(right), 3) if right else None,
                                       acc_end_to_end=round(e2e / n, 3), ci_e2e=wilson(e2e, n))
        B['E5']['L2_by_join'] = {g: (lambda os_: dict(n=len(os_), acc=round(sum(o in ok for o in os_) / len(os_), 3)) if os_ else None)(
            [o for o in rt if (A5[o]['join_quality'] == 'slug_only') == (g == 'weak')]) for g in ('strong', 'weak')}
    # confusion: most common wrong chapter pairs (avg2)
    f = variants['avg2' if rb else 'identity']; conf = collections.Counter()
    for o in ra:
        if rb and o not in rb: continue
        pr = max(range(25), key=lambda i: f(o)[i]); tru = APS_CODES.index(A5[o]['chapter_code'])
        if pr != tru: conf[(s1lib.CH_DE[tru], s1lib.CHAPTERS['de'][pr][:30])] += 1
    B['E5']['top_confusions'] = [f'{a} → {b}: {n}' for (a, b), n in conf.most_common(8)]

# ---------------- E6
ra, rb = load('e6a', 'oid'), load('e6b', 'oid')
if ra:
    D = json.load(open(f'{DATA}/dvs.json')); info = {x['opd_affair_id']: x for L in (D['pos'], D['neg']) for x in L}
    B['E6'] = {'builds': {f'{m}|{f}': n for (m, f), n in builds(ra, rb).items()}}
    def py(o):
        return (ra[o]['p_yes'] + rb[o]['p_yes']) / 2 if o in rb else ra[o]['p_yes']
    pos = [o for o, r in ra.items() if r['pos'] == 'pos' and (not rb or o in rb)]
    neg = [o for o, r in ra.items() if r['pos'] == 'neg' and (not rb or o in rb)]
    tab = []
    for th in (0.3, 0.5, 0.7, 0.9):
        rp = sum(py(o) >= th for o in pos); fn = sum(py(o) >= th for o in neg)
        tab.append(dict(thr=th, recall=round(rp / len(pos), 3), ci_r=wilson(rp, len(pos)), flag_rate_random=round(fn / len(neg), 3),
                        ci_f=wilson(fn, len(neg)), n_flagged=fn))
    B['E6']['table'] = tab; B['E6']['n_pos'] = len(pos); B['E6']['n_neg'] = len(neg)
    if rb:
        B['E6']['order_agree@0.5'] = sum((ra[o]['p_yes'] >= .5) == (rb[o]['p_yes'] >= .5) for o in rb) / len(rb)
        B['E6']['single_order_recall_flag'] = {nm: dict(recall=round(sum(r[o]['p_yes'] >= .5 for o in pos) / len(pos), 3),
                                                       flag=round(sum(r[o]['p_yes'] >= .5 for o in neg) / len(neg), 3)) for nm, r in (('yes=A', ra), ('yes=B', rb))}
    B['E6']['missed_pos'] = [(info[o]['body'], info[o]['title'][:90], round(py(o), 3)) for o in pos if py(o) < 0.5]
    B['E6']['top10_random'] = [(info[o]['body'], info[o]['year'], info[o]['type'], info[o]['title'][:140], round(py(o), 3), o)
                               for o in sorted(neg, key=py, reverse=True)[:10]]
rf = load('e6f', 'key')
if rf:
    def norm(s):
        s = unicodedata.normalize('NFKC', s or '').lower().strip(' .«»"')
        return s
    curia = {norm(TN['de'][str(t)]) for t in TAGS}
    aps = {norm(x) for x in s1lib.CH_DE} | {norm(s) for v in s1lib.SUBS.values() for s in v}
    out = {}
    for arm in ('free', 'list'):
        rows = [r for r in rf.values() if r['arm'] == arm]
        ans = [norm(r['answer']) for r in rows]
        none = sum('kein' in a and 'thema' in a or 'kein sachthema' in a for a in ans)
        inC = sum(a in curia for a in ans); inA = sum(a in aps for a in ans); inAny = sum(a in curia or a in aps for a in ans)
        gold_hit = sum(norm(r['answer']) in {norm(TN['de'][str(g)]) for g in r['gold']} for r in rows)
        out[arm] = dict(n=len(rows), no_topic=none, in_curia=inC, in_aps=inA, outside_both=len(rows) - inAny - none,
                        outside_rate=round((len(rows) - inAny - none) / len(rows), 3), ci=wilson(len(rows) - inAny - none, len(rows)),
                        exact_gold_hit=gold_hit, examples=[r['answer'] for r in rows][:40])
    B['E6f'] = out
json.dump(B, open(f'{OUT}/analysis2.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(B, ensure_ascii=False, indent=1)[:12000])
