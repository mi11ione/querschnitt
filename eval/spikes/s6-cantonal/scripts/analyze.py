"""S6 analysis of A1 (raw/a1.jsonl) and A2 (raw/a2.jsonl). No calls. Usage: python3 -I analyze.py -> ../analysis.json"""
import json, os, sys, math, random, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s6lib import S6, RAW6, APS_CODES, BUILD_S3, wilson
import s1lib, be_scheme as B

C = collections.Counter
PIN, POUT = 0.10, 0.20   # USD per 1M tokens (gw PRICES for -8b)


def recs_stats(recs):
    fps = C(r['fp'] for r in recs); models = C(r['model'] for r in recs)
    st = C(s for r in recs for s in r['statuses'])
    return dict(calls=len(recs), cached=sum(bool(r['cached']) for r in recs), fps=dict(fps), models=dict(models),
                statuses={str(k): v for k, v in st.items()}, pt=sum(r['pt'] for r in recs), ct=sum(r['ct'] for r in recs),
                usd_ledger=round(sum(r['usd'] for r in recs), 5))


def a1():
    R = [json.loads(l) for l in open(f'{RAW6}/a1.jsonl')]
    out = dict(n=len(R))
    allrecs = [x for r in R for x in r['recs']]
    out['receipts'] = recs_stats(allrecs)
    nm = lambda c: 'none' if c == 24 else f"{APS_CODES[c]} {s1lib.CH_DE[c]}"
    out['final_dist'] = {lv: C(nm(r['final']) for r in R if lv == 'all' or r['level'] == lv).most_common()
                         for lv in ('all', 'cantonal', 'communal')}
    out['l1_dist_all'] = C(nm(r['l1_top1']) for r in R).most_common()
    out['final_changed_from_l1'] = sum(r['final'] != r['l1_top1'] for r in R)
    out['l2_none_picks'] = sum(r['l2_chapter'] is None for r in R)
    out['mass_a_min'] = min(r['mass_a'] for r in R)

    def strat(rs):
        n = len(rs)
        sec = [r for r in rs if r['pb'] is not None]
        dis = sum(bool(r['order_disagree']) for r in rs)
        low = sum(r['l1_top1_p'] < 0.5 for r in rs)
        abst = sum(bool(r['order_disagree']) or r['l1_top1_p'] < 0.5 for r in rs)
        l2low = sum(r['l2_pick_p'] < 0.5 for r in rs)
        return dict(n=n, second_order=len(sec), second_share=round(len(sec) / n, 3),
                    order_disagree=dis, order_disagree_share=round(dis / n, 3),
                    top1_p_lt_0_5=low, abstain=abst, abstain_share=round(abst / n, 3), abstain_ci=wilson(abst, n),
                    l2_p_lt_0_5=l2low, none_final=sum(r['final'] == 24 for r in rs),
                    median_top1_p=round(sorted(r['l1_top1_p'] for r in rs)[n // 2], 3),
                    pt_per_affair=round(sum(x['pt'] for r in rs for x in r['recs']) / n, 1),
                    calls_per_affair=round(sum(len(r['recs']) for r in rs) / n, 3))
    S = {'all': R}
    for lv in ('cantonal', 'communal'): S[lv] = [r for r in R if r['level'] == lv]
    for lg in ('de', 'fr', 'it'): S[lg] = [r for r in R if r['lang'] == lg]
    S['text'] = [r for r in R if not r['title_only']]; S['title-only'] = [r for r in R if r['title_only']]
    out['strata'] = {k: strat(v) for k, v in S.items()}
    pt = out['receipts']['pt']; ct = out['receipts']['ct']
    out['usd_per_1000'] = round((pt * PIN + ct * POUT) / 1e6 / len(R) * 1000, 4)
    out['usd_per_1000_ledger'] = round(out['receipts']['usd_ledger'] / len(R) * 1000, 4)
    return out


def boot_diff(x, y, n=2000, seed=1):
    rng = random.Random(seed); m = len(x); ds = []
    for _ in range(n):
        idx = [rng.randrange(m) for _ in range(m)]
        ds.append(sum(x[i] - y[i] for i in idx) / m)
    ds.sort(); return (round(ds[int(0.025 * n)], 3), round(ds[int(0.975 * n)], 3))


def a2():
    S = json.load(open(f'{S6}/a2_sample.json')); items = {it['uid']: it for it in S['items']}; prior = S['prior']
    R = [json.loads(l) for l in open(f'{RAW6}/a2.jsonl')]
    by = collections.defaultdict(dict)
    for r in R: by[r['uid']][r['lang']] = r
    uids = sorted(u for u in by if 'de' in by[u] and 'fr' in by[u])
    labs = B.DIRS + ['none']
    out = dict(n=len(uids), n_eligible=S['n_eligible'], receipts=recs_stats([r['rec'] for r in R]))
    gold = [items[u]['lead'] for u in uids]
    pde = [by[u]['de']['pred'] for u in uids]; pfr = [by[u]['fr']['pred'] for u in uids]
    pool = []
    for u in uids:
        p = [(a + b) / 2 for a, b in zip(by[u]['de']['p'], by[u]['fr']['p'])]
        pool.append(labs[max(range(9), key=lambda i: p[i])])
    maj = [prior[0]] * len(uids)
    kde = [B.keyword_pred(items[u]['title_de'], 'de', prior)[0] for u in uids]
    kfr = [B.keyword_pred(items[u]['title_fr'], 'fr', prior)[0] for u in uids]
    khit_de = sum(B.keyword_pred(items[u]['title_de'], 'de', prior)[1] > 0 for u in uids)
    khit_fr = sum(B.keyword_pred(items[u]['title_fr'], 'fr', prior)[1] > 0 for u in uids)
    n = len(uids)
    def A(pred):
        k = sum(p == g for p, g in zip(pred, gold)); return dict(acc=round(k / n, 3), k=k, ci=wilson(k, n))
    out['acc'] = dict(apertus_de=A(pde), apertus_fr=A(pfr), apertus_pooled=A(pool), majority=A(maj),
                      keyword_de=A(kde), keyword_fr=A(kfr))
    hd = [int(p == g) for p, g in zip(pde, gold)]; hf = [int(p == g) for p, g in zip(pfr, gold)]; hp = [int(p == g) for p, g in zip(pool, gold)]
    hk = [int(p == g) for p, g in zip(kde, gold)]
    out['parity_gap_de_minus_fr'] = dict(gap=round((sum(hd) - sum(hf)) / n, 3), ci=boot_diff(hd, hf),
                                         de_only_right=sum(a and not b for a, b in zip(hd, hf)), fr_only_right=sum(b and not a for a, b in zip(hd, hf)))
    out['pooled_minus_de'] = dict(d=round((sum(hp) - sum(hd)) / n, 3), ci=boot_diff(hp, hd))
    out['de_minus_keyword_de'] = dict(d=round((sum(hd) - sum(hk)) / n, 3), ci=boot_diff(hd, hk))
    agr = sum(a == b for a, b in zip(pde, pfr))
    out['de_fr_top1_agreement'] = dict(k=agr, share=round(agr / n, 3), ci=wilson(agr, n))
    both = [i for i in range(n) if pde[i] == pfr[i]]
    out['acc_when_de_fr_agree'] = dict(n=len(both), acc=round(sum(hd[i] for i in both) / len(both), 3) if both else None)
    dis = [i for i in range(n) if pde[i] != pfr[i]]
    out['acc_when_disagree'] = dict(n=len(dis), de=round(sum(hd[i] for i in dis) / max(1, len(dis)), 3),
                                    fr=round(sum(hf[i] for i in dis) / max(1, len(dis)), 3), pooled=round(sum(hp[i] for i in dis) / max(1, len(dis)), 3))
    out['keyword_coverage'] = dict(de=khit_de, fr=khit_fr)
    out['none_preds'] = dict(de=pde.count('none'), fr=pfr.count('none'), pooled=pool.count('none'))
    out['per_directorate'] = {d: dict(n=gold.count(d), de=sum(1 for p, g in zip(pde, gold) if g == d and p == d),
                                      fr=sum(1 for p, g in zip(pfr, gold) if g == d and p == d),
                                      pooled=sum(1 for p, g in zip(pool, gold) if g == d and p == d),
                                      pred_de=pde.count(d), pred_fr=pfr.count(d)) for d in B.DIRS}
    out['confusions_de'] = [[g, p, c] for (g, p), c in C((g, p) for g, p in zip(gold, pde) if g != p).most_common(8)]
    out['confusions_fr'] = [[g, p, c] for (g, p), c in C((g, p) for g, p in zip(gold, pfr) if g != p).most_common(8)]
    types = C(items[u]['type'] for u in uids)
    out['by_type'] = {t: dict(n=c, de=round(sum(hd[i] for i in range(n) if items[uids[i]]['type'] == t) / c, 3),
                              fr=round(sum(hf[i] for i in range(n) if items[uids[i]]['type'] == t) / c, 3))
                      for t, c in types.most_common(5)}
    out['by_period'] = {per: dict(n=len(ix), de=round(sum(hd[i] for i in ix) / len(ix), 3), fr=round(sum(hf[i] for i in ix) / len(ix), 3))
                        for per, ix in (('2015-2019', [i for i in range(n) if items[uids[i]]['year'] < '2020']),
                                        ('2020+', [i for i in range(n) if items[uids[i]]['year'] >= '2020'])) if ix}
    for lg in ('de', 'fr'):
        rr = [by[u][lg] for u in uids]
        out[f'top1_p_median_{lg}'] = round(sorted(max(r['p']) for r in rr)[n // 2], 3)
        out[f'mass_min_{lg}'] = min(r['mass'] for r in rr)
    pt = out['receipts']['pt']; ct = out['receipts']['ct']
    out['pt_per_call'] = round(pt / len(R), 1)
    out['usd_per_1000_affairs_de_plus_fr'] = round((pt * PIN + ct * POUT) / 1e6 / n * 1000, 4)
    return out


if __name__ == '__main__':
    res = {}
    if os.path.exists(f'{RAW6}/a1.jsonl'): res['a1'] = a1()
    if os.path.exists(f'{RAW6}/a2.jsonl'): res['a2'] = a2()
    json.dump(res, open(f'{S6}/analysis.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False))
