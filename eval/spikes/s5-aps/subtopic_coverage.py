"""Lead's offline check: precision-at-coverage for the joint subtopic step (order a), and majority baselines. No calls."""
import json, os, sys, math, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import APS, L2_GOLD, load, RAW5, APS_CODES, SUBS, wilson  # noqa
from s5lib import q2_options, CODES_EXT
q2 = load(f'{RAW5}/q2a.jsonl', 'oid')
rows = []
for o, r in q2.items():
    if o not in L2_GOLD: continue
    opts = q2_options(r['chs']); codes = CODES_EXT[:len(opts) + 1]
    lp = r['codes']; best = max(codes, key=lambda c: lp.get(c, -1e9))
    z = sum(math.exp(lp[c]) for c in codes if c in lp); p = math.exp(lp.get(best, -1e9)) / z if z else 0
    a = APS[o]; i = codes.index(best)
    ok = i < len(opts) and opts[i][0] == L2_GOLD[o] and opts[i][1] == a['subtopic_name']
    chok = i < len(opts) and opts[i][0] == L2_GOLD[o]
    rows.append((p, ok, chok))
rows.sort(key=lambda x: -x[0]); n = len(rows); out = {'n': n}
for cov in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3):
    k = max(1, round(cov * n)); s = rows[:k]; h = sum(x[1] for x in s); c = sum(x[2] for x in s)
    out[f'cov{cov}'] = dict(k=k, p_min=round(s[-1][0], 3), subtopic_prec=round(h / k, 3), ci=wilson(h, k), chapter_prec=round(c / k, 3))
ch = collections.Counter(a['chapter_code'] for a in APS.values()); top, m = ch.most_common(1)[0]
out['aps_majority'] = dict(chapter=top, acc=round(m / len(APS), 3), n=len(APS))
print(json.dumps(out, indent=1)); json.dump(out, open('subtopic_coverage.json', 'w'), indent=1)
