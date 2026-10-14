"""S27 analysis: precision of S19 flags without and with the verification step; recall among the judged positives (all of
which S19 flagged); paired bootstrap over the flagged items. No model calls."""
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
V = {json.loads(l)["pid"]: json.loads(l) for l in open(HERE / "raw.jsonl")}
def wout(k, n, z=1.96):
    if not n: return None
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return [max(0.0, math.floor((c - h) / d * 1000) / 1000), min(1.0, math.ceil((c + h) / d * 1000) / 1000)]
R = {}
for topic in ("wolf", "hitze", "ki-schule"):
    fl = [p for p, k in K.items() if k["topic"] == topic and k["flag"] and gold(p) in ("Y", "N") and p in V]
    y = lambda p: gold(p) == "Y"
    kept = [p for p in fl if V[p]["keep"]]
    pos = [p for p, k in K.items() if k["topic"] == topic and gold(p) == "Y"]
    rng = random.Random(7); ds = []
    for _ in range(2000):
        s = [rng.choice(fl) for _ in fl]; a = [p for p in s if V[p]["keep"]]
        if a: ds.append(sum(map(y, a)) / len(a) - sum(map(y, s)) / len(s))
    ds.sort()
    R[topic] = dict(flags=len(fl), kept=len(kept), positives=len(pos),
                    precision_s19=dict(value=round(sum(map(y, fl)) / len(fl), 4), ci=wout(sum(map(y, fl)), len(fl))),
                    precision_verified=dict(value=round(sum(map(y, kept)) / len(kept), 4) if kept else None, ci=wout(sum(map(y, kept)), len(kept))),
                    recall_verified=round(sum(V[p]["keep"] for p in pos if p in V) / len(pos), 4) if pos else None,
                    diff=dict(value=round((sum(map(y, kept)) / len(kept) if kept else 0) - sum(map(y, fl)) / len(fl), 4),
                              ci=[math.floor(ds[int(.025 * len(ds))] * 1000) / 1000, math.ceil(ds[int(.975 * len(ds)) - 1] * 1000) / 1000] if ds else None))
(HERE / "results.json").write_text(json.dumps(R, indent=1)); print(json.dumps(R, indent=1))
