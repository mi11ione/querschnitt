"""S21 analysis: examples (other fold) + permuted reading vs S20 (names only), paired on the same items."""
import csv, gzip, json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt.scheme import named  # noqa: E402
S = named("bs-themen"); NAMES = [o["name"]["de"] for o in S["options"]] + [S["none"]["name"]["de"]]; n = len(NAMES)
G = {r["Signatur"]: r for r in csv.DictReader(open(ROOT.parent / "data/manual/bs_100086.csv", encoding="utf-8-sig"), delimiter=";")}
num = {}
with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f:
    for line in f:
        x = json.loads(line)
        if x["body"] == "BS" and x["number"] in G:
            num[x["id"]] = x["number"]
s21 = {json.loads(l)["id"]: json.loads(l) for l in open(HERE / "raw.jsonl")}
s20 = {}
for l in open(ROOT / "eval/s20/results.json"):
    pass
# S20 per-item predictions: recompute from its rows with the S20 rule
sys.path.insert(0, str(ROOT / "eval/s20"))
from querschnitt import prompts as P  # noqa: E402
from querschnitt.compose import read_run  # noqa: E402
_, rows = read_run(ROOT / "runs/s20")
X = {}
with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f:
    for line in f:
        x = json.loads(line)
        if x["id"] in s21:
            X[x["id"]] = x
def wilson(k, m, z=1.96):
    p = k / m; d = 1 + z * z / m; c = p + z * z / (2 * m); h = z * ((p * (1 - p) / m + z * z / (4 * m * m)) ** 0.5)
    return (round((c - h) / d, 3), round((c + h) / d, 3))
res = []
for i, r in s21.items():
    x = X[i]; g = G[num[i]]
    pm = [(a + b) / 2 for a, b in zip(r["pa"], r["pb"])]; rk = sorted(range(n), key=lambda k: -pm[k])
    ra = rows.get(P.pid(*P.named_prompt(S, x)[:2])); rb = rows.get(P.pid(*P.named_prompt(S, x, P.named_perm(n))[:2]))
    p20 = [(a + b) / 2 for a, b in zip(ra["p"], rb["p"])] if (ra and rb and max(ra["p"]) < 0.9) else ra["p"]
    agree = max(range(n), key=lambda k: r["pa"][k]) == max(range(n), key=lambda k: r["pb"][k])
    res.append(dict(t1=g["Thema 1"], t2=g["Thema 2"], p21=NAMES[rk[0]], top3=[NAMES[k] for k in rk[:3]], p20=NAMES[max(range(n), key=lambda k: p20[k])], agree=agree,
                    fps=set(r["fp"])))
N = len(res)
k21 = sum(r["p21"] == r["t1"] for r in res); k20 = sum(r["p20"] == r["t1"] for r in res)
R = dict(n=N, builds=sorted({f for r in res for f in r["fps"]}), s21_top1=dict(acc=round(k21 / N, 4), ci=wilson(k21, N)), s20_top1_same_items=round(k20 / N, 4),
         s21_t1_or_t2=round(sum(r["p21"] in (r["t1"], r["t2"]) for r in res) / N, 4), s21_top3=round(sum(r["t1"] in r["top3"] for r in res) / N, 4))
va = [int(r["p21"] == r["t1"]) for r in res]; vb = [int(r["p20"] == r["t1"]) for r in res]; rng = random.Random(2026); ds = []
for _ in range(2000):
    s = [rng.randrange(N) for _ in range(N)]; ds.append(sum(va[i] - vb[i] for i in s) / N)
ds.sort(); R["diff_vs_s20"] = dict(diff=round((k21 - k20) / N, 4), ci=(round(ds[50], 4), round(ds[1949], 4)))
for lane, flag in (("agree", True), ("disagree", False)):
    s = [r for r in res if r["agree"] == flag]; k = sum(r["p21"] == r["t1"] for r in s)
    R[f"lane_{lane}"] = dict(n=len(s), share=round(len(s) / N, 4), acc=round(k / len(s), 4) if s else None, ci=wilson(k, len(s)) if s else None)
(HERE / "results.json").write_text(json.dumps(R, indent=1, ensure_ascii=False, default=list)); print(json.dumps(R, indent=1, ensure_ascii=False, default=list))
