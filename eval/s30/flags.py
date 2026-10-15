"""S30: test topics, population, frozen keywords and each arm's flag per (affair, topic), from raw.jsonl. No model calls."""
import json
from run_common import HERE, ROOT, PERIOD, population, ARMS

KW = json.loads((HERE / "keywords_frozen.json").read_text())


def kw_hit(slug, x):
    t = " " + (x["title"][:400] + " " + (x["title_long"][:400] if x["title_long"] != x["title"] else "")).lower() + " "
    return any(s in t for s in KW[slug])


def load():
    T = json.loads((HERE / "topics.json").read_text())
    X = {x["id"]: x for x in population()}
    R = {}
    for l in open(HERE / "raw.jsonl"):
        r = json.loads(l); R[(r["id"], r["topic"], r["step"])] = r
    F = {}
    for i, x in X.items():
        for slug in T:
            g = lambda step: R.get((i, slug, step))
            F[(i, slug)] = dict({a: bool(f(g)) for a, f in ARMS.items()}, kw=kw_hit(slug, x))
    return T, X, F
