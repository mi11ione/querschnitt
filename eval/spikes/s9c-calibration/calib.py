"""S9c: 2-fold cross-fitted isotonic recalibration of D0/D1/D3 top-1 confidence on S9 items (no model calls)."""
import sys, json, random
sys.path.insert(0, '/Users/mi11ion/Desktop/hackapertus/bern/ideation2/spikes/s9-aps/scripts')
from s9lib import DATA, RAW, geo2, load
items = {it['oid']: it for it in json.load(open(f'{DATA}/items.json'))}
raw = {ph: load(f'{RAW}/{ph}.jsonl') for ph in ('d0a', 'd0b', 'd1', 'd3m')}
order = lambda p: sorted(range(len(p)), key=lambda i: -p[i])
def d0(o): p = geo2(raw['d0a'][o]['p'], raw['d0b'][o]['p']); k = order(p)[0]; return k, p[k]
def d1(o):
    a, b = raw['d0a'][o]['p'], raw['d0b'][o]['p']; PA = [(x + y) / 2 for x, y in zip(a, b)]
    r = raw['d1'][o]; sc = {(c, s): r['p'][i] * PA[c] for i, (c, s) in enumerate(r['opts'])}; tot = sum(sc.values()) or 1
    best = max(sc, key=sc.get); return best[0], sum(v for (c, s), v in sc.items() if c == best[0]) / tot
def d3(o): p = geo2(raw['d3m'][o]['p'], raw['d0b'][o]['p']); k = order(p)[0]; return k, p[k]
def pav(xs, ys):
    pts = sorted(zip(xs, ys)); blocks = []
    for x, y in pts:
        blocks.append([x, x, y, 1])
        while len(blocks) > 1 and blocks[-2][2] / blocks[-2][3] > blocks[-1][2] / blocks[-1][3]:
            b = blocks.pop(); blocks[-1][1] = b[1]; blocks[-1][2] += b[2]; blocks[-1][3] += b[3]
    return [(b[0], b[1], b[2] / b[3]) for b in blocks]
def apply(f, x):
    for lo, hi, v in f:
        if x <= hi: return v
    return f[-1][2]
def ece(ps, ys, bins=10):
    e = 0; n = len(ps)
    for b in range(bins):
        idx = [i for i, p in enumerate(ps) if (b / bins < p <= (b + 1) / bins) or (b == 0 and p == 0)]
        if idx: e += len(idx) / n * abs(sum(ps[i] for i in idx) / len(idx) - sum(ys[i] for i in idx) / len(idx))
    return e
out = {}
for name, fn, need in (('D0', d0, ('d0a', 'd0b')), ('D1', d1, ('d0a', 'd0b', 'd1')), ('D3', d3, ('d3m', 'd0b'))):
    ids = sorted(o for o in items if all(o in raw[ph] for ph in need)); random.Random(3).shuffle(ids)
    rows = [(fn(o), int(items[o]['chapter'])) for o in ids]
    ps = [r[0][1] for r in rows]; ys = [int(r[0][0] == r[1]) for r in rows]
    half = len(ids) // 2; cal = [None] * len(ids)
    for tr, te in ((range(half), range(half, len(ids))), (range(half, len(ids)), range(half))):
        f = pav([ps[i] for i in tr], [ys[i] for i in tr])
        for i in te: cal[i] = apply(f, ps[i])
    out[name] = dict(n=len(ids), acc=round(sum(ys) / len(ys), 3), ece_raw=round(ece(ps, ys), 3), ece_isotonic_crossfit=round(ece(cal, ys), 3),
                     mean_p_raw=round(sum(ps) / len(ps), 3), mean_p_cal=round(sum(cal) / len(cal), 3))
json.dump(out, open('results.json', 'w'), indent=1); print(json.dumps(out, indent=1))
