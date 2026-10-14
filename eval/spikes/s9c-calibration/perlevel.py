"""Per-chapter precision/recall, macro-F1 for D1 and D3 chapters on S9 (no calls)."""
import sys, json, collections
sys.path.insert(0, '/Users/mi11ion/Desktop/hackapertus/bern/ideation2/spikes/s9-aps/scripts')
from s9lib import DATA, RAW, geo2, load
items = {it['oid']: it for it in json.load(open(f'{DATA}/items.json'))}
raw = {ph: load(f'{RAW}/{ph}.jsonl') for ph in ('d0a', 'd0b', 'd1', 'd3m')}
order = lambda p: sorted(range(len(p)), key=lambda i: -p[i])
def d1(o):
    a, b = raw['d0a'][o]['p'], raw['d0b'][o]['p']; PA = [(x + y) / 2 for x, y in zip(a, b)]
    r = raw['d1'][o]; sc = {(c, s): r['p'][i] * PA[c] for i, (c, s) in enumerate(r['opts'])}
    return max(sc, key=sc.get)[0]
d3 = lambda o: order(geo2(raw['d3m'][o]['p'], raw['d0b'][o]['p']))[0]
out = {}
for name, fn in (('D1', d1), ('D3', d3)):
    pairs = [(int(items[o]['chapter']), fn(o)) for o in items if o in raw['d1'] and o in raw['d3m']]
    labs = sorted({g for g, _ in pairs})
    f1s = []; rows = {}
    for c in labs:
        tp = sum(1 for g, p in pairs if g == c and p == c); fp = sum(1 for g, p in pairs if g != c and p == c); fn_ = sum(1 for g, p in pairs if g == c and p != c)
        P = tp / (tp + fp) if tp + fp else 0; R = tp / (tp + fn_) if tp + fn_ else 0; F = 2 * P * R / (P + R) if P + R else 0
        f1s.append(F); rows[c] = dict(n=tp + fn_, P=round(P, 3), R=round(R, 3), F1=round(F, 3))
    out[name] = dict(n=len(pairs), acc=round(sum(g == p for g, p in pairs) / len(pairs), 3), macro_F1=round(sum(f1s) / len(f1s), 3),
                     chapters=len(labs), worst=sorted(rows.items(), key=lambda kv: kv[1]['F1'])[:3], best=sorted(rows.items(), key=lambda kv: -kv[1]['F1'])[:3])
json.dump(out, open('perlevel.json', 'w'), indent=1); print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk in ('n', 'acc', 'macro_F1', 'chapters')} for k, v in out.items()}))
