"""Hierarchical metrics for the shipped federal design D4 (S16), computed after S16 from its rows. No model calls, no network.
Not pre-registered: a computation on existing measurements (S16 raw rows, S9 raw rows, S9 gold).

Designs, all on the same S9 held-out items (gold = APS editors' chapter; subtopic gold = the process page's main subtopic
when it is one of the 190 names, `sub_gold`):
  D4  shipped: S16 rows (prior = mean of S9 d3m and d0b; one subtopic call over the top chapters); chapter read back from the
      best subtopic, score = p(subtopic) × prior(chapter) — exactly eval/s16/analyze.py `readback`.
  D1  S9 d1 rows, prior = mean of d0a and d0b, same read-back (S9 pipeline, recomputed as in eval/s16/analyze.py).
  D0  chapter = top of the geometric mean of d0a and d0b; subtopic = the best joint-L2 subtopic (S9 d1 row) within that
      chapter. If D0's chapter is not in the d1 shortlist (or is "none"), D0 predicts the chapter only (no subtopic) — a
      consistent path in the tree. S9's own derived baseline ranks the other chapters' subtopics next instead; its top-1 /
      top-3 are reported alongside as `D0_s9_definition` for reference.
  keyword  frozen S9 keyword baseline (APS subtopic-name words, chapter level only; ties → gold-majority order, as S9).
Metrics
  (1) subtopic top-1 / top-3 end to end (items with sub_gold; a hit needs chapter and subtopic right), Wilson 95%.
  (2) subtopic top-1 given the design's top-1 chapter is right (conditional), Wilson 95%.
  (3) hierarchical precision / recall / F1 (Kiritchenko et al. 2005/2006: predicted and gold label sets augmented with their
      ancestors; tree = chapter → subtopic; the root is not counted; micro-averaged: hP = Σ|P∩G| / Σ|P|, hR = Σ|P∩G| / Σ|G|,
      hF = 2·hP·hR / (hP + hR)). Primary set: the sub_gold items (both levels defined). Secondary: all items, gold depth 1
      where the main subtopic is not among the 190. Paired-free percentile bootstrap, 2,000 resamples of items.
  (4) per-chapter F1 of the top-1 chapter (one vs rest; predictions of chapters absent from the gold, or "none", count as
      misses), macro over the 22 chapters present in the gold (all items); percentile bootstrap 2,000 stratified by gold
      chapter (so every chapter, including the one with a single gold item, is present in every resample).
Interval bounds are stored exactly and rounded outward at 3 decimals (`ci95`); points stored unrounded (quote truncated).
-> eval/s16/hierarchical.json"""
import collections, json, math, random, sys
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt import prompts as P  # noqa: E402
from querschnitt.scheme import APS  # noqa: E402

S9 = HERE.parent / "spikes/s9-aps"  # vendored S9 (eval/spikes/)
B, SEED = 2000, 20261016
load = lambda p: {json.loads(l)["oid"]: json.loads(l) for l in open(p)}
items = {it["oid"]: it for it in json.load(open(S9 / "data/items.json"))}
raw = {ph: load(S9 / f"raw/{ph}.jsonl") for ph in ("d0a", "d0b", "d1", "d3m")}
s16 = load(HERE / "raw.jsonl")
order = lambda p: sorted(range(len(p)), key=lambda i: -p[i])
ids = sorted(o for o in items if o in s16 and all(o in raw[k] for k in ("d0a", "d0b", "d1", "d3m")))
sub_ids = [o for o in ids if items[o]["sub_gold"]]
gold_ch = {o: items[o]["chapter"] for o in ids}
gold_sub = {o: (items[o]["chapter"], items[o]["subtopic_name"]) for o in sub_ids}
for o in sub_ids:
    assert gold_sub[o][1] in APS.subs_de[gold_sub[o][0]], (o, gold_sub[o])


def geo2(a, b):
    g = [math.exp((math.log(max(x, 1e-12)) + math.log(max(y, 1e-12))) / 2) for x, y in zip(a, b)]
    s = sum(g); return [v / s for v in g]


def readback(prior, opts, psub):
    """-> chapter, chapter ranking, subtopic ranking [(chapter, name)] (as eval/s16/analyze.py readback)."""
    sc = {(c, s): psub[k] * prior[c] for k, (c, s) in enumerate(opts)}
    best = max(sc, key=sc.get)
    chbest = {}
    for (c, s), v in sc.items(): chbest[c] = max(chbest.get(c, 0), v)
    rk = sorted(chbest, key=lambda c: -chbest[c]) + [c for c in order(prior) if c not in chbest]
    return best[0], rk, sorted(sc, key=lambda k: -sc[k])


pred = {}   # design -> oid -> dict(ch, subs (ranked list or []))
for o in ids:
    a, b, m = raw["d0a"][o]["p"], raw["d0b"][o]["p"], raw["d3m"][o]["p"]
    r1 = raw["d1"][o]; opts1 = [tuple(x) for x in r1["opts"]]
    ch, _, subs = readback([(x + y) / 2 for x, y in zip(a, b)], opts1, r1["p"])
    pred.setdefault("D1", {})[o] = dict(ch=ch, subs=subs)
    x = s16[o]["d4"]
    opts4 = [(c, APS.subs_de[c][j]) for c, j in P.subtopic_options(x["chs"])]
    ch, _, subs = readback(x["prior"], opts4, x["p"])
    pred.setdefault("D4", {})[o] = dict(ch=ch, subs=subs)
    c0 = order(geo2(a, b))[0]
    sc = {opt: r1["p"][k] for k, opt in enumerate(opts1)}
    within = sorted((k for k in sc if k[0] == c0), key=lambda k: -sc[k])
    pred.setdefault("D0", {})[o] = dict(ch=c0, subs=within)
    pred.setdefault("D0_s9_definition", {})[o] = dict(ch=c0, subs=sorted(sc, key=lambda k: (k[0] != c0, -sc[k])))

# keyword baseline (S9 analyze.py, verbatim rule)
KW = json.load(open(S9 / "data/keywords_frozen.json"))
kw = {int(c): v["keywords"] for c, v in KW["chapters"].items()}
gc = collections.Counter(gold_ch[o] for o in ids)
majorder = [c for c, _ in gc.most_common()] + [c for c in range(24) if c not in gc]
for o in ids:
    it = items[o]["de"]; txt = " ".join((it["title"], it["title_long"], it["text"])).lower()
    s = {c: sum(w in txt for w in kw[c]) for c in range(24)}
    mx = max(s.values())
    pred.setdefault("keyword", {})[o] = dict(ch=min((c for c in range(24) if s[c] == mx), key=majorder.index), subs=[])

# consistency with stored results (same rows, same rules)
S16R = json.load(open(HERE / "results.json"))
for d in ("D1", "D4"):
    k1 = sum(pred[d][o]["ch"] == gold_ch[o] for o in ids)
    assert k1 == S16R["designs"][d]["k1"], (d, k1)
S9R = json.load(open(S9 / "results.json"))
assert sum(pred["keyword"][o]["ch"] == gold_ch[o] for o in ids) / len(ids) == S9R["baselines"]["keyword_top1"] or \
    round(sum(pred["keyword"][o]["ch"] == gold_ch[o] for o in ids) / len(ids), 4) == S9R["baselines"]["keyword_top1"]


# ---------------------------------------------------------------- helpers
def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(c - h, 0.0), min(c + h, 1.0)]


def out(ci):
    return [float(Decimal(repr(ci[0])).quantize(Decimal("0.001"), ROUND_FLOOR)),
            float(Decimal(repr(ci[1])).quantize(Decimal("0.001"), ROUND_CEILING))]


def prop(k, n):
    w = wilson(k, n)
    return dict(value=k / n, k=k, n=n, ci95=out(w), ci95_exact=w, ci_method="Wilson 95%, bounds rounded outward at 3 decimals")


def boot(fn, n, seed, strata=None):
    """fn(idx) -> dict of statistics; -> {stat: (ci95 outward, exact percentile bounds)}; None values are skipped.
    strata: lists of item indices resampled separately (stratified bootstrap), else plain resampling of n items."""
    rng = random.Random(seed); v = collections.defaultdict(list)
    for _ in range(B):
        idx = [g[rng.randrange(len(g))] for g in strata for _ in g] if strata else [rng.randrange(n) for _ in range(n)]
        for k, x in fn(idx).items():
            if x is not None: v[k].append(x)
    res = {}
    for k, xs in v.items():
        xs.sort(); lo, hi = xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs)) - 1]
        res[k] = (out([lo, hi]), [lo, hi])
    return res


# ---------------------------------------------------------------- (1) + (2) subtopic
R = dict(n_items=len(ids), n_sub_gold=len(sub_ids), build=S16R["build"],
         note="computed after S16 from its rows (not pre-registered); no model calls",
         sources=["bern/querschnitt/eval/s16/raw.jsonl", "bern/ideation2/spikes/s9-aps/raw/{d0a,d0b,d1,d3m}.jsonl",
                  "bern/ideation2/spikes/s9-aps/data/items.json", "bern/ideation2/spikes/s9-aps/data/keywords_frozen.json"],
         designs={})
for d in ("D4", "D1", "D0", "D0_s9_definition"):
    t1 = sum(bool(pred[d][o]["subs"]) and pred[d][o]["subs"][0] == gold_sub[o] for o in sub_ids)
    t3 = sum(gold_sub[o] in pred[d][o]["subs"][:3] for o in sub_ids)
    right = [o for o in sub_ids if pred[d][o]["ch"] == gold_ch[o]]
    tc = sum(bool(pred[d][o]["subs"]) and pred[d][o]["subs"][0] == gold_sub[o] for o in right)
    R["designs"].setdefault(d, {})["subtopic"] = dict(top1=prop(t1, len(sub_ids)), top3=prop(t3, len(sub_ids)),
                                                       top1_given_chapter_right=prop(tc, len(right)),
                                                       chapter_top1_on_sub_gold=prop(len(right), len(sub_ids)))
R["designs"]["keyword"] = {"subtopic": None}
for k in ("top1", "top3"):
    s9v = S9R["subtopic"]["D0 chapter top-1 -> best joint-L2 subtopic within it [derived]"][k]
    assert round(R["designs"]["D0_s9_definition"]["subtopic"][k]["value"], 4) == s9v, (k, s9v)


# ---------------------------------------------------------------- (3) hierarchical P/R/F1
def pset(d, o):
    p = pred[d][o]; s = set()
    if p["ch"] < 24: s.add(("ch", p["ch"]))
    if p["subs"] and d != "D0_s9_definition":
        c, n_ = p["subs"][0]; s |= {("ch", c), ("sub", c, n_)}
    return s


def gset(o, depth1_ok):
    s = {("ch", gold_ch[o])}
    if o in gold_sub: s.add(("sub",) + gold_sub[o])
    elif not depth1_ok: raise ValueError
    return s


def hprf(cnt):
    inter, np_, ng = (sum(x) for x in zip(*cnt))
    hp = inter / np_ if np_ else 0.0; hr = inter / ng if ng else 0.0
    return hp, hr, (2 * hp * hr / (hp + hr) if hp + hr else 0.0)


for d in ("D4", "D1", "D0", "keyword"):
    R["designs"][d]["hierarchical"] = {}
    for setname, sel in (("sub_gold_items", sub_ids), ("all_items", ids)):
        cnt = []
        for o in sel:
            P_, G_ = pset(d, o), gset(o, True)
            cnt.append((len(P_ & G_), len(P_), len(G_)))
        hp, hr, hf = hprf(cnt)
        blk = dict(n=len(sel), sums=dict(zip(("intersection", "predicted", "gold"), (sum(x) for x in zip(*cnt)))))
        bs = boot(lambda idx: dict(zip(("hP", "hR", "hF"), hprf([cnt[j] for j in idx]))), len(sel), SEED)
        for nm, v in (("hP", hp), ("hR", hr), ("hF", hf)):
            ci, ex = bs[nm]
            blk[nm] = dict(value=v, ci95=ci, ci95_exact=ex, ci_method="percentile bootstrap 2,000 (items), bounds rounded outward at 3 decimals")
        R["designs"][d]["hierarchical"][setname] = blk


# ---------------------------------------------------------------- (4) per-chapter F1, macro
CH = sorted(gc)
STRATA = [[j for j, o in enumerate(ids) if gold_ch[o] == c] for c in CH]   # resample within each gold chapter


def per_ch(idx, d):
    tp, fp, fn = collections.Counter(), collections.Counter(), collections.Counter()
    for j in idx:
        o = ids[j]; g, p = gold_ch[o], pred[d][o]["ch"]
        if g == p: tp[g] += 1
        else: fp[p] += 1; fn[g] += 1
    return {c: (2 * tp[c] / (2 * tp[c] + fp[c] + fn[c]) if (2 * tp[c] + fp[c] + fn[c]) else None) for c in CH}


def macro(idx, d, pc=None):
    v = [x for x in (pc or per_ch(idx, d)).values() if x is not None]
    return sum(v) / len(v)


for d in ("D4", "D1", "D0", "keyword"):
    full = per_ch(range(len(ids)), d)
    bs = boot(lambda idx: (lambda pc: dict(pc, macro=macro(idx, d, pc)))(per_ch(idx, d)), len(ids), SEED + 10, STRATA)
    ci, ex = bs["macro"]
    rows = {}
    for c in CH:
        cc_, ce = bs[c]
        rows[str(c)] = dict(chapter=APS.names["de"][c], n_gold=gc[c], F1=full[c], ci95=cc_, ci95_exact=ce)
    R["designs"][d]["per_chapter"] = dict(n=len(ids), chapters=len(CH), macro_F1=dict(value=macro(range(len(ids)), d), ci95=ci, ci95_exact=ex,
                                          ci_method="percentile bootstrap 2,000, stratified by gold chapter (every chapter keeps its "
                                          "gold count in every resample), bounds rounded outward at 3 decimals"),
                                          by_chapter=rows)
R["designs"]["D0_s9_definition"]["note"] = ("S9's derived D0 subtopic baseline (other chapters' subtopics ranked after D0's own); "
                                            "kept to show the reproduction of S9 results.json; not used for hierarchical metrics")
(HERE / "hierarchical.json").write_text(json.dumps(R, ensure_ascii=False, indent=1))

t = lambda v: f"{math.floor(v * 1000) / 1000:.3f}"
for d in ("D4", "D1", "D0", "keyword"):
    x = R["designs"][d]; s = x["subtopic"]; h = x["hierarchical"]["sub_gold_items"]; m = x["per_chapter"]["macro_F1"]
    line = f"{d:8s}"
    if s: line += (f" sub top1 {t(s['top1']['value'])} {s['top1']['ci95']} top3 {t(s['top3']['value'])} {s['top3']['ci95']}"
                   f" | given ch right {t(s['top1_given_chapter_right']['value'])} {s['top1_given_chapter_right']['ci95']} (n {s['top1_given_chapter_right']['n']})")
    line += f" | hP {t(h['hP']['value'])} hR {t(h['hR']['value'])} hF {t(h['hF']['value'])} {h['hF']['ci95']} | macro-F1 {t(m['value'])} {m['ci95']}"
    print(line)
