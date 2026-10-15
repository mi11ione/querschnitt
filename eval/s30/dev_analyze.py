"""S30 dev readout on the S19 packets (gold = S19 judge A/B + C). Arms: S19 yes/no, shipped (yes/no + S27 verify), V1 (yes/no +
scope check), V2 (yes/no + contrast check: the topic against its generated neighbours), V3 (scope question alone), V4 (scope question + S27 verify). Weighted
(S19 stratum weights) precision and recall. No model calls."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]; S19 = ROOT / "eval/s19"
K = [json.loads(l) for l in open(S19 / "key.jsonl")]
def rd(p):
    d = {}
    for line in (S19 / p).read_text().splitlines():
        x = line.split("\t")
        if len(x) >= 2 and x[1].strip(): d[x[0]] = x[1].strip().upper()[:1]
    return d
A, B, C = rd("ann_A.tsv"), rd("ann_B.tsv"), rd("ann_C.tsv")
gold = lambda p: A[p] if A.get(p) in ("Y", "N") and A.get(p) == B.get(p) else C.get(p)
V27 = {json.loads(l)["pid"]: json.loads(l) for l in open(ROOT / "eval/s27/raw.jsonl")}
R = {}
for l in open(HERE / "dev_raw.jsonl"):
    r = json.loads(l); R[(r["pid"], r["v"])] = r["p"]
cut = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
arms = {
 "s19_yn": lambda k: k["flag"],
 "shipped": lambda k: k["flag"] and V27[k["pid"]]["keep"],
 "V1_yn+scope": lambda k: k["flag"] and R.get((k["pid"], "scope"), 0) >= cut,
 "V2_yn+contrast": lambda k: k["flag"] and R.get((k["pid"], "contrast"), 0) >= cut,
 "V3_scope": lambda k: R.get((k["pid"], "scope"), 0) >= cut,
 "V4_scope+S27": lambda k: R.get((k["pid"], "scope"), 0) >= cut and k["flag"] and V27[k["pid"]]["keep"],
 "kw": lambda k: k["kw"],
}
out = {}
for t in ("wolf", "ki-schule", "hitze"):
    items = [k for k in K if k["topic"] == t and gold(k["pid"]) in ("Y", "N") and ((k["pid"], "scope") in R) and (not k["flag"] or (k["pid"], "contrast") in R)]
    pos = sum(k["N_h"] / k["n_h"] for k in items if gold(k["pid"]) == "Y")
    print(f"{t}: items {len(items)} judge-pos {sum(gold(k['pid'])=='Y' for k in items)}")
    for a, f in arms.items():
        fl = [k for k in items if f(k)]; tp = sum(gold(k["pid"]) == "Y" for k in fl)
        wtp = sum(k["N_h"] / k["n_h"] for k in fl if gold(k["pid"]) == "Y"); wfl = sum(k["N_h"] / k["n_h"] for k in fl)
        out.setdefault(t, {})[a] = dict(flags=len(fl), tp=tp, precision=round(wtp / wfl, 3) if wfl else None, recall=round(wtp / pos, 3) if pos else None)
        print(f"  {a:22s} flags {len(fl):4d} tp {tp:4d}  P {out[t][a]['precision']}  R {out[t][a]['recall']}")
(HERE / f"dev_results{'' if cut == 0.5 else '_' + str(cut)}.json").write_text(json.dumps(out, indent=1))
