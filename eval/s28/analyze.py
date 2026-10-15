"""S28 analysis (eval/PREREG-BUILD.md S28): the shipped pipeline in the no-prefill mode (QS_PREFILL=0) on the 927 S25
affairs vs the shipped prefill design (S25 final, eval/s25/decisions.jsonl). Decisions are composed from runs/s28 with
compose.decide in no-prefill mode: no calibration applies, so the lane is the readings rule only. No model calls.
-> eval/s28/results.json"""
import collections, gzip, json, math, os, random, sys
from pathlib import Path
os.environ["QS_PREFILL"] = "0"   # compose in the mode the rows were made in (prompt ids differ from the measured ones)
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt.compose import decide, read_run  # noqa: E402
from querschnitt.engine import Engine  # noqa: E402
from querschnitt.examples import ExamplePool  # noqa: E402

RUN, S25FP = ROOT / "runs/s28", "vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840"
items = {json.loads(l)["oid"]: json.loads(l) for l in open(ROOT / "eval/s25/items.jsonl")}
ship = {json.loads(l)["oid"]: json.loads(l) for l in open(ROOT / "eval/s25/decisions.jsonl")}
S25 = json.load(open(ROOT / "eval/s25/results.json"))
lock, rows = read_run(RUN)
assert lock["fp"] == S25FP and lock.get("mode") == "no-prefill", lock
for r in rows.values():   # build lock: every row on the S25 build, the 8b model, no-prefill mode
    m = r["meta"]
    assert m["fp"] == S25FP and m["model"] == "swiss-ai/apertus-v1.5-8b" and m.get("mode") == "no-prefill", (r["pid"], m)
eng = Engine(None, ExamplePool.load(ROOT / "data/eval/aps_pool.jsonl"))


def wout(k, n, z=1.96):
    if not n: return None
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return [math.floor((c - h) / d * 1000) / 1000, math.ceil((c + h) / d * 1000) / 1000]


trunc = lambda v, d=4: math.trunc(v * 10 ** d) / 10 ** d   # toward zero: never rounded up in magnitude
share = lambda k, n: dict(k=k, n=n, value=trunc(k / n) if n else None, ci=wout(k, n))


def read_path(r):
    """How the engine got the code of one step row: top_logprobs, the generated text (a single code at log-probability
    exactly 0.0, the engine's text fallback; an upper bound), or not at all (no listed code)."""
    c = r["codes"]
    if not c: return "unparseable"
    return "text" if (len(c) == 1 and next(iter(c.values())) == 0.0) else "logprobs"


D = {}
with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f:
    for line in f:
        a = json.loads(line)
        if a["id"] in items:
            d = decide(a, rows, eng.ch1_prompt, []).get("aps")
            if d and d["meta"].get("mode") == "no-prefill" and len(d["pids"]) == d["n_readings"] + 1:   # complete: readings + sub
                D[a["id"]] = d
gold = {o: items[o]["chapter"] for o in items}
ids = sorted(o for o in D if o in ship)
assert all(D[o]["p_cal"] is None for o in ids), "a no-prefill row got a calibrated p"
k1 = sum(D[o]["ch"] == gold[o] for o in ids); k3 = sum(gold[o] in D[o]["rank"][:3] for o in ids)
s1 = sum(ship[o]["ch"] == gold[o] for o in ids); s3 = sum(gold[o] in ship[o]["rank"][:3] for o in ids)

# paired bootstrap over items: shipped prefill − no-prefill (same resamples for top-1 and top-3)
v1 = [int(ship[o]["ch"] == gold[o]) - int(D[o]["ch"] == gold[o]) for o in ids]
v3 = [int(gold[o] in ship[o]["rank"][:3]) - int(gold[o] in D[o]["rank"][:3]) for o in ids]
rng = random.Random(2026); b1, b3 = [], []
for _ in range(2000):
    s = [rng.randrange(len(ids)) for _ in ids]
    b1.append(sum(v1[i] for i in s) / len(s)); b3.append(sum(v3[i] for i in s) / len(s))
b1.sort(); b3.sort()
pdiff = lambda v, b: dict(value=trunc(sum(v) / len(v)), ci95=[math.floor(b[50] * 1000) / 1000, math.ceil(b[1949] * 1000) / 1000],
                          prefill_only_right=sum(x == 1 for x in v), no_prefill_only_right=sum(x == -1 for x in v))

R = dict(prereg="eval/PREREG-BUILD.md S28", build=lock["fp"], mode=lock["mode"], items=len(items), scored=len(ids),
         missing=len(items) - len(ids),
         no_prefill_top1=share(k1, len(ids)), no_prefill_top3=share(k3, len(ids)),
         prefill_top1_same_items=share(s1, len(ids)), prefill_top3_same_items=share(s3, len(ids)),
         prefill_minus_no_prefill_top1=pdiff(v1, b1), prefill_minus_no_prefill_top3=pdiff(v3, b3),
         same_chapter_as_prefill=share(sum(D[o]["ch"] == ship[o]["ch"] for o in ids), len(ids)))
# lanes: no-prefill rows get no calibration, so pass = the readings agree (one reading with top p >= 0.9 counts as agree)
lane = collections.defaultdict(list)
for o in ids: lane[D[o]["lane"]].append(o)
R["lanes_no_prefill"] = {k: dict(share=trunc(len(v) / len(ids)), **share(sum(D[o]["ch"] == gold[o] for o in v), len(v)))
                         for k, v in sorted(lane.items())}
assert all((D[o]["lane"] == "pass") == (D[o]["readings"] == "agree") for o in ids)
R["lanes_prefill_s25"] = {k: S25["lanes"][k] for k in ("pass", "please_check", "readings_agree", "readings_disagree")}
R["by_design"] = {k: dict(no_prefill=share(sum(D[o]["ch"] == gold[o] for o in v), len(v)),
                          prefill=share(sum(ship[o]["ch"] == gold[o] for o in v), len(v))) for k, v in
                  (("D4 (German text: five examples)", [o for o in ids if D[o].get("examples")]),
                   ("D1 (no examples)", [o for o in ids if not D[o].get("examples")]))}
# how each step's code was read, over the rows the decisions use and over every row of the run
used = [rows[p] for o in ids for p in D[o]["pids"]]
R["read_path_rows_used"] = {st: dict(collections.Counter(read_path(r) for r in used if r["step"] == st))
                            for st in ("ch1", "ch2", "sub")}
R["read_path_rows_used"]["all"] = dict(collections.Counter(read_path(r) for r in used))
R["read_path_note"] = ("rows_used: per affair, the rows its decision uses (a row shared by affairs with identical prompts counts "
                        "once per affair); all_rows: every row of runs/s28 once")
R["read_path_all_rows"] = dict(collections.Counter(read_path(r) for r in rows.values()))
R["affairs_with_a_text_read"] = sum(any(read_path(rows[p]) == "text" for p in D[o]["pids"]) for o in ids)
R["affairs_with_an_unparseable_row"] = sum(any(read_path(rows[p]) == "unparseable" for p in D[o]["pids"]) for o in ids)
R["readings_per_affair"] = dict(collections.Counter(D[o]["n_readings"] for o in ids))
R["mass_in_listed_codes_ch1_mean"] = trunc(sum(r["meta"]["mass"] for r in used if r["step"] == "ch1") / max(1, sum(r["step"] == "ch1" for r in used)))


def ledger(p):
    L = [json.loads(l) for l in open(p)]
    return dict(calls=len(L), usd=trunc(sum(x["usd"] for x in L), 6), prompt_tokens=sum(x["pt"] for x in L),
                completion_tokens=sum(x["ct"] for x in L), fps=sorted({x["fp"] for x in L}), models=sorted({x["model"] for x in L}))


R["cost"] = dict(no_prefill=ledger(RUN / "ledger.jsonl"), prefill_s25=ledger(ROOT / "runs/s25/ledger.jsonl"),
                 note="list price (client.PRICES); the S25 ledger also holds its pre-fix re-asks (eval/PREREG-BUILD.md S25 amendment)")
R["cost"]["smoke1_discarded"] = ledger(ROOT / "runs/s28-smoke1/ledger.jsonl")   # before the read fix (amendment), never scored
R["cost"]["s28_total"] = dict(calls=R["cost"]["no_prefill"]["calls"] + R["cost"]["smoke1_discarded"]["calls"],
                              usd=trunc(R["cost"]["no_prefill"]["usd"] + R["cost"]["smoke1_discarded"]["usd"], 6))
R["cost"]["no_prefill"]["calls_per_affair"] = trunc(R["cost"]["no_prefill"]["calls"] / len(items), 3)
R["errors_logged"] = sum(1 for _ in open(RUN / "errors.jsonl")) if (RUN / "errors.jsonl").exists() else 0
R["sessions"] = [l.split("counts=")[1].strip() for l in open(RUN / "run.log") if "counts=" in l]
(HERE / "results.json").write_text(json.dumps(R, indent=1, ensure_ascii=False)); print(json.dumps(R, indent=1, ensure_ascii=False))
