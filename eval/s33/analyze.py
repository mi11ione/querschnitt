"""S33 analysis (eval/PREREG-BUILD.md S33): the 927 S25 held-out federal affairs read from the French text, with the design
production runs for a French federal affair (D1 read-back without examples, French frame), vs the APS editors' chapter and
paired against the shipped S25 decisions on the German text (eval/s25/decisions.jsonl, D4). Decisions are composed from
runs/s33 with compose.decide exactly as the export composes them. No model calls.
Secondary (a): same design at the level of the chapter readings (no read-back), German from eval/s25b/raw.jsonl (identity order,
no examples) + the S1-order rows of runs/s25, French from runs/s33 (the full German D1 read-back is not composable: see prereg).
-> eval/s33/results.json"""
import collections, gzip, json, math, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt import prompts as P  # noqa: E402
from querschnitt import data as Dm  # noqa: E402
from querschnitt.compose import decide, geo, read_run  # noqa: E402
from querschnitt.engine import Engine, mean_p, need_ch2  # noqa: E402
from querschnitt.examples import ExamplePool  # noqa: E402

RUN, FP, MODEL = ROOT / "runs/s33", "vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840", "swiss-ai/apertus-v1.5-8b"
items = {json.loads(l)["oid"]: json.loads(l) for l in open(ROOT / "eval/s25/items.jsonl")}
ship = {json.loads(l)["oid"]: json.loads(l) for l in open(ROOT / "eval/s25/decisions.jsonl")}
assert set(ship) == set(items)
lock, rows = read_run(RUN)
assert lock["fp"] == FP and not lock.get("mode"), lock
for r in rows.values():   # build lock: every row on the S25 build, the 8b model, prefill mode
    m = r["meta"]
    assert m["fp"] == FP and m["model"] == MODEL and not m.get("mode"), (r["pid"], m)
eng = Engine(None, ExamplePool.load(ROOT / "data/eval/aps_pool.jsonl"))


def wout(k, n, z=1.96):
    if not n: return None
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return [math.floor((c - h) / d * 1000) / 1000, math.ceil((c + h) / d * 1000) / 1000]


trunc = lambda v, d=4: math.trunc(v * 10 ** d) / 10 ** d   # toward zero: never rounded up in magnitude
share = lambda k, n: dict(k=k, n=n, value=math.floor(k / n * 10 ** 4) / 10 ** 4 if n else None, ci=wout(k, n))
argmax = lambda v: max(range(len(v)), key=lambda i: v[i])

# ---- French decisions (production composition)
X = {a["id"]: a for a in map(json.loads, gzip.open(HERE / "inputs_fr.jsonl.gz", "rt"))}
assert set(X) == set(items)
D = {}
for o, a in X.items():
    assert eng.ch1_prompt(a)[2] is None   # no examples for a French affair
    d = decide(a, rows, eng.ch1_prompt, []).get("aps")
    if d and len(d["pids"]) == d["n_readings"] + 1:   # complete: the readings + the subtopic request
        D[o] = d
gold = {o: items[o]["chapter"] for o in items}
ids = sorted(D)
N = len(ids)


def paired(va, vb):
    """paired bootstrap over affairs of mean(va − vb): 2,000 resamples, random.Random(2026), percentile 2.5/97.5, outward."""
    v = [a - b for a, b in zip(va, vb)]
    rng = random.Random(2026); bs = []
    for _ in range(2000):
        s = [rng.randrange(len(v)) for _ in v]
        bs.append(sum(v[i] for i in s) / len(s))
    bs.sort()
    return dict(value=trunc(sum(v) / len(v)), ci95=[math.floor(bs[50] * 1000) / 1000, math.ceil(bs[1949] * 1000) / 1000], n=len(v),
                first_only_right=sum(x == 1 for x in v), second_only_right=sum(x == -1 for x in v))


fr1 = [int(D[o]["ch"] == gold[o]) for o in ids]; de1 = [int(ship[o]["ch"] == gold[o]) for o in ids]
fr3 = [int(gold[o] in D[o]["rank"][:3]) for o in ids]; de3 = [int(gold[o] in ship[o]["rank"][:3]) for o in ids]
R = dict(prereg="eval/PREREG-BUILD.md 2026-10-16 11:33 CEST — S33", build=lock["fp"], model=MODEL, items=len(items), scored=N,
         missing=len(items) - N, with_examples=sum(bool(D[o].get("examples")) for o in ids),
         inputs=json.load(open(HERE / "inputs_counts.json")),
         french_top1=share(sum(fr1), N), german_shipped_top1=share(sum(de1), N),
         french_minus_german_top1=dict(paired(fr1, de1), note="first = French (S33), second = German shipped (S25 decisions, D4)"),
         french_top3=share(sum(fr3), N), german_shipped_top3=share(sum(de3), N),
         french_minus_german_top3=dict(paired(fr3, de3), note="the same 2,000 resamples as top-1 (same seed, same n)"),
         same_chapter_as_german=share(sum(D[o]["ch"] == ship[o]["ch"] for o in ids), N))

# ---- (a) same design, chapter readings only (no read-back): top of the geometric mean of the readings production asks
#      for a no-example affair (identity order; S1 order where the first top p < 0.9)
d0a = {json.loads(l)["oid"]: json.loads(l) for l in open(ROOT / "eval/s25b/raw.jsonl")}
_, rows25 = read_run(ROOT / "runs/s25")
base = {x["id"]: x for x in Dm.rows(ROOT.parent / "data/inputs.jsonl.gz") if x["id"] in items}
docs = Dm.docs_index(ROOT.parent / "data/opd-new/docs_slim.jsonl.gz",
                     {o for o, a in base.items() if P.pid(*P.chapter_prompt(a, list(range(25)))) != d0a[o]["pid"]})
old_input = 0


def s25_input(o):
    """the German input S25/S25b were asked on: the current production row, or (40 affairs) the same row with the untrimmed
    document head the inputs had before the 16 Oct rebuild (QS_TRIM_DOCS); verified by the d0a prompt id."""
    global old_input
    a = base[o]
    if P.pid(*P.chapter_prompt(a, list(range(25)))) == d0a[o]["pid"]:
        return a
    r, _, _ = Dm.pick_doc(docs.get(o, []), a["title"])
    a = dict(a, text=r["head"][:1500] if r else "")
    assert P.pid(*P.chapter_prompt(a, list(range(25)))) == d0a[o]["pid"], o
    old_input += 1
    return a


def readings_top(p1, p2):
    return argmax(geo(p1, p2) if p2 else p1)


RO, sub_have = {}, 0
for o in ids:
    a = s25_input(o); p1 = d0a[o]["p"]; p2 = None
    if need_ch2(p1):
        r2 = rows25.get(P.pid(*P.chapter_prompt(a, P.S1PERM)))
        if not r2: continue
        p2 = r2["p"]
    RO[o] = (readings_top(D[o]["R1"], D[o]["R2"]), readings_top(p1, p2), 2 if p2 else 1)
    sub_have += P.pid(*P.subtopic_prompt(a, P.subtopic_chapters(mean_p(p1, p2)))[:2]) in rows25   # the German D1 read-back's request
ro = sorted(RO)
fr_ro = [int(RO[o][0] == gold[o]) for o in ro]; de_ro = [int(RO[o][1] == gold[o]) for o in ro]
R["same_design_readings_only"] = dict(
    design="top of the geometric mean of the chapter readings production asks without examples (identity order; S1 order where "
           "the first top p < 0.9), no subtopic read-back, both languages",
    n=len(ro), french_top1=share(sum(fr_ro), len(ro)), german_top1=share(sum(de_ro), len(ro)),
    french_minus_german_top1=dict(paired(fr_ro, de_ro), note="first = French, second = German, same design"),
    german_two_readings=sum(RO[o][2] == 2 for o in ro), french_two_readings=sum(D[o]["n_readings"] == 2 for o in ro),
    german_inputs_matched_pre_rebuild=old_input,
    german_sources="eval/s25b/raw.jsonl (identity order, no examples) + runs/s25 ch2 rows (S1 order, no examples)")
R["same_design_read_back"] = dict(skipped=True, german_subtopic_rows_available=sub_have, missing=len(RO) - sub_have,
                                  why=f"the German D1 read-back needs the subtopic request over the chapter set of the no-example "
                                  f"readings; runs/s25 holds it for {sub_have} of the {len(RO)} affairs, so it is not composable "
                                  "without new calls (pre-registered)",
                                  count_note="the entry's count (171 of the 927, 716 missing) was made on the 16 Oct inputs, where the 40 "
                                  "affairs whose document text the rebuild trims match no S25 row; matched with their S25-time input "
                                  "here, the count is the one above; the skip stands either way")
# French read-back vs French readings-only (what the subtopic step adds in French), descriptive
R["french_read_back_minus_readings_only"] = dict(paired(fr1 if ro == ids else [fr1[ids.index(o)] for o in ro], fr_ro),
                                                 note="descriptive, not pre-registered")

# ---- (c) lanes
lane = collections.defaultdict(list)
for o in ids:
    lane["readings_" + D[o]["readings"]].append(o); lane[D[o]["lane"]].append(o)
R["lanes_french"] = {k: dict(share=trunc(len(v) / N), **share(sum(D[o]["ch"] == gold[o] for o in v), len(v))) for k, v in sorted(lane.items())}
R["lanes_rule"] = ("readings: disagree when the two code orders give different top chapters; one reading (top p >= 0.9, so no second "
                   "order) counts as agree. pass / please_check: production's lane (recalibrated p >= 0.7, map fitted on S16; "
                   "compose.decide)")
lg = collections.defaultdict(list)
for o in ids:
    lg["readings_" + ship[o]["readings"]].append(o); lg[ship[o]["lane"]].append(o)
R["lanes_german_shipped"] = {k: dict(share=trunc(len(v) / N), **share(sum(ship[o]["ch"] == gold[o] for o in v), len(v))) for k, v in sorted(lg.items())}
R["readings_per_affair_french"] = dict(collections.Counter(D[o]["n_readings"] for o in ids))

# ---- (d) with French text vs title only
for name, s in (("french_with_text", [o for o in ids if X[o]["text"]]), ("french_title_only", [o for o in ids if not X[o]["text"]])):
    R[name] = dict(french=share(sum(D[o]["ch"] == gold[o] for o in s), len(s)),
                   german_shipped_same_items=share(sum(ship[o]["ch"] == gold[o] for o in s), len(s)))
s = [o for o in ids if not X[o]["text"] and base[o].get("text_kind") == "doc"]
R["french_title_only_german_document_text"] = dict(french=share(sum(D[o]["ch"] == gold[o] for o in s), len(s)),
                                                   german_shipped_same_items=share(sum(ship[o]["ch"] == gold[o] for o in s), len(s)))
s = [o for o in ids if not X[o]["text"] and not base[o].get("text")]
R["french_title_only_german_no_text"] = dict(french=share(sum(D[o]["ch"] == gold[o] for o in s), len(s)),
                                             german_shipped_same_items=share(sum(ship[o]["ch"] == gold[o] for o in s), len(s)))


# ---- cost
def ledger(p):
    L = [json.loads(l) for l in open(p)]
    return dict(calls=len(L), usd=trunc(sum(x["usd"] for x in L), 6), prompt_tokens=sum(x["pt"] for x in L),
                completion_tokens=sum(x["ct"] for x in L), fps=sorted({x["fp"] for x in L}), models=sorted({x["model"] for x in L}))


lost = sum(1 for _ in open(RUN / "errors-first-launch.jsonl")) if (RUN / "errors-first-launch.jsonl").exists() else 0
R["cost"] = dict(ledger(RUN / "ledger.jsonl"), rows=len(rows), calls_per_affair=trunc(len(rows) / len(items), 3),
                 first_launch_calls_not_written=lost,
                 note="list price (client.PRICES); the ledger includes the first launch's 25 answered calls whose rows were not "
                      "written (the run dir lacked its build folder; eval/s33/run.py), re-asked on relaunch")
R["errors_logged"] = sum(1 for _ in open(RUN / "errors.jsonl")) if (RUN / "errors.jsonl").exists() else 0
R["gold_chapters"] = dict(collections.Counter(gold[o] for o in ids).most_common())
(HERE / "results.json").write_text(json.dumps(R, indent=1, ensure_ascii=False)); print(json.dumps(R, indent=1, ensure_ascii=False))
