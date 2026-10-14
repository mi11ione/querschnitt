"""S17 (eval/PREREG-BUILD.md): shipped production chapter vs blind consensus on 200 communal 2026 affairs. No model calls.
`python eval/s17/analyze.py --c-template` writes the tie-break packet template (ids where A and B differ on the first chapter)."""
import json, random, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
K = {json.loads(l)["oid"]: json.loads(l) for l in open(HERE / "key.jsonl")}


def rd(p):
    d = {}
    if not (HERE / p).exists():
        return d
    for line in (HERE / p).read_text().splitlines():
        x = line.rstrip("\n").split("\t")
        if len(x) >= 2 and x[0].startswith("M") and x[1].strip():
            d[x[0]] = x[1].strip()
    return d


A, B, C = rd("ann_A.tsv"), rd("ann_B.tsv"), rd("ann_C.tsv")
dis = sorted(i for i in K if A.get(i) and B.get(i) and A[i] != B[i])
if "--c-template" in sys.argv:
    (HERE / "packet/ann_C_TEMPLATE.tsv").write_text("".join(f"{i}\t\t\n" for i in dis)); print("C ids", len(dis)); sys.exit()
gold = lambda i: A[i] if A.get(i) and A.get(i) == B.get(i) else C.get(i)


def wilson(k, n, z=1.96):
    if not n: return (0, 0)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return (round((c - h) / d, 3), round((c + h) / d, 3))


ids = [i for i in K if gold(i)]
N = len(ids)
both = [i for i in K if A.get(i) and B.get(i)]
po = sum(A[i] == B[i] for i in both) / len(both)
cats = sorted({A[i] for i in both} | {B[i] for i in both})
pe = sum((sum(A[i] == c for i in both) / len(both)) * (sum(B[i] == c for i in both) / len(both)) for c in cats)
k1 = sum(K[i]["shipped"] == gold(i) for i in ids); k3 = sum(gold(i) in K[i]["top3"] for i in ids)
maj = max(set(gold(i) for i in ids), key=lambda c: sum(gold(i) == c for i in ids))
R = dict(n=N, A=len(A), B=len(B), C=len(C), disagreements=len(dis), kappa_AB=round((po - pe) / (1 - pe), 3), agree_AB=round(po, 3),
         top1=dict(acc=round(k1 / N, 4), ci=wilson(k1, N)), top3=dict(acc=round(k3 / N, 4), ci=wilson(k3, N)),
         majority=dict(label=maj, acc=round(sum(gold(i) == maj for i in ids) / N, 4)))
for key, vals in (("lang", ("de", "fr", "it")), ("lane", ("readings_agree", "please_check"))):
    for v in vals:
        s = [i for i in ids if K[i][key] == v]; k = sum(K[i]["shipped"] == gold(i) for i in s)
        R[f"{key}_{v}"] = dict(n=len(s), acc=round(k / len(s), 4) if s else None, ci=wilson(k, len(s)))
for flag, name in ((True, "title_only"), (False, "with_text")):
    s = [i for i in ids if K[i]["title_only"] == flag]; k = sum(K[i]["shipped"] == gold(i) for i in s)
    R[name] = dict(n=len(s), acc=round(k / len(s), 4) if s else None, ci=wilson(k, len(s)))
# frozen S9 keyword baseline (APS subtopic words → chapter)
kwf = Path("/Users/mi11ion/Desktop/hackapertus/bern/ideation2/spikes/s9-aps/data/keywords_frozen.json")
KW = json.load(open(kwf)); kw = {int(c): v["keywords"] for c, v in KW["chapters"].items()}
sys.path.insert(0, str(ROOT / "src"))
import gzip  # noqa: E402
from querschnitt.scheme import APS  # noqa: E402
code = lambda ci: APS.codes[ci].split(":")[1]
gc = {}
for i in ids: gc[gold(i)] = gc.get(gold(i), 0) + 1
majorder = sorted(gc, key=lambda c: -gc[c]) + [code(c) for c in range(24) if code(c) not in gc]
X = {}
with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f:
    want = {K[i]["affair_id"] for i in ids}
    for line in f:
        x = json.loads(line)
        if x["id"] in want: X[x["id"]] = x
def kw_pred(i):   # S9 frozen rule: distinct subtopic keywords in title + long title + text; ties -> majority order of this gold
    x = X[K[i]["affair_id"]]; txt = " ".join((x["title"], x["title_long"], x["text"])).lower()
    sc = {code(c): sum(w in txt for w in kw[c]) for c in range(24)}
    m = max(sc.values()); tied = [c for c in sc if sc[c] == m]
    return min(tied, key=lambda c: majorder.index(c) if c in majorder else 99)
kk = sum(kw_pred(i) == gold(i) for i in ids)
R["keyword"] = dict(acc=round(kk / N, 4), ci=wilson(kk, N), file=str(kwf))
(HERE / "results.json").write_text(json.dumps(R, indent=1, ensure_ascii=False)); print(json.dumps(R, indent=1, ensure_ascii=False))
