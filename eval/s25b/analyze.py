"""S25b analysis (eval/PREREG-BUILD.md): plain list prompting (S9 D0) on the S25 items vs the shipped pipeline. D0 = top of the
geometric mean of d0a (identity order, no examples: eval/s25b/raw.jsonl, or the S25 run's first reading for the affairs read
without examples) and d0b (the S25 run's second reading, S1 permutation, no examples). No model calls.
-> eval/s25b/results.json"""
import gzip, json, math, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt import prompts as P  # noqa: E402
from querschnitt.compose import geo, read_run  # noqa: E402

items = {json.loads(l)["oid"]: json.loads(l) for l in open(ROOT / "eval/s25/items.jsonl")}
ship = {json.loads(l)["oid"]: json.loads(l) for l in open(ROOT / "eval/s25/decisions.jsonl")}
d0a = {json.loads(l)["oid"]: json.loads(l)["p"] for l in open(HERE / "raw.jsonl")}
lock, rows = read_run(ROOT / "runs/s25")
D0 = {}
with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f:
    for line in f:
        a = json.loads(line)
        if a["id"] not in items:
            continue
        ra = rows.get(P.pid(*P.chapter_prompt(a, list(range(25)))))   # identity order, no examples
        pa = d0a.get(a["id"]) or (ra and ra["p"])
        rb = rows.get(P.pid(*P.chapter_prompt(a, P.S1PERM)))
        if pa and rb:
            g = geo(pa, rb["p"]); D0[a["id"]] = max(range(25), key=lambda i: g[i])
ids = sorted(o for o in D0 if o in ship)
gold = {o: items[o]["chapter"] for o in ids}


def wout(k, n, z=1.959964):
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return [math.floor((c - h) / d * 1000) / 1000, math.ceil((c + h) / d * 1000) / 1000]


trunc = lambda v: math.floor(v * 10 ** 4) / 10 ** 4
v0 = [int(D0[o] == gold[o]) for o in ids]; vs = [int(ship[o]["ch"] == gold[o]) for o in ids]
rng = random.Random(2026); diffs = []
for _ in range(2000):
    s = [rng.randrange(len(ids)) for _ in ids]
    diffs.append(sum(vs[i] - v0[i] for i in s) / len(s))
diffs.sort()
R = dict(prereg="eval/PREREG-BUILD.md S25b", build=lock["fp"], n=len(ids), d0a_asked=len(d0a),
         not_scored=dict(n=len(items) - len(ids), why="no d0b: one-word procedural affairs (Vereidigung, Nachruf, "
                         "Ordnungsantrag) with no APS-labelled neighbour are read without examples, and their first reading was p >= 0.9, "
                         "so the production run asked no second reading (engine.need_ch2); D0 needs both"),
         D0_top1=dict(k=sum(v0), n=len(ids), value=trunc(sum(v0) / len(ids)), ci95=wout(sum(v0), len(ids))),
         shipped_top1=dict(k=sum(vs), n=len(ids), value=trunc(sum(vs) / len(ids)), ci95=wout(sum(vs), len(ids))),
         shipped_minus_D0=dict(value=round((sum(vs) - sum(v0)) / len(ids), 4),
                               ci95=[math.floor(diffs[50] * 1000) / 1000, math.ceil(diffs[1949] * 1000) / 1000]))
(HERE / "results.json").write_text(json.dumps(R, indent=1)); print(json.dumps(R, indent=1))
