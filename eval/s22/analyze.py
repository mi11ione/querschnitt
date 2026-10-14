"""S22 (eval/PREREG-BUILD.md): Italian D1 on the S9 items vs the S9 German D1 on the same items. No model calls."""
import json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt import prompts as P  # noqa: E402
S9 = Path("/Users/mi11ion/Desktop/hackapertus/bern/ideation2/spikes/s9-aps")
load = lambda p: {json.loads(l)["oid"]: json.loads(l) for l in open(p)}
items = {x["oid"]: x for x in json.load(open(S9 / "data/items.json"))}
raw = {ph: load(S9 / f"raw/{ph}.jsonl") for ph in ("d0a", "d0b", "d1")}
it = load(HERE / "raw.jsonl")
order = lambda p: sorted(range(len(p)), key=lambda i: -p[i])


def readback(prior, chs, psub):
    opts = P.subtopic_options(chs)
    sc = {(c, j): psub[k] * prior[c] for k, (c, j) in enumerate(opts)}
    best = max(sc, key=sc.get)
    chbest = {}
    for (c, j), v in sc.items():
        chbest[c] = max(chbest.get(c, 0), v)
    return best[0], sorted(chbest, key=lambda c: -chbest[c]) + [c for c in order(prior) if c not in chbest]


def wilson_out(k, n, z=1.96):   # outward to 3 decimals
    import math
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return (math.floor((c - h) / d * 1000) / 1000, math.ceil((c + h) / d * 1000) / 1000)


ids = sorted(o for o in it if o in raw["d1"] and o in raw["d0a"] and o in raw["d0b"])
fps = sorted({f for o in ids for f in it[o]["fp"]})
de, itp = {}, {}
for o in ids:
    PA = [(x + y) / 2 for x, y in zip(raw["d0a"][o]["p"], raw["d0b"][o]["p"])]
    de[o] = readback(PA, raw["d1"][o]["chs"], raw["d1"][o]["p"])
    PI = [(x + y) / 2 for x, y in zip(it[o]["p1"], it[o]["p2"])]
    itp[o] = readback(PI, it[o]["chs"], it[o]["psub"])
g = {o: items[o]["chapter"] for o in ids}
N = len(ids)
kd = sum(de[o][0] == g[o] for o in ids); ki = sum(itp[o][0] == g[o] for o in ids)
R = dict(n=N, builds=fps, de_top1=dict(acc=round(kd / N, 4), ci=wilson_out(kd, N)), it_top1=dict(acc=round(ki / N, 4), ci=wilson_out(ki, N)),
         it_top3=round(sum(g[o] in itp[o][1][:3] for o in ids) / N, 4), de_top3=round(sum(g[o] in de[o][1][:3] for o in ids) / N, 4))
va = [int(de[o][0] == g[o]) for o in ids]; vb = [int(itp[o][0] == g[o]) for o in ids]
rng = random.Random(2026); ds = []
for _ in range(2000):
    s = [rng.randrange(N) for _ in range(N)]; ds.append(sum(va[i] - vb[i] for i in s) / N)
ds.sort(); R["de_minus_it"] = dict(diff=round((kd - ki) / N, 4), ci=(round(ds[50], 4), round(ds[1949], 4)))
for flag, name in ((True, "it_with_text"), (False, "it_title_only")):
    s = [o for o in ids if it[o]["text"] == flag]; k = sum(itp[o][0] == g[o] for o in s); kd_ = sum(de[o][0] == g[o] for o in s)
    R[name] = dict(n=len(s), acc=round(k / len(s), 4) if s else None, de_same_items=round(kd_ / len(s), 4) if s else None)
(HERE / "results.json").write_text(json.dumps(R, indent=1)); print(json.dumps(R, indent=1))
