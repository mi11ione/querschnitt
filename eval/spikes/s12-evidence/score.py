"""S12 scoring. Reads key.jsonl, raw/s12.jsonl, ann_A.tsv, ann_B.tsv (+ optional ann_C.tsv tie-break on A/B disagreements).
Label per item: A if A == B, else C (if present; unresolved items reported and excluded from the consensus figures).
Reports: support rate overall, when the D1 chapter is right vs wrong (APS editors), substring-check pass rate (all 120 rows;
an unparseable/out-of-range number counts as fail), A-B agreement + Cohen's kappa, Wilson 95% intervals. Writes results.json.
  python3 -I score.py               # score
  python3 -I score.py --c-template  # write packet/ann_C_TEMPLATE.tsv with the A/B-disagreeing ids
"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))


def wilson(k, n, z=1.96):
    if n == 0: return [None, None]
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def prop(k, n): return dict(k=k, n=n, rate=round(k / n, 4) if n else None, ci95=wilson(k, n))


def read_ann(name, ids):
    p = f"{HERE}/{name}"
    if not os.path.exists(p): return None
    out = {}
    for ln in open(p, encoding="utf-8"):
        f = ln.rstrip("\n").split("\t")
        if len(f) < 2 or not f[0].strip(): continue
        v = f[1].strip().upper()
        if v not in ("Y", "N"): raise SystemExit(f"{name}: bad label {f!r}")
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
    return round((po - pe) / (1 - pe), 4) if pe < 1 else None


def main():
    key = {r["pid"]: r for r in map(json.loads, open(f"{HERE}/key.jsonl"))}
    ids = sorted(key)
    rows = [json.loads(l) for l in open(f"{HERE}/raw/s12.jsonl")]
    A, B = read_ann("ann_A.tsv", ids), read_ann("ann_B.tsv", ids)
    if A is None or B is None: raise SystemExit("need ann_A.tsv and ann_B.tsv")
    for nm, X in (("A", A), ("B", B)):
        miss = [i for i in ids if i not in X]
        if miss: raise SystemExit(f"ann_{nm}: {len(miss)} ids missing, e.g. {miss[:5]}")
    dis = [i for i in ids if A[i] != B[i]]
    if "--c-template" in sys.argv:
        open(f"{HERE}/packet/ann_C_TEMPLATE.tsv", "w").write("".join(f"{i}\t\n" for i in dis))
        print(f"wrote packet/ann_C_TEMPLATE.tsv with {len(dis)} disagreeing ids"); return
    C = read_ann("ann_C.tsv", ids) or {}
    lab = {i: A[i] for i in ids if A[i] == B[i]}
    lab.update({i: C[i] for i in dis if i in C})
    unresolved = [i for i in dis if i not in C]
    R = dict(n_rows=len(rows), n_packet=len(ids),
             fingerprints=sorted({(r["model"], r["fp"]) for r in rows}),
             substring_pass=prop(sum(bool(r["substring_ok"]) for r in rows), len(rows)),
             ab_agreement=prop(len(ids) - len(dis), len(ids)), ab_kappa=kappa(A, B, ids),
             n_disagree=len(dis), n_tiebroken=len(dis) - len(unresolved), unresolved=unresolved)
    L = [i for i in ids if i in lab]
    def sup(sel): return prop(sum(lab[i] == "Y" for i in sel), len(sel))
    R["support"] = dict(
        overall=sup(L),
        d1_right=sup([i for i in L if key[i]["correct"]]),
        d1_wrong=sup([i for i in L if not key[i]["correct"]]))
    # strict view: rows with no valid sentence (not in packet) count as unsupported
    R["support_strict_all_rows"] = prop(sum(lab[i] == "Y" for i in L), len(rows) - len(unresolved))
    R["per_annotator"] = {nm: dict(overall=prop(sum(X[i] == "Y" for i in ids), len(ids)),
                                   d1_right=prop(sum(X[i] == "Y" for i in ids if key[i]["correct"]), sum(key[i]["correct"] for i in ids)),
                                   d1_wrong=prop(sum(X[i] == "Y" for i in ids if not key[i]["correct"]), sum(not key[i]["correct"] for i in ids)))
                          for nm, X in (("A", A), ("B", B))}
    R["d1_accuracy_on_sample"] = prop(sum(r["correct"] for r in rows), len(rows))
    pos = {}
    for r in rows: pos[r["num"]] = pos.get(r["num"], 0) + 1
    R["chosen_sentence_number"] = dict(sorted(((str(k), v) for k, v in pos.items()), key=lambda x: -x[1]))
    json.dump(R, open(f"{HERE}/results.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(R, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
