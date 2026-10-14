"""S23 analysis (eval/PREREG-BUILD.md, "S23 evidence on production rows"). No model calls.
Reads key.jsonl and ann_A.tsv, ann_B.tsv (+ ann_C.tsv, the tie-break run on the ids where A and B differ).
Label per item (tie-break rule, fixed): A if A == B, else C. Items where A ≠ B and C is missing are unresolved: reported and
left out of the consensus rates (the run fails if any remain unless --allow-unresolved).
Outcomes: support rate (share Y) per kind (chapter, digitalisierung) and overall, Wilson 95%; substring check rate (code, all
200 rows; also on rows whose input hash is unchanged); A/B agreement and Cohen's κ; per-annotator rates; S12 (0.850, spike)
for a descriptive comparison only. Wilson bounds are stored exactly and rounded outward (lower floored, upper ceiled at 3
decimals); point values are stored unrounded (truncate when quoting).
  python eval/s23/analyze.py --c-template   # write packet/ann_C_TEMPLATE.tsv (ids where A and B differ)
  python eval/s23/analyze.py                # -> results.json"""
import json, math, sys
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from pathlib import Path

HERE = Path(__file__).resolve().parent
S12 = HERE.parent / "spikes/s12-evidence/results.json"  # vendored S12 (eval/spikes/)
KINDS = ("chapter", "digitalisierung")


def wilson(k, n, z=1.96):
    if not n: return None
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(c - h, 0.0), min(c + h, 1.0)]


def outward(ci):
    if ci is None: return None
    return [float(Decimal(repr(ci[0])).quantize(Decimal("0.001"), ROUND_FLOOR)),
            float(Decimal(repr(ci[1])).quantize(Decimal("0.001"), ROUND_CEILING))]


def prop(k, n):
    ci = wilson(k, n)
    return dict(k=k, n=n, rate=k / n if n else None, ci95=outward(ci), ci95_exact=ci,
                ci_method="Wilson 95%, bounds rounded outward at 3 decimals")


def read_ann(name, ids):
    p = HERE / name
    if not p.exists(): return None
    out = {}
    for ln in open(p, encoding="utf-8"):
        f = ln.rstrip("\n").split("\t")
        if len(f) < 2 or not f[0].strip(): continue
        v = f[1].strip().upper()
        if v not in ("Y", "N"): raise SystemExit(f"{name}: bad label {f!r}")
        if f[0].strip() in out: raise SystemExit(f"{name}: duplicate id {f[0]!r}")
        out[f[0].strip()] = v
    extra = set(out) - set(ids)
    if extra: raise SystemExit(f"{name}: unknown ids {sorted(extra)[:5]}")
    return out


def kappa(a, b, ids):
    n = len(ids)
    if not n: return None
    po = sum(a[i] == b[i] for i in ids) / n
    pa, pb = sum(a[i] == "Y" for i in ids) / n, sum(b[i] == "Y" for i in ids) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else None


def main():
    key = {r["pid"]: r for r in map(json.loads, open(HERE / "key.jsonl", encoding="utf-8"))}
    ids = sorted(key)
    A, B = read_ann("ann_A.tsv", ids), read_ann("ann_B.tsv", ids)
    if A is None or B is None: raise SystemExit("need ann_A.tsv and ann_B.tsv")
    for nm, X in (("A", A), ("B", B)):
        miss = [i for i in ids if i not in X]
        if miss: raise SystemExit(f"ann_{nm}: {len(miss)} ids missing, e.g. {miss[:5]}")
    dis = [i for i in ids if A[i] != B[i]]
    if "--c-template" in sys.argv:
        (HERE / "packet/ann_C_TEMPLATE.tsv").write_text("".join(f"{i}\t\n" for i in dis), encoding="utf-8")
        print(f"wrote packet/ann_C_TEMPLATE.tsv with {len(dis)} ids where A and B differ"); return
    C = read_ann("ann_C.tsv", ids) or {}
    lab = {i: A[i] for i in ids if A[i] == B[i]}
    lab.update({i: C[i] for i in dis if i in C})
    unresolved = [i for i in dis if i not in C]
    if unresolved and "--allow-unresolved" not in sys.argv:
        raise SystemExit(f"{len(unresolved)} A/B disagreements without ann_C (run --c-template, collect ann_C.tsv)")
    L = [i for i in ids if i in lab]
    sup = lambda sel: prop(sum(lab[i] == "Y" for i in sel), len(sel))
    R = dict(prereg="eval/PREREG-BUILD.md — 2026-10-14 17:10 CEST — S23 evidence on production rows",
             n_packet=len(ids), by_kind={kd: sum(key[i]["kind"] == kd for i in ids) for kd in KINDS},
             fingerprints=sorted({key[i]["fp"] for i in ids}),
             tie_break_rule="label = A if A == B, else C (blind third run on the disagreeing ids only)",
             n_disagree=len(dis), n_tiebroken=len(dis) - len(unresolved), unresolved=unresolved)
    R["support"] = dict(overall=sup(L), **{kd: sup([i for i in L if key[i]["kind"] == kd]) for kd in KINDS})
    R["substring"] = dict(all_rows=prop(sum(key[i]["substring_ok"] for i in ids), len(ids)),
                          input_unchanged=prop(sum(key[i]["substring_ok"] for i in ids if key[i]["ih_match"]),
                                               sum(key[i]["ih_match"] for i in ids)),
                          input_changed_since_row=sum(not key[i]["ih_match"] for i in ids),
                          method="inputs[field][start:end] == stored quote (current inputs.jsonl.gz)")
    R["ab_agreement"] = prop(len(ids) - len(dis), len(ids))
    R["ab_kappa"] = kappa(A, B, ids)
    R["per_annotator"] = {nm: dict(overall=prop(sum(X[i] == "Y" for i in ids), len(ids)),
                                   **{kd: prop(sum(X[i] == "Y" for i in ids if key[i]["kind"] == kd),
                                               sum(key[i]["kind"] == kd for i in ids)) for kd in KINDS})
                          for nm, X in (("A", A), ("B", B))}
    R["by_field"] = {fd: sup([i for i in L if key[i]["field"] == fd]) for fd in ("title", "title_long", "text")}
    R["by_level"] = {lv: sup([i for i in L if key[i]["level"] == lv]) for lv in sorted({key[i]["level"] for i in ids})}
    s12 = json.load(open(S12)) if S12.exists() else None
    if s12:
        R["s12_descriptive"] = dict(rate=s12["support"]["overall"]["rate"], n=s12["support"]["overall"]["n"],
                                    note="S12 spike (120 federal affairs, D1 chapter, German); descriptive comparison only, no test",
                                    file=str(S12.relative_to(HERE.parents[1])))
    (HERE / "results.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    s = R["support"]
    print("\n".join([f"S23 n {len(ids)}; A/B agree {R['ab_agreement']['k']}/{len(ids)}, κ {R['ab_kappa']}; tie-broken {R['n_tiebroken']}",
                     *(f"support {k}: {v['k']}/{v['n']} = {v['rate']} {v['ci95']}" for k, v in s.items()),
                     f"substring: {R['substring']['all_rows']['k']}/{len(ids)} (input unchanged: "
                     f"{R['substring']['input_unchanged']['k']}/{R['substring']['input_unchanged']['n']})"]))


if __name__ == "__main__":
    main()
