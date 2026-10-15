"""Hierarchical metrics for the shipped design on the S25 held-out items, computed after the S25 result from its rows
(eval/s25/decisions.jsonl and the subtopics composed again here). No model calls, no network. Not pre-registered: the same
definitions as eval/s16/hierarchical.py, applied to S25 once.
Subtopic gold = the process page's main subtopic when it is one of the scheme's 190 (`aps:kw:<id>`).
  (1) subtopic top-1 / top-3 end to end (items with a subtopic gold; a hit needs chapter and subtopic right), Wilson 95%.
  (2) subtopic top-1 given the shipped chapter is right (conditional), Wilson 95%.
  (3) hierarchical P / R / F1 (Kiritchenko et al.; label sets augmented with their ancestors; tree chapter → subtopic; root
      not counted; micro-averaged) on the subtopic-gold items; percentile bootstrap 2,000.
  (4) macro-F1 of the chapter over the chapters present in the gold (all items); bootstrap stratified by gold chapter.
Interval bounds rounded outward at 3 decimals; points truncated at 4. -> eval/s25/hierarchical.json"""
import collections, gzip, json, math, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt.compose import decide, read_run  # noqa: E402
from querschnitt.engine import Engine  # noqa: E402
from querschnitt.examples import ExamplePool  # noqa: E402
from querschnitt.scheme import APS  # noqa: E402

items = {json.loads(l)["oid"]: json.loads(l) for l in open(HERE / "items.jsonl")}
lock, rows = read_run(ROOT / "runs/s25")
eng = Engine(None, ExamplePool.load(ROOT / "data/eval/aps_pool.jsonl"))
D = {}
with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f:
    for line in f:
        a = json.loads(line)
        if a["id"] in items:
            d = decide(a, rows, eng.ch1_prompt, []).get("aps")
            if d:
                D[a["id"]] = d
ids = sorted(D)
gold_ch = {o: items[o]["chapter"] for o in ids}
gold_sub = {o: f"aps:kw:{items[o]['subtopic_id']}" for o in ids if f"aps:kw:{items[o].get('subtopic_id')}" in APS.sub_index}
subs = {o: [c for c, _ in D[o]["subs"]] for o in ids}


def wout(k, n, z=1.959964):
    if not n: return None
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return [math.floor((c - h) / d * 1000) / 1000, math.ceil((c + h) / d * 1000) / 1000]


trunc = lambda v: math.floor(v * 10 ** 4) / 10 ** 4
share = lambda k, n: dict(k=k, n=n, value=trunc(k / n) if n else None, ci95=wout(k, n))
outward = lambda v: [math.floor(v[int(.025 * len(v))] * 1000) / 1000, math.ceil(v[int(.975 * len(v)) - 1] * 1000) / 1000]
sg = sorted(gold_sub)
R = dict(prereg="not pre-registered: computed after the S25 result (eval/s16/hierarchical.py definitions)", build=lock["fp"],
         items=len(ids), subtopic_gold_items=len(sg))
R["subtopic_top1"] = share(sum(bool(subs[o]) and subs[o][0] == gold_sub[o] for o in sg), len(sg))
R["subtopic_top3"] = share(sum(gold_sub[o] in subs[o][:3] for o in sg), len(sg))
right = [o for o in sg if D[o]["ch"] == gold_ch[o]]
R["subtopic_top1_given_chapter_right"] = share(sum(bool(subs[o]) and subs[o][0] == gold_sub[o] for o in right), len(right))


def hsets(o):
    g = {("c", gold_ch[o]), ("s", gold_sub[o])}
    p = {("c", D[o]["ch"])} if D[o]["ch"] < 24 else set()
    if subs[o] and D[o]["ch"] < 24:
        c, _ = APS.sub_index[subs[o][0]]
        p |= {("c", c), ("s", subs[o][0])}
    return len(p & g), len(p), len(g)


def hprf(sample):
    t = [hsets(o) for o in sample]; i, p, g = (sum(x[j] for x in t) for j in range(3))
    hp, hr = i / p if p else 0, i / g
    return hp, hr, 2 * hp * hr / (hp + hr) if hp + hr else 0


hp, hr, hf = hprf(sg); rng = random.Random(7); bs = [hprf([rng.choice(sg) for _ in sg]) for _ in range(2000)]
R["hierarchical"] = {k: dict(value=trunc(v), ci95=outward(sorted(b[j] for b in bs))) for j, (k, v) in enumerate((("hP", hp), ("hR", hr), ("hF1", hf)))}


def macro(sample):
    chs = sorted({gold_ch[o] for o in sample}); f = []
    for c in chs:
        tp = sum(D[o]["ch"] == c and gold_ch[o] == c for o in sample); fp = sum(D[o]["ch"] == c and gold_ch[o] != c for o in sample)
        fn = sum(D[o]["ch"] != c and gold_ch[o] == c for o in sample)
        f.append(2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0)
    return sum(f) / len(f)


by = collections.defaultdict(list)
for o in ids: by[gold_ch[o]].append(o)
rng = random.Random(7); mb = sorted(macro([rng.choice(v) for v in by.values() for _ in v]) for _ in range(2000))
R["chapter_macro_f1"] = dict(value=trunc(macro(ids)), ci95=outward(mb), chapters=len(by))
(HERE / "hierarchical.json").write_text(json.dumps(R, indent=1)); print(json.dumps(R, indent=1))
