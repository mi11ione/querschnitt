"""S20 (eval/PREREG-BUILD.md): Basel-Stadt topics (human, KSE «Thema 1/2») vs the bs-themen scheme file. No model calls.
-> eval/s20/results.json, results.md"""
import collections, csv, gzip, json, random, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt import prompts as P  # noqa: E402
from querschnitt.compose import read_run  # noqa: E402
from querschnitt.scheme import named  # noqa: E402

S = named("bs-themen")
NAMES = [o["name"]["de"] for o in S["options"]] + [S["none"]["name"]["de"]]
n = len(NAMES)
lock, rows = read_run(ROOT / "runs/s20")
G = {r["Signatur"]: r for r in csv.DictReader(open(ROOT.parent / "data/manual/bs_100086.csv", encoding="utf-8-sig"), delimiter=";")}
X = []
with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f:
    for line in f:
        x = json.loads(line)
        if x["body"] == "BS" and x["number"] in G:
            X.append(x)
KW = json.loads((HERE / "keywords_frozen.json").read_text())["stems"]
freq = collections.Counter(G[x["number"]]["Thema 1"] for x in X)
FORDER = [t for t, _ in freq.most_common()] + [t for t in NAMES if t not in freq]


def kw(title):
    t = title.lower(); sc = {th: sum(s in t for s in st) for th, st in KW.items()}
    best = max(sc.values())
    return FORDER[0] if best == 0 else next(th for th in FORDER if sc.get(th, 0) == best)


def wilson(k, m, z=1.96):
    if not m: return (0, 0)
    p = k / m; d = 1 + z * z / m; c = p + z * z / (2 * m); h = z * ((p * (1 - p) / m + z * z / (4 * m * m)) ** 0.5)
    return (round((c - h) / d, 3), round((c + h) / d, 3))


res = []
for x in X:
    ra = rows.get(P.pid(*P.named_prompt(S, x)[:2]))
    if not ra:
        continue
    rb = None
    if max(ra["p"]) < 0.9:
        rb = rows.get(P.pid(*P.named_prompt(S, x, P.named_perm(n))[:2]))
        if not rb:
            continue
    pm = [(a + b) / 2 for a, b in zip(ra["p"], rb["p"])] if rb else ra["p"]
    rk = sorted(range(n), key=lambda i: -pm[i])
    g = G[x["number"]]
    lane = "please_check" if (rb and max(range(n), key=lambda i: ra["p"][i]) != max(range(n), key=lambda i: rb["p"][i])) else "readings_agree"
    res.append(dict(id=x["id"], t1=g["Thema 1"], t2=g["Thema 2"], typ=g["Geschäftstyp"], pred=NAMES[rk[0]], top3=[NAMES[i] for i in rk[:3]],
                    p=pm[rk[0]], lane=lane, kw=kw(x["title"]), text=bool(x["text"])))
N = len(res)
k1 = sum(r["pred"] == r["t1"] for r in res); k12 = sum(r["pred"] in (r["t1"], r["t2"]) for r in res); k3 = sum(r["t1"] in r["top3"] for r in res)
kk = sum(r["kw"] == r["t1"] for r in res); km = sum(r["t1"] == FORDER[0] for r in res)
R = dict(n=N, n_items=len(X), build=lock["fp"], themes=n - 1,
         top1=dict(acc=round(k1 / N, 4), ci=wilson(k1, N)), top1_t1_or_t2=dict(acc=round(k12 / N, 4), ci=wilson(k12, N)),
         top3=dict(acc=round(k3 / N, 4), ci=wilson(k3, N)),
         keyword=dict(acc=round(kk / N, 4), ci=wilson(kk, N)), majority=dict(label=FORDER[0], acc=round(km / N, 4)))
for ln in ("readings_agree", "please_check"):
    s = [r for r in res if r["lane"] == ln]; k = sum(r["pred"] == r["t1"] for r in s)
    R[f"lane_{ln}"] = dict(n=len(s), share=round(len(s) / N, 4), acc=round(k / len(s), 4) if s else None, ci=wilson(k, len(s)))
R["by_type"] = {}
for typ, c in collections.Counter(r["typ"] for r in res).most_common():
    s = [r for r in res if r["typ"] == typ]; k = sum(r["pred"] == r["t1"] for r in s)
    R["by_type"][typ] = dict(n=len(s), acc=round(k / len(s), 4), ci=wilson(k, len(s)))
for flag in (True, False):
    s = [r for r in res if r["text"] == flag]; k = sum(r["pred"] == r["t1"] for r in s)
    R["with_text" if flag else "title_only"] = dict(n=len(s), acc=round(k / len(s), 4) if s else None, ci=wilson(k, len(s)))
rng = random.Random(2026); ds = []
va = [int(r["pred"] == r["t1"]) for r in res]; vb = [int(r["kw"] == r["t1"]) for r in res]
for _ in range(2000):
    s = [rng.randrange(N) for _ in range(N)]; ds.append(sum(va[i] - vb[i] for i in s) / N)
ds.sort(); R["minus_keyword"] = dict(diff=round((sum(va) - sum(vb)) / N, 4), ci=(round(ds[50], 4), round(ds[1949], 4)))
(HERE / "results.json").write_text(json.dumps(R, indent=1, ensure_ascii=False))
print(json.dumps({k: v for k, v in R.items() if k != "by_type"}, indent=1, ensure_ascii=False))
