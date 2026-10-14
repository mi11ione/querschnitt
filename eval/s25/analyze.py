"""S25 analysis (eval/PREREG-BUILD.md 2026-10-14 20:20): the shipped federal design on fresh APS-labelled affairs, held out.
Decisions are composed from runs/s25 exactly as the export composes them (compose.decide, the S5+S9 example pool, the
calibration map fitted on S16 only) and scored against the APS editors' chapter. No model calls.
-> eval/s25/results.json"""
import collections, gzip, json, math, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt.compose import decide, read_run  # noqa: E402
from querschnitt.engine import Engine  # noqa: E402
from querschnitt.examples import ExamplePool  # noqa: E402
from querschnitt.scheme import APS  # noqa: E402

S9 = HERE.parent / "spikes/s9-aps/data"  # vendored S9 (eval/spikes/)
items = {json.loads(l)["oid"]: json.loads(l) for l in open(HERE / "items.jsonl")}
lock, rows = read_run(ROOT / "runs/s25")
eng = Engine(None, ExamplePool.load(ROOT / "data/eval/aps_pool.jsonl"))
pool_ids = {x.get("oid") or x.get("id") for x in map(json.loads, open(ROOT / "data/eval/aps_pool.jsonl"))}
assert not pool_ids & set(items), "an S25 item is in the example pool"


def wout(k, n, z=1.96):
    if not n: return None
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return [math.floor((c - h) / d * 1000) / 1000, math.ceil((c + h) / d * 1000) / 1000]


trunc = lambda v, d=4: math.floor(v * 10 ** d) / 10 ** d
share = lambda k, n: dict(k=k, n=n, value=trunc(k / n) if n else None, ci=wout(k, n))

# frozen S9 keyword rule (keywords_frozen.json, majority order of the S9 gold), on the fields the model sees
KW = json.load(open(S9 / "keywords_frozen.json")); kw = {int(c): v["keywords"] for c, v in KW["chapters"].items()}
s9c = collections.Counter(it["chapter"] for it in json.load(open(S9 / "items.json")))
majorder = [c for c, _ in s9c.most_common()] + [c for c in range(24) if c not in s9c]


def kw_pred(a):
    txt = " ".join((a.get("title") or "", a.get("title_long") or "", a.get("text") or "")).lower()
    sc = {c: sum(w in txt for w in kw[c]) for c in range(24)}
    m = max(sc.values())
    return min([c for c in range(24) if sc[c] == m], key=majorder.index)


D, K, langs = {}, {}, {}
with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f:
    for line in f:
        a = json.loads(line)
        if a["id"] not in items:
            continue
        K[a["id"]] = kw_pred(a); langs[a["id"]] = a["lang"]
        d = decide(a, rows, eng.ch1_prompt, []).get("aps")
        if d:
            D[a["id"]] = d
gold = {o: items[o]["chapter"] for o in items}
ids = sorted(D)
k1 = sum(D[o]["ch"] == gold[o] for o in ids); k3 = sum(gold[o] in D[o]["rank"][:3] for o in ids)
R = dict(prereg="eval/PREREG-BUILD.md 2026-10-14 20:20 CEST", build=lock.get("fp"), items=len(items), scored=len(ids),
         missing=len(items) - len(ids), with_examples=sum(bool(D[o].get("examples")) for o in ids),
         top1=share(k1, len(ids)), top3=share(k3, len(ids)),
         keyword_top1=share(sum(K[o] == gold[o] for o in ids), len(ids)),
         keyword_top1_all_items=share(sum(K[o] == gold[o] for o in K), len(K)))
lane = collections.defaultdict(list)
for o in ids:
    lane[D[o]["lane"]].append(o); lane["readings_" + D[o]["readings"]].append(o)
R["lanes"] = {k: dict(share=trunc(len(v) / len(ids)), **share(sum(D[o]["ch"] == gold[o] for o in v), len(v))) for k, v in sorted(lane.items())}
# coverage–precision when routing by calibrated p (map fitted on S16 only)
cp = sorted(ids, key=lambda o: -(D[o]["p_cal"] or 0))
R["routing_by_p_cal"] = {str(t): dict(coverage=trunc(len(s) / len(ids)), **share(sum(D[o]["ch"] == gold[o] for o in s), len(s)))
                         for t in (0.5, 0.6, 0.7, 0.8, 0.9) for s in [[o for o in ids if (D[o]["p_cal"] or 0) >= t]]}
by_lang = collections.defaultdict(list)
for o in ids: by_lang[langs[o]].append(o)
R["by_lang"] = {l: share(sum(D[o]["ch"] == gold[o] for o in v), len(v)) for l, v in sorted(by_lang.items())}
R["by_design"] = {k: share(sum(D[o]["ch"] == gold[o] for o in v), len(v)) for k, v in
                  (("D4 (German text: five examples)", [o for o in ids if D[o].get("examples")]),
                   ("D1 (French/Italian text: no examples)", [o for o in ids if not D[o].get("examples")]))}
R["gold_chapters"] = {APS.names["de"][c]: n for c, n in collections.Counter(gold[o] for o in ids).most_common()}
(HERE / "results.json").write_text(json.dumps(R, indent=1, ensure_ascii=False)); print(json.dumps(R, indent=1, ensure_ascii=False))
