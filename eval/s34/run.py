"""S34 (eval/PREREG-BUILD.md 2026-10-16 14:03): a trained text classifier on the shipped design's own APS labels (the
example pool, 1,654 affairs) vs the shipped design on the 927 held-out S25 affairs. No model calls.
`run.py build` (local, data only) writes the texts both sides read to eval/s34/texts.jsonl.gz from the production inputs;
`run.py` fits and scores from that file alone (GitHub Actions: workflow «eval», script eval/s34/run.py). Needs scikit-learn
(pip install -e '.[eval]'). -> eval/s34/results.json, eval/s34/predictions.jsonl"""
import collections, gzip, json, math, random, sys, warnings
from pathlib import Path

import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import FeatureUnion, make_pipeline

warnings.filterwarnings("ignore", message="The least populated class")  # one chapter has a single pool affair
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
pool = [json.loads(l) for l in open(ROOT / "data/eval/aps_pool.jsonl")]
items = {json.loads(l)["oid"]: json.loads(l) for l in open(ROOT / "eval/s25/items.jsonl")}
shipped = {d["oid"]: d for d in map(json.loads, open(ROOT / "eval/s25/decisions.jsonl"))}
ids = sorted(int(x) for x in open(ROOT / "eval/s25/ids.txt").read().split())
P = {p["oid"]: p["chapter"] for p in pool}
assert not set(P) & set(ids), "an S25 item is in the pool"

TEXTS = HERE / "texts.jsonl.gz"
if sys.argv[1:] == ["build"]:
    with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f, gzip.open(TEXTS, "wt") as o:
        for line in f:
            a = json.loads(line)
            if a["id"] in P or a["id"] in items:
                o.write(json.dumps(dict(id=a["id"], text="\n".join(a.get(k) or "" for k in ("title", "title_long", "text"))),
                                   ensure_ascii=False) + "\n")
    sys.exit(0)
text = {r["id"]: r["text"] for r in map(json.loads, gzip.open(TEXTS, "rt"))}
assert set(P) <= set(text) and set(ids) <= set(text)


def wout(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return [math.floor((c - h) / d * 1000) / 1000, math.ceil((c + h) / d * 1000) / 1000]


trunc = lambda v, d=4: math.floor(v * 10 ** d) / 10 ** d
share = lambda k, n: dict(k=k, n=n, value=trunc(k / n), ci=wout(k, n)) if n else None


def model(C):
    feats = FeatureUnion([("w", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2)),
                          ("c", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2))])
    return make_pipeline(feats, LogisticRegression(C=C, max_iter=3000))


Xp = [text[o] for o in P]; yp = [P[o] for o in P]
cv = StratifiedKFold(5, shuffle=True, random_state=2026)
grid = {C: float(np.mean(cross_val_score(model(C), Xp, yp, cv=cv, scoring="accuracy", n_jobs=-1))) for C in (0.3, 1, 3, 10, 30, 100)}
C = max(grid, key=grid.get)
clf = model(C).fit(Xp, yp)
Xt = [text[o] for o in ids]
prob = clf.predict_proba(Xt); cls = list(clf.classes_)
rank = {o: [cls[j] for j in np.argsort(-prob[i])[:3]] for i, o in enumerate(ids)}
gold = {o: items[o]["chapter"] for o in ids}
T1 = {o: int(rank[o][0] == gold[o]) for o in ids}; S1 = {o: int(shipped[o]["ch"] == gold[o]) for o in ids}

rng = random.Random(2026); diffs = []
for _ in range(2000):
    s = [rng.choice(ids) for _ in ids]
    diffs.append(sum(S1[o] - T1[o] for o in s) / len(s))
diffs.sort()
pd = sum(S1[o] - T1[o] for o in ids) / len(ids)

R = dict(prereg="eval/PREREG-BUILD.md 2026-10-16 14:03 CEST", train=len(P), test=len(ids),
         cv_accuracy={str(c): trunc(v) for c, v in grid.items()}, C=C,
         trained_top1=share(sum(T1.values()), len(ids)), shipped_top1=share(sum(S1.values()), len(ids)),
         paired_shipped_minus_trained=dict(value=trunc(pd) if pd >= 0 else -trunc(-pd),
                                           ci=[math.floor(diffs[49] * 1000) / 1000, math.ceil(diffs[1949] * 1000) / 1000]),
         trained_top3=share(sum(gold[o] in rank[o] for o in ids), len(ids)),
         shipped_top3=share(sum(gold[o] in shipped[o]["rank"][:3] for o in ids), len(ids)))
R["trained_by_shipped_lane"] = {l: share(sum(T1[o] for o in v), len(v)) for l, v in sorted(
    collections.defaultdict(list, {k: [o for o in ids if shipped[o]["lane"] == k] for k in {shipped[o]["lane"] for o in ids}}).items())}
R["shipped_by_lane"] = {l: share(sum(S1[o] for o in ids if shipped[o]["lane"] == l), sum(shipped[o]["lane"] == l for o in ids))
                        for l in sorted({shipped[o]["lane"] for o in ids})}
curve = {}
for frac in (0.25, 0.5):
    # stratified by chapter: from each chapter's pool affairs (shuffled, random.Random(2026)) the first ceil(frac · n),
    # so a chapter with one pool affair keeps it
    by = collections.defaultdict(list)
    for j, y in enumerate(yp): by[y].append(j)
    rs = random.Random(2026); keep = []
    for y in sorted(by):
        js = by[y][:]; rs.shuffle(js); keep += js[:math.ceil(frac * len(js))]
    Xs, ys = [Xp[j] for j in sorted(keep)], [yp[j] for j in sorted(keep)]
    pr = model(C).fit(Xs, ys).predict(Xt)
    curve[f"{int(frac * 100)}%"] = dict(train=len(Xs), **share(sum(pr[i] == gold[o] for i, o in enumerate(ids)), len(ids)))
curve["100%"] = dict(train=len(Xp), **R["trained_top1"])
R["learning_curve"] = curve
same = [o for o in ids if rank[o][0] == shipped[o]["ch"]]
R["agreement"] = dict(share=trunc(len(same) / len(ids)), shipped_top1_where_same=share(sum(S1[o] for o in same), len(same)),
                      shipped_top1_where_different=share(sum(S1[o] for o in ids if o not in set(same)), len(ids) - len(same)),
                      trained_top1_where_different=share(sum(T1[o] for o in ids if o not in set(same)), len(ids) - len(same)))
(HERE / "results.json").write_text(json.dumps(R, indent=1, ensure_ascii=False) + "\n")
with open(HERE / "predictions.jsonl", "w") as f:
    for o in ids:
        f.write(json.dumps(dict(oid=o, gold=gold[o], trained=rank[o][0], trained_rank=rank[o], shipped=shipped[o]["ch"])) + "\n")
print(json.dumps(R, indent=1, ensure_ascii=False))
