"""Lead's offline check: 2-fold cross-fitted 'sure' threshold for subtopics (target: top half by confidence on the fitting fold). No calls."""
import json, os, sys, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import APS, L2_GOLD, load, RAW5, wilson  # noqa
from s5lib import q2_options, CODES_EXT
q2 = load(f'{RAW5}/q2a.jsonl', 'oid'); rows = []
for o, r in q2.items():
    if o not in L2_GOLD: continue
    opts = q2_options(r['chs']); codes = CODES_EXT[:len(opts) + 1]; lp = r['codes']
    best = max(codes, key=lambda c: lp.get(c, -1e9)); z = sum(math.exp(lp[c]) for c in codes if c in lp)
    p = math.exp(lp.get(best, -1e9)) / z; i = codes.index(best)
    rows.append((o, p, i < len(opts) and opts[i][0] == L2_GOLD[o] and opts[i][1] == APS[o]['subtopic_name']))
res = {}
for target in (0.75, 0.80):
    tot_k = tot_h = 0; folds = []
    for seed in range(20):
        rng = random.Random(seed); idx = list(range(len(rows))); rng.shuffle(idx); half = len(idx) // 2
        for fit, app in ((idx[:half], idx[half:]), (idx[half:], idx[:half])):
            F = sorted((rows[j] for j in fit), key=lambda x: -x[1]); thr = None
            for k in range(len(F), 9, -1):
                if sum(x[2] for x in F[:k]) / k >= target: thr = F[k - 1][1]; break
            if thr is None: continue
            A = [rows[j] for j in app if rows[j][1] >= thr]; tot_k += len(A); tot_h += sum(x[2] for x in A); folds.append(len(A) / len(app))
    res[str(target)] = dict(heldout_precision=round(tot_h / tot_k, 3), mean_coverage=round(sum(folds) / len(folds), 3), n_rows=len(rows))
print(json.dumps(res, indent=1)); json.dump(res, open('crossfit.json', 'w'), indent=1)
