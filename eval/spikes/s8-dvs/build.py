"""S8 post-processing. python3 -I build.py snapshot  -> copies raw a/b to snapshot/, writes flags, packet, key, loop_order, results_auto.md
                      python3 -I build.py live      -> estimates from live raw only, results_live.md (never touches packet/key)."""
import sys, os, json, gzip, random, collections, math, shutil, statistics, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/Users/mi11ion/Desktop/hackapertus/bern/ideation2/lib')
from common import *
import pai
MODE = sys.argv[1]; assert MODE in ('snapshot', 'live', 'resnap')  # resnap: recompute results from snapshot/, verify packet unchanged
if MODE == 'snapshot':
    assert not os.path.exists(f'{HERE}/packet/items.txt'), 'packet exists - frozen'
    os.makedirs(f'{HERE}/snapshot', exist_ok=True)
    for f in ('a.jsonl', 'b.jsonl', 'throughput.jsonl'):
        if os.path.exists(f'{HERE}/raw/{f}'):
            lines = open(f'{HERE}/raw/{f}').read().splitlines(); lines = [l for l in lines if l.endswith('}')]  # drop a torn last line
            open(f'{HERE}/snapshot/{f}', 'w').write('\n'.join(lines) + '\n')
    SRC = f'{HERE}/snapshot'
elif MODE == 'resnap':
    SRC = f'{HERE}/snapshot'
else:
    SRC = f'{HERE}/raw'
SNAP_T = json.load(open(f'{HERE}/snapshot/snapshot.json'))['t'] if MODE == 'resnap' else time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
def rd(p):
    out = {}
    if os.path.exists(p):
        for l in open(p):
            if l.strip().endswith('}'): r = json.loads(l); out.setdefault(r['id'], r)
    return out
I = json.load(open(f'{HERE}/items_cache.json')); B = load_bodies(); IT = {x['id']: x for x in I}
O = json.load(open(f'{HERE}/order.json'))
RA, RB = rd(f'{SRC}/a.jsonl'), rd(f'{SRC}/b.jsonl')
def complete(i): return i in RA and (not (0.1 < RA[i]['p_yes'] < 0.9) or i in RB)
CF = O['census_from']
C = [i for i in IT if IT[i]['in_window'] and IT[i]['title'] and IT[i]['date'] >= CF]
c_missing = [i for i in C if not complete(i)]
NR = len(O['srs']); nR = 0
for i in O['srs']:
    if not complete(i): break
    nR += 1
PRE = set(O['srs'][:nR]); WR = NR / nR if nR else float('nan')

def wilson(k, n, z=1.96):
    if n == 0: return (float('nan'),) * 2
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)

rows = []
for x in I:
    i = x['id']; a = RA.get(i); b = RB.get(i)
    pa = a['p_yes'] if a else None; pb = b['p_yes'] if b else None
    p = None if pa is None else (pa + pb) / 2 if pb is not None else pa
    design = 'census' if (i in C) else 'srs' if i in PRE else None
    rows.append(dict(id=i, body=x['body'], level=x['level'], lang=x['lang'], date=x['date'], week=x['week'], in_window=x['in_window'],
                     on_dvs_list=x['on_dvs_list'], p_a=pa, p_b=pb, b_needed=pa is not None and 0.1 < pa < 0.9, p=p,
                     flag=None if p is None else p >= 0.5, kw=x['kw'], orders_disagree=None if pb is None else ((pa >= 0.5) != (pb >= 0.5)),
                     please_check=None if p is None else bool((pb is not None and (pa >= 0.5) != (pb >= 0.5)) or 0.3 <= p < 0.7),
                     design=design, design_weight=1.0 if design == 'census' else WR if design == 'srs' else None,
                     srs_rank=(O['srs'].index(i) if i in set(O['srs']) else None)))
R = {r['id']: r for r in rows}
S = [r for r in rows if r['design'] and r['p'] is not None]       # design sample
SC = [r for r in S if r['design'] == 'census']; SR = [r for r in S if r['design'] == 'srs']
fn = 'flags.jsonl.gz' if MODE in ('snapshot', 'resnap') else 'flags_live.jsonl.gz'
with gzip.open(f'{HERE}/{fn}', 'wt') as f:
    for r in rows: f.write(json.dumps(r, ensure_ascii=False) + '\n')

def est(pred, sub_c=SC, sub_r=SR, N_r=NR):
    """census count + N_r * sample share (Wilson 95% on the SRS share; fpc ignored -> conservative)."""
    kc = sum(1 for r in sub_c if pred(r)); kr = sum(1 for r in sub_r if pred(r)); n = len(sub_r)
    if n == 0: return kc, (kc, kc), kc, kr, n
    lo, hi = wilson(kr, n)
    return kc + N_r * kr / n, (kc + N_r * lo, kc + N_r * hi), kc, kr, n
def fmt(e): return f"{e[0]:.1f} [{e[1][0]:.1f}, {e[1][1]:.1f}] (census {e[2]} + SRS {e[3]}/{e[4]})"

L = []; P = L.append
P(f'## Results ({MODE}, data as of {SNAP_T} UTC; source {os.path.relpath(SRC, HERE)}/)')
nwin = sum(1 for x in I if x['in_window']); nti = sum(1 for x in I if x['in_window'] and x['title'])
nsc = sum(1 for x in I if x['in_window'] and complete(x['id']))
P(f'- Window affairs (begin_date {LO}..{HI}): {nwin}; titled: {nti}; scored complete (A, plus B where 0.1<p_A<0.9) in window: {nsc}')
P(f'- Order-A rows: {len(RA)}; order B needed among them: {sum(1 for r in RA.values() if 0.1 < r["p_yes"] < 0.9)}, B rows: {len(RB)}')
P(f'- Design sample: census C ({CF}..{HI}) N=n={len(C)} (missing {len(c_missing)}); SRS stratum R (2026-01-01..{CF} excl.) N_R={NR}, n_R={nR} '
  f'(sampling fraction {nR/NR:.4f}, weight {WR:.3f}); scored affairs outside the design (DVS out-of-order, prefix gaps): {nsc - len(S)}')
cov = 'complete census (all titled window affairs scored)' if nR == NR and not c_missing else 'PARTIAL: estimates below are design-weighted'
P(f'- Coverage: {cov}')
F = lambda r: r['flag']; Kf = lambda r: r['kw']; PC = lambda r: r['please_check']
P(f'- Apertus flags (p>=0.5), estimated window total: {fmt(est(F))}')
P(f'- Keyword flags, estimated window total: {fmt(est(Kf))}')
P(f'- Please-check (orders disagree or 0.3<=p<0.7), estimated total: {fmt(est(PC))}')
P(f'- Both flags (A∩K): {fmt(est(lambda r: r["flag"] and r["kw"]))}; A only: {fmt(est(lambda r: r["flag"] and not r["kw"]))}; '
  f'K only: {fmt(est(lambda r: (not r["flag"]) and r["kw"]))}')
P(f'- Distinct parliaments among Apertus flags in the design sample: {len({r["body"] for r in S if r["flag"]})} '
  f'(of {len({r["body"] for r in S})} parliaments present in the sample; of 86 in the window) — a lower bound for the window; '
  f'among keyword flags: {len({r["body"] for r in S if r["kw"]})}')
def table(key, vals, title):
    P(f'\n### {title} (estimated window totals; census + N_R,group x SRS share within group, Wilson 95%; post-stratified)')
    P(f'| {key} | N window | sample n | Apertus flags (sample) | est. flags [95%] | kw flags (sample) | est. kw [95%] |'); P('|---|---|---|---|---|---|---|')
    for v in vals:
        sc = [r for r in SC if r[key] == v]; sr = [r for r in SR if r[key] == v]
        Nw = sum(1 for x in I if x['in_window'] and x['title'] and x[key] == v); Nrg = sum(1 for i in O['srs'] if IT[i][key] == v)
        e1 = est(F, sc, sr, Nrg); e2 = est(Kf, sc, sr, Nrg)
        P(f'| {v} | {Nw} | {len(sc) + len(sr)} | {e1[2] + e1[3]} | {e1[0]:.1f} [{e1[1][0]:.1f}, {e1[1][1]:.1f}] | {e2[2] + e2[3]} | {e2[0]:.1f} [{e2[1][0]:.1f}, {e2[1][1]:.1f}] |')
table('level', ['federal', 'cantonal', 'communal', 'other'], 'By level')
table('lang', ['de', 'fr', 'it'], 'By prompt language')
P('\n### By body (counts in the design sample; est. = census + N_R,body x SRS share within body, point only)')
P('| body | level | N window | sample n | flags (sample) | est. flags | kw (sample) |'); P('|---|---|---|---|---|---|---|')
for bk, n in collections.Counter(x['body'] for x in I if x['in_window'] and x['title']).most_common():
    sc = [r for r in SC if r['body'] == bk]; sr = [r for r in SR if r['body'] == bk]; Nrg = sum(1 for i in O['srs'] if IT[i]['body'] == bk)
    P(f'| {bk} | {level(bk, B)} | {n} | {len(sc) + len(sr)} | {sum(r["flag"] for r in sc + sr)} | {est(F, sc, sr, Nrg)[0]:.1f} | {sum(r["kw"] for r in sc + sr)} |')
P('\n### Weekly lane (P8.4), ISO week of begin_date; post-stratified by week: census part + N_R,week x (SRS share within week)')
P('| week | N window | sample n | flags (sample) | est. flags | please-check (sample) | est. please-check | please-check share of flags (sample) |'); P('|---|---|---|---|---|---|---|---|')
wk_est = []
for wk in sorted({x['week'] for x in I if x['in_window'] and x['title']}):
    sc = [r for r in SC if r['week'] == wk]; sr = [r for r in SR if r['week'] == wk]
    Nrw = sum(1 for i in O['srs'] if IT[i]['week'] == wk); Nw = sum(1 for x in I if x['in_window'] and x['title'] and x['week'] == wk)
    ef = est(F, sc, sr, Nrw); ep = est(PC, sc, sr, Nrw); fl = [r for r in sc + sr if r['flag']]
    wk_est.append(ef[0])
    P(f'| {wk} | {Nw} | {len(sc) + len(sr)} | {len(fl)} | {ef[0]:.1f} | {sum(r["please_check"] for r in sc + sr)} | {ep[0]:.1f} | '
      f'{(sum(r["please_check"] for r in fl) / len(fl)) if fl else float("nan"):.3f} |')
fl = [r for r in S if r['flag']]
P(f'\nWeekly est. flags: median {statistics.median(wk_est):.1f}, min {min(wk_est):.1f}, max {max(wk_est):.1f} over {len(wk_est)} ISO weeks (2026-W01 and W41 partial). '
  f'Please-check share among flags in the sample: {sum(r["please_check"] for r in fl)}/{len(fl)}; among all sampled: {sum(r["please_check"] for r in S)}/{len(S)}.')
D = [r for r in rows if r['on_dvs_list']]
for lab, s in (('all 30', D), ('begin_date in window', [r for r in D if r['in_window']])):
    s = [r for r in s if r['p'] is not None and (not r['b_needed'] or r['p_b'] is not None)]
    k = sum(r['flag'] for r in s); kk = sum(r['kw'] for r in s); w1, w2 = wilson(k, len(s)), wilson(kk, len(s))
    P(f'\n- DVS recall (P8.2, {lab}): Apertus {k}/{len(s)} [{w1[0]:.3f}, {w1[1]:.3f}]; keyword {kk}/{len(s)} [{w2[0]:.3f}, {w2[1]:.3f}]')

if MODE in ('snapshot', 'resnap'):
    rng = random.Random(20261014)
    ST = collections.OrderedDict([('A∩K', (lambda r: r['flag'] and r['kw'], 120)), ('A only', (lambda r: r['flag'] and not r['kw'], 150)),
                                  ('K only', (lambda r: not r['flag'] and r['kw'], 100)), ('neither', (lambda r: not r['flag'] and not r['kw'], 180))])
    pick = []; P('\n### Strata (design sample) and blind packet'); P('| stratum | N in design sample | est. N window | sampled n |'); P('|---|---|---|---|')
    for name, (f_, cap) in ST.items():
        pop = sorted((r for r in S if f_(r)), key=lambda r: r['id'])
        smp = rng.sample(pop, min(cap, len(pop)))
        Nh = len(pop); pick += [(name, r, Nh, len(smp)) for r in smp]
        P(f'| {name} | {Nh} | {sum(r["design_weight"] for r in pop):.1f} | {len(smp)} |')
    rng.shuffle(pick)
    def clean(s): return ' '.join((s or '').split())
    PK = f'{HERE}/packet' if MODE == 'snapshot' else f'{HERE}/snapshot/verify'; KY = f'{HERE}/key.jsonl' if MODE == 'snapshot' else f'{PK}/key.jsonl'
    os.makedirs(PK, exist_ok=True)
    shutil.copyfile(f'{S4}/packet/GUIDE.md', f'{PK}/GUIDE.md')
    with open(f'{PK}/items.txt', 'w') as fi, open(KY, 'w') as fk, open(f'{PK}/ann_TEMPLATE.tsv', 'w') as ft:
        for j, (name, r, Nh, nh) in enumerate(pick, 1):
            pid = f'D{j:03d}'; x = IT[r['id']]
            tl = clean(x['title_long']) if x['title_long'] and x['title_long'] != x['title'] else ''
            fi.write('\t'.join([pid, parl_name(x['body'], B), x['level'], clean(x['type']), x['date'], clean(x['title']), tl[:300]]) + '\n')
            fk.write(json.dumps(dict(pid=pid, oid=r['id'], body=r['body'], level=r['level'], lang=r['lang'], stratum=name, p_yes=r['p'],
                                     p_a=r['p_a'], p_b=r['p_b'], kw=r['kw'], on_dvs_list=r['on_dvs_list'], design=r['design'],
                                     design_weight=r['design_weight'], stratum_N_sample=Nh, stratum_n=nh,
                                     final_weight=r['design_weight'] * Nh / nh), ensure_ascii=False) + '\n')
            ft.write(f'{pid}\t\n')
    ids = sorted(f'D{j:03d}' for j in range(1, len(pick) + 1)); random.Random(60).shuffle(ids)
    json.dump(dict(seed=60, note='sorted packet ids shuffled with random.Random(60); first 60 = editor first decisions (P8.5); loop not run',
                   order=ids), open(f'{HERE}/loop_order.json' if MODE == 'snapshot' else f'{PK}/loop_order.json', 'w'), indent=0)
    if MODE == 'resnap':
        import filecmp
        same = all(filecmp.cmp(a, b, shallow=False) for a, b in [(f'{PK}/items.txt', f'{HERE}/packet/items.txt'), (KY, f'{HERE}/key.jsonl'), (f'{PK}/loop_order.json', f'{HERE}/loop_order.json')])
        P(f'\n(resnap: packet/key/loop_order regenerated from snapshot/ are byte-identical to the frozen ones: {same})')
        assert same
    if MODE == 'snapshot': json.dump(dict(t=SNAP_T, nR=nR, NR=NR, census=len(C), a_rows=len(RA), b_rows=len(RB)), open(f'{HERE}/snapshot/snapshot.json', 'w'))
    P(f'\nPacket: {len(pick)} items D001..D{len(pick):03d} (packet/items.txt, ann_TEMPLATE.tsv, GUIDE.md = byte copy of S4 GUIDE.md); key.jsonl outside packet/ '
      f'(final_weight = design_weight x N_h/n_h for population-weighted P8.1); loop_order.json seed 60.')

TP = [json.loads(l) for l in open(f'{SRC}/throughput.jsonl')] if os.path.exists(f'{SRC}/throughput.jsonl') else []
P('\n### Throughput, 3 workers, alongside the separate bulk job and other spikes (P8.6), one row per 500 calls')
P('| UTC | orders | calls | wall s | req/s | HTTP p50 s | HTTP p95 s | 429s | errors |'); P('|---|---|---|---|---|---|---|---|---|')
for t in TP:
    P(f'| {time.strftime("%H:%M", time.gmtime(t["ts"]))} | {t["order"]} | {t["calls"]} | {t["wall_s"]} | {t["req_per_s"]} | {t["http_p50"]} | {t["http_p95"]} | {t["n429"]} | {t["errors"]} |')
allr = list(RA.values()) + list(RB.values())
s = sorted(r['secs'] for r in allr if not r['cached']); n429 = sum(sum(1 for h in r['http'] if h == 429) for r in allr); ts = sorted(r['ts'] for r in allr)
P(f'\nOverall: {len(allr)} calls in {ts[-1] - ts[0]:.0f} s = {len(allr) / (ts[-1] - ts[0]):.3f} req/s (incl. the 1 min restart at 18:23); pai secs per call (incl. backoff) '
  f'p50 {statistics.median(s):.3f} s, p95 {s[int(0.95 * (len(s) - 1))]:.3f} s; 429 responses {n429}; calls needing a retry {sum(1 for r in allr if len(r["http"]) > 1)}')
P(f'Fingerprints: {dict(collections.Counter(r["fp"] for r in allr))}; served: {dict(collections.Counter(r["served"] for r in allr))}')
_, by = pai._read_ledger()
P(f'\nSpend (pai ledger, list price): ' + ', '.join(f'{k} ${v:.4f}' for k, v in sorted(by.items()) if k.startswith('bern2-s8-')) +
  f'; total ${sum(v for k, v in by.items() if k.startswith("bern2-s8-")):.4f} of $3.00 cap')
out = 'results_auto.md' if MODE in ('snapshot', 'resnap') else 'results_live.md'
open(f'{HERE}/{out}', 'w').write('\n'.join(L) + '\n')
open(f'{HERE}/results.md', 'w').write(open(f'{HERE}/results_head.md').read() + '\n' + open(f'{HERE}/results_auto.md').read() if os.path.exists(f'{HERE}/results_auto.md') else open(f'{HERE}/results_head.md').read() + '\n' + '\n'.join(L) + '\n')
print('\n'.join(L[:14]))
