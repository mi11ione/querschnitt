"""S16 analysis (eval/PREREG-BUILD.md) + per-build recalibration file. No model calls.
-> eval/s16/results.json, eval/s16/results.md, eval/calibration.json"""
import json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt import prompts as P  # noqa: E402
from querschnitt.calibrate import crossfit, pav  # noqa: E402

S9 = Path("/Users/mi11ion/Desktop/hackapertus/bern/ideation2/spikes/s9-aps")
BUILD = "vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840"
load = lambda p: {json.loads(l)["oid"]: json.loads(l) for l in open(p)}
items = {it["oid"]: it for it in json.load(open(S9 / "data/items.json"))}
raw = {ph: load(S9 / f"raw/{ph}.jsonl") for ph in ("d0a", "d0b", "d1", "d3m")}
s16 = load(HERE / "raw.jsonl")
order = lambda p: sorted(range(len(p)), key=lambda i: -p[i])


def geo2(a, b):
    import math
    g = [math.exp((math.log(max(x, 1e-12)) + math.log(max(y, 1e-12))) / 2) for x, y in zip(a, b)]
    s = sum(g); return [v / s for v in g]


def readback(prior, chs, psub):
    opts = P.subtopic_options(chs)
    sc = {(c, j): psub[k] * prior[c] for k, (c, j) in enumerate(opts)}
    tot = sum(sc.values()) or 1
    best = max(sc, key=sc.get)
    chbest = {}
    for (c, j), v in sc.items():
        chbest[c] = max(chbest.get(c, 0), v)
    rk = sorted(chbest, key=lambda c: -chbest[c]) + [c for c in order(prior) if c not in chbest]
    return best[0], rk, sum(v for (c, j), v in sc.items() if c == best[0]) / tot


ids = sorted(o for o in items if o in s16 and all(o in raw[k] for k in ("d0a", "d0b", "d1", "d3m")))
pred = {}
for o in ids:
    a, b, m = raw["d0a"][o]["p"], raw["d0b"][o]["p"], raw["d3m"][o]["p"]
    PA = [(x + y) / 2 for x, y in zip(a, b)]
    r = raw["d1"][o]
    pred.setdefault("D1", {})[o] = readback(PA, r["chs"], r["p"])
    d3 = geo2(m, b); pred.setdefault("D3", {})[o] = (order(d3)[0], order(d3), d3[order(d3)[0]])
    for name in ("d4", "d4s"):
        x = s16[o][name]
        pred.setdefault(name.upper(), {})[o] = readback(x["prior"], x["chs"], x["p"])
gold = {o: items[o]["chapter"] for o in ids}


def wilson(k, n, z=1.96):
    if not n: return (0, 0)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return (round((c - h) / d, 3), round((c + h) / d, 3))


R = dict(n=len(ids), build=BUILD, designs={})
for d, P_ in pred.items():
    k1 = sum(P_[o][0] == gold[o] for o in ids); k3 = sum(gold[o] in P_[o][1][:3] for o in ids)
    R["designs"][d] = dict(top1=round(k1 / len(ids), 4), top1_ci=wilson(k1, len(ids)), top3=round(k3 / len(ids), 4), k1=k1)
rng = random.Random(2026)
for a_, b_ in (("D4", "D3"), ("D4", "D1"), ("D4S", "D3"), ("D4S", "D1"), ("D3", "D1")):
    diffs = []
    va = [int(pred[a_][o][0] == gold[o]) for o in ids]; vb = [int(pred[b_][o][0] == gold[o]) for o in ids]
    for _ in range(2000):
        s = [rng.randrange(len(ids)) for _ in ids]
        diffs.append(sum(va[i] - vb[i] for i in s) / len(s))
    diffs.sort()
    R[f"{a_}-{b_}"] = dict(diff=round((sum(va) - sum(vb)) / len(ids), 4), ci=(round(diffs[50], 4), round(diffs[1949], 4)))
ship = "D4" if R["designs"]["D4"]["top1"] >= R["designs"]["D3"]["top1"] else "D3"
R["decision"] = (f"{ship} shipped for federal affairs (pre-registered rule: D4 if its top-1 ≥ D3's). The corpus run uses D4 as "
                 "registered: both code orders always, examples on the first. D4s (secondary) is reported, not shipped.")
# lanes of the shipped design: the two code orders (d3m with examples, d0b without) agree / disagree on the top chapter
agree = [o for o in ids if order(raw["d3m"][o]["p"])[0] == order(raw["d0b"][o]["p"])[0]]
dis = [o for o in ids if o not in set(agree)]
ka = sum(pred["D4"][o][0] == gold[o] for o in agree); kd = sum(pred["D4"][o][0] == gold[o] for o in dis)
R["lanes_D4"] = dict(agree_share=round(len(agree) / len(ids), 4), agree_n=len(agree), agree_precision=round(ka / len(agree), 4),
                     agree_ci=wilson(ka, len(agree)), disagree_n=len(dis), disagree_precision=round(kd / len(dis), 4), disagree_ci=wilson(kd, len(dis)))
new = sum(1 for o in ids if s16[o]["d4"]["src"] == "new") + sum(1 for o in ids if s16[o]["d4s"]["src"] == "new")
R["new_calls"] = new
# calibration: aps = D1 (no examples), aps-fed = production federal rule (D4s if D4 shipped, else D3)
cal = dict(build=BUILD, fitted_on="S9 held-out federal affairs (APS editors' chapters)", n=len(ids), maps={})
for key, d in (("aps", "D1"), ("aps-fed", ship)):
    ps = [pred[d][o][2] for o in ids]; ys = [int(pred[d][o][0] == gold[o]) for o in ids]
    cal["maps"][key] = dict(design=d, map=pav(ps, ys), **crossfit(ps, ys))
    R.setdefault("calibration", {})[key] = {k: v for k, v in cal["maps"][key].items() if k != "map"}
    # coverage-precision on recalibration-free ranking
    o_ = sorted(range(len(ps)), key=lambda i: -ps[i]); k = 0; cp = []
    for n_, i in enumerate(o_, 1):
        k += ys[i]
        cp.append((round(n_ / len(ps), 4), round(k / n_, 4)))
    R.setdefault("coverage_precision", {})[key] = cp
(ROOT / "eval/calibration.json").write_text(json.dumps(cal, indent=1))
(HERE / "results.json").write_text(json.dumps(R, indent=1))
md = [f"# S16 — read-back combined with examples (n = {len(ids)}, build …{BUILD[-8:]})", "",
      "| Design | top-1 [95%] | top-3 |", "|---|---|---|"]
for d, v in R["designs"].items():
    md.append(f"| {d} | {v['top1']} [{v['top1_ci'][0]}, {v['top1_ci'][1]}] | {v['top3']} |")
md += ["", *(f"- {k}: {v['diff']:+} [{v['ci'][0]:+}, {v['ci'][1]:+}]" for k, v in R.items() if "-" in k and isinstance(v, dict) and "diff" in v),
       f"- Decision: {R['decision']}", f"- New subtopic calls: {new}",
       f"- Lanes (D4): orders agree on {R['lanes_D4']['agree_share']} of affairs, precision {R['lanes_D4']['agree_precision']} {R['lanes_D4']['agree_ci']}; "
       f"disagree: precision {R['lanes_D4']['disagree_precision']} {R['lanes_D4']['disagree_ci']} (n {R['lanes_D4']['disagree_n']})",
       *(f"- Calibration {k}: ECE {v['ece_raw']} → {v['ece_crossfit']} (2-fold cross-fitted, n {v['n']}, acc {v['acc']})" for k, v in R["calibration"].items())]
(HERE / "results.md").write_text("\n".join(md) + "\n")
print("\n".join(md))
