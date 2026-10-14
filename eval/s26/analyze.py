"""S26 analysis: precision of flags with editor examples vs S19 (no examples) on the same test items, paired bootstrap;
flags and recall among the judged positives of the test items. No model calls."""
import json, math, random
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]; S19 = ROOT / "eval/s19"
K = {json.loads(l)["pid"]: json.loads(l) for l in open(S19 / "key.jsonl")}
def rd(p):
    d = {}
    if (S19 / p).exists():
        for line in (S19 / p).read_text().splitlines():
            x = line.split("\t")
            if len(x) >= 2 and x[1].strip(): d[x[0]] = x[1].strip().upper()[:1]
    return d
A, B, C = rd("ann_A.tsv"), rd("ann_B.tsv"), rd("ann_C.tsv")
gold = lambda p: A[p] if A.get(p) in ("Y", "N") and A.get(p) == B.get(p) else C.get(p)
R26 = {json.loads(l)["pid"]: json.loads(l) for l in open(HERE / "raw.jsonl")}
split = json.loads((HERE / "split.json").read_text())


def wout(k, n, z=1.96):
    if not n: return None
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return [math.floor((c - h) / d * 1000) / 1000, math.ceil((c + h) / d * 1000) / 1000]


R = {}
for slug, s in split.items():
    test = [p for p in s["test"] if p in R26]
    f19 = [p for p in test if K[p]["flag"]]; f26 = [p for p in test if R26[p]["flag"]]
    y = lambda p: gold(p) == "Y"
    pos = [p for p in test if y(p)]
    k19, k26 = sum(map(y, f19)), sum(map(y, f26))
    # paired bootstrap of the precision difference over test items
    rng = random.Random(7); ds = []
    for _ in range(2000):
        smp = [rng.choice(test) for _ in test]
        a = [p for p in smp if R26[p]["flag"]]; b = [p for p in smp if K[p]["flag"]]
        if a and b: ds.append(sum(map(y, a)) / len(a) - sum(map(y, b)) / len(b))
    ds.sort()
    R[slug] = dict(n_test=len(test), editor_examples=len(s["editor"]), positives=len(pos),
                   s19=dict(flags=len(f19), precision=round(k19 / len(f19), 4) if f19 else None, ci=wout(k19, len(f19)), recall=round(sum(K[p]["flag"] for p in pos) / len(pos), 4) if pos else None),
                   s26=dict(flags=len(f26), precision=round(k26 / len(f26), 4) if f26 else None, ci=wout(k26, len(f26)), recall=round(sum(R26[p]["flag"] for p in pos) / len(pos), 4) if pos else None),
                   precision_diff=dict(value=round((k26 / len(f26) if f26 else 0) - (k19 / len(f19) if f19 else 0), 4),
                                       ci=[math.floor(ds[int(.025 * len(ds))] * 1000) / 1000, math.ceil(ds[int(.975 * len(ds)) - 1] * 1000) / 1000] if ds else None))
(HERE / "results.json").write_text(json.dumps(R, indent=1)); print(json.dumps(R, indent=1))
