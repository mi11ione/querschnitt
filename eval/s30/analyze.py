"""S30 analysis (eval/PREREG-BUILD.md § S30). No model calls. Gold = blind judge A and B where they agree, tie-break C where
they differ. Per topic and pooled over the three topics: precision of flags (Wilson 95%; every flag is in the census
stratum), recall weighted by the stratum sampling fraction (stratified bootstrap 2,000, random.Random(30)), the same for the
keyword list, and the paired differences variant − shipped (same bootstrap). Points truncated, intervals outward (3 dp).
`--c-template` writes the tie-break id list (A != B)."""
import collections, json, math, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
K = [json.loads(l) for l in open(HERE / "key.jsonl")]
ARMS = ("shipped", "variant", "kw", "shipped_yn", "yn_sc")


def rd(name):
    d = {}
    for p in sorted(HERE.glob(f"ann/{name}_*.tsv")):
        for line in p.read_text().splitlines():
            x = line.rstrip("\n").split("\t")
            if len(x) >= 2 and x[1].strip():
                d[x[0]] = x[1].strip().upper()[:1]
    return d


A, B, C = rd("A"), rd("B"), rd("C")
if "--c-template" in sys.argv:
    dis = [k for k in K if A.get(k["pid"]) and B.get(k["pid"]) and A[k["pid"]] != B[k["pid"]]]
    by = collections.defaultdict(list)
    for k in dis: by[k["topic"]].append(k["pid"])
    (HERE / "packet_c_ids.json").write_text(json.dumps(by, indent=1)); print({t: len(v) for t, v in by.items()}); sys.exit()
gold = lambda p: A[p] if A.get(p) in ("Y", "N") and A.get(p) == B.get(p) else C.get(p)
tr = lambda v: None if v is None else math.trunc(v * 1000) / 1000
lo = lambda v: math.floor(v * 1000) / 1000
hi = lambda v: math.ceil(v * 1000) / 1000


def wilson(k, n, z=1.96):
    if not n: return None
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return [max(0.0, lo((c - h) / d)), min(1.0, hi((c + h) / d))]


def est(items):
    t = collections.Counter()
    for k in items:
        y = gold(k["pid"]) == "Y"; w = k["N_h"] / k["n_h"]
        t["pos"] += w * y
        for a in ARMS:
            t[a + "_tp"] += w * (k[a] and y); t[a + "_fl"] += w * k[a]
    out = dict(pos=t["pos"])
    for a in ARMS:
        out[a + "_P"] = t[a + "_tp"] / t[a + "_fl"] if t[a + "_fl"] else None
        out[a + "_R"] = t[a + "_tp"] / t["pos"] if t["pos"] else None
    for m in ("P", "R"):
        v, s = out["variant_" + m], out["shipped_" + m]
        out["diff_" + m] = v - s if v is not None and s is not None else None
    return out


def block(items, strata_key):
    by = collections.defaultdict(list)
    for k in items: by[strata_key(k)].append(k)
    e = est(items)
    rng = random.Random(30); bs = collections.defaultdict(list)
    for _ in range(2000):
        b = est([rng.choice(v) for v in by.values() for _ in v])
        for kk, vv in b.items():
            if vv is not None: bs[kk].append(vv)
    ci = {}
    for kk, v in bs.items():
        v.sort(); ci[kk] = [lo(v[int(.025 * len(v))]), hi(v[int(.975 * len(v)) - 1])]
    r = dict(n_items=len(items), judge_pos_items=sum(gold(k["pid"]) == "Y" for k in items),
             relevant_est=dict(value=tr(e["pos"]), ci=ci.get("pos")),
             strata={(h if isinstance(h, str) else "/".join(h)): dict(N=v[0]["N_h"], n=len(v), judge_Y=sum(gold(k["pid"]) == "Y" for k in v)) for h, v in by.items()})
    for a in ARMS:
        fl = [k for k in items if k[a]]; kp = sum(gold(k["pid"]) == "Y" for k in fl)
        r[a] = dict(flags=len(fl), precision=dict(k=kp, n=len(fl), value=tr(kp / len(fl)) if fl else None, ci=wilson(kp, len(fl))),
                    recall_weighted=dict(value=tr(e[a + "_R"]), ci=ci.get(a + "_R") if e[a + "_R"] is not None else None))
    for m in ("P", "R"):
        r["diff_variant_minus_shipped_" + m] = dict(value=tr(e["diff_" + m]), ci=ci.get("diff_" + m) if e["diff_" + m] is not None else None,
                                                    n_boot=len(bs.get("diff_" + m, [])))
    return r


missing = [k["pid"] for k in K if gold(k["pid"]) not in ("Y", "N")]
assert not missing, f"{len(missing)} items without gold, e.g. {missing[:5]}"
both = [k["pid"] for k in K if A.get(k["pid"]) and B.get(k["pid"])]
R = dict(agree_AB=tr(sum(A[p] == B[p] for p in both) / len(both)), n_C=sum(A[p] != B[p] for p in both))
for t in sorted({k["topic"] for k in K}):
    R[t] = block([k for k in K if k["topic"] == t], lambda k: k["stratum"])
R["pooled"] = block(K, lambda k: (k["topic"], k["stratum"]))
(HERE / "results.json").write_text(json.dumps(R, indent=1, ensure_ascii=False)); print(json.dumps(R, indent=1, ensure_ascii=False))
