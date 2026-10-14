"""S19 (eval/PREREG-BUILD.md): three new ad-hoc topics vs a blind judge. Precision of Apertus flags, recall estimated with
the neither-stratum sampling weight, the same for the frozen keywords; stratified bootstrap (2,000). No model calls.
`--c-template` writes the tie-break list (ids where A and B differ)."""
import collections, json, math, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
K = [json.loads(l) for l in open(HERE / "key.jsonl")]


def rd(p):
    d = {}
    if not (HERE / p).exists():
        return d
    for line in (HERE / p).read_text().splitlines():
        x = line.rstrip("\n").split("\t")
        if len(x) >= 2 and x[1].strip():
            d[x[0]] = x[1].strip().upper()[:1]
    return d


A, B, C = rd("ann_A.tsv"), rd("ann_B.tsv"), rd("ann_C.tsv")
if "--c-template" in sys.argv:
    dis = [k["pid"] for k in K if A.get(k["pid"]) and B.get(k["pid"]) and A[k["pid"]] != B[k["pid"]]]
    (HERE / "packet_c_ids.txt").write_text("\n".join(dis) + "\n"); print("C ids", len(dis)); sys.exit()
gold = lambda p: A[p] if A.get(p) in ("Y", "N") and A.get(p) == B.get(p) else C.get(p)


def wout(k, n, z=1.96):
    if not n: return None
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return [math.floor((c - h) / d * 1000) / 1000, math.ceil((c + h) / d * 1000) / 1000]


def est(items):
    t = collections.Counter()
    for k in items:
        g = gold(k["pid"])
        if g not in ("Y", "N"): continue
        w = k["N_h"] / k["n_h"]; y = g == "Y"
        t["pos"] += w * y
        t["a_tp"] += w * (k["flag"] and y); t["a_fp"] += w * (k["flag"] and not y); t["a_fn"] += w * ((not k["flag"]) and y)
        t["k_tp"] += w * (k["kw"] and y); t["k_fp"] += w * (k["kw"] and not y); t["k_fn"] += w * ((not k["kw"]) and y)
    f = lambda a, b: a / (a + b) if a + b else float("nan")
    return dict(pos=t["pos"], a_P=f(t["a_tp"], t["a_fp"]), a_R=f(t["a_tp"], t["a_fn"]), k_P=f(t["k_tp"], t["k_fp"]), k_R=f(t["k_tp"], t["k_fn"]))


R = {}
both = [k["pid"] for k in K if A.get(k["pid"]) and B.get(k["pid"])]
R["agree_AB"] = round(sum(A[p] == B[p] for p in both) / len(both), 4) if both else None
for topic in sorted({k["topic"] for k in K}):
    items = [k for k in K if k["topic"] == topic]
    flagged = [k for k in items if k["flag"] and gold(k["pid"]) in ("Y", "N")]
    kp = sum(gold(k["pid"]) == "Y" for k in flagged)
    e = est(items)
    by = collections.defaultdict(list)
    for k in items: by[k["stratum"]].append(k)
    rng = random.Random(7); bs = collections.defaultdict(list)
    for _ in range(2000):
        s = [rng.choice(v) for v in by.values() for _ in v]; b = est(s)
        for kk, vv in b.items():
            if vv == vv: bs[kk].append(vv)
    ci = {kk: [math.floor(sorted(v)[int(.025 * len(v))] * 1000) / 1000, math.ceil(sorted(v)[int(.975 * len(v)) - 1] * 1000) / 1000] for kk, v in bs.items() if v}
    R[topic] = dict(n_packet=len(items), flags=sum(k["flag"] for k in items), kw_hits=sum(k["kw"] for k in items),
                    precision_flags=dict(k=kp, n=len(flagged), value=round(kp / len(flagged), 4) if flagged else None, ci=wout(kp, len(flagged))),
                    weighted=dict(point={kk: round(vv, 4) for kk, vv in e.items()}, ci=ci),
                    strata={h: dict(N=v[0]["N_h"], n=len(v), gold_Y=sum(gold(k["pid"]) == "Y" for k in v)) for h, v in by.items()})
(HERE / "results.json").write_text(json.dumps(R, indent=1, ensure_ascii=False)); print(json.dumps(R, indent=1, ensure_ascii=False))
