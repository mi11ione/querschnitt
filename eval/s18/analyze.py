"""S18 (eval/PREREG-BUILD.md): Bern directorates on the production run vs the Grand Council's own lead-directorate field.
No model calls. -> eval/s18/results.json, results.md"""
import gzip, json, random, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt import prompts as P  # noqa: E402
from querschnitt.compose import read_run  # noqa: E402
from querschnitt.scheme import flat  # noqa: E402
sys.path.insert(0, "/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s6-cantonal/scripts")
import be_scheme as B  # noqa: E402  (frozen S6 keyword stems)

DIRS = ["BKD", "BVD", "DIJ", "FIN", "GSI", "SID", "STA", "WEU"]
sch = flat("be-directorates")
lock, rows = read_run(ROOT / "runs/main", ROOT / "runs/side")


def gold_of(dept):
    t = re.split(r"[\s\xa0]+", (dept or "").strip())[0].upper()
    if t in DIRS: return t
    if t in ("GR",) or (dept or "").lower().startswith("grosser rat"): return "none"
    return None


def pred(title, lang):
    u, p, codes = P.flat_prompt(sch, title, lang)
    r = rows.get(P.pid(u, p))
    if not r: return None
    i = max(range(len(r["p"])), key=lambda k: r["p"][k])
    return DIRS[i] if i < 8 else "none"


PRIOR = DIRS  # replaced below by gold frequency order (S6 keyword_pred: ties and no-hit -> the more frequent directorate)


def kw(title, lang):
    return B.keyword_pred(title, lang, PRIOR)[0]


def wilson(k, n, z=1.96):
    if not n: return (0, 0)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return (round((c - h) / d, 3), round((c + h) / d, 3))


items = []
with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f:
    for line in f:
        x = json.loads(line)
        if x["body"] == "BE" and "2025-01-01" <= x["date"] <= "2026-10-11" and gold_of(x["dept"]):
            items.append(x)
R = dict(n_items=len(items), build=lock["fp"])
PRIOR = sorted(DIRS, key=lambda d: -sum(gold_of(x["dept"]) == d for x in items))
res = []
for x in items:
    g = gold_of(x["dept"])
    v = {x["lang"]: (x["title"], pred(x["title"], x["lang"]))}
    if x.get("alt_lang") in ("de", "fr") and x["title_alt"]:
        v[x["alt_lang"]] = (x["title_alt"], pred(x["title_alt"], x["alt_lang"]))
    res.append(dict(id=x["id"], gold=g, main=x["lang"], v={l: p for l, (t, p) in v.items()},
                    kw={l: kw(t, l) for l, (t, p) in v.items() if l in ("de", "fr")}))
scored = [r for r in res if r["v"].get(r["main"])]
R["n_scored"] = len(scored)
k = sum(r["v"][r["main"]] == r["gold"] for r in scored)
R["overall"] = dict(acc=round(k / len(scored), 4) if scored else None, ci=wilson(k, len(scored)), n=len(scored))
kk = sum(r["kw"].get(r["main"]) == r["gold"] for r in scored)
R["keyword"] = dict(acc=round(kk / len(scored), 4) if scored else None, ci=wilson(kk, len(scored)))
maj = max(set(r["gold"] for r in scored), key=lambda g: sum(r["gold"] == g for r in scored)) if scored else None
km = sum(r["gold"] == maj for r in scored)
R["majority"] = dict(label=maj, acc=round(km / len(scored), 4) if scored else None)
for lang in ("de", "fr"):
    s = [r for r in res if r["v"].get(lang)]
    k = sum(r["v"][lang] == r["gold"] for r in s); kk = sum(r["kw"].get(lang) == r["gold"] for r in s)
    R[f"lang_{lang}"] = dict(n=len(s), acc=round(k / len(s), 4) if s else None, ci=wilson(k, len(s)), keyword=round(kk / len(s), 4) if s else None)
both = [r for r in res if r["v"].get("de") and r["v"].get("fr")]
if both:
    va = [int(r["v"]["de"] == r["gold"]) for r in both]; vb = [int(r["v"]["fr"] == r["gold"]) for r in both]
    rng = random.Random(2026); ds = []
    for _ in range(2000):
        s = [rng.randrange(len(both)) for _ in both]; ds.append(sum(va[i] - vb[i] for i in s) / len(s))
    ds.sort()
    R["paired_de_minus_fr"] = dict(n=len(both), de=round(sum(va) / len(both), 4), fr=round(sum(vb) / len(both), 4),
                                   diff=round((sum(va) - sum(vb)) / len(both), 4), ci=(round(ds[50], 4), round(ds[1949], 4)))
(HERE / "results.json").write_text(json.dumps(R, indent=1))
print(json.dumps(R, indent=1))
