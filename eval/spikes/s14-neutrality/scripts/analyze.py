"""S14 neutrality (PREREG-ADDENDA 2026-10-13 21:20 UTC): quality by language, level, canton/region and submitter party on existing
S6, S8, S9, S10 results. No model calls, no network. Party = submitter party from OPD contributors (6 Oct export, data/opd_subset.json).
Per cell: n, metric, Wilson 95% (unweighted) or within-stratum bootstrap 95% (S8 weighted). Per dimension: permutation test (5,000,
labels shuffled within S8 packet strata where weighted) of the between-group chi-square statistic (= Pearson chi-square when
unweighted; asymptotic p also given), and the largest gap between cells with n >= 20 (bootstrap 95%, 2,000). n < 20 = 'small'.
Usage: python3 -I scripts/analyze.py  -> results.json"""
import json, os, sys, random, collections, time, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s14lib as L
H = L.H
B2 = '/Users/mi11ion/Desktop/hackapertus/bern/ideation2/spikes'; B1 = '/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes'
NB, SMALL = 2000, 20
R = dict(generated_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), small_threshold=SMALL)

def wmean(rows):
    W = sum(r['w'] for r in rows); return sum(r['w'] * r['y'] for r in rows) / W if W else float('nan')

def boot_cell(rows, rng, weighted):
    by = collections.defaultdict(list)
    for r in rows: by[r['s']].append(r)
    out = []
    for _ in range(NB):
        smp = [rng.choice(v) for v in by.values() for _ in v]
        out.append(wmean(smp) if weighted else sum(r['y'] for r in smp) / len(smp))
    return sorted(out)

def q(v): return [round(v[int(.025 * len(v))], 4), round(v[int(.975 * len(v)) - 1], 4)]

def dimension(rows, weighted=False, order=None, test_groups=None, seed=14, bootarr=None):
    """rows: dicts g (cell), y (0/1), w (weight), s (stratum). Returns cells, test, gap.
    weighted: bootarr[g] = cell estimate in each full-packet stratified resample (NaN if the cell is empty in that resample)."""
    rng = random.Random(seed)
    groups = collections.defaultdict(list)
    for r in rows: groups[r['g']].append(r)
    bysize = sorted(groups, key=lambda g: (-len(groups[g]), str(g)))
    keys = ([k for k in order if k in groups] + [k for k in bysize if k not in order]) if order else bysize
    cells, boots = [], {}
    for g in keys:
        rr = groups[g]; n = len(rr); k = sum(r['y'] for r in rr)
        c = dict(cell=g, n=n, k=k, p=round(k / n, 4), ci=L.wilson(k, n), small=n < SMALL)
        if weighted:
            b = sorted(v for v in bootarr[g] if v == v)
            c.update(p_w=round(wmean(rr), 4), ci_w=q(b))
        cells.append(c)
    allk = sum(r['y'] for r in rows)
    overall = dict(n=len(rows), k=allk, p=round(allk / len(rows), 4) if rows else None, ci=L.wilson(allk, len(rows)))
    if weighted: overall['p_w'] = round(wmean(rows), 4)
    tg = test_groups or keys
    sub = [r for r in rows if r['g'] in tg]
    test = L.perm_test([r['g'] for r in sub], [r['y'] for r in sub], [r['w'] for r in sub] if weighted else None, None)
    test['cells_tested'] = [g for g in keys if g in tg]
    met = 'p_w' if weighted else 'p'
    big = [c for c in cells if not c['small'] and c['cell'] in tg]
    basis = 'cells n>=20'
    if len(big) < 2: big = [c for c in cells if c['cell'] in tg and c['n'] >= 5]; basis = 'no 2 cells with n>=20: cells n>=5 (small)'
    gap = None
    if len(big) >= 2:
        hi = max(big, key=lambda c: c[met]); lo = min(big, key=lambda c: c[met])
        if weighted:
            d = sorted(x - y for x, y in zip(bootarr[hi['cell']], bootarr[lo['cell']]) if x == x and y == y)
            return dict(overall=overall, cells=cells, test=test, gap=dict(hi=hi['cell'], lo=lo['cell'], diff=round(hi[met] - lo[met], 4),
                        ci=q(d), basis=basis + '; paired over full-packet resamples'))
        bh = boots.get(hi['cell']) or boot_cell(groups[hi['cell']], rng, False)
        bl = boots.get(lo['cell']) or boot_cell(groups[lo['cell']], rng, False)
        rng2 = random.Random(seed + 1); d = sorted(bh[rng2.randrange(NB)] - bl[rng2.randrange(NB)] for _ in range(NB))
        # independent groups: pair random draws of the two cell bootstrap distributions
        gap = dict(hi=hi['cell'], lo=lo['cell'], diff=round(hi[met] - lo[met], 4), ci=q(d), basis=basis)
    return dict(overall=overall, cells=cells, test=test, gap=gap)

# ======================= S9 federal APS (D1 recomputed from raw; same functions as s9-aps/scripts/analyze.py)
sys.path.insert(0, f'{B2}/s9-aps/scripts')
from s9lib import DATA as S9D, RAW as S9R, geo2, load   # noqa: E402  (s9lib imports pai: reads key file only, no call)
items = {it['oid']: it for it in json.load(open(f'{S9D}/items.json'))}
raw = {ph: load(f'{S9R}/{ph}.jsonl') for ph in ('d0a', 'd0b', 'd1', 'd2fr')}
def order(p): return sorted(range(len(p)), key=lambda i: -p[i])
PA = {o: [(x + y) / 2 for x, y in zip(raw['d0a'][o]['p'], raw['d0b'][o]['p'])] for o in items if o in raw['d0a'] and o in raw['d0b']}
def d1(o):
    r = raw['d1'][o]; prior = PA[o]
    sc = {(c, s): r['p'][i] * prior[c] for i, (c, s) in enumerate(r['opts'])}
    best = max(sc, key=sc.get); chbest = {}
    for (c, s), v in sc.items(): chbest[c] = max(chbest.get(c, 0), v)
    rk = sorted(chbest, key=lambda c: -chbest[c]); rk += [c for c in order(prior) if c not in rk]
    return best[0], rk
ids = sorted(o for o in PA if o in raw['d1'])
D1 = {o: d1(o) for o in ids}
gold_c = collections.Counter(items[o]['chapter'] for o in ids)
majorder = [c for c, _ in gold_c.most_common()] + [c for c in range(24) if c not in gold_c]
KW = json.load(open(f'{S9D}/keywords_frozen.json')); kw = {int(c): v['keywords'] for c, v in KW['chapters'].items()}
def kw_pred(o):
    it = items[o]['de']; txt = ' '.join((it['title'], it['title_long'], it['text'])).lower()
    sc = {c: sum(w in txt for w in kw[c]) for c in range(24)}; m = max(sc.values())
    return min([c for c in range(24) if sc[c] == m], key=majorder.index)
hit = {o: int(D1[o][0] == items[o]['chapter']) for o in ids}
hit3 = {o: int(items[o]['chapter'] in D1[o][1][:3]) for o in ids}
khit = {o: int(kw_pred(o) == items[o]['chapter']) for o in ids}
check = sum(hit.values())
s9ref = json.load(open(f'{B2}/s9-aps/results.json'))['chapter']['D1']
R['S9_check'] = dict(n=len(ids), D1_top1_k=check, s9_results_json_top1_k=s9ref['top1_k'], match=check == s9ref['top1_k'],
                     kw_top1_k=sum(khit.values()))
sub9 = {o: L.submitter(o) for o in ids}
def kind(o):
    c = sub9[o][0]
    return 'member/faction' if c in L.MAIN + ['other party', 'party unknown'] else c
TYPE = lambda o: (L.AFF[str(o)]['type'] if L.AFF[str(o)]['type'] in ('Motion', 'Postulat', 'Parlamentarische Initiative', 'Regierungsgeschäft',
                  'Standesinitiative') else 'other type')
S9 = {}
for dim, f, ordr, tg in (('party', lambda o: sub9[o][0], L.MAIN + ['other party', 'committee', 'government', 'canton', 'unknown'], L.MAIN),
                         ('submitter kind', kind, ['member/faction', 'committee', 'government', 'canton', 'unknown'], None),
                         ('instrument', TYPE, None, None)):
    S9[dim] = {}
    for mname, H_ in (('D1_top1', hit), ('D1_top3', hit3), ('keyword_top1', khit)):
        S9[dim][mname] = dimension([dict(g=f(o), y=H_[o], w=1.0, s=0) for o in ids], order=ordr, test_groups=tg)
    if dim == 'party':   # all categories test as secondary
        S9[dim]['D1_top1_all_categories_test'] = dimension([dict(g=f(o), y=hit[o], w=1.0, s=0) for o in ids], order=ordr)['test']
# language: same affairs, DE prompt+text (d0a, identity order) vs FR prompt+text (d2fr, identity order), single calls
lid = sorted(o for o in ids if o in raw['d2fr'])
de = [int(order(raw['d0a'][o]['p'])[0] == items[o]['chapter']) for o in lid]
fr = [int(order(raw['d2fr'][o]['p'])[0] == items[o]['chapter']) for o in lid]
b = sum(1 for x, y in zip(de, fr) if x and not y); c = sum(1 for x, y in zip(de, fr) if y and not x)
rng = random.Random(9); dd = []
for _ in range(NB):
    ii = [rng.randrange(len(lid)) for _ in lid]; dd.append(sum(de[i] - fr[i] for i in ii) / len(lid))
mcn = (abs(b - c) - 1) ** 2 / (b + c) if b + c else 0
S9['language (paired, same affairs; single identity-order call)'] = dict(
    n=len(lid), DE=dict(k=sum(de), p=round(sum(de) / len(lid), 4), ci=L.wilson(sum(de), len(lid))),
    FR=dict(k=sum(fr), p=round(sum(fr) / len(lid), 4), ci=L.wilson(sum(fr), len(lid))),
    diff_DE_minus_FR=round((sum(de) - sum(fr)) / len(lid), 4), diff_ci=q(sorted(dd)), only_DE_right=b, only_FR_right=c,
    mcnemar_chi2=round(mcn, 3), p_mcnemar=round(L.chi2_sf(mcn, 1), 4))
S9['canton/region'] = 'not available: federal submitters carry no canton in the OPD contributors export; Standesinitiativen appear as the "canton" submitter cell'
R['S9'] = S9

# ======================= S8 digitalisation
def rd(p):
    d = {}
    if not os.path.exists(p): return d
    for line in open(p).read().splitlines():
        x = line.rstrip('\n').split('\t')
        if len(x) >= 2 and x[0].startswith('D') and x[1].strip():
            d[x[0]] = 'Q' if (len(x) > 2 and x[2].strip() == '?') else x[1].strip().upper()
    return d
K8 = [json.loads(l) for l in open(f'{B2}/s8-dvs/key.jsonl')]
A, B, C = (rd(f'{B2}/s8-dvs/ann_{x}.tsv') for x in 'ABC')
def gold8(i):
    if A.get(i) in ('Y', 'N') and A.get(i) == B.get(i): return A[i]
    return C.get(i) if C.get(i) in ('Y', 'N') else None
for k in K8:
    k['gold'] = gold8(k['pid']); k['a'] = k['p_yes'] >= 0.5; k['kwf'] = bool(k['kw'])
    k['region'] = L.region_of(k['body']); k['canton'] = L.canton_of(k['body']); k['party'] = L.submitter(k['oid'])[0]
R['S8_check'] = dict(n=len(K8), gold_missing=sum(k['gold'] is None for k in K8), gold_Y=sum(k['gold'] == 'Y' for k in K8))
S8 = {}
def s8rows(f, metric):
    out = []
    for k in K8:
        if k['gold'] is None: continue
        flag = k['a'] if metric[0] == 'a' else k['kwf']
        if metric[1] == 'P' and flag: out.append(dict(g=f(k), y=int(k['gold'] == 'Y'), w=k['final_weight'], s=k['stratum']))
        if metric[1] == 'R' and k['gold'] == 'Y': out.append(dict(g=f(k), y=int(flag), w=k['final_weight'], s=k['stratum']))
    return out
ord_c = lambda key: None
DIMS8 = (('language', lambda k: k['lang'], ['de', 'fr', 'it'], None),
         ('level', lambda k: k['level'], ['federal', 'cantonal', 'communal', 'other'], None),
         ('region', lambda k: k['region'], ['federal', 'Deutschschweiz', 'Romandie', 'Svizzera italiana', 'bilingual cantons (BE FR VS GR)', 'other (LIE)'], None),
         ('canton (cantonal+communal bodies; federal separate)', lambda k: k['canton'], None,
          sorted({k['canton'] for k in K8} - {'federal', 'LIE'})),
         ('party', lambda k: k['party'], L.MAIN + ['other party', 'party unknown', 'government', 'committee', 'other group', 'unknown'], L.MAIN))
G8 = [k for k in K8 if k['gold'] is not None]
def rel(k, m):   # -> (relevant, y)
    flag = k['a'] if m[0] == 'a' else k['kwf']
    return (flag, int(k['gold'] == 'Y')) if m[1] == 'P' else (k['gold'] == 'Y', int(flag))
MET8 = ('aP', 'aR', 'kP', 'kR')
pre = [[(f(k), [rel(k, m) for m in MET8]) for _, f, _, _ in DIMS8] for k in G8]
bystr = collections.defaultdict(list)
for i, k in enumerate(G8): bystr[k['stratum']].append(i)
rngb = random.Random(7); BA = collections.defaultdict(list)   # (dim index, metric index, cell) -> per-resample estimate
cellset = {(di, mi, pre[i][di][0]) for i in range(len(G8)) for di in range(len(DIMS8)) for mi in range(4)}
for _ in range(NB):
    num = collections.defaultdict(float); den = collections.defaultdict(float)
    for v in bystr.values():
        for _ in v:
            i = rngb.choice(v); w = G8[i]['final_weight']
            for di, (g, rl) in enumerate(pre[i]):
                for mi, (r_, y) in enumerate(rl):
                    if r_: den[(di, mi, g)] += w; num[(di, mi, g)] += w * y
    for key in cellset: BA[key].append(num[key] / den[key] if den[key] else float('nan'))
for di, (dim, f, ordr, tg) in enumerate(DIMS8):
    S8[dim] = {m: dimension(s8rows(f, m), weighted=True, order=ordr, test_groups=tg,
                            bootarr={g: BA[(di, mi, g)] for (d_, mi_, g) in cellset if d_ == di and mi_ == mi})
               for mi, m in enumerate(MET8)}
R['S8'] = S8
R['S8_metric_names'] = dict(aP='Apertus precision (p_yes>=0.5)', aR='Apertus recall', kP='keyword precision', kR='keyword recall')

# ======================= S6 cantonal + communal APS
import importlib.util
sp = importlib.util.spec_from_file_location('s6score', f'{B1}/s6-cantonal/scripts/score.py'); s6 = importlib.util.module_from_spec(sp); sp.loader.exec_module(s6)
K6 = {json.loads(l)['oid']: json.loads(l) for l in open(f'{B1}/s6-cantonal/key.jsonl')}
A6, B6 = s6.read_ann(f'{B1}/s6-cantonal/ann_A.tsv'), s6.read_ann(f'{B1}/s6-cantonal/ann_B.tsv')
rows6 = []
for o in sorted(set(A6) & set(B6) & set(K6)):
    k = K6[o]; sa = {c for c in A6[o] if c}; sb = {c for c in B6[o] if c}
    rows6.append(dict(k, strict=A6[o][0] if A6[o][0] == B6[o][0] else None, lenient=(sa & sb) or None,
                      canton=L.canton_of(k['body']), region=L.region_of(k['body']), party=L.submitter(k['affair_id'])[0]))
st = [r for r in rows6 if r['strict']]
R['S6_check'] = dict(n=len(rows6), strict_n=len(st), strict_k=sum(r['apertus_final'] == r['strict'] for r in st),
                     lenient_k=sum(r['apertus_final'] in r['lenient'] for r in rows6))
S6 = {}
for dim, f, ordr, tg in (('language', lambda r: r['lang'], ['de', 'fr', 'it'], None), ('level', lambda r: r['level'], ['cantonal', 'communal'], None),
                         ('region', lambda r: r['region'], ['Deutschschweiz', 'Romandie', 'Svizzera italiana', 'bilingual cantons (BE FR VS GR)'], None),
                         ('canton', lambda r: r['canton'], None, None),
                         ('party', lambda r: r['party'], L.MAIN + ['other party', 'party unknown', 'government', 'other group', 'unknown'], L.MAIN)):
    S6[dim] = dict(strict=dimension([dict(g=f(r), y=int(r['apertus_final'] == r['strict']), w=1.0, s=0) for r in st], order=ordr, test_groups=tg),
                   lenient=dimension([dict(g=f(r), y=int(r['apertus_final'] in r['lenient']), w=1.0, s=0) for r in rows6], order=ordr, test_groups=tg))
R['S6'] = S6

# ======================= S10 bilingual cantons (titles only)
sp = importlib.util.spec_from_file_location('s10score', f'{B2}/s10-bilingual/scripts/score.py'); s10 = importlib.util.module_from_spec(sp); sp.loader.exec_module(s10)
K10 = {json.loads(l)['oid']: json.loads(l) for l in open(f'{B2}/s10-bilingual/key.jsonl')}
A10, B10 = s10.read_ann(f'{B2}/s10-bilingual/ann_A.tsv'), s10.read_ann(f'{B2}/s10-bilingual/ann_B.tsv')
C10 = s10.read_ann(f'{B2}/s10-bilingual/ann_C.tsv')
rows10 = []
for o, k in sorted(K10.items()):
    if o not in A10 or o not in B10: continue
    g = A10[o][0] if A10[o][0] == B10[o][0] else (C10[o][0] if o in C10 else None)
    if g is None: continue
    rows10.append(dict(k, gold=g, party=L.submitter(k['affair_id'])[0]))
R['S10_check'] = dict(n=len(rows10), pooled_k=sum(r['apertus_pooled'] == r['gold'] for r in rows10),
                      de_k=sum(r['apertus_de'] == r['gold'] for r in rows10), fr_k=sum(r['apertus_fr'] == r['gold'] for r in rows10))
S10 = {}
for dim, f, ordr, tg in (('canton', lambda r: r['canton'], ['BE', 'FR', 'VS'], None), ('shown language', lambda r: r['shown_lang'], ['de', 'fr'], None),
                         ('party', lambda r: r['party'], L.MAIN + ['other party', 'party unknown', 'government', 'unknown'], L.MAIN)):
    S10[dim] = {m: dimension([dict(g=f(r), y=int(r[f'apertus_{m}'] == r['gold']), w=1.0, s=0) for r in rows10], order=ordr, test_groups=tg)
                for m in ('pooled', 'de', 'fr')}
# matched prompt language (= shown/original language) vs the other language, paired
m = [int(r[f"apertus_{r['shown_lang']}"] == r['gold']) for r in rows10]
x = [int(r[f"apertus_{'fr' if r['shown_lang'] == 'de' else 'de'}"] == r['gold']) for r in rows10]
rng = random.Random(10); dd = []
for _ in range(NB):
    ii = [rng.randrange(len(m)) for _ in m]; dd.append(sum(m[i] - x[i] for i in ii) / len(m))
b = sum(1 for u, v in zip(m, x) if u and not v); c = sum(1 for u, v in zip(m, x) if v and not u)
mcn = (abs(b - c) - 1) ** 2 / (b + c) if b + c else 0
S10['prompt in original language vs the other (paired)'] = dict(n=len(m), matched=dict(k=sum(m), p=round(sum(m) / len(m), 4), ci=L.wilson(sum(m), len(m))),
    other=dict(k=sum(x), p=round(sum(x) / len(x), 4), ci=L.wilson(sum(x), len(x))), diff=round((sum(m) - sum(x)) / len(m), 4), diff_ci=q(sorted(dd)),
    only_matched_right=b, only_other_right=c, p_mcnemar=round(L.chi2_sf(mcn, 1), 4))
R['S10'] = S10
json.dump(R, open(f'{H}/results.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in R.items() if k.endswith('_check')}, indent=1))
