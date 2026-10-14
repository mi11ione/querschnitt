"""S8 scoring (lead): population-weighted precision/recall for Apertus and keyword against blind gold.
Gold = A and B agree on Y/N (a '?' counts as disagreement) else tie-break C. Sensitivity: majority of A, B, Qwen.
Weights: key.jsonl final_weight (design weight x stratum N_h/n_h). Bootstrap: resample items within packet strata, 2,000.
Usage: python3 -I score.py [--c-template]"""
import json, sys, random, collections, pathlib
H = pathlib.Path(__file__).resolve().parent
DVS9 = {'BE', 'CHE', 'ZG', 'OW', 'TG', 'BS', 'ZH', 'AG', 'BL'}

def rd(p):
    d = {}
    if not (H / p).exists() and not pathlib.Path(p).exists(): return d
    f = (H / p) if (H / p).exists() else pathlib.Path(p)
    for line in f.read_text().splitlines():
        x = line.rstrip('\n').split('\t')
        if len(x) >= 2 and x[0].startswith('D') and x[1].strip():
            d[x[0]] = 'Q' if (len(x) > 2 and x[2].strip() == '?') else x[1].strip().upper()
    return d

K = {r['pid']: r for r in map(json.loads, (H / 'key.jsonl').read_text().splitlines())}
A, B, C = rd('ann_A.tsv'), rd('ann_B.tsv'), rd('ann_C.tsv')
Qw = rd('../s8q-crossfamily/ann_Q.tsv')
dis = sorted(i for i in K if A.get(i) in ('Y', 'N') and B.get(i) in ('Y', 'N') and A[i] != B[i] or (i in A and i in B and ('Q' in (A[i], B[i]))))
if '--c-template' in sys.argv:
    (H / 'packet/ann_C_TEMPLATE.tsv').write_text(''.join(f'{i}\t\n' for i in dis)); print('C ids', len(dis)); sys.exit()

def gold(i):
    if A.get(i) in ('Y', 'N') and A.get(i) == B.get(i): return A[i]
    return C.get(i) if C.get(i) in ('Y', 'N') else None

def gold_maj(i):
    v = [x for x in (A.get(i), B.get(i), Qw.get(i)) if x in ('Y', 'N')]
    return None if len(v) < 2 else ('Y' if v.count('Y') * 2 > len(v) else 'N' if v.count('N') * 2 > len(v) else None)

def est(items, g):
    t = collections.Counter()
    for i in items:
        r = K[i]; y = g(i)
        if y is None: continue
        w = r['final_weight']; a = r['p_yes'] >= 0.5; k = bool(r['kw'])
        t['pos'] += w * (y == 'Y')
        t['a_tp'] += w * (a and y == 'Y'); t['a_fp'] += w * (a and y == 'N'); t['a_fn'] += w * ((not a) and y == 'Y')
        t['k_tp'] += w * (k and y == 'Y'); t['k_fp'] += w * (k and y == 'N'); t['k_fn'] += w * ((not k) and y == 'Y')
    f = lambda tp, x: tp / (tp + x) if tp + x else float('nan')
    return dict(pos=t['pos'], a_P=f(t['a_tp'], t['a_fp']), a_R=f(t['a_tp'], t['a_fn']), k_P=f(t['k_tp'], t['k_fp']), k_R=f(t['k_tp'], t['k_fn']),
                a_flags=t['a_tp'] + t['a_fp'], k_flags=t['k_tp'] + t['k_fp'])

def boot(g, n=2000, seed=7):
    rng = random.Random(seed); by = collections.defaultdict(list)
    for i in K: by[K[i]['stratum']].append(i)
    out = collections.defaultdict(list)
    for _ in range(n):
        s = [rng.choice(v) for v in by.values() for _ in v]
        e = est(s, g)
        for k, v in e.items(): out[k].append(v)
        out['dP'].append(e['a_P'] - e['k_P']); out['dR'].append(e['a_R'] - e['k_R'])
    ci = lambda v: (round(sorted(v)[int(.025 * len(v))], 3), round(sorted(v)[int(.975 * len(v)) - 1], 3))
    return {k: ci([x for x in v if x == x]) for k, v in out.items()}

def kappa(X, Y):
    ids = [i for i in K if X.get(i) in ('Y', 'N') and Y.get(i) in ('Y', 'N')]
    if not ids: return (0, None, None)
    po = sum(X[i] == Y[i] for i in ids) / len(ids)
    px, py = sum(X[i] == 'Y' for i in ids) / len(ids), sum(Y[i] == 'Y' for i in ids) / len(ids)
    pe = px * py + (1 - px) * (1 - py)
    return len(ids), round(po, 3), round((po - pe) / (1 - pe), 3)

res = {}
res['annotators'] = dict(nA=len(A), nB=len(B), nC=len(C), nQ=len(Qw), AB=kappa(A, B), AQ=kappa(A, Qw), BQ=kappa(B, Qw),
                         disagreements=len(dis), gold_missing=sum(gold(i) is None for i in K))
for name, g in (('gold_AB_C', gold), ('gold_majority_ABQ', gold_maj)):
    e = est(list(K), g); b = boot(g)
    res[name] = dict(point={k: round(v, 3) for k, v in e.items()}, ci=b,
                     d_precision=round(e['a_P'] - e['k_P'], 3), d_recall=round(e['a_R'] - e['k_R'], 3))
# coverage among blind-confirmed positives (primary gold)
posi = [i for i in K if gold(i) == 'Y']
w = lambda i: K[i]['final_weight']
res['positives'] = dict(
    n_packet=len(posi), parliaments=len({K[i]['body'] for i in posi}),
    parliaments_outside_dvs9=len({K[i]['body'] for i in posi} - DVS9),
    est_total=round(sum(w(i) for i in posi), 1),
    est_outside_dvs9=round(sum(w(i) for i in posi if K[i]['body'] not in DVS9), 1),
    est_by_level={l: round(sum(w(i) for i in posi if K[i]['level'] == l), 1) for l in ('federal', 'cantonal', 'communal', 'other')},
    est_by_lang={l: round(sum(w(i) for i in posi if K[i]['lang'] == l), 1) for l in ('de', 'fr', 'it')},
    packet_by_level=collections.Counter(K[i]['level'] for i in posi), packet_by_lang=collections.Counter(K[i]['lang'] for i in posi),
    on_dvs_list=sum(K[i]['on_dvs_list'] for i in posi),
    apertus_found_kw_missed=sum(1 for i in posi if K[i]['p_yes'] >= 0.5 and not K[i]['kw']),
    est_apertus_found_kw_missed=round(sum(w(i) for i in posi if K[i]['p_yes'] >= 0.5 and not K[i]['kw']), 1),
    kw_found_apertus_missed=sum(1 for i in posi if K[i]['p_yes'] < 0.5 and K[i]['kw']),
    est_kw_found_apertus_missed=round(sum(w(i) for i in posi if K[i]['p_yes'] < 0.5 and K[i]['kw']), 1))
# bootstrap interval for est_total and est_outside_dvs9
rng = random.Random(11); by = collections.defaultdict(list)
for i in K: by[K[i]['stratum']].append(i)
tot, out9 = [], []
for _ in range(2000):
    s = [rng.choice(v) for v in by.values() for _ in v]
    tot.append(sum(w(i) for i in s if gold(i) == 'Y')); out9.append(sum(w(i) for i in s if gold(i) == 'Y' and K[i]['body'] not in DVS9))
q = lambda v: (round(sorted(v)[50], 1), round(sorted(v)[1949], 1))
res['positives']['est_total_ci'] = q(tot); res['positives']['est_outside_dvs9_ci'] = q(out9)
# per stratum confirmation rates
res['by_stratum'] = {s: dict(n=len(v), gold_Y=sum(gold(i) == 'Y' for i in v), gold_N=sum(gold(i) == 'N' for i in v)) for s, v in by.items()}
(H / 'score.json').write_text(json.dumps(res, indent=1, ensure_ascii=False, default=dict))
print(json.dumps(res, indent=1, ensure_ascii=False, default=dict))
