"""S32: neutrality of the SHIPPED federal design (D4 as it runs in production), a re-analysis of existing measurements.
NOT pre-registered; no model calls, no network. It repeats the S14 breakdowns (eval/spikes/s14-neutrality, which used the earlier
D1 design) on the decisions that ship:
  * S9 prod: the 1,357 S9 APS-labelled federal affairs as composed for production (eval/prod_gold/topics.jsonl.gz, written by
    eval/prod_gold/rows.py from runs/main + runs/side with the export's rule; the rows `make eval GOLD=data/eval/gold_aps_s9.csv`
    scores). 1,340 are scored, 17 have no chapter row.
  * S25: the 927 held-out affairs (eval/s25/decisions.jsonl, composed by eval/s25/analyze.py with compose.decide).
  * pooled: both (top-1 only; permutation within set).
  * secondary: S16 D4 on the S9 items (eval/s16/raw.jsonl, S9 input), the pre-registered S16 design measurement.
Gold: the APS editors' chapter. Submitter party / kind and instrument: S14's own functions (eval/spikes/s14-neutrality/scripts/s14lib.py,
executed unchanged except for the line that loads its OPD subset) on the OpenParlData export the production run reads
(../data/opd-new, 16 Oct 2026; it reproduces S14's S9 submitter cells exactly). Language: `text_lang` of the production input.
Statistics as S14: Wilson 95% per cell; permutation test (5,000, seed 14) of Pearson's chi-square across cells (+ asymptotic p);
largest gap = highest − lowest cell among tested cells with n >= SMALL, interval from independent within-cell bootstraps (2,000).
Deviation from S14: SMALL = 30 (S14: 20). Points truncated at 4 decimals; Wilson bounds and bootstrap bounds rounded outward at 3.
Usage: .venv/bin/python -I eval/s32/analyze.py  -> eval/s32/results.json"""
import collections, csv, gzip, json, math, random, sys, time, types
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt import prompts as P  # noqa: E402
from querschnitt.scheme import APS  # noqa: E402

EXPORT = ROOT.parent / "data/opd-new"          # the OPD export the production run reads (make data / querschnitt delta)
INPUTS = ROOT.parent / "data/inputs.jsonl.gz"  # production inputs (S25 affairs' text language)
S14LIB = ROOT / "eval/spikes/s14-neutrality/scripts/s14lib.py"
S9D = ROOT / "eval/spikes/s9-aps/data"
SMALL, NB, NPERM = 30, 2000, 5000

# ---------------------------------------------------------------- ids
s9_items = {it["oid"]: it for it in json.load(open(S9D / "items.json"))}
s25_dec = {d["oid"]: d for d in map(json.loads, open(ROOT / "eval/s25/decisions.jsonl"))}
IDS = set(s9_items) | set(s25_dec)

# ---------------------------------------------------------------- S14's submitter functions on the production OPD export
KEEP = ("id", "affair_id", "body_key", "type", "role_de", "role_harmonized", "fullname", "person_id", "group_id", "party_de",
        "party_harmonized_de", "position")   # as S14 scripts/extract.py
contrib = collections.defaultdict(list)
for line in gzip.open(EXPORT / "contributors.ndjson.gz", "rt"):
    r = json.loads(line)
    if r["affair_id"] in IDS: contrib[r["affair_id"]].append({k: r.get(k) for k in KEEP})
aff = {}
for line in gzip.open(EXPORT / "affairs.ndjson.gz", "rt"):
    r = json.loads(line)
    if int(r["id"]) in IDS:
        aff[int(r["id"])] = dict(body_key=r["body_key"], type=r.get("type_harmonized_de") or r.get("type_name_de"),
                                 type_raw=r.get("type_name_de"), number=r.get("number"))
assert set(aff) == IDS, IDS - set(aff)
src = S14LIB.read_text(encoding="utf-8")
LOADLINE = "OPD = json.load(open(f'{H}/data/opd_subset.json'))"
assert src.count(LOADLINE) == 1
L = types.ModuleType("s14lib"); L.__file__ = str(S14LIB)
L._OPD = dict(contributors={str(k): v for k, v in contrib.items()}, affairs={str(k): v for k, v in aff.items()}, bodies={})
exec(compile(src.replace(LOADLINE, "OPD = _OPD"), str(S14LIB), "exec"), L.__dict__)
SUB = {o: L.submitter(o)[0] for o in IDS}
# check: the S9 submitter cells equal S14's (eval/spikes/s14-neutrality/results.json, party > D1_top1 cells)
s14 = json.load(open(ROOT / "eval/spikes/s14-neutrality/results.json"))
s14n = {c["cell"]: c["n"] for c in s14["S9"]["party"]["D1_top1"]["cells"]}
mine = collections.Counter(SUB[o] for o in s9_items)
assert dict(mine) == s14n, (dict(mine), s14n)

MEMBER = L.MAIN + ["other party", "party unknown"]
kind = lambda o: "member/faction" if SUB[o] in MEMBER else SUB[o]
TYPES = ("Motion", "Postulat", "Regierungsgeschäft", "Parlamentarische Initiative", "Standesinitiative")
instr = lambda o: aff[o]["type"] if aff[o]["type"] in TYPES else "other type"
ORD_PARTY = L.MAIN + ["other party", "party unknown", "committee", "government", "canton", "other group", "unknown"]
ORD_KIND = ["member/faction", "committee", "government", "canton", "other group", "unknown"]
ORD_TYPE = list(TYPES) + ["other type"]

# ---------------------------------------------------------------- frozen S9 keyword rule (as eval/s25/analyze.py, on the production input)
KW = json.load(open(S9D / "keywords_frozen.json")); kw = {int(c): v["keywords"] for c, v in KW["chapters"].items()}
s9c = collections.Counter(it["chapter"] for it in s9_items.values())
majorder = [c for c, _ in s9c.most_common()] + [c for c in range(24) if c not in s9c]


def kw_pred(a):
    txt = " ".join((a.get("title") or "", a.get("title_long") or "", a.get("text") or "")).lower()
    sc = {c: sum(w in txt for w in kw[c]) for c in range(24)}
    m = max(sc.values())
    return min([c for c in range(24) if sc[c] == m], key=majorder.index)


# ---------------------------------------------------------------- S9 production rows (what ships; `make eval` scores the same rows)
CODE = {c: i for i, c in enumerate(APS.codes)}
gold9 = {}
for r in csv.DictReader(open(ROOT / "data/eval/gold_aps_s9.csv", encoding="utf-8")):
    gold9[int(r["affair_id"])] = CODE[r["code"]]
assert set(gold9) == set(s9_items) and all(gold9[o] == s9_items[o]["chapter"] for o in gold9)
latest = {}
for line in gzip.open(ROOT / "eval/prod_gold/topics.jsonl.gz", "rt"):
    t = json.loads(line)
    if t["scheme"] != "aps" or t["level"] != 1 or t["provenance"] == "editor": continue
    key = (t["affair_id"], t["rank"])
    if key not in latest or t["valid_from"] > latest[key]["valid_from"]: latest[key] = t
rank9 = collections.defaultdict(dict)
for (o, rk), t in latest.items(): rank9[o][rk] = CODE[t["code"]]
inp9 = {a["id"]: a for a in map(json.loads, gzip.open(ROOT / "eval/prod_gold/inputs.jsonl.gz", "rt"))}
assert set(inp9) == set(s9_items)
S9P = {}
for o in sorted(rank9):
    rk = [rank9[o][i] for i in sorted(rank9[o])]
    S9P[o] = dict(top1=int(rk[0] == gold9[o]), top3=int(gold9[o] in rk[:3]), kw=int(kw_pred(inp9[o]) == gold9[o]), lang=inp9[o]["text_lang"])
ev = json.load(open(ROOT / "eval/results/eval-gold_aps_s9.json"))["schemes"]["aps"]
assert (sum(x["top1"] for x in S9P.values()), len(S9P)) == (ev["overall"]["accuracy"]["k"], ev["overall"]["accuracy"]["n"]), "≠ make eval"
assert sum(x["top3"] for x in S9P.values()) == ev["overall"]["top3"]["k"] and len(s9_items) - len(S9P) == ev["not_scored"]
unscored9 = sorted(set(s9_items) - set(S9P))

# ---------------------------------------------------------------- S25 held-out decisions; text language from the production inputs
lang25 = {}
with gzip.open(INPUTS, "rt") as f:
    for line in f:
        if '"id": ' not in line[:40]: continue
        a = json.loads(line)
        if a["id"] in s25_dec: lang25[a["id"]] = a.get("text_lang") or a["lang"]
assert set(lang25) == set(s25_dec), set(s25_dec) - set(lang25)
S25 = {o: dict(top1=int(d["ch"] == d["gold"]), top3=int(d["gold"] in d["rank"][:3]), kw=int(d["keyword"] == d["gold"]), lang=lang25[o])
       for o, d in s25_dec.items()}
s25r = json.load(open(ROOT / "eval/s25/results.json"))
assert sum(x["top1"] for x in S25.values()) == s25r["top1"]["k"] and sum(x["top3"] for x in S25.values()) == s25r["top3"]["k"]
assert sum(x["kw"] for x in S25.values()) == s25r["keyword_top1"]["k"]

# ---------------------------------------------------------------- S16 D4 on the S9 items (secondary; the S16 read-back, eval/s16/analyze.py)
order = lambda p: sorted(range(len(p)), key=lambda i: -p[i])


def readback(prior, chs, psub):   # = eval/s16/analyze.py readback (chapter of the best p(subtopic) × prior)
    opts = P.subtopic_options(chs)
    sc = {(c, j): psub[k] * prior[c] for k, (c, j) in enumerate(opts)}
    best = max(sc, key=sc.get); chbest = {}
    for (c, j), v in sc.items(): chbest[c] = max(chbest.get(c, 0), v)
    return best[0], sorted(chbest, key=lambda c: -chbest[c]) + [c for c in order(prior) if c not in chbest]


s16raw = {json.loads(l)["oid"]: json.loads(l) for l in open(ROOT / "eval/s16/raw.jsonl")}
S16 = {}
for o in sorted(s16raw):
    x = s16raw[o]["d4"]; ch, rk = readback(x["prior"], x["chs"], x["p"])
    S16[o] = dict(top1=int(ch == gold9[o]), top3=int(gold9[o] in rk[:3]), lang=inp9[o]["text_lang"])
s16r = json.load(open(ROOT / "eval/s16/results.json"))
assert sum(x["top1"] for x in S16.values()) == s16r["designs"]["D4"]["k1"] and len(S16) == s16r["n"]

# ---------------------------------------------------------------- statistics (S14's, eval/spikes/s14-neutrality/scripts/analyze.py `dimension`)
trunc = lambda v, d=4: math.trunc(v * 10 ** d) / 10 ** d
fl3, ce3 = (lambda v: math.floor(v * 1000) / 1000), (lambda v: math.ceil(v * 1000) / 1000)


def wout(k, n, z=1.96):   # Wilson 95%, clipped to [0, 1], bounds rounded outward at 3 decimals (as eval/s25/analyze.py)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return [math.floor(max((c - h) / d, 0.0) * 1000) / 1000, math.ceil(min((c + h) / d, 1.0) * 1000) / 1000]


def boot_cell(ys, rng):
    return sorted(sum(rng.choice(ys) for _ in ys) / len(ys) for _ in range(NB))


def q(v): return [v[int(.025 * len(v))], v[int(.975 * len(v)) - 1]]   # S14's percentile picks


def gap(groups, cand, seed, basis):
    hi = max(cand, key=lambda c: c["p"]); lo = min(cand, key=lambda c: c["p"])
    rng = random.Random(seed)
    bh, bl = boot_cell(groups[hi["cell"]], rng), boot_cell(groups[lo["cell"]], rng)
    rng2 = random.Random(seed + 1); d = sorted(bh[rng2.randrange(NB)] - bl[rng2.randrange(NB)] for _ in range(NB))
    raw = q(d)
    return dict(hi=hi["cell"], lo=lo["cell"], diff=trunc(hi["p"] - lo["p"]), ci=[fl3(raw[0]), ce3(raw[1])], ci_raw=[round(x, 4) for x in raw],
                basis=basis, ci_method="independent within-cell bootstraps (2,000 each, random.Random(14)), paired at random (random.Random(15)); "
                "2.5 / 97.5 percentiles as S14, bounds rounded outward at 3 decimals")


def dimension(rows, order_, test_groups=None, strata=None, seed=14, test=True):
    """rows: (cell, y) pairs. Cells with k/n, truncated share, outward Wilson; S14's permutation test over test_groups; largest gap."""
    groups = collections.defaultdict(list)
    for g_, y in rows: groups[g_].append(y)
    keys = [k for k in order_ if k in groups] + sorted(k for k in groups if k not in order_)
    cells = []
    for g_ in keys:
        ys = groups[g_]; k = sum(ys); n = len(ys)
        c = dict(cell=g_, k=k, n=n, value=trunc(k / n), ci=wout(k, n), p=k / n)
        if n < SMALL: c["small"] = True
        cells.append(c)
    K = sum(y for _, y in rows); N = len(rows)
    out = dict(overall=dict(k=K, n=N, value=trunc(K / N), ci=wout(K, N)), cells=cells)
    tg = test_groups or keys
    if test and len([g_ for g_ in keys if g_ in tg]) >= 2:
        idx = [i for i, (g_, _) in enumerate(rows) if g_ in tg]
        t = L.perm_test([rows[i][0] for i in idx], [rows[i][1] for i in idx], None, [strata[i] for i in idx] if strata else None, n=NPERM, seed=seed)
        if strata: t["p_chi2_note"] = "asymptotic p ignores the set strata; the permutation shuffles within set"
        t["cells_tested"] = [g_ for g_ in keys if g_ in tg]
        out["test"] = t
        big = [c for c in cells if c["cell"] in tg and c["n"] >= SMALL]
        if len(big) >= 2: out["gap"] = gap(groups, big, seed, f"tested cells with n >= {SMALL}")
        allc = [c for c in cells if c["cell"] in tg]
        if len(allc) > len(big) and len(allc) >= 2:
            out["gap_all_tested_cells"] = gap(groups, allc, seed, "every tested cell, small ones included")
    for c in cells: c.pop("p")
    return out


def analyse(D, metrics, label):
    ids = sorted(D)
    res = {"n": len(ids)}
    dims = (("party", lambda o: SUB[o], ORD_PARTY, L.MAIN), ("submitter kind", kind, ORD_KIND, None),
            ("instrument", instr, ORD_TYPE, None), ("language of the text", lambda o: D[o]["lang"], ["de", "fr", "it"], None))
    for dim, f, ordr, tg in dims:
        res[dim] = {}
        for m in metrics:
            rows = [(f(o), D[o][m]) for o in ids]
            langs = {D[o]["lang"] for o in ids}
            informative = dim != "language of the text" or min(collections.Counter(D[o]["lang"] for o in ids).values()) >= SMALL and len(langs) > 1
            res[dim][m] = dimension(rows, ordr, tg, test=informative)
            if not informative:
                res[dim][m]["test"] = None
                res[dim][m]["not_informative"] = (f"{dict(collections.Counter(D[o]['lang'] for o in ids))}: every input of the shipped federal "
                                                  "design is read in one language, so this set cannot measure a language effect")
        if dim == "party":
            res[dim]["top1_all_categories_test"] = dimension([(f(o), D[o]["top1"]) for o in ids], ordr)["test"]
    print(label, "done", time.strftime("%H:%M:%S"), flush=True)
    return res


R = dict(test="S32", generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), prereg=None,
         not_preregistered="a re-analysis of existing measurements (S9 production rows, S25 held-out decisions, S16 raw); no model calls; "
                           "written after the reviewer note (round 8, J2 change 2) that S14 measured the earlier D1 design",
         small_threshold=SMALL, permutations=NPERM, bootstrap=NB,
         sources=dict(party_functions="eval/spikes/s14-neutrality/scripts/s14lib.py (unchanged; OPD subset replaced by the export below)",
                      opd_export="../data/opd-new (affairs.ndjson.gz, contributors.ndjson.gz; OpenParlData export of 16 Oct 2026)",
                      s9_rows="eval/prod_gold/topics.jsonl.gz + inputs.jsonl.gz (eval/prod_gold/rows.py)", s9_gold="data/eval/gold_aps_s9.csv",
                      s25="eval/s25/decisions.jsonl", s25_lang="../data/inputs.jsonl.gz (text_lang)", s16="eval/s16/raw.jsonl"),
         checks=dict(s9_submitter_cells_equal_s14=True, s9_prod_top1=[sum(x["top1"] for x in S9P.values()), len(S9P)],
                     s9_prod_equals_make_eval="eval/results/eval-gold_aps_s9.json", s25_top1=[s25r["top1"]["k"], s25r["top1"]["n"]],
                     s16_d4_top1=[s16r["designs"]["D4"]["k1"], s16r["n"]]),
         shipped_path="S9 prod = the production rows (D4 where the affair has APS-labelled neighbours, D1 otherwise, as compose.decide); "
                      "S25 = the same composition on the held-out affairs. S16 D4 (S9 input, every item with examples) is secondary.")
R["s9_prod"] = analyse(S9P, ("top1", "top3", "kw"), "s9_prod")
R["s9_prod"]["not_scored"] = dict(n=len(unscored9), ids=unscored9, by_party=dict(collections.Counter(SUB[o] for o in unscored9)),
                                  why="no APS chapter row in the production run (as make eval: not scored)")
R["s25"] = analyse(S25, ("top1", "top3", "kw"), "s25")
PO = {("s9", o): v for o, v in S9P.items()} | {("s25", o): v for o, v in S25.items()}
pid = sorted(PO)
pool = {}
for dim, f, ordr, tg in (("party", SUB.get, ORD_PARTY, L.MAIN), ("submitter kind", kind, ORD_KIND, None), ("instrument", instr, ORD_TYPE, None)):
    pool[dim] = dimension([(f(o), PO[(s, o)]["top1"]) for s, o in pid], ordr, tg, strata=[s for s, _ in pid])
pool["n"] = len(pid); pool["note"] = "S9 prod + S25, top-1; permutation within set (strata), gap bootstraps within cell"
R["pooled"] = pool
print("pooled done", flush=True)
s16a = {"n": len(S16)}
s16a["party"] = {"top1": dimension([(SUB[o], S16[o]["top1"]) for o in sorted(S16)], ORD_PARTY, L.MAIN)}
s16a["submitter kind"] = {"top1": dimension([(kind(o), S16[o]["top1"]) for o in sorted(S16)], ORD_KIND)}
s16a["instrument"] = {"top1": dimension([(instr(o), S16[o]["top1"]) for o in sorted(S16)], ORD_TYPE)}
R["s16_d4_secondary"] = s16a
(HERE / "results.json").write_text(json.dumps(R, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
for st in ("s9_prod", "s25"):
    pt = R[st]["party"]["top1"]
    print(st, {c["cell"]: (c["value"], c["n"]) for c in pt["cells"]}, pt["test"]["p_perm"], pt.get("gap"))
print("pooled", R["pooled"]["party"]["test"]["p_perm"], R["pooled"]["party"].get("gap"))
print("s16", R["s16_d4_secondary"]["party"]["top1"]["test"]["p_perm"], R["s16_d4_secondary"]["party"]["top1"].get("gap"))
