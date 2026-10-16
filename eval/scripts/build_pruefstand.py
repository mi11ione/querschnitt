"""Build eval/pruefstand.json from the spike result files (read-only; no model calls, no network).
Every value is read from its source file by key (JSON) or located by an exact needle (Markdown line), so the record of where a
number sits is produced by the same code that copies it. Paths are relative to the repository root (the S1–S15 spikes are
vendored under eval/spikes/). Run: python3 -I eval/scripts/build_pruefstand.py   (from anywhere)"""
import json, math, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools"))
import numfmt as F  # noqa: E402
import claims_check as cc  # noqa: E402

EVAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(EVAL)  # repository root
BUILD = "vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840"
MODEL = "swiss-ai/apertus-v1.5-8b"
I2 = "eval/spikes"  # S8–S15 (second round)
I1 = "eval/spikes"  # S1–S7 (first round)
_cache = {}


def J(rel):
    if rel not in _cache:
        _cache[rel] = json.load(open(os.path.join(ROOT, rel), encoding="utf-8"))
    return _cache[rel]


def g(rel, *keys):
    """value at keys in a JSON file + its location string."""
    v = J(rel)
    for k in keys:
        v = v[k]
    return v


def loc(rel, *keys):
    return {"file": rel, "key": " > ".join(str(k) for k in keys)}


def md(rel, needle):
    """{file, line} of the first line that contains needle (asserts it exists)."""
    for i, line in enumerate(open(os.path.join(ROOT, rel), encoding="utf-8"), 1):
        if needle in line:
            return {"file": rel, "line": i, "text": needle}
    raise SystemExit(f"needle not found in {rel}: {needle!r}")


def prop(rel, *keys, value="p", ci="ci", k="k", n="n"):
    """proportion block from a dict with p/ci/k/n-like fields."""
    d = g(rel, *keys)
    out = {"value": d[value], "ci95": d[ci]}
    if k in d: out["k"] = d[k]
    if n in d: out["n"] = d[n]
    out["at"] = loc(rel, *keys)
    return out


def lst(rel, *keys):
    """[k, n, p, lo, hi] list (S11 anchor.json style)."""
    k, n, p, lo, hi = g(rel, *keys)
    return {"value": p, "ci95": [lo, hi], "k": k, "n": n, "at": loc(rel, *keys)}


def cells(rel, *keys, weighted=False):
    d = g(rel, *keys)
    rows = []
    for c in d["cells"]:
        r = {"cell": c["cell"], "n": c["n"], "k": c["k"]}
        if weighted and "p_w" in c:
            r.update(value=c["p_w"], ci95=c["ci_w"], unweighted=c["p"])
        else:
            r.update(value=c["p"], ci95=c["ci"])
        if c.get("small"): r["small"] = True
        rows.append(r)
    t = d.get("test") or {}
    gap = d.get("gap") or {}
    return {"cells": rows, "test": {"p_perm": t.get("p_perm"), "p_chi2": t.get("p_chi2"), "df": t.get("df")},
            "largest_gap": {"hi": gap.get("hi"), "lo": gap.get("lo"), "diff": gap.get("diff"), "ci95": gap.get("ci"),
                            "basis": gap.get("basis")} if gap else None,
            "at": loc(rel, *keys)}


def mdtable(rel, heading):
    """rows of the first Markdown table after the line containing heading -> (list of dicts, location)."""
    lines = open(os.path.join(ROOT, rel), encoding="utf-8").read().splitlines()
    start = next(i for i, l in enumerate(lines) if heading in l)
    i = start + 1
    while not lines[i].startswith("|"): i += 1
    head = [c.strip() for c in lines[i].strip("|").split("|")]
    rows = []
    for l in lines[i + 2:]:
        if not l.startswith("|"): break
        cells = [c.strip() for c in l.strip("|").split("|")]
        r = {}
        for h, c in zip(head, cells):
            try: r[h] = int(c) if re.fullmatch(r"-?\d+", c) else float(c) if re.fullmatch(r"-?\d*\.\d+", c) else c
            except ValueError: r[h] = c
        rows.append(r)
    return rows, {"file": rel, "line": start + 1, "text": heading}


S9R = f"{I2}/s9-aps/results.json"
S9M = f"{I2}/s9-aps/results.md"
S9C = f"{I2}/s9c-calibration/results.json"
S9P = f"{I2}/s9c-calibration/perlevel.json"
S8M = f"{I2}/s8-dvs/results.md"
S8CH = f"{I2}/s8-dvs/score_ch.json"
S8S = f"{I2}/s8-dvs/score.json"
S8OP = f"{I2}/s8-dvs/operating_points_ch.json"
S8L = f"{I2}/s8-dvs/loop.json"
S10S = f"{I2}/s10-bilingual/score.json"
S10M = f"{I2}/s10-bilingual/results.md"
S10V = f"{I2}/s10-bilingual/secondary.txt"
S11 = f"{I2}/s11-anchor/anchor.json"
S12 = f"{I2}/s12-evidence/results.json"
S13M = f"{I2}/s13-timing/results.md"
S8B = f"{I2}/s13-timing/s8b.json"
S14 = f"{I2}/s14-neutrality/results.json"
S14M = f"{I2}/s14-neutrality/results.md"
S15 = f"{I2}/s15-judgecheck/results.json"
S15M = f"{I2}/s15-judgecheck/RESULTS.md"
S3M = f"{I1}/s3-accuracy/results.md"
S5M = f"{I1}/s5-aps/results.md"
S6S = f"{I1}/s6-cantonal/score.json"
S6M = f"{I1}/s6-cantonal/results.md"
S7S = f"{I1}/s7-crossfamily/score.json"
PRE = "eval/spikes/PREREG.md"
ADD = "eval/spikes/PREREG-ADDENDA.md"
QE = "eval"
PB = f"{QE}/PREREG-BUILD.md"
S16R, S16M = f"{QE}/s16/results.json", f"{QE}/s16/results.md"
S17R, S18R, S20R, S21R, S8F = (f"{QE}/s17/results.json", f"{QE}/s18/results.json", f"{QE}/s20/results.json",
                               f"{QE}/s21/results.json", f"{QE}/s8full/results.json")


def pre(rel, needle):
    m = md(rel, needle)
    return {"file": rel, "anchor": needle, "line": m["line"]}


def s9chapter(d):
    c = g(S9R, "chapter", d)
    out = {"metric": "chapter top-1 vs APS editors", "value": c["top1"], "ci95": c["top1_ci"], "k": c["top1_k"], "n": c["n"],
           "display": f"{c['top1']:.3f} [{c['top1_ci'][0]:.3f}, {c['top1_ci'][1]:.3f}]",
           "at": loc(S9R, "chapter", d, "top1")}
    top3 = {"metric": "chapter top-3", "value": c["top3"], "ci95": c["top3_ci"], "k": c["top3_k"], "n": c["n"],
            "at": loc(S9R, "chapter", d, "top3")}
    return out, top3


def s9diff(d):
    c = g(S9R, "chapter", d)
    return {"metric": f"paired Δ top-1 {d} − D0", "value": c["diff_top1"], "ci95": c["diff_top1_ci"],
            "flips_gain_loss": [c["flips"]["gain"], c["flips"]["loss"]], "method": "paired bootstrap 2,000, percentile",
            "at": loc(S9R, "chapter", d, "diff_top1")}


def s9baselines():
    b = g(S9R, "baselines")
    d0, _ = s9chapter("D0")
    d0 = dict(d0, name="D0 plain list prompting (v14: chapter step, two code orders)")
    return [d0,
            {"name": "keyword (APS subtopic-name words, frozen before scoring)", "value": b["keyword_top1"], "ci95": b["keyword_ci"],
             "n": b["n"], "at": loc(S9R, "baselines", "keyword_top1")},
            {"name": f"majority chapter ({b['majority_chapter']})", "value": b["majority_top1"], "ci95": b["majority_ci"], "n": b["n"],
             "at": loc(S9R, "baselines", "majority_top1")}]


def s9strata(d):
    out = []
    for name, v in g(S9R, "strata", d).items():
        out.append({"cell": name, "n": v["n"], "k": v["top1_k"], "value": v["top1"], "ci95": v["top1_ci"]})
    return {"cells": out, "at": loc(S9R, "strata", d)}


def s9lanes(d):
    out = []
    for name, v in g(S9R, "lanes", d).items():
        out.append({"cell": name, "n": v["n"], "share": v["share"], "share_ci95": v["share_ci"], "precision": v["precision"],
                    "k": v["k"], "ci95": v["ci"]})
    return {"cells": out, "at": loc(S9R, "lanes", d)}


SRC_S9 = [S9R, S9M, f"{I2}/s9-aps/scripts/analyze.py", f"{I2}/s9-aps/raw/"]
date_s9 = g(S9R, "generated_utc")

tests = []

# ---------------------------------------------------------------- human labels
d3, d3t3 = s9chapter("D3")
tests.append(dict(
    id="aps_chapter_examples", gold="human", subject="Apertus",
    title_de="APS-Kapitel gegen APS-Redaktion, mit fünf APS-Beispielen (D3)",
    title_fr="Chapitre APS contre la rédaction APS, avec cinq exemples APS (D3)",
    n=d3["n"], design="Bundesgeschäfte mit APS-Kapitel aus Wayback-Prozessseiten, nicht vorher benutzt; DE-Titel + eingereichter Text (Curia); "
    "Kapitelschritt mit den 5 BM25-nächsten APS-gelabelten Geschäften als Beispiele, mit der permutierten Reihenfolge geometrisch gemittelt",
    result=d3, results_more=[d3t3, s9diff("D3")], baselines=s9baselines(),
    split="held-out, pre-registered (nothing tuned on these items)", prereg=pre(PRE, "## S9 — APS extended held-out"),
    hypothesis="H9.3 D3 > D0: wins (paired interval excludes 0)",
    sources=SRC_S9, build=BUILD, model=MODEL, date=date_s9, shipped="where APS-labelled examples exist",
    breakdowns={"period_and_join": s9strata("D3"), "lanes_orders_agree_disagree": s9lanes("D3"),
                "per_chapter": {"macro_F1": g(S9P, "D3", "macro_F1"), "chapters": g(S9P, "D3", "chapters"),
                                "worst": g(S9P, "D3", "worst"), "best": g(S9P, "D3", "best"), "at": loc(S9P, "D3")}}))

d1, d1t3 = s9chapter("D1")
tests.append(dict(
    id="aps_chapter_readback", gold="human", subject="Apertus",
    title_de="APS-Kapitel gegen APS-Redaktion, aus dem Unterthema zurückgelesen (D1, ausgeliefert)",
    title_fr="Chapitre APS contre la rédaction APS, relu depuis le sous-thème (D1, livré)",
    n=d1["n"], design="wie D3, ohne Beispiele: Kapitelschritt (2 Code-Reihenfolgen) → ein Aufruf über die Unterthemen der Top-2/3-Kapitel → "
    "Kapitel des gewählten Unterthemas × Kapitel-Prior (β = 1)",
    result=d1, results_more=[d1t3, s9diff("D1")], baselines=s9baselines(),
    split="held-out, pre-registered", prereg=pre(PRE, "## S9 — APS extended held-out"), hypothesis="H9.1 D1 > D0: wins",
    sources=SRC_S9, build=BUILD, model=MODEL, date=date_s9, shipped="default chapter",
    breakdowns={"per_chapter": {"macro_F1": g(S9P, "D1", "macro_F1"), "chapters": g(S9P, "D1", "chapters"),
                                "worst": g(S9P, "D1", "worst"), "best": g(S9P, "D1", "best"), "at": loc(S9P, "D1")},
                "see_also": "neutrality_s9 (party, submitter kind, instrument on D1); the shipped design: neutrality_shipped_s32"}))

d2, d2t3 = s9chapter("D2")
tests.append(dict(
    id="aps_chapter_pooling", gold="human", subject="Apertus",
    title_de="APS-Kapitel: deutsche und französische Fassung gemittelt (D2, nicht übernommen)",
    title_fr="Chapitre APS : versions allemande et française moyennées (D2, non retenu)",
    n=d2["n"], design="Mittel der Wahrscheinlichkeiten aus D0 (2 deutsche Reihenfolgen) und einem Aufruf auf dem französischen Text",
    result=d2, results_more=[d2t3, s9diff("D2")], baselines=s9baselines()[:1],
    split="held-out, pre-registered", prereg=pre(PRE, "## S9 — APS extended held-out"),
    hypothesis="H9.2 D2 > D0: not supported (Δ −0.021, interval below 0); the second language is used for the lane instead",
    sources=SRC_S9, build=BUILD, model=MODEL, date=date_s9, shipped="no"))

sub = g(S9R, "subtopic", "D1 (joint L2 x D0-arith prior, beta=1) [pre-registered pipeline]")
tests.append(dict(
    id="aps_subtopic", gold="human", subject="Apertus",
    title_de="APS-Unterthema gegen APS-Redaktion, Ende zu Ende (Top-1 / Top-3)",
    title_fr="Sous-thème APS contre la rédaction APS, de bout en bout (top-1 / top-3)",
    n=sub["n"], design="D1-Pipeline; Gold = Hauptunterthema der Prozessseite, sofern unter den 190 deutschen Namen",
    result={"metric": "subtopic top-1", "value": sub["top1"], "ci95": sub["top1_ci"], "k": sub["top1_k"], "n": sub["n"],
            "at": loc(S9R, "subtopic", "D1 (joint L2 x D0-arith prior, beta=1) [pre-registered pipeline]", "top1")},
    results_more=[{"metric": "subtopic top-3", "value": sub["top3"], "ci95": sub["top3_ci"], "k": sub["top3_k"], "n": sub["n"],
                   "at": loc(S9R, "subtopic", "D1 (joint L2 x D0-arith prior, beta=1) [pre-registered pipeline]", "top3")},
                  dict(prop(S9R, "subtopic_gold_chapter_in_shortlist", value="share"), metric="gold chapter inside the D1 shortlist")],
    baselines=[{"name": "D0 chapter top-1 → best subtopic within it [derived]",
                "value": g(S9R, "subtopic", "D0 chapter top-1 -> best joint-L2 subtopic within it [derived]", "top1"),
                "ci95": g(S9R, "subtopic", "D0 chapter top-1 -> best joint-L2 subtopic within it [derived]", "top1_ci"),
                "at": loc(S9R, "subtopic", "D0 chapter top-1 -> best joint-L2 subtopic within it [derived]", "top1")}],
    split="held-out, pre-registered", prereg=pre(PRE, "## S9 — APS extended held-out"),
    sources=SRC_S9, build=BUILD, model=MODEL, date=date_s9, shipped="ranked suggestions only"))

cal = {d: g(S9C, d) for d in ("D0", "D1", "D3")}
tests.append(dict(
    id="aps_calibration", gold="human", subject="Apertus",
    title_de="Konfidenz: erwarteter Kalibrierfehler vor / nach isotoner Rekalibrierung",
    title_fr="Confiance : erreur de calibration attendue avant / après recalibration isotone",
    n=cal["D1"]["n"], design="2-fach kreuzangepasste isotone Regression auf den 1'357 S9-Geschäften; ECE über 10 gleich breite Klassen",
    result={"metric": "ECE D1 raw → isotonic (cross-fit)", "value": cal["D1"]["ece_isotonic_crossfit"], "raw": cal["D1"]["ece_raw"],
            "ci95": None, "at": loc(S9C, "D1")},
    results_more=[{"metric": f"ECE {d} raw → isotonic (cross-fit)", "raw": cal[d]["ece_raw"], "value": cal[d]["ece_isotonic_crossfit"],
                   "mean_p_raw": cal[d]["mean_p_raw"], "mean_p_cal": cal[d]["mean_p_cal"], "acc": cal[d]["acc"], "at": loc(S9C, d)}
                  for d in ("D0", "D1", "D3")],
    baselines=[{"name": "raw p (no recalibration)", "D0": cal["D0"]["ece_raw"], "D1": cal["D1"]["ece_raw"], "D3": cal["D3"]["ece_raw"]}],
    split="cross-fitted (2 folds, seed 3), no new calls", prereg=pre(ADD, "S9c calibration (no calls)"),
    sources=[S9C, f"{I2}/s9c-calibration/calib.py"], build=BUILD, model=MODEL, date="2026-10-13",
    note="no interval computed for ECE (TO MEASURE: bootstrap)"))

tests.append(dict(
    id="dvs_human30", gold="human", subject="Apertus",
    title_de="«Digitalisierung»: die 30 von Hand kuratierten DVS-Geschäfte (Recall)",
    title_fr="« Numérique » : les 30 objets choisis à la main par DVS (rappel)",
    n=30, design="Ja/Nein-Frage mit Themenbeschreibung, Titel + Langtitel in der Sprache des Geschäfts; Flag bei p ≥ 0.5 (S3), nicht neu angepasst",
    result={"metric": "recall on the 30 public DVS items", "value": 27 / 30, "k": 27, "n": 30, "ci95": [0.744, 0.965],
            "display": "27/30 [0.744, 0.965]", "at": md(S8M, "DVS recall (P8.2, all 30): Apertus 27/30 [0.744, 0.965]")},
    results_more=[{"metric": "recall, begun in the 2026 window", "k": 23, "n": 24, "value": 23 / 24, "ci95": [0.798, 0.993],
                   "at": md(S8M, "Apertus 23/24 [0.798, 0.993]")},
                  {"metric": "AI judge on the same 30 items (both Claude runs Y), for reference", "k": g(S15, "both_Y"), "n": g(S15, "n_dvs"),
                   "value": 0.9, "ci95": [0.74, 0.97], "at": loc(S15, "both_Y")}],
    baselines=[{"name": "keyword list (29 de/fr/it stems)", "k": 21, "n": 30, "value": 0.7, "ci95": [0.521, 0.833],
                "at": md(S8M, "keyword 21/30 [0.521, 0.833]")},
               {"name": "keyword list, begun in the window", "k": 16, "n": 24, "ci95": [0.467, 0.820], "at": md(S8M, "keyword 16/24 [0.467, 0.820]")}],
    split="pre-registered re-run (P8.2); the yes/no prompt and the 0.5 cut-off were set on these 30 items in S3 E6",
    prereg=pre(PRE, "## S8 — \"Digitalisierung\" over every affair of 2026"),
    sources=[S8M, f"{I1}/s3-accuracy/results.md", f"{I1}/s2-oracles/results.md"], build=BUILD, model=MODEL, date="2026-10-13"))

tests.append(dict(
    id="curia_sachbereiche", gold="human", subject="Apertus",
    title_de="Sachbereiche des Bundesparlaments gegen die Curia-Tags, alle Tags pro Geschäft",
    title_fr="Thèmes du Parlement fédéral contre les tags Curia, tous les tags par objet",
    n=200, design="Testteil (n = 200) des sauberen Pools (eingereicht ab 6.11.2024, nach dem BFH-Modell); 5 abgerufene getaggte Beispiele "
    "(Pool 52'408 Geschäfte vor dem 6.11.2024) + Ja/Nein-Prüfung der Top 6, fusioniert (V3)",
    result={"metric": "micro-F1", "value": 0.654, "ci95": [0.623, 0.686], "n": 200,
            "at": md(S5M, "**V3 fused: 0.9·p(yes) + 0.1·p_E3 ≥ 0.9, 2 orders** | **0.654 [0.623, 0.686]**")},
    results_more=[{"metric": "macro-F1", "value": 0.570, "ci95": [0.520, 0.622], "at": md(S5M, "**0.570 [0.520, 0.622]**")},
                  {"metric": "top-1 is a gold tag, no examples (E2, 2 orders)", "value": 0.865, "ci95": [0.811, 0.906],
                   "at": md(S3M, "| E2 desc, average of 2 orders (arith.) |")},
                  {"metric": "paired Δ micro-F1 V3 − BFH", "ci95": [-0.079, 0.010], "at": md(S5M, "vs BFH micro **−0.079 to +0.010**")}],
    baselines=[{"name": "BFH Omikuji (trained on 15,007 tagged affairs), thr 0.25", "value": 0.687, "ci95": [0.652, 0.722],
                "top1": 0.855, "top1_ci95": [0.800, 0.897], "at": md(S3M, "| **BFH Omikuji, thr 0.25 (tuned on BFH's dev)** |"),
                "training_size_at": md("eval/research/R1-parts/prior-art.md", "15,007 German training docs")}],
    split="test n = 200; rules, τ and λ tuned on 100 dev items (tuning split)", prereg=None,
    sources=[S3M, S5M, f"{I1}/s2-oracles/results.md"], build=BUILD, model=MODEL, date="2026-10-13"))

tests.append(dict(
    id="bern_directorates", gold="human", subject="Apertus",
    title_de="Bern: federführende Direktion (Schema-Tausch, 8 Direktionen) gegen das Feld des Grossen Rats, nur Titel",
    title_fr="Berne : direction responsable (8 directions) contre le champ du Grand Conseil, titres seuls",
    n=200, design="Zufallsstichprobe aus 4'530 Geschäften (ab 2015); Titel DE und FR getrennt, Prompt in der jeweiligen Sprache; "
    "Direktionsbeschreibungen vom Agenten geschrieben; Stichwörter vor jedem Resultat eingefroren",
    result={"metric": "accuracy DE title", "value": 0.615, "ci95": [0.546, 0.680], "n": 200, "at": md(S6M, "| **Apertus, DE title** |")},
    results_more=[{"metric": "accuracy FR title", "value": 0.645, "ci95": [0.577, 0.708], "at": md(S6M, "| **Apertus, FR title (FR prompt)** |")},
                  {"metric": "DE + FR pooled", "value": 0.645, "ci95": [0.577, 0.708], "at": md(S6M, "| Apertus, DE + FR pooled")},
                  {"metric": "DE − FR (paired)", "value": -0.030, "ci95": [-0.085, 0.025], "at": md(S6M, "DE/FR parity gap (DE − FR): −0.030")}],
    baselines=[{"name": "keyword stems DE / FR", "value": [0.520, 0.495], "ci95": [[0.451, 0.588], [0.426, 0.564]],
                "at": md(S6M, "| Keyword stems, DE / FR |")},
               {"name": "majority class (BVD)", "value": 0.175, "ci95": [0.129, 0.234], "at": md(S6M, "| Majority class (BVD) |")}],
    split="one run, nothing tuned on the 200", prereg=None, sources=[S6M], build=BUILD, model=MODEL, date="2026-10-13"))

tests.append(dict(
    id="judge_anchor_aps", gold="human", subject="AI judge (Claude, blind)",
    title_de="Der KI-Richter selbst gegen die APS-Redaktion (Kapitel)",
    title_fr="Le juge IA lui-même contre la rédaction APS (chapitres)",
    n=200, design="200 zufällige S9-Geschäfte (Seed 20261014), gleicher Input wie Apertus; zwei blinde Claude-Läufe, S6-Leitfaden",
    result=dict(lst(S11, "A"), metric="judge run A first chapter = editors' chapter"),
    results_more=[dict(lst(S11, "B"), metric="judge run B"), dict(lst(S11, "AB_agree"), metric="run A = run B"),
                  dict(lst(S11, "A_lenient"), metric="editors' chapter among the judge's first or second code")],
    baselines=[dict(lst(S11, "apertus_same_items", d, "apertus_vs_editors"), name=f"Apertus {d} on the same 200") for d in ("D0", "D1", "D3")],
    split="random S9 sample, pre-registered", prereg=pre(ADD, "S11 annotator anchor"),
    sources=[S11, f"{I2}/s11-anchor/RESULTS.md"], build="judge: Claude (blind agent runs); Apertus rows " + BUILD, date="2026-10-13"))

tests.append(dict(
    id="judge_dvs_human", gold="human", subject="AI judge (Claude, blind)",
    title_de="Der KI-Richter auf den 30 von Hand kuratierten DVS-Geschäften (Recall)",
    title_fr="Le juge IA sur les 30 objets DVS choisis à la main (rappel)",
    n=30, design="30 DVS-Geschäfte gemischt mit 70 zufälligen Geschäften 2026, gemischt; zwei blinde Claude-Läufe, S8-Leitfaden",
    result={"metric": "both runs Y on the DVS items", "k": g(S15, "both_Y"), "n": g(S15, "n_dvs"), "value": 0.9, "ci95": [0.74, 0.97],
            "at": loc(S15, "both_Y"), "ci_at": md(S15M, "0.90 [0.74, 0.97]")},
    results_more=[{"metric": "run A", "k": g(S15, "A_recall"), "n": 30, "at": loc(S15, "A_recall")},
                  {"metric": "run B", "k": g(S15, "B_recall"), "n": 30, "at": loc(S15, "B_recall")}],
    baselines=[{"name": "Apertus on the same 30 (S8)", "k": 27, "n": 30}, {"name": "keyword list (S8)", "k": 21, "n": 30}],
    split="pre-registered", prereg=pre(ADD, "S15 judge check on the binary task"), sources=[S15, S15M],
    build="judge: Claude (blind agent runs)", date="2026-10-13",
    note="judge precision on human negatives: not measured (no human negatives)"))

s9lang = g(S14, "S9", "language (paired, same affairs; single identity-order call)")
tests.append(dict(
    id="neutrality_s9", gold="human", subject="Apertus",
    title_de="Neutralität, Bund (S9, APS-Redaktion): Sprache, Partei, Einreichende, Instrument — D1, früheres Design (ausgeliefert: S32)",
    title_fr="Neutralité, Confédération (S9, rédaction APS) : langue, parti, auteur, instrument — D1, design antérieur (livré : S32)",
    n=1357, design="keine neuen Aufrufe; D1 aus S9-Rohdaten neu berechnet (955/1357 wie S9); Partei aus dem OPD-Export",
    result={"metric": "language: DE − FR, paired (identity-order chapter call on DE vs FR text)", "value": s9lang["diff_DE_minus_FR"],
            "ci95": s9lang["diff_ci"], "p_mcnemar": s9lang["p_mcnemar"],
            "at": loc(S14, "S9", "language (paired, same affairs; single identity-order call)", "diff_DE_minus_FR")},
    results_more=[{"metric": "DE", **s9lang["DE"]}, {"metric": "FR", **s9lang["FR"]}],
    baselines=[{"name": "keyword top-1 per cell (in breakdowns)"}],
    breakdowns={"party_D1_top1": cells(S14, "S9", "party", "D1_top1"),
                "party_keyword_top1": cells(S14, "S9", "party", "keyword_top1"),
                "submitter_kind_D1_top1": cells(S14, "S9", "submitter kind", "D1_top1"),
                "submitter_kind_keyword_top1": cells(S14, "S9", "submitter kind", "keyword_top1"),
                "instrument_D1_top1": cells(S14, "S9", "instrument", "D1_top1"),
                "instrument_keyword_top1": cells(S14, "S9", "instrument", "keyword_top1"),
                "all_11_submitter_categories_test": dict(g(S14, "S9", "party", "D1_top1_all_categories_test"),
                                                         at=loc(S14, "S9", "party", "D1_top1_all_categories_test"))},
    split="no new calls; reported whatever it showed", prereg=pre(ADD, "S14 neutrality (no calls)"),
    sources=[S14, S14M], build="no calls (S9 rows: " + BUILD + ")", date=g(S14, "generated_utc")))

tests.append(dict(
    id="free_generation", gold="none", gold_note="rule check: is the answer one of the listed labels",
    subject="Apertus", title_de="Freie Benennung ohne Liste", title_fr="Dénomination libre sans liste",
    n=40, design="40 Testgeschäfte (DE), Thema frei benennen lassen; dann mit der Curia-Liste",
    result={"metric": "answers outside both the Curia 28 and the APS label sets", "k": 36, "n": 40, "value": 0.9, "ci95": [0.77, 0.96],
            "at": md(S3M, "36/40 = 90 % [77, 96]")},
    results_more=[{"metric": "answers 'kein Thema'", "k": 0, "n": 40, "at": md(S3M, "**0/40 say \"kein Thema\"**")},
                  {"metric": "with the Curia list shown: off-list", "k": 0, "n": 40, "at": md(S3M, "With the Curia list shown, 0/40 fall outside it")}],
    baselines=[], split="test items", prereg=None, sources=[S3M], build=BUILD, model=MODEL, date="2026-10-13"))

# ---------------------------------------------------------------- AI-judge rows
ch = g(S8CH, "point"); ci = g(S8CH, "ci")
tests.append(dict(
    id="dvs_2026", gold="ai-judge", subject="Apertus",
    title_de="«Digitalisierung» in Schweizer Parlamenten 2026, gegen den KI-Richter",
    title_fr="« Numérique » dans les parlements suisses en 2026, contre le juge IA",
    n=14513, n_checked=453, design="Population: 14'513 Schweizer Geschäfte 1.1.–6.10.2026 (ohne LIE); bewertet: letzte Woche ganz (577) + 37,6 % "
    "Zufallsstichprobe (5'338 von 14'212); 464 geprüfte Geschäfte aus vier Schichten (beide / nur Apertus / nur Stichwörter / keines), "
    "auf die Population zurückgewichtet; Gold: zwei blinde Claude-Läufe + Stichentscheid, Qwen-SEA-LION als Gegenprobe",
    result={"metric": "precision vs the judge (Swiss)", "value": ch["aP"], "ci95": ci["aP"], "at": loc(S8CH, "point", "aP"),
            "ci_at": loc(S8CH, "ci", "aP")},
    results_more=[{"metric": "recall vs the judge (Swiss)", "value": ch["aR"], "ci95": ci["aR"], "at": loc(S8CH, "point", "aR")},
                  {"metric": "Δ precision Apertus − keyword", "value": round(ch["aP"] - ch["kP"], 3), "ci95": ci["dP"], "at": loc(S8CH, "ci", "dP")},
                  {"metric": "Δ recall Apertus − keyword", "value": round(ch["aR"] - ch["kR"], 3), "ci95": ci["dR"], "at": loc(S8CH, "ci", "dR")},
                  {"metric": "estimated flags (Swiss)", "value": ch["aflags"], "ci95": ci["aflags"], "at": loc(S8CH, "point", "aflags")},
                  {"metric": "estimated digitalisation affairs (judge positives, Swiss)", "value": ch["pos"], "ci95": ci["pos"],
                   "at": loc(S8CH, "point", "pos")},
                  {"metric": "judge = Qwen alone: precision / recall", "value": [g(S8CH, "qwen_only", "aP"), g(S8CH, "qwen_only", "aR")],
                   "at": loc(S8CH, "qwen_only")},
                  {"metric": "all bodies incl. LIE: precision / recall", "value": [g(S8S, "gold_AB_C", "point", "a_P"), g(S8S, "gold_AB_C", "point", "a_R")],
                   "ci95": [g(S8S, "gold_AB_C", "ci", "a_P"), g(S8S, "gold_AB_C", "ci", "a_R")], "at": loc(S8S, "gold_AB_C")},
                  {"metric": "gold = majority of Claude A, B, Qwen (all bodies): precision / recall",
                   "value": [g(S8S, "gold_majority_ABQ", "point", "a_P"), g(S8S, "gold_majority_ABQ", "point", "a_R")],
                   "ci95": [g(S8S, "gold_majority_ABQ", "ci", "a_P"), g(S8S, "gold_majority_ABQ", "ci", "a_R")], "at": loc(S8S, "gold_majority_ABQ")},
                  {"metric": "operating points (cut-off → P, R, flags)", "value": g(S8OP), "at": loc(S8OP)}],
    baselines=[{"name": "keyword list (29 de/fr/it stems), same input", "precision": ch["kP"], "precision_ci95": ci["kP"],
                "recall": ch["kR"], "recall_ci95": ci["kR"], "flags": ch["kflags"], "flags_ci95": ci["kflags"],
                "qwen_only": [g(S8CH, "qwen_only", "kP"), g(S8CH, "qwen_only", "kR")], "at": loc(S8CH, "point", "kP")}],
    judge={"runs": "Claude A (forward) / B (reverse) + tie-break C on 15", "AB": g(S8S, "annotators", "AB"),
           "AQ": g(S8S, "annotators", "AQ"), "BQ": g(S8S, "annotators", "BQ"), "format": "[n, agreement, kappa]",
           "at": loc(S8S, "annotators")},
    breakdowns={"positives_in_checked_sample": dict(g(S8CH, "positives"), at=loc(S8CH, "positives")),
                "strata_confirmations": dict(g(S8S, "by_stratum"), at=loc(S8S, "by_stratum")),
                "language_precision": cells(S14, "S8", "language", "aP", weighted=True),
                "language_recall": cells(S14, "S8", "language", "aR", weighted=True),
                "level_precision": cells(S14, "S8", "level", "aP", weighted=True),
                "level_recall": cells(S14, "S8", "level", "aR", weighted=True),
                "region_precision": cells(S14, "S8", "region", "aP", weighted=True),
                "party_precision": cells(S14, "S8", "party", "aP", weighted=True),
                "party_keyword_precision": cells(S14, "S8", "party", "kP", weighted=True),
                "canton_precision": cells(S14, "S8", "canton (cantonal+communal bodies; federal separate)", "aP", weighted=True),
                "per_body_flags": (lambda t: {"note": "flag counts per parliament in the design sample (all bodies, 20:30 UTC snapshot); "
                                              "est. = census + N_R,body × SRS share, point only; no judge gold per body", "rows": t[0], "at": t[1]})(
                    mdtable(S8M, "### By body (counts in the design sample")),
                "per_level_flags": (lambda t: {"rows": t[0], "at": t[1]})(mdtable(S8M, "### By level (estimated window totals")),
                "per_language_flags": (lambda t: {"rows": t[0], "at": t[1]})(mdtable(S8M, "### By prompt language (estimated window totals")),
                "breakdown_note": "language/level/region/party/canton cells are on all 464 checked items (incl. LIE), weighted (S14)"},
    split="pre-registered; cut-off p ≥ 0.5 fixed before the run (S3), not re-fitted", prereg=pre(PRE, "## S8 — \"Digitalisierung\" over every affair of 2026"),
    prereg_more=pre(ADD, "S8 reporting addition"),
    sources=[S8CH, S8S, S8M, S8OP, f"{I2}/s8-dvs/score.py", f"{I2}/s8q-crossfamily/ann_Q.tsv"], build=BUILD, model=MODEL,
    judge_build="Claude (blind agent runs); Qwen-SEA-LION aisingapore/Qwen-SEA-LION-v4-32B-IT", date="2026-10-13"))

lp = g(S8L)
tests.append(dict(
    id="dvs_correction_loop", gold="ai-judge", subject="Apertus",
    title_de="Korrekturschleife (simuliert): 60 Richter-Labels als erste Entscheide einer Redaktion",
    title_fr="Boucle de correction (simulée) : 60 étiquettes du juge comme premières décisions",
    n=lp["n"], design="die ersten 60 geprüften Geschäfte (feste Zufallsreihenfolge) als Beispiele, je 4 nächste (BM25); "
    "F1 auf den übrigen 404 gegen denselben Richter; ungewichtet",
    result={"metric": "F1 after (with examples)", "value": lp["after"]["F1"], "ci95": None, "at": loc(S8L, "after", "F1")},
    results_more=[{"metric": "Δ F1", "value": lp["dF1"], "ci95": lp["dF1_ci"], "at": loc(S8L, "dF1")},
                  {"metric": "precision / recall after", "value": [lp["after"]["P"], lp["after"]["R"]], "at": loc(S8L, "after")}],
    baselines=[{"name": "same prompt without examples (before)", "F1": lp["before"]["F1"], "precision": lp["before"]["P"],
                "recall": lp["before"]["R"], "at": loc(S8L, "before")}],
    split="pre-registered (P8.5); unweighted, sample over-represents flagged affairs", prereg=pre(PRE, "Secondary: P8.5 correction loop"),
    sources=[S8L, f"{I2}/s8-dvs/loop.py"], build=BUILD, model=MODEL, date="2026-10-13"))

b8 = g(S8B, "all")
tests.append(dict(
    id="dvs_text_lever", gold="ai-judge", subject="Apertus",
    title_de="«Digitalisierung» mit eingereichtem Text statt nur Titel (Bund)",
    title_fr="« Numérique » avec le texte déposé au lieu du titre seul (fédéral)",
    n=b8["n"], design="S8-Paket, Bundesgeschäfte mit Curia-DE-Text (120); eine Reihenfolge; Titel + Langtitel + erste 1'500 Zeichen",
    result={"metric": "precision / recall, title + text", "value": [b8["title_text"]["P"], b8["title_text"]["R"]],
            "ci95": [[0.908, 1.000], [0.548, 0.786]], "at": loc(S8B, "all", "title_text"), "ci_at": md(S13M, "| title + text | 1.000 [0.908, 1.000]")},
    results_more=[{"metric": "Δ recall", "value": b8["dRecall"], "ci95": b8["dRecall_ci95"], "at": loc(S8B, "all", "dRecall")},
                  {"metric": "Δ F1", "value": b8["dF1"], "ci95": b8["dF1_ci95"], "at": loc(S8B, "all", "dF1")}],
    baselines=[{"name": "title only (same items, same order)", "value": [b8["title_only"]["P"], b8["title_only"]["R"]],
                "ci95": [[0.778, 0.955], [0.642, 0.859]], "at": md(S13M, "| title only (key p_a>=0.5) | 0.896 [0.778, 0.955]")}],
    split="pre-registered (S8b)", prereg=pre(ADD, "S8b text lever"), sources=[S8B, S13M], build=BUILD, model=MODEL, date="2026-10-13"))

ev = g(S12, "support")
tests.append(dict(
    id="evidence_support", gold="ai-judge", subject="Apertus",
    title_de="Beleg: der zitierte Satz stützt das Thema (blinder KI-Richter)",
    title_fr="Preuve : la phrase citée soutient le thème (juge IA à l'aveugle)",
    n=ev["overall"]["n"], design="120 zufällige S9-Geschäfte mit DE-Text; geschlossene Wahl über die nummerierten Sätze; Code prüft exakte Teilzeichenkette; "
    "Richter: zwei blinde Claude-Läufe + Stichentscheid",
    result=dict(prop(S12, "support", "overall", value="rate", ci="ci95"), metric="sentence supports the D1 chapter"),
    results_more=[dict(prop(S12, "support", "d1_right", value="rate", ci="ci95"), metric="when the chapter is right (APS editors)"),
                  dict(prop(S12, "support", "d1_wrong", value="rate", ci="ci95"), metric="when the chapter is wrong"),
                  dict(prop(S12, "substring_pass", value="rate", ci="ci95"), metric="quote is an exact substring"),
                  dict(prop(S12, "ab_agreement", value="rate", ci="ci95"), metric="judge run A = run B", kappa=g(S12, "ab_kappa"))],
    baselines=[], split="random S9 sample, pre-registered", prereg=pre(ADD, "S12 evidence support"),
    sources=[S12, f"{I2}/s12-evidence/results.md", f"{I2}/s12-evidence/score.py"], build=BUILD, model=MODEL, date="2026-10-13"))

s6 = g(S6S, "accuracy")
tests.append(dict(
    id="aps_cantonal_communal", gold="ai-judge", subject="Apertus",
    title_de="APS-Kapitel, Kantone und Gemeinden, gegen den KI-Richter",
    title_fr="Chapitre APS, cantons et communes, contre le juge IA",
    n=s6["all"]["final_top1"]["strict"]["n"], design="160 Geschäfte ab 2015 (100 kantonal, 60 kommunal; de/fr/it); Kapitel aus dem Unterthema; "
    "Gold: zwei blinde Claude-Läufe, wo beide übereinstimmen (153); Gegenprobe Mehrheit Claude ×2 + Qwen (S7)",
    result=dict(prop(S6S, "accuracy", "all", "final_top1", "strict", value="acc"), metric="final chapter = consensus gold"),
    results_more=[dict(prop(S7S, "aps", "apertus", "(c) majority of 3 first choices", "all", value="acc"), metric="gold = majority of Claude A, B, Qwen"),
                  dict(prop(S7S, "aps", "apertus", "(b) Qwen first choice", "all", value="acc"), metric="gold = Qwen alone"),
                  dict(prop(S6S, "accuracy", "all", "l1_top3", "strict", value="acc"), metric="chapter top-3 (chapter step)")],
    baselines=[],
    judge={"AB_agreement": g(S6S, "agreement", "A_vs_B", "raw", "acc"), "kappa": g(S6S, "agreement", "A_vs_B", "kappa"),
           "at": loc(S6S, "agreement", "A_vs_B")},
    breakdowns={nk: dict(prop(S6S, "accuracy", k, "final_top1", "strict", value="acc"), cell=k)
                for k, nk in (("level=cantonal", "level_cantonal"), ("level=communal", "level_communal"), ("lang=de", "lang_de"),
                              ("lang=fr", "lang_fr"), ("lang=it", "lang_it"), ("text", "with_text"), ("title-only", "title_only"),
                              ("L1 first order p>=0.9", "first_reading_p_ge_0.9"), ("L1 second order run", "second_reading_run"),
                              ("orders disagree", "readings_disagree"))}
    | {"canton": cells(S14, "S6", "canton", "strict"), "region": cells(S14, "S6", "region", "strict"),
       "party": cells(S14, "S6", "party", "strict")},
    split="one run, nothing tuned on these items", prereg=None, sources=[S6S, S6M, S7S, f"{I1}/s7-crossfamily/results.md"],
    build=BUILD, model=MODEL, judge_build="Claude (blind agent runs); Qwen-SEA-LION", date="2026-10-13"))

acc = g(S10S, "accuracy")
st = g(S10S, "strata")
tests.append(dict(
    id="aps_bilingual", gold="ai-judge", subject="Apertus",
    title_de="APS-Kapitel, zweisprachige Kantone (BE, FR, VS), nur Titel: Deutsch gegen Französisch",
    title_fr="Chapitre APS, cantons bilingues (BE, FR, VS), titres seuls : allemand contre français",
    n=acc["de"]["n"], design="210 Grossrats-Geschäfte 2025–26 (70 je Kanton), Titel getrennt auf Deutsch und Französisch bewertet; "
    "Gold: zwei blinde Claude-Läufe + Stichentscheid, je zur Hälfte deutsch / französisch gezeigt",
    result=dict(prop(S10S, "accuracy", "de"), metric="chapter top-1, German title"),
    results_more=[dict(prop(S10S, "accuracy", "fr"), metric="chapter top-1, French title"),
                  dict(prop(S10S, "accuracy", "pooled"), metric="chapter top-1, averaged"),
                  {"metric": "DE − FR (paired)", "value": g(S10S, "paired_diff", "de-fr", "diff"), "ci95": g(S10S, "paired_diff", "de-fr", "ci"),
                   "at": loc(S10S, "paired_diff", "de-fr")},
                  {"metric": "gold in top 3 (DE / FR / averaged)", "value": [0.771, 0.738, 0.81],
                   "ci95": [[0.71, 0.823], [0.675, 0.793], [0.751, 0.857]], "at": {"file": S10V, "lines": [1, 2, 3]}}],
    baselines=[],
    judge={"AB": g(S10S, "annotators", "AB_agree"), "kappa": g(S10S, "annotators", "kappa_AB"), "at": loc(S10S, "annotators")},
    breakdowns={"languages_agree": dict(prop(S10S, "strata", "languages agree", "de"), share=g(S10S, "no_gold", "agree_all")),
                "languages_disagree_de": prop(S10S, "strata", "languages disagree (please check)", "de"),
                "languages_disagree_fr": prop(S10S, "strata", "languages disagree (please check)", "fr"),
                "languages_disagree_pooled": prop(S10S, "strata", "languages disagree (please check)", "pooled"),
                "please_check_share_weighted": {"value": g(S10S, "no_gold", "please_check_weighted"),
                                                "ci95": g(S10S, "no_gold", "please_check_weighted_ci"), "at": loc(S10S, "no_gold", "please_check_weighted")},
                "canton": {c: {l: prop(S10S, "strata", f"canton={c}", l) for l in ("de", "fr", "pooled")} for c in ("BE", "FR", "VS")},
                "canton_test": cells(S14, "S10", "canton", "pooled"),
                "shown_language": cells(S14, "S10", "shown language", "pooled"),
                "party": cells(S14, "S10", "party", "pooled"),
                "clerk_load": {"value": "0.2975 × weekly volume (median 10.0, mean 25.5, p90 76.7) = 3.0 / 7.6 / 22.8 a week",
                               "at": md(S10M, "Clerk load: please-check 0.2975")}},
    split="pre-registered", prereg=pre(PRE, "## S10 — bilingual cantonal parliaments"),
    sources=[S10S, S10M, S10V, f"{I2}/s10-bilingual/scripts/score.py"], build=BUILD, model=MODEL, date="2026-10-13"))

tests.append(dict(
    id="neutrality_judge_sets", gold="ai-judge", subject="Apertus",
    title_de="Neutralität auf den Richter-Sets (S8, S6, S10): Sprache, Ebene, Region, Kanton, Partei",
    title_fr="Neutralité sur les jeux du juge (S8, S6, S10) : langue, niveau, région, canton, parti",
    n=None, design="keine neuen Aufrufe; Permutationstest (5'000) über Zellen; Zellen n < 20 werden nicht gelesen",
    result={"metric": "S8 precision by language, permutation p", "value": g(S14, "S8", "language", "aP", "test", "p_perm"),
            "at": loc(S14, "S8", "language", "aP", "test", "p_perm")},
    results_more=[{"metric": "S8 recall by language, permutation p", "value": g(S14, "S8", "language", "aR", "test", "p_perm")},
                  {"metric": "S8 precision by level, permutation p", "value": g(S14, "S8", "level", "aP", "test", "p_perm")},
                  {"metric": "S8 precision by party, permutation p", "value": g(S14, "S8", "party", "aP", "test", "p_perm")},
                  {"metric": "S8 precision gap among party cells n ≥ 20", "value": g(S14, "S8", "party", "aP", "gap", "diff"),
                   "ci95": g(S14, "S8", "party", "aP", "gap", "ci")},
                  {"metric": "S6 language, permutation p", "value": g(S14, "S6", "language", "strict", "test", "p_perm")},
                  {"metric": "S6 party, permutation p", "value": g(S14, "S6", "party", "strict", "test", "p_perm")},
                  {"metric": "S6 canton, permutation p", "value": g(S14, "S6", "canton", "strict", "test", "p_perm")},
                  {"metric": "S10 canton, permutation p", "value": g(S14, "S10", "canton", "pooled", "test", "p_perm")},
                  {"metric": "S10 party, permutation p", "value": g(S14, "S10", "party", "pooled", "test", "p_perm")}],
    baselines=[{"name": "keyword precision by party (S8)", "p_perm": g(S14, "S8", "party", "kP", "test", "p_perm")}],
    breakdowns={"see": "dvs_2026, aps_cantonal_communal, aps_bilingual breakdowns"},
    split="no new calls; reported whatever it showed", prereg=pre(ADD, "S14 neutrality (no calls)"),
    sources=[S14, S14M], build="no calls", date=g(S14, "generated_utc")))

# ================================================================ build week (eval/PREREG-BUILD.md): S16–S23, S8 full census
def wilson_exact(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def acc(rel, *keys, metric, value="acc", ci="ci"):
    d = g(rel, *keys)
    out = {"metric": metric, "value": d[value]}
    if d.get(ci) is not None: out["ci95"] = list(d[ci])
    if "n" in d: out["n"] = d["n"]
    if "share" in d: out["share"] = d["share"]
    out["at"] = loc(rel, *keys, value)
    return out


N16 = g(S16R, "n")
B16 = g(S16R, "build")


def s16top1(d):
    c = g(S16R, "designs", d)
    return {"metric": f"chapter top-1 vs APS editors ({d})", "value": c["top1"], "ci95": c["top1_ci"], "k": c["k1"], "n": N16,
            "at": loc(S16R, "designs", d, "top1")}


def s16top3(d):
    return {"metric": "chapter top-3", "value": g(S16R, "designs", d, "top3"), "n": N16, "at": loc(S16R, "designs", d, "top3")}


def s16diff(a, b):
    x = g(S16R, f"{a}-{b}")
    return {"metric": f"paired Δ top-1 {a} − {b}", "value": x["diff"], "ci95": x["ci"], "method": "paired bootstrap 2,000, percentile",
            "at": loc(S16R, f"{a}-{b}")}


def s16curve(key):
    """grid points 5–100% of an S16 coverage–precision list ([coverage, precision] per k = 1..n); k recovered as precision × n,
    Wilson 95% computed here (exact, bounds stored rounded outward at 4 decimals)."""
    pts = g(S16R, "coverage_precision", key)
    out = []
    for c in sorted({round(x / 100, 2) for x in range(5, 101, 5)}):
        k = max(1, round(c * N16)); cov, prec = pts[k - 1]
        assert abs(cov - round(k / N16, 4)) < 1e-9, (key, c, cov)
        h = round(prec * k); assert round(h / k, 4) == prec, (key, c, prec)
        lo_, hi_ = wilson_exact(h, k)
        out.append(dict(coverage=c, n=k, correct=h, precision=prec,
                        ci=[float(F.q(lo_, 3, F.ROUND_FLOOR)), float(F.q(hi_, 3, F.ROUND_CEILING))], ci_method="Wilson 95% from correct and n, bounds rounded outward"))
    return out


SRC_S16 = [S16R, S16M, f"{QE}/s16/analyze.py", f"{QE}/s16/raw.jsonl", f"{QE}/calibration.json"]
pre16 = pre(PB, "— S16 read-back combined with examples")
pre25 = pre(PB, "— S25 fresh APS-labelled federal affairs")
pre25a = pre(PB, "— S25 amendment: a determinism fix before the final score")
S25R = f"{QE}/s25/results.json"
s25 = g(S25R); N25 = s25["scored"]
assert s25["items"] == N25 and s25["missing"] == 0, (s25["items"], N25, s25["missing"])


def knblock(rel, *keys, metric, ci_key="ci", script="eval/s25/analyze.py"):
    """a {k, n, value, ci} block of an S25-family result file: value = k / n truncated to 4 decimals and ci = Wilson 95% with bounds
    rounded outward at 3 decimals, both by the analysis script; re-checked here from k and n (asserts)."""
    b = g(rel, *keys); k, n = b["k"], b["n"]
    assert b["value"] == math.floor(k / n * 10 ** 4) / 10 ** 4, (rel, keys, b)
    lo_, hi_ = wilson_exact(k, n)
    assert list(b[ci_key]) == [float(F.q(max(lo_, 0.0), 3, F.ROUND_FLOOR)), float(F.q(min(hi_, 1.0), 3, F.ROUND_CEILING))], (rel, keys, b, lo_, hi_)
    out = {"metric": metric, "value": b["value"], "ci95": list(b[ci_key]), "k": k, "n": n, "kn": f"{k}/{n}",
           "ci_method": f"Wilson 95% from k and n, bounds rounded outward ({script}; re-checked by build_pruefstand.py)"}
    for x in ("share", "coverage"):
        if x in b: out[x] = b[x]
    out["at"] = loc(rel, *keys)
    return out


def s25p(*keys, metric):
    """a {k, n, value, ci} block of eval/s25/results.json (see knblock)."""
    return knblock(S25R, *keys, metric=metric)


def s25prefix(k, n, stored, needle, metric):
    """a pre-fix reading stated in the S25 amendment (k/n and the 4-decimal share as written there); Wilson 95% computed here."""
    m_ = md(PB, needle)
    assert stored == math.floor(k / n * 10 ** 4) / 10 ** 4 and f"{stored} ({k}/{n})" in open(os.path.join(ROOT, PB), encoding="utf-8").read(), (k, n, stored)
    lo_, hi_ = wilson_exact(k, n)
    return {"metric": metric, "value": stored, "k": k, "n": n, "kn": f"{k}/{n}",
            "ci95": [float(F.q(lo_, 3, F.ROUND_FLOOR)), float(F.q(hi_, 3, F.ROUND_CEILING))],
            "ci_method": "Wilson 95% computed by build_pruefstand.py from k and n (the amendment states k/n only), bounds rounded outward",
            "at": m_}


t25 = s25p("top1", metric="chapter top-1 vs APS editors (the production pipeline as shipped, held out)")
H25 = (f"S25 (pre-registered, held out): {N25} fresh APS-labelled federal affairs, the production pipeline as shipped, "
       f"top-1 {F.t(t25['value'])} [{F.lo(t25['ci95'][0])}, {F.hi(t25['ci95'][1])}] (aps_chapter_heldout_s25)")
SPLIT_D4 = ("pre-registered (S16), measured on the S9 items; the D4 design was chosen after S9 on the same items (D4 combines D1 and D3), "
            "so this is not a held-out result; fresh held-out test: " + H25)
HELDOUT_D4 = {"id": "aps_chapter_heldout_s25", "what": "fresh held-out test: " + H25}
ln16 = g(S16R, "lanes_D4")
cal16 = g(S16R, "calibration")
d4, d4s = s16top1("D4"), s16top1("D4S")
s9b = s9baselines()
tests.append(dict(
    id="aps_chapter_shipped_d4", gold="human", subject="Apertus",
    title_de="APS-Kapitel gegen APS-Redaktion, Bundesgeschäfte: ausgeliefertes Design D4 (Beispiele + Rücklesen)",
    title_fr="Chapitre APS contre la rédaction APS, objets fédéraux : design livré D4 (exemples + relecture)",
    n=N16, design="die 1'357 S9-Geschäfte, gleicher Input; Prior = Mittel aus der Lesart mit fünf APS-gelabelten Beispielen (Identitätsreihenfolge) "
    "und der zweiten Reihenfolge ohne Beispiele (immer beide); ein Unterthema-Aufruf über die Top-2/3-Kapitel; Kapitel aus dem besten "
    "Unterthema zurückgelesen (p(Unterthema) × Prior)",
    result=dict(d4, display=f"{F.t(d4['value'])} [{F.lo(d4['ci95'][0])}, {F.hi(d4['ci95'][1])}]"),
    results_more=[s16top3("D4"), s16diff("D4", "D3"), s16diff("D4", "D1")],
    baselines=[dict(s16top1("D3"), name="D3 five APS-labelled examples (same items, recomputed in S16)"),
               dict(s16top1("D1"), name="D1 read back from the subtopic, no examples (same items, recomputed in S16)")] + s9b,
    breakdowns={
        "lanes": {"agree": {"share": ln16["agree_share"], "n": ln16["agree_n"], "precision": ln16["agree_precision"], "ci95": ln16["agree_ci"]},
                  "disagree": {"share": round(ln16["disagree_n"] / N16, 4), "share_note": "disagree_n / n (computed here)",
                               "n": ln16["disagree_n"], "precision": ln16["disagree_precision"], "ci95": ln16["disagree_ci"]},
                  "rule": "the two code orders (with examples / without) agree on the top chapter → lane 'readings agree'; else 'please check' "
                          "(the lane rule until 14 Oct; replaced by recalibrated p < 0.7 → 'please check', see aps_lane_rule)",
                  "at": loc(S16R, "lanes_D4")},
        "calibration": dict(cal16["aps-fed"], at=loc(S16R, "calibration", "aps-fed"), file="eval/calibration.json"),
        "coverage_precision": {"points": s16curve("aps-fed"), "at": loc(S16R, "coverage_precision", "aps-fed")},
        "new_subtopic_calls": {"value": g(S16R, "new_calls"), "at": loc(S16R, "new_calls")}},
    split=SPLIT_D4 + " (S16 decision rule fixed before any call: ship D4 if its top-1 ≥ D3's)",
    prereg=pre16, prereg_more=pre25, heldout_test=HELDOUT_D4, decision=g(S16R, "decision"), decision_at=loc(S16R, "decision"),
    sources=SRC_S16, build=B16, model=MODEL, date="2026-10-14", shipped="federal affairs (production design)"))

tests.append(dict(
    id="aps_chapter_d4s", gold="human", subject="Apertus",
    title_de="APS-Kapitel, Bundesgeschäfte: D4s (zweite Reihenfolge nur bei p < 0.9; sekundär, nicht ausgeliefert)",
    title_fr="Chapitre APS, objets fédéraux : D4s (second ordre seulement si p < 0,9 ; secondaire, non livré)",
    n=N16, design="wie D4, die Lesart ohne Beispiele nur, wenn die Lesart mit Beispielen unter p 0.9 liegt",
    result=dict(d4s, display=f"{F.t(d4s['value'])} [{F.lo(d4s['ci95'][0])}, {F.hi(d4s['ci95'][1])}]"),
    results_more=[s16top3("D4S"), s16diff("D4S", "D3"), s16diff("D4S", "D1")],
    baselines=[dict(s16top1("D3"), name="D3 (same items)"), dict(s16top1("D1"), name="D1 (same items)")],
    split="pre-registered secondary (S16), measured on the S9 items; designed after S9 on the same items (a variant of D4, which "
          "combines D1 and D3), so not a held-out result", prereg=pre16, sources=SRC_S16, build=B16, model=MODEL, date="2026-10-14",
    shipped="no (reported, not shipped; S16 decision)"))

tests.append(dict(
    id="aps_calibration_shipped", gold="human", subject="Apertus",
    title_de="Konfidenz der ausgelieferten Designs: Kalibrierfehler vor / nach isotoner Rekalibrierung (Datei pro Build)",
    title_fr="Confiance des designs livrés : erreur de calibration avant / après recalibration isotone (fichier par build)",
    n=cal16["aps-fed"]["n"], design="isotone Regression, 2-fach kreuzangepasst, auf den 1'357 S9-Geschäften; Karten `aps-fed` (D4) und `aps` (D1) "
    "in eval/calibration.json, die der Produktionslauf liest",
    result={"metric": "ECE D4 (aps-fed) raw → isotonic (cross-fit)", "raw": cal16["aps-fed"]["ece_raw"], "value": cal16["aps-fed"]["ece_crossfit"],
            "ci95": None, "acc": cal16["aps-fed"]["acc"], "at": loc(S16R, "calibration", "aps-fed")},
    results_more=[{"metric": "ECE D1 (aps) raw → isotonic (cross-fit)", "raw": cal16["aps"]["ece_raw"], "value": cal16["aps"]["ece_crossfit"],
                   "acc": cal16["aps"]["acc"], "at": loc(S16R, "calibration", "aps")}],
    baselines=[{"name": "raw p (no recalibration)", "D4": cal16["aps-fed"]["ece_raw"], "D1": cal16["aps"]["ece_raw"]}],
    split="cross-fitted (2 folds), no new calls", prereg=pre16, sources=[S16R, f"{QE}/calibration.json", f"{QE}/s16/analyze.py"],
    build=B16, model=MODEL, date="2026-10-14", note="no interval computed for ECE (TO MEASURE: bootstrap)"))

# ---------------------------------------------------------------- lane rule (14 Oct, after juror round 3; computed after S16 from its rows)
LR = f"{QE}/lanes/results.json"


def lane(d, key, metric):
    """one lane block of eval/lanes/results.json: coverage, precision, k/n, Wilson 95% (bounds already floored / ceiled at 3 decimals)."""
    b = g(LR, d, key)
    return {"metric": metric, "value": b["precision"], "ci95": b["ci"], "k": b["k"], "n": b["n"], "coverage": b["coverage"],
            "ci_method": "Wilson 95% from k and n, bounds rounded outward (eval/lanes/analyze.py)", "at": loc(LR, d, key)}


tests.append(dict(
    id="aps_lane_rule", gold="human", subject="Apertus",
    title_de="Lane-Regel, Bundesgeschäfte: «bitte prüfen», wenn das rekalibrierte p < 0.7 (nach S16 aus seinen Zeilen berechnet; "
             "hold-out getestet in S25)",
    title_fr="Règle de voie, objets fédéraux : « à vérifier » si le p recalibré < 0,7 (calculé après S16 à partir de ses lignes ; "
             "testé hors échantillon dans S25)",
    n=g(LR, "D4", "n"), design="die 1'357 S9-Geschäfte, S16-Zeilen; p isoton rekalibriert, 2-fach kreuzangepasst (Seed 3, wie S9c); "
    "ausgeliefert: p ≥ 0.7 → durchgelassen, sonst «bitte prüfen»; verglichen mit der bisherigen Regel «Lesarten einig» und mit dem "
    "rekalibrierten p bei gleicher Abdeckung",
    result=lane("D4", "calibrated_tau_0_7", "D4: precision of the affairs passed at recalibrated p ≥ 0.7 (shipped lane rule)"),
    results_more=[lane("D4", "calibrated_tau_0_7_check", "D4: precision of the rest (recalibrated p < 0.7 → please check)"),
                  lane("D4", "calibrated_same_coverage", "D4: recalibrated p, top affairs at the readings-agree coverage"),
                  lane("D1", "calibrated_tau_0_7", "D1: precision passed at recalibrated p ≥ 0.7"),
                  lane("D1", "calibrated_tau_0_7_check", "D1: precision of the rest (please check)"),
                  lane("D1", "calibrated_same_coverage", "D1: recalibrated p at the readings-agree coverage")],
    baselines=[dict(lane("D4", "readings_agree", "D4: readings agree (earlier lane rule)"), name="D4 readings agree (lane rule until 14 Oct)"),
               dict(lane("D1", "readings_agree", "D1: readings agree"), name="D1 readings agree")],
    split="S9 items (S16 rows); rule chosen after S16 on these items, calibration 2-fold cross-fitted (not pre-registered; no new calls); "
          "tested held out in S25 (pre-registered; lanes in aps_chapter_heldout_s25)",
    prereg=None, prereg_more=pre25,
    heldout_test={"id": "aps_chapter_heldout_s25", "what": "the same rule (recalibrated p ≥ 0.7 passes, map fitted on S16 only) on the "
                  f"{N25} fresh S25 affairs: breakdowns > lanes > pass / please_check"},
    sources=[LR, f"{QE}/lanes/analyze.py", S16R, f"{QE}/s16/analyze.py", f"{QE}/s16/raw.jsonl"], build=B16, model=MODEL, date="2026-10-14",
    shipped="lane rule of the APS chapter (D4 federal, D1 elsewhere; src/querschnitt/compose.py LANE_TAU): please check when the "
            "recalibrated p < 0.7, or when the German and French readings of a bilingual parliament disagree"))

# ---------------------------------------------------------------- hierarchical metrics of D4 (computed after S16 from its rows)
HR = f"{QE}/s16/hierarchical.json"
NHS = g(HR, "n_sub_gold")


def hblk(d, *keys, metric):
    """value + outward interval (already outward in the file) at designs > d > keys."""
    b = g(HR, "designs", d, *keys)
    o = {"metric": metric, "value": b["value"], "ci95": b["ci95"], "ci_method": b.get("ci_method"), "at": loc(HR, "designs", d, *keys)}
    if "k" in b: o.update(k=b["k"], n=b["n"])
    return o


HS = ("hierarchical", "sub_gold_items")
pcd4 = g(HR, "designs", "D4", "per_chapter")
tests.append(dict(
    id="aps_hierarchical_d4", gold="human", subject="Apertus",
    title_de="APS-Unterthema und Hierarchie, Bundesgeschäfte: ausgeliefertes Design D4 (nach S16 aus seinen Zeilen berechnet)",
    title_fr="Sous-thème APS et hiérarchie, objets fédéraux : design livré D4 (calculé après S16 à partir de ses lignes)",
    n=NHS, design="die S9-Geschäfte mit Hauptunterthema unter den 190 Namen; D4-Zeilen aus S16 (Unterthema-Rangliste = p(Unterthema) × Prior); "
    "hierarchisches P/R/F1 nach Kiritchenko (Mengen um Vorfahren ergänzt; Ebenen Kapitel + Unterthema; mikro); Kapitel-F1 je Kapitel, Makro",
    result=hblk("D4", *HS, "hF", metric="hierarchical F1 (D4, chapter + subtopic, micro)"),
    results_more=[hblk("D4", "subtopic", "top1", metric="subtopic top-1 end to end (D4)"),
                  hblk("D4", "subtopic", "top3", metric="subtopic top-3 end to end (D4)"),
                  hblk("D4", "subtopic", "top1_given_chapter_right", metric="subtopic top-1 given the chapter is right (D4)"),
                  hblk("D4", *HS, "hP", metric="hierarchical precision (D4)"),
                  hblk("D4", *HS, "hR", metric="hierarchical recall (D4)"),
                  dict(hblk("D4", "per_chapter", "macro_F1", metric="per-chapter F1, macro over the chapters present (D4)"),
                       n=pcd4["n"], chapters=pcd4["chapters"])],
    baselines=[dict(hblk(d, *HS, "hF", metric=f"hierarchical F1 ({d})"), name=nm) for d, nm in
               (("D1", "D1 read back from the subtopic, no examples (same items)"),
                ("D0", "D0 plain list prompting, best subtopic within its chapter (same items)"),
                ("keyword", "keyword (APS subtopic words, frozen; chapter only)"))] +
              [dict(hblk(d, "subtopic", k, metric=f"{m} ({d})"), name=f"{d} {m}") for d in ("D1", "D0")
               for k, m in (("top1", "subtopic top-1"), ("top3", "subtopic top-3"), ("top1_given_chapter_right", "subtopic top-1 given chapter right"))] +
              [dict(hblk(d, *HS, x, metric=f"{x} ({d})"), name=f"{d} {x}") for d in ("D1", "D0", "keyword") for x in ("hP", "hR")] +
              [dict(hblk(d, "per_chapter", "macro_F1", metric=f"per-chapter macro-F1 ({d})"), name=f"{d} per-chapter macro-F1")
               for d in ("D1", "D0", "keyword")],
    breakdowns={"per_chapter_D4": {"cells": [{"cell": v["chapter"], "n": v["n_gold"], "value": v["F1"], "ci95": v["ci95"],
                                              **({"small": True} if v["n_gold"] < 20 else {})} for v in pcd4["by_chapter"].values()],
                                   "metric": "F1 per chapter (one vs rest), stratified bootstrap 2,000",
                                   "at": loc(HR, "designs", "D4", "per_chapter", "by_chapter")},
                "all_items_hF": hblk("D4", "hierarchical", "all_items", "hF",
                                     metric="hierarchical F1 on all 1,357 items (gold depth 1 where the main subtopic is not among the 190)")},
    split="S9 items; computed after S16 from its rows (not pre-registered; no new calls); D4 was chosen after S9 on the same items "
          "(it combines D1 and D3), so not a held-out result; the same metrics on the held-out S25 items, also computed after the fact "
          "(not pre-registered): aps_hierarchical_heldout_s25",
    prereg=None, prereg_more=pre25,
    heldout_test={"id": "aps_hierarchical_heldout_s25", "what": "the same metrics of the shipped design on the S25 items (held out for "
                  "the design; computed after the S25 result, not pre-registered)"},
    sources=[HR, f"{QE}/s16/hierarchical.py", f"{QE}/s16/raw.jsonl", f"{I2}/s9-aps/raw/", f"{I2}/s9-aps/data/items.json"],
    build=B16, model=MODEL, date="2026-10-14", shipped="ranked subtopic suggestions (federal affairs, D4)"))

# ---------------------------------------------------------------- S25: the shipped federal design held out, on fresh APS-labelled affairs
L25 = {"pass": "pass: recalibrated p ≥ 0.7 (shipped lane rule; map fitted on S16 only)",
       "please_check": "please check: recalibrated p < 0.7",
       "readings_agree": "the two readings (with / without examples) agree on the chapter",
       "readings_disagree": "the two readings disagree"}
cy25 = g(S25R, "curia_year")
cy25_before = sum(v for y_, v in cy25.items() if int(y_) < 2015); cy25_from = sum(v for y_, v in cy25.items() if int(y_) >= 2015)
assert cy25_before + cy25_from == N25, (cy25_before, cy25_from, N25)
gc25 = g(S25R, "gold_chapters"); assert sum(gc25.values()) == N25
# D1 = read without examples: no APS-labelled BM25 neighbour (one-word procedural titles such as «Vereidigung») or a text that is
# not German (engine.ch1_prompt asks for examples only for federal affairs in German)
K25_D4 = "D4 (German text: five examples)"
K25_D1 = "D1 (no examples: no APS-labelled neighbour for one-word procedural titles such as «Vereidigung», or a French text)"
DES25 = {K25_D4: "D4", K25_D1: "D1"}
bd25 = g(S25R, "by_design"); assert set(bd25) == set(DES25) and sum(v["n"] for v in bd25.values()) == N25
assert g(S25R, "with_examples") == bd25[K25_D4]["n"]
bl25 = g(S25R, "by_lang"); assert set(bl25) == {"de", "fr"}, set(bl25)
N25_D1_FR = bl25["fr"]["n"]; N25_D1_DE = bd25[K25_D1]["n"] - N25_D1_FR     # every non-German affair is D1
assert bl25["de"]["n"] == bd25[K25_D4]["n"] + N25_D1_DE, (bl25, bd25)
pf25 = [s25prefix(636, 904, 0.7035, "904 affairs scored, top-1 0.7035 (636/904)",
                  "pre-fix reading 1 (old, non-deterministic example retrieval; seen before the fix): chapter top-1"),
        s25prefix(633, 905, 0.6994, "905 scored, 0.6994 (633/905)",
                  "pre-fix reading 2 (old, non-deterministic example retrieval; seen before the fix): chapter top-1")]
# S25b (pre-registered after the S25 result, before any S25b call): plain list prompting (S9 D0) on the S25 items, paired with the shipped
S25BR = f"{QE}/s25b/results.json"
pre25b = pre(PB, "— S25b plain list prompting on the S25 items")
s25b = g(S25BR)
d025 = knblock(S25BR, "D0_top1", ci_key="ci95", script="eval/s25b/analyze.py",
               metric="chapter top-1, plain list prompting (S9 D0: two code orders, no examples, geometric mean; S25b)")
sh25b = knblock(S25BR, "shipped_top1", ci_key="ci95", script="eval/s25b/analyze.py",
                metric="chapter top-1 of the shipped pipeline on the same affairs as D0 (S25b)")
N25B = s25b["n"]
assert d025["n"] == sh25b["n"] == N25B and N25B + s25b["not_scored"]["n"] == N25, (N25B, s25b["not_scored"], N25)
df25b = g(S25BR, "shipped_minus_D0")
assert abs(df25b["value"] - (sh25b["k"] - d025["k"]) / N25B) < 5e-5, df25b
assert df25b["ci95"][0] <= df25b["value"] <= df25b["ci95"][1], df25b
dif25b = {"metric": "paired Δ top-1 shipped − D0 (same affairs)", "value": df25b["value"], "ci95": list(df25b["ci95"]), "n": N25B,
          "method": "paired bootstrap 2,000 over affairs, percentile, bounds rounded outward (eval/s25b/analyze.py)",
          "value_note": "the file stores the difference rounded to 4 decimals; shown truncated at 3",
          "at": loc(S25BR, "shipped_minus_D0")}
tests.append(dict(
    id="aps_chapter_heldout_s25", gold="human", subject="Apertus",
    title_de=f"APS-Kapitel gegen APS-Redaktion, {N25} neue Bundesgeschäfte (hold-out): ausgeliefertes Design, Produktionspipeline unverändert (S25)",
    title_fr=f"Chapitre APS contre la rédaction APS, {N25} nouveaux objets fédéraux (hors échantillon) : design livré, pipeline de production "
             "inchangé (S25)",
    n=N25, design=f"Bundesgeschäfte mit APS-Kapitel der Redaktion aus Wayback-Aufnahmen der Prozessseiten von anneepolitique.swiss, keines in den "
    "S5- oder S9-Sets oder im Beispielpool (S9-Regeln: Kapitel + Hauptunterthema); Produktions-Input aus OPD; Produktionspipeline wie ausgeliefert: "
    "D4 (fünf BM25-nächste APS-gelabelte Beispiele aus dem S5+S9-Pool + zweite Lesart ohne Beispiele, Kapitel aus dem Unterthema zurückgelesen), "
    f"D1 (ohne Beispiele) für die {bd25[K25_D1]['n']} Geschäfte ohne passendes APS-Beispiel ({N25_D1_DE} einwortige Verfahrenstitel wie "
    f"«Vereidigung», «Nachruf», «Ordnungsantrag» ohne BM25-Nachbarn im Pool; {N25_D1_FR} französischer Text); "
    "Lane: rekalibriertes p ≥ 0.7 → durchgelassen, Kalibrierkarte nur auf S16 angepasst; Entscheide komponiert wie im Export (compose.decide)",
    result=dict(t25, display=f"{F.t(t25['value'])} [{F.lo(t25['ci95'][0])}, {F.hi(t25['ci95'][1])}]"),
    results_more=[s25p("top3", metric="chapter top-3")] + pf25,
    baselines=[dict(d025, name=f"plain list prompting (S9 D0), same build and input, on {N25B} of the {N25} affairs (S25b, pre-registered)",
                    prereg=pre25b),
               dict(s25p("keyword_top1", metric="keyword top-1"),
                    name="keyword (S9 frozen rule: APS subtopic words, ties by the S9 majority order), same input")],
    breakdowns={
        "lanes": {k_: dict(s25p("lanes", k_, metric=f"precision, {L25[k_]}"), cell=k_) for k_ in ("pass", "please_check", "readings_agree", "readings_disagree")}
        | {"rule": "shipped: pass when the recalibrated p ≥ 0.7 (src/querschnitt/compose.py LANE_TAU), else please check; readings agree / "
                   "disagree is the earlier lane rule, reported as pre-registered", "share_note": "share = share of the scored affairs (truncated)"},
        "routing_by_p_cal": {"points": [dict(s25p("routing_by_p_cal", t_, metric=f"precision of the affairs with recalibrated p ≥ {t_}"),
                                             threshold=float(t_)) for t_ in g(S25R, "routing_by_p_cal")],
                             "note": "coverage = share of the scored affairs at or above the threshold; calibration map fitted on S16 only",
                             "at": loc(S25R, "routing_by_p_cal")},
        "by_design": {"cells": [dict(s25p("by_design", k_, metric=f"chapter top-1, {k_}"), cell=DES25[k_],
                                     **({"small": True} if bd25[k_]["n"] < 20 else {})) for k_ in DES25], "at": loc(S25R, "by_design")},
        "by_lang": {"cells": [dict(s25p("by_lang", l_, metric=f"chapter top-1, affair language {l_}"), cell=l_,
                                   **({"small": True} if v_["n"] < 20 else {})) for l_, v_ in g(S25R, "by_lang").items()],
                    "note": "OPD language of the affair; the D4/D1 split (by_design) follows whether the chapter step showed examples",
                    "at": loc(S25R, "by_lang")},
        "curia_year": {"before_2015": cy25_before, "from_2015": cy25_from, "by_year": cy25,
                       "derived": "years from the Curia number (analyze.py), summed here", "at": loc(S25R, "curia_year")},
        "gold_chapters": {"chapters": len(gc25), "counts": gc25, "at": loc(S25R, "gold_chapters")},
        "with_examples": {"value": g(S25R, "with_examples"), "at": loc(S25R, "with_examples")},
        "scored": {"in_set": g(S25R, "items"), "scored": N25, "missing": g(S25R, "missing"), "at": loc(S25R, "scored")},
        "list_prompting_s25b": {"D0": d025, "shipped_same_affairs": sh25b, "paired_shipped_minus_D0": dif25b,
                                "not_scored": {"value": s25b["not_scored"]["n"], "why": s25b["not_scored"]["why"], "at": loc(S25BR, "not_scored")},
                                "d0a_asked": {"value": s25b["d0a_asked"], "at": loc(S25BR, "d0a_asked")},
                                "prereg": pre25b, "sources": [S25BR, f"{QE}/s25b/analyze.py", f"{QE}/s25b/run.py", f"{QE}/s25b/raw.jsonl",
                                                               f"{QE}/s25b/ledger.jsonl"],
                                "build": s25b["build"] + " (run runs/s25)"}},
    pre_fix_note="results_more[1:]: two compositions of the finished run seen with the old example retrieval (set order, randomised per "
                 "process) before the determinism fix; reported as such next to the final score (amendment)",
    split="held out, pre-registered (S25): fresh items never used while designing (none in S5, S9 or the example pool); nothing tuned on "
          "them; calibration map fitted on S16 only; the example retrieval was made deterministic before the final score (amendment, a bug "
          "fix, not a design change), and the two readings seen before the fix are reported",
    prereg=pre25, prereg_more=pre25a, prereg_baseline=pre25b,
    sources=[S25R, f"{QE}/s25/analyze.py", f"{QE}/s25/decisions.jsonl", f"{QE}/s25/items.jsonl", f"{QE}/s25/FETCH.md", "src/querschnitt/compose.py",
             "src/querschnitt/examples.py", f"{QE}/calibration.json", PB],
    build=s25["build"] + " (run runs/s25)", model=MODEL, date="2026-10-15",
    shipped="federal affairs: the production design as shipped (D4; D1 where no APS-labelled example is found: a text that is not "
            "German, or a title with no BM25 neighbour in the pool)"))

# S25 subtopic / hierarchy (computed after the S25 result from its rows; NOT pre-registered; eval/s16/hierarchical.py definitions)
HR25 = f"{QE}/s25/hierarchical.json"
h25 = g(HR25)
assert h25["prereg"].startswith("not pre-registered") and h25["items"] == N25, (h25["prereg"], h25["items"])
NH25 = h25["subtopic_gold_items"]
H25M = "percentile bootstrap 2,000, bounds rounded outward (eval/s25/hierarchical.py)"


def h25k(key, metric):
    return knblock(HR25, key, ci_key="ci95", script="eval/s25/hierarchical.py", metric=metric)


def h25b(*keys, metric):
    b = g(HR25, *keys)
    assert b["ci95"][0] <= b["value"] <= b["ci95"][1], (keys, b)
    return {"metric": metric, "value": b["value"], "ci95": list(b["ci95"]), "ci_method": H25M, "at": loc(HR25, *keys)}


st25 = [h25k("subtopic_top1", "subtopic top-1 end to end (shipped, held out)"),
        h25k("subtopic_top3", "subtopic top-3 end to end (shipped, held out)"),
        h25k("subtopic_top1_given_chapter_right", "subtopic top-1 given the chapter is right (shipped, held out)")]
assert st25[0]["n"] == st25[1]["n"] == NH25
mf25 = dict(h25b("chapter_macro_f1", metric="per-chapter F1, macro over the chapters present (shipped, held out)"),
            n=N25, chapters=g(HR25, "chapter_macro_f1", "chapters"))
assert mf25["chapters"] == len(gc25), (mf25["chapters"], len(gc25))
tests.append(dict(
    id="aps_hierarchical_heldout_s25", gold="human", subject="Apertus",
    title_de=f"APS-Unterthema und Hierarchie, {N25} neue Bundesgeschäfte (hold-out): ausgeliefertes Design (nach S25 aus seinen Zeilen "
             "berechnet, nicht vorregistriert)",
    title_fr=f"Sous-thème APS et hiérarchie, {N25} nouveaux objets fédéraux (hors échantillon) : design livré (calculé après S25 à partir de "
             "ses lignes, non préenregistré)",
    n=NH25, design=f"die S25-Geschäfte mit Hauptunterthema unter den 190 Namen ({NH25} von {N25}); Entscheide der Produktionspipeline wie in S25 "
    "(Unterthema-Rangliste neu komponiert, keine neuen Aufrufe); Definitionen wie eval/s16/hierarchical.py: hierarchisches P/R/F1 nach "
    "Kiritchenko (Mengen um Vorfahren ergänzt; Ebenen Kapitel + Unterthema; mikro); Kapitel-F1 je Kapitel, Makro über alle "
    f"{N25} Geschäfte",
    result=h25b("hierarchical", "hF1", metric="hierarchical F1 (shipped, held out, chapter + subtopic, micro)"),
    results_more=st25 + [h25b("hierarchical", "hP", metric="hierarchical precision (shipped, held out)"),
                         h25b("hierarchical", "hR", metric="hierarchical recall (shipped, held out)"), mf25],
    baselines=[],
    reference={"id": "aps_hierarchical_d4", "what": "the same metrics of D4 on the design set (S9 items, S16 rows; not held out)"},
    split="S25 items (held out for the design: none used while designing); computed after the S25 result from its rows (not "
          "pre-registered; no new calls); same definitions as eval/s16/hierarchical.py; noted as not pre-registered in the S25b entry",
    prereg=None, prereg_more=pre25b,
    sources=[HR25, f"{QE}/s25/hierarchical.py", f"{QE}/s16/hierarchical.py", f"{QE}/s25/decisions.jsonl", f"{QE}/s25/items.jsonl"],
    build=h25["build"] + " (run runs/s25)", model=MODEL, date="2026-10-15", shipped="ranked subtopic suggestions (federal affairs)"))

# ---------------------------------------------------------------- S28: the shipped pipeline in no-prefill mode (QS_PREFILL=0) on the S25 items
# An endpoint-capability check: what the labelled fallback for an endpoint that cannot continue an assistant message costs, paired
# against the shipped prefill design (S25 final) on the same 927 held-out affairs.
S28R = f"{QE}/s28/results.json"
pre28 = pre(PB, "— S28 no-prefill mode on the S25 held-out items")
pre28a = pre(PB, "— S28 amendment: a read fix after the smoke run")
s28 = g(S28R)
assert s28["items"] == s28["scored"] == N25 and s28["missing"] == 0 and s28["mode"] == "no-prefill", (s28["items"], s28["scored"], s28["mode"])
assert s28["build"] == s25["build"], (s28["build"], s25["build"])


def s28k(*keys, metric):
    """a {k, n, value, ci} block of eval/s28/results.json (see knblock)."""
    return knblock(S28R, *keys, metric=metric, script="eval/s28/analyze.py")


def s28d(key, metric):
    """a paired difference prefill − no-prefill of eval/s28/results.json (mean of per-affair differences truncated toward zero at 4
    decimals; percentile bootstrap 2,000, seed 2026, bounds rounded outward at 3 decimals, by eval/s28/analyze.py)."""
    b = g(S28R, key)
    assert b["ci95"][0] <= b["value"] <= b["ci95"][1], (key, b)
    return {"metric": metric, "value": b["value"], "ci95": list(b["ci95"]), "n": N25,
            "prefill_only_right": b["prefill_only_right"], "no_prefill_only_right": b["no_prefill_only_right"],
            "method": "paired bootstrap 2,000 over affairs, percentile, seed 2026, bounds rounded outward (eval/s28/analyze.py)",
            "value_note": "the file stores the mean difference truncated toward zero at 4 decimals; shown truncated at 3", "at": loc(S28R, key)}


t28 = s28k("no_prefill_top1", metric="chapter top-1 vs APS editors, no-prefill mode (QS_PREFILL=0), otherwise the pipeline as shipped")
pf28 = s28k("prefill_top1_same_items", metric="chapter top-1 of the shipped prefill design on the same affairs (S25 final)")
assert (pf28["k"], pf28["n"]) == (t25["k"], t25["n"]), (pf28["kn"], t25["kn"])   # the S25 final decisions, re-read by eval/s28/analyze.py
df28 = s28d("prefill_minus_no_prefill_top1", "paired Δ top-1, shipped prefill − no-prefill (same affairs)")
assert abs(df28["value"] - (pf28["k"] - t28["k"]) / N25) < 1e-4, df28
rp28 = g(S28R, "read_path_rows_used"); ra28 = g(S28R, "read_path_all_rows")
assert set(ra28) == {"logprobs"} and all(set(v) == {"logprobs"} for v in rp28.values()), (ra28, rp28)
assert g(S28R, "affairs_with_a_text_read") == 0 and g(S28R, "affairs_with_an_unparseable_row") == 0
c28 = g(S28R, "cost")
D28 = {"D4 (German text: five examples)": "D4", "D1 (no examples)": "D1"}
assert set(g(S28R, "by_design")) == set(D28), set(g(S28R, "by_design"))
tests.append(dict(
    id="aps_chapter_heldout_s28_no_prefill", gold="human", subject="Apertus",
    title_de=f"APS-Kapitel gegen APS-Redaktion, dieselben {N25} neuen Bundesgeschäfte (hold-out): ohne Prefill (Endpunkt-Fallback "
             "QS_PREFILL=0) gegen das ausgelieferte Prefill (S28)",
    title_fr=f"Chapitre APS contre la rédaction APS, les mêmes {N25} nouveaux objets fédéraux (hors échantillon) : sans prefill (repli pour "
             "l'endpoint, QS_PREFILL=0) contre le prefill livré (S28)",
    n=N25, design="eine Prüfung der Endpunkt-Fähigkeit, kein neues Design: Produktionspipeline wie ausgeliefert (D4 / D1 wie S25), aber mit "
    "QS_PREFILL=0: eine Nutzernachricht = der gemessene Prompt + eine Zeile, die Antwort mit der JSON-Öffnung zu beginnen; Code aus den "
    "top_logprobs des ersten Tokens nach der Öffnung (sonst aus dem Text); ohne Kalibrierung: Lane = Lesarten-Regel (durchgelassen, wenn "
    "die zwei Code-Reihenfolgen übereinstimmen oder eine Lesart mit p ≥ 0.9); gepaart gegen die S25-Entscheide (Prefill) auf denselben Geschäften",
    result=dict(t28, display=f"{F.t(t28['value'])} [{F.lo(t28['ci95'][0])}, {F.hi(t28['ci95'][1])}]"),
    results_more=[s28k("no_prefill_top3", metric="chapter top-3, no-prefill"), df28,
                  s28d("prefill_minus_no_prefill_top3", "paired Δ top-3, shipped prefill − no-prefill (same affairs)"),
                  s28k("same_chapter_as_prefill", metric="same chapter as the shipped prefill decision")],
    baselines=[dict(pf28, name=f"shipped prefill design (S25 final), same {N25} affairs"),
               dict(s28k("prefill_top3_same_items", metric="chapter top-3 of the shipped prefill design (S25 final)"),
                    name="shipped prefill design, top-3")],
    breakdowns={
        "lanes_no_prefill": {k_: dict(s28k("lanes_no_prefill", k_, metric=f"precision, no-prefill readings lane: {k_}"), cell=k_)
                             for k_ in ("pass", "please_check")}
        | {"rule": "no calibration in no-prefill mode: pass when the two code orders agree or one reading has top p ≥ 0.9, else please check "
                   "(compose.decide)", "share_note": "share = share of the scored affairs (truncated)"},
        "lanes_prefill_s25": {k_: dict(s28k("lanes_prefill_s25", k_, metric=f"precision, shipped prefill lane (S25): {k_}"), cell=k_)
                              for k_ in ("pass", "please_check", "readings_agree", "readings_disagree")},
        "by_design": {"cells": [dict(s28k("by_design", k_, mode_, metric=f"chapter top-1, {k_}, {mode_}"), cell=f"{D28[k_]} {mode_}",
                                     **({"small": True} if g(S28R, "by_design", k_, mode_)["n"] < 20 else {}))
                                for k_ in D28 for mode_ in ("no_prefill", "prefill")], "at": loc(S28R, "by_design")},
        "read_path": {"rows_used": {k_: v_["logprobs"] for k_, v_ in rp28.items()}, "all_rows_logprobs": ra28["logprobs"],
                      "affairs_with_a_text_read": g(S28R, "affairs_with_a_text_read"),
                      "affairs_with_an_unparseable_row": g(S28R, "affairs_with_an_unparseable_row"),
                      "share_from_logprobs": "every row (100%): no code read from the generated text, none unparseable",
                      "mass_in_listed_codes_ch1_mean": g(S28R, "mass_in_listed_codes_ch1_mean"),
                      "note": g(S28R, "read_path_note"), "at": loc(S28R, "read_path_all_rows")},
        "cost": {"no_prefill_calls": c28["no_prefill"]["calls"], "no_prefill_usd": c28["no_prefill"]["usd"],
                 "calls_per_affair": c28["no_prefill"]["calls_per_affair"], "prefill_s25_calls": c28["prefill_s25"]["calls"],
                 "prefill_s25_usd": c28["prefill_s25"]["usd"], "smoke1_discarded_calls": c28["smoke1_discarded"]["calls"],
                 "s28_total_calls": c28["s28_total"]["calls"], "s28_total_usd": c28["s28_total"]["usd"], "note": c28["note"],
                 "at": loc(S28R, "cost")},
        "scored": {"in_set": s28["items"], "scored": s28["scored"], "missing": s28["missing"], "at": loc(S28R, "scored")}},
    split=f"the {N25} S25 held-out affairs (none used while designing), pre-registered (S28) before any S28 call; a read fix after the "
          "first smoke run (amendment, a bug fix, not a design change; the 28 smoke calls were never scored); nothing tuned",
    prereg=pre28, prereg_more=pre28a,
    reference={"id": "aps_chapter_heldout_s25", "what": "the shipped prefill design on the same affairs (S25)"},
    sources=[S28R, f"{QE}/s28/analyze.py", f"{QE}/s25/decisions.jsonl", f"{QE}/s25/items.jsonl", "src/querschnitt/client.py",
             "src/querschnitt/compose.py", PB],
    build=s28["build"] + " (run runs/s28, mode no-prefill)", model=MODEL, date="2026-10-15",
    shipped="labelled fallback only (QS_PREFILL=0) for an endpoint that cannot continue an assistant message; the default ships prefill"))

# ---------------------------------------------------------------- S33: the same held-out affairs read from the French text
# Production reads federal affairs from the German text; S33 reads the 927 S25 affairs from OPD's French title and submitted text,
# with the design production runs for a French federal affair (examples only for German federal text: D1 read-back, French frame),
# paired against the shipped S25 decisions on the German text.
S33R = f"{QE}/s33/results.json"
pre33 = pre(PB, "— S33 the S25 held-out affairs read from the French text")
s33 = g(S33R)
assert s33["items"] == s33["scored"] == N25 and s33["missing"] == 0 and s33["with_examples"] == 0, (s33["items"], s33["scored"])
assert s33["build"] == s25["build"], (s33["build"], s25["build"])


def s33k(*keys, metric):
    """a {k, n, value, ci} block of eval/s33/results.json (see knblock)."""
    return knblock(S33R, *keys, metric=metric, script="eval/s33/analyze.py")


def s33d(*keys, metric, first, second):
    """a paired difference of eval/s33/results.json (mean of per-affair differences truncated toward zero at 4 decimals; percentile
    bootstrap 2,000, random.Random(2026), bounds rounded outward at 3 decimals, by eval/s33/analyze.py)."""
    b = g(S33R, *keys)
    assert b["ci95"][0] <= b["value"] <= b["ci95"][1], (keys, b)
    return {"metric": metric, "value": b["value"], "ci95": list(b["ci95"]), "n": b["n"],
            f"{first}_only_right": b["first_only_right"], f"{second}_only_right": b["second_only_right"],
            "method": "paired bootstrap 2,000 over affairs, percentile, random.Random(2026), bounds rounded outward (eval/s33/analyze.py)",
            "value_note": "the file stores the mean difference truncated toward zero at 4 decimals; shown truncated at 3", "at": loc(S33R, *keys)}


t33 = s33k("french_top1", metric="chapter top-1 vs APS editors, French text (D1 read-back without examples, French frame: what "
           "production runs for a French federal affair)")
de33 = s33k("german_shipped_top1", metric="chapter top-1 of the shipped pipeline on the German text (S25 final, D4), same affairs")
assert (de33["k"], de33["n"]) == (t25["k"], t25["n"]), (de33["kn"], t25["kn"])   # the S25 final decisions, re-read by eval/s33/analyze.py
df33 = s33d("french_minus_german_top1", metric="paired Δ top-1, French − German shipped (same affairs)", first="french", second="german")
assert abs(df33["value"] - (t33["k"] - de33["k"]) / N25) < 1e-4, df33
sd33 = g(S33R, "same_design_readings_only")
ro33 = {"french": s33k("same_design_readings_only", "french_top1", metric="chapter top-1, French, chapter readings only (no read-back)"),
        "german": s33k("same_design_readings_only", "german_top1", metric="chapter top-1, German, chapter readings only (no read-back)"),
        "paired": s33d("same_design_readings_only", "french_minus_german_top1", metric="paired Δ top-1, French − German, same design "
                       "(chapter readings only)", first="french", second="german"),
        "design": sd33["design"], "german_sources": sd33["german_sources"],
        "two_readings": {"french": sd33["french_two_readings"], "german": sd33["german_two_readings"], "at": loc(S33R, "same_design_readings_only")},
        "german_inputs_matched_pre_rebuild": {"value": sd33["german_inputs_matched_pre_rebuild"],
                                              "at": loc(S33R, "same_design_readings_only", "german_inputs_matched_pre_rebuild")}}
assert ro33["french"]["n"] == ro33["german"]["n"] == N25, (ro33["french"]["kn"], ro33["german"]["kn"])
in33 = g(S33R, "inputs"); c33 = g(S33R, "cost")
assert in33["with_french_text"] + in33["french_title_only"] == N25
assert c33["fps"] == [s25["build"]] and c33["models"] == [MODEL], (c33["fps"], c33["models"])
TX33 = {"french_with_text": "French submitted text", "french_title_only": "French title only",
        "french_title_only_german_document_text": "French title only, German read with a document text",
        "french_title_only_german_no_text": "French title only, German had no text either"}
tests.append(dict(
    id="aps_chapter_heldout_s33_french", gold="human", subject="Apertus",
    title_de=f"APS-Kapitel gegen APS-Redaktion, dieselben {N25} neuen Bundesgeschäfte (hold-out): aus dem französischen Text gelesen, "
             "gegen das ausgelieferte Design auf dem deutschen Text (S33)",
    title_fr=f"Chapitre APS contre la rédaction APS, les mêmes {N25} nouveaux objets fédéraux (hors échantillon) : lus dans le texte "
             "français, contre le design livré sur le texte allemand (S33)",
    n=N25, design=f"die {N25} S25-Geschäfte, Gold = APS-Kapitel der Redaktion; Input aus OPD: französischer Titel (+ Langtitel, bei keinem "
    f"vorhanden) + französischer eingereichter Text («Texte déposé», erste 1'500 Zeichen) bei {in33['with_french_text']}, nur Titel bei "
    f"{in33['french_title_only']} (davon {in33['title_only_and_german_had_document_text']} auf Deutsch mit Dokumenttext gelesen); Design wie "
    "die Produktion ein französisches Bundesgeschäft heute liest: Beispiele nur für deutschen Bundestext, also D1 ohne Beispiele im "
    "französischen Rahmen (Kapitelnamen französisch, Unterthemen deutsch wie publiziert), zweite Code-Reihenfolge, wenn die erste Lesart "
    "p < 0.9 hat, Kapitel aus dem Unterthema zurückgelesen; Entscheide komponiert wie im Export (compose.decide); gepaart gegen die "
    "S25-Entscheide (D4 auf dem deutschen Text) auf denselben Geschäften",
    result=dict(t33, display=f"{F.t(t33['value'])} [{F.lo(t33['ci95'][0])}, {F.hi(t33['ci95'][1])}]"),
    results_more=[s33k("french_top3", metric="chapter top-3, French"), df33,
                  s33d("french_minus_german_top3", metric="paired Δ top-3, French − German shipped (same affairs)", first="french", second="german"),
                  s33k("same_chapter_as_german", metric="same chapter as the shipped German decision")],
    baselines=[dict(de33, name=f"shipped design on the German text (S25 final, D4), same {N25} affairs"),
               dict(s33k("german_shipped_top3", metric="chapter top-3 of the shipped design on the German text (S25 final)"),
                    name="shipped design on the German text, top-3")],
    breakdowns={
        "same_design_readings_only": ro33,
        "same_design_read_back": {"skipped": True, "why": g(S33R, "same_design_read_back", "why"),
                                  "german_subtopic_rows_available": g(S33R, "same_design_read_back", "german_subtopic_rows_available"),
                                  "missing": g(S33R, "same_design_read_back", "missing"), "at": loc(S33R, "same_design_read_back")},
        "lanes_french": {k_: dict(s33k("lanes_french", k_, metric=f"precision, French: {L25[k_]}"), cell=k_)
                         for k_ in ("pass", "please_check", "readings_agree", "readings_disagree")}
        | {"rule": g(S33R, "lanes_rule"), "share_note": "share = share of the scored affairs (truncated)"},
        "by_text": {"cells": [dict(s33k(k_, "french", metric=f"chapter top-1, French, {v_}"), cell=v_,
                                   german_same_items=s33k(k_, "german_shipped_same_items", metric=f"chapter top-1, German shipped, same affairs ({v_})"),
                                   **({"small": True} if g(S33R, k_, "french")["n"] < 20 else {})) for k_, v_ in TX33.items()],
                    "at": loc(S33R, "french_with_text")},
        "inputs": {**in33, "at": loc(S33R, "inputs")},
        "cost": {"calls": c33["calls"], "usd": c33["usd"], "rows": c33["rows"], "calls_per_affair": c33["calls_per_affair"],
                 "first_launch_calls_not_written": c33["first_launch_calls_not_written"], "note": c33["note"], "at": loc(S33R, "cost")},
        "scored": {"in_set": s33["items"], "scored": s33["scored"], "missing": s33["missing"], "at": loc(S33R, "scored")}},
    split=f"the {N25} S25 held-out affairs (none used while designing), pre-registered (S33) before any S33 call; nothing tuned",
    prereg=pre33,
    reference={"id": "aps_chapter_heldout_s25", "what": "the shipped design on the German text of the same affairs (S25)"},
    sources=[S33R, f"{QE}/s33/analyze.py", f"{QE}/s33/run.py", f"{QE}/s33/inputs_fr.jsonl.gz", f"{QE}/s25/decisions.jsonl",
             f"{QE}/s25/items.jsonl", f"{QE}/s25b/raw.jsonl", "src/querschnitt/engine.py", "src/querschnitt/compose.py", PB],
    build=s33["build"] + " (run runs/s33)", model=MODEL, date="2026-10-16",
    shipped="measurement of the shipped code path for French federal text; production keeps reading federal affairs from the German text"))

# ---------------------------------------------------------------- S31: a documented design search on the design set (dev only, not pre-registered)
# Five variants of the federal design against D4 on the S9/S16 design set, leave-one-out examples, a gate fixed before any S31 call
# (paired Δ vs D4 ≥ +0.02 on all 1,357 with the 95% interval above 0). No variant cleared it, so no test was run: the S25 held-out
# items were not touched (unspent). Documents that the shipped design was not beaten on the set it was chosen on.
S31R, S31M = f"{QE}/s31/results.json", f"{QE}/s31/DEV.md"
s31 = g(S31R); d31 = s31["dev"]; x31 = s31["test"]
assert d31["winner"] is None and x31["run"] is False, (d31["winner"], x31["run"])
assert d31["stage2_all"]["n_items"] == d31["stage2_all"]["n_scored_all"] == N16, d31["stage2_all"]["n_items"]
assert d31["stage1_sub400"]["n_items"] == d31["stage1_sub400"]["n_scored_all"]
assert d31["stage2_rest957"]["n_items"] + d31["stage1_sub400"]["n_items"] == N16
assert d31["calls"]["builds"] == [BUILD], d31["calls"]["builds"]
V31 = {"D4": ("shipped D4: reading 1 with the five nearest APS-labelled examples + reading 2 (other code order) without, chapter read back "
              "from the subtopic", None),
       "V1": ("k10: reading 1 shows the 10 nearest examples (frozen 5 + next 5)", "| V1 | k10 |"),
       "V2": ("subn: reading 1's five examples also name the editors' main subtopic", "| V2 | subn |"),
       "V3": ("ex2: reading 2 (S1 code order) also shows the five examples", "| V3 | ex2 |"),
       "V4": ("third: when readings 1 and 2 disagree, a third reading (five examples, a third code order)", "| V4 | third |"),
       "V5": ("ex2+third: V3, plus V4's third reading when V3's two readings disagree (fixed after V1–V4 were seen on the 400)", "| V5 | ex2+third |")}
STAGE31 = {"stage1_sub400": "stage 1, a fixed random subset of the design set (random.Random(31).sample)",
           "stage2_all": "stage 2, all design-set items", "stage2_rest957": "stage 2, the design-set items stage 1 did not see"}


def s31k(stage, d_, metric):
    """chapter top-1 of one design in eval/s31/results.json: top1 = k1 / n truncated at 4 decimals (asserted); Wilson 95% recomputed
    exactly from k and n, bounds rounded outward at 3 decimals (the stored interval is kept as ci95_source when it differs)."""
    b = g(S31R, "dev", stage, "designs", d_); k, n = b["k1"], g(S31R, "dev", stage, "n_items")
    assert b["top1"] == math.floor(k / n * 10 ** 4) / 10 ** 4 and b["n_missing"] == 0, (stage, d_, b)
    lo_, hi_ = wilson_exact(k, n)
    ci_ = [float(F.q(max(lo_, 0.0), 3, F.ROUND_FLOOR)), float(F.q(min(hi_, 1.0), 3, F.ROUND_CEILING))]
    out = {"metric": metric, "value": b["top1"], "k": k, "n": n, "kn": f"{k}/{n}", "ci95": ci_,
           "ci_method": "Wilson 95% from k and n, bounds rounded outward at 3 decimals (re-checked by build_pruefstand.py)"}
    if list(b["top1_ci"]) != ci_: out["ci95_source"] = list(b["top1_ci"])
    out["at"] = loc(S31R, "dev", stage, "designs", d_, "top1")
    return out


def s31d(stage, d_, metric):
    """paired Δ top-1 design − D4 (mean of per-item differences, stored truncated at 4 decimals; percentile bootstrap 2,000 over items,
    seed 2026, bounds rounded outward at 4 decimals, eval/s31/analyze.py)."""
    b = g(S31R, "dev", stage, "designs", d_, "minus_D4")
    return {"metric": metric, "value": b["diff"], "ci95": list(b["ci"]),
            "ci_method": "paired bootstrap 2,000 over items (percentile, seed 2026), bounds rounded outward at 4 decimals (eval/s31/analyze.py)",
            "n": g(S31R, "dev", stage, "n_items"), "at": loc(S31R, "dev", stage, "designs", d_, "minus_D4", "diff"),
            "ci_at": loc(S31R, "dev", stage, "designs", d_, "minus_D4", "ci")}


st31 = {}
for stage_, lab_ in STAGE31.items():
    n_ = d31[stage_]["n_items"]; cells_ = []
    for d_ in d31[stage_]["designs"]:
        c_ = {"design": d_, "what": V31[d_][0], "top1": s31k(stage_, d_, f"chapter top-1, {d_}, {lab_} (n {n_})"),
              "top3": {"metric": f"chapter top-3, {d_}, {lab_}", "value": g(S31R, "dev", stage_, "designs", d_, "top3"),
                       "at": loc(S31R, "dev", stage_, "designs", d_, "top3")}}
        if d_ != "D4": c_["minus_D4"] = s31d(stage_, d_, f"paired Δ top-1, {d_} − D4, {lab_}")
        if V31[d_][1]: c_["described_at"] = md(S31M, V31[d_][1])
        cells_.append(c_)
    st31[stage_] = {"what": lab_, "n": {"value": n_, "at": loc(S31R, "dev", stage_, "n_items")}, "designs": cells_}
gate31 = g(S31R, "dev", "gate")
assert set(gate31) == {"V1", "V3"} and not any(v_["passes"] for v_ in gate31.values())
GATE31 = 0.02
for d_, v_ in gate31.items():   # the gate as written: Δ ≥ +0.02 and the interval above 0; neither holds for either finalist
    assert not (v_["diff"] >= GATE31 and v_["ci"][0] > 0) and v_["diff"] == g(S31R, "dev", "stage2_all", "designs", d_, "minus_D4", "diff")
m31 = re.search(r"S16 reported (0\.\d+) with the S16 rule.*\((\d+) items differ\)", d31["note"])
assert m31 and float(m31.group(1)) == next(t_ for t_ in tests if t_["id"] == "aps_chapter_shipped_d4")["result"]["value"], d31["note"]
m31b = re.search(r"\((\d+) numbers\).*?: (\d+) match, (\d+) have a production input", x31["fresh_items"]["also"])
assert m31b, x31["fresh_items"]["also"]
best31 = max(gate31, key=lambda d_: gate31[d_]["diff"]); assert best31 == "V3"
tests.append(dict(
    id="aps_design_search_s31", gold="human", subject="Apertus",
    title_de=f"APS-Kapitel, Design-Set ({F.t(N16, sep=chr(39))} Bundesgeschäfte): fünf Varianten gegen D4, keine besser (S31, nur Dev, nicht vorregistriert)",
    title_fr=f"Chapitre APS, jeu de conception ({F.t(N16, sep=' ')} objets fédéraux) : cinq variantes contre D4, aucune meilleure (S31, dev seulement, "
             "non préenregistré)",
    n=N16, design="die S9/S16-Geschäfte (Design-Set, Gold = APS-Redaktion), gleicher Input wie S16; Beispiele leave-one-out (die eingefrorenen "
    "S9-Nachbarn, jedes Geschäft ohne sich selbst); fünf Varianten von D4 (V1 10 Beispiele, V2 Beispiele mit Unterthema, V3 Beispiele in "
    "beiden Code-Reihenfolgen, V4 dritte Lesart bei Uneinigkeit, V5 V3 + V4); Stufe 1 auf 400 zufälligen Geschäften, die zwei besten auf allen; "
    "eine Entscheidregel für alle (compose.chapter_decision auf n Lesarten verallgemeinert); Schwelle vor jedem S31-Aufruf: Δ gegen D4 ≥ +0.02 "
    "auf allen mit 95%-Intervall über 0",
    result=s31d("stage2_all", best31, f"paired Δ chapter top-1, best variant ({best31}: examples in both code orders) − D4, all {N16} design-set items"),
    results_more=[s31d("stage2_all", "V1", f"paired Δ chapter top-1, V1 − D4, all {N16} design-set items"),
                  s31k("stage2_all", best31, f"chapter top-1, {best31}, all {N16} design-set items"),
                  s31d("stage2_rest957", best31, f"paired Δ chapter top-1, {best31} − D4, the {d31['stage2_rest957']['n_items']} items stage 1 did not see")],
    baselines=[dict(s31k("stage2_all", "D4", f"chapter top-1, D4 (shipped), production decision rule, all {N16} design-set items"),
                    name="D4 (shipped), same items, production decision rule (compose.chapter_decision)")],
    breakdowns={**st31,
                "gate": {"rule": "paired Δ top-1 vs D4 on all design-set items ≥ +0.02, with the 95% interval above 0 (fixed before any S31 call)",
                         "threshold": GATE31, "threshold_at": md(S31M, "+0.02 on all 1,357 items"),
                         "finalists": {d_: {"value": v_["diff"], "ci95": list(v_["ci"]), "passes": v_["passes"], "at": loc(S31R, "dev", "gate", d_)}
                                       for d_, v_ in gate31.items()},
                         "winner": None, "at": loc(S31R, "dev", "winner")},
                "decision_rule_note": {"text": d31["note"], "s16_reported": float(m31.group(1)), "items_differ": int(m31.group(2)),
                                       "at": loc(S31R, "dev", "note")},
                "heldout_unspent": {"test_run": False, "reason": x31["reason"], "at": loc(S31R, "test", "reason"),
                                    "what": f"the {N25} S25 held-out affairs were not used by any S31 model call; they stay unspent for a later "
                                            "single pre-registered look at one winner (eval/s31/run.py, not run)"},
                "fresh_items": {"searched": x31["fresh_items"]["searched"],
                                "new_process_ids_with_200_capture": {"value": x31["fresh_items"]["new_process_ids_with_200_capture"],
                                                                     "at": loc(S31R, "test", "fresh_items", "new_process_ids_with_200_capture")},
                                "unjoined_s25_numbers": int(m31b.group(1)), "match_newer_opd": int(m31b.group(2)),
                                "with_production_input": int(m31b.group(3)), "also_at": loc(S31R, "test", "fresh_items", "also"),
                                "files": x31["fresh_items"]["files"]},
                "calls": {"calls": d31["calls"]["calls"], "usd_list_price": d31["calls"]["usd_list_price"], "at": loc(S31R, "dev", "calls")}},
    split="design set (the S9 items D4 was chosen on), leave-one-out examples; dev only: not pre-registered as a test and not held out; "
          "no variant cleared the gate, so no test was run and the S25 held-out items stay unspent",
    prereg=None, not_preregistered="dev only (eval/s31/DEV.md); the gate was written before any S31 call, but no pre-registration entry exists",
    sources=[S31R, S31M, f"{QE}/s31/analyze.py", f"{QE}/s31/dev.py", f"{QE}/s31/dev_raw.jsonl", f"{QE}/s31/ledger.jsonl",
             f"{QE}/s31/cdx_check/", f"{QE}/s31/run.py"],
    build=BUILD, model=MODEL, date="2026-10-15", shipped="no change: D4 stays the federal design (no variant cleared the gate)"))

s18 = g(S18R)
tests.append(dict(
    id="bern_directorates_production", gold="human", subject="Apertus",
    title_de="Bern: federführende Direktion (8) gegen das Feld des Grossen Rats, Geschäfte 2025–26, Produktionslauf",
    title_fr="Berne : direction responsable (8) contre le champ du Grand Conseil, objets 2025–26, production",
    n=s18["n_scored"], design="jedes Grossratsgeschäft ab 1.1.2025 mit Leitdirektion im OPD-Export (role leading_department); "
    "Schema-Datei be-directorates (S6-Prompt, nur Titel, Sprache des Geschäfts), argmax über 8 Direktionen + «keine davon»",
    result=acc(S18R, "lang_de", metric="accuracy, German title"),
    results_more=[acc(S18R, "lang_fr", metric="accuracy, French title"),
                  {"metric": "DE − FR, paired (affairs with both titles)", "value": s18["paired_de_minus_fr"]["diff"],
                   "ci95": s18["paired_de_minus_fr"]["ci"], "n": s18["paired_de_minus_fr"]["n"],
                   "de": s18["paired_de_minus_fr"]["de"], "fr": s18["paired_de_minus_fr"]["fr"], "at": loc(S18R, "paired_de_minus_fr")},
                  acc(S18R, "overall", metric="accuracy, overall (= German titles: every affair has one)")],
    baselines=[{"name": "keyword stems (S6, frozen 13 Oct), German", "value": s18["keyword"]["acc"], "ci95": s18["keyword"]["ci"],
                "at": loc(S18R, "keyword", "acc")},
               {"name": "keyword stems, French", "value": s18["lang_fr"]["keyword"], "at": loc(S18R, "lang_fr", "keyword")},
               {"name": f"majority directorate ({s18['majority']['label']})", "value": s18["majority"]["acc"], "at": loc(S18R, "majority", "acc")}],
    split="every eligible affair 2025–26, pre-registered; nothing tuned", prereg=pre(PB, "— S18 Bern directorates on the production run"),
    sources=[S18R, f"{QE}/s18/analyze.py"], build=s18["build"], model=MODEL, date="2026-10-14"))

s20 = g(S20R)
tests.append(dict(
    id="basel_themes_names", gold="human", subject="Apertus",
    title_de="Basel-Stadt: die 46 eigenen Themen gegen das von Hand gesetzte «Thema 1», alle Grossratsgeschäfte 2019–24 (nur Namen)",
    title_fr="Bâle-Ville : ses 46 thèmes contre le « Thema 1 » attribué à la main, tous les objets du Grand Conseil 2019–24 (noms seuls)",
    n=s20["n"], design="Schema-Datei schemes/bs-themen.yaml: die 46 Themennamen wörtlich, ohne Beschreibungen, nichts abgestimmt; Produktions-Input "
    "(Titel, Langtitel, 1'500 Zeichen Text); zweite Reihenfolge bei p < 0.9",
    result=acc(S20R, "top1", metric="top-1 = Thema 1"),
    results_more=[acc(S20R, "top1_t1_or_t2", metric="top-1 ∈ {Thema 1, Thema 2}"), acc(S20R, "top3", metric="top-3 contains Thema 1"),
                  {"metric": "Δ top-1 − keyword, paired", "value": s20["minus_keyword"]["diff"], "ci95": s20["minus_keyword"]["ci"],
                   "at": loc(S20R, "minus_keyword")}],
    baselines=[dict(acc(S20R, "keyword", metric="keyword"), name="frozen keyword stems (eval/s20/keywords_frozen.json)"),
               {"name": f"majority theme ({s20['majority']['label']})", "value": s20["majority"]["acc"], "at": loc(S20R, "majority", "acc")}],
    breakdowns={"lane_readings_agree": acc(S20R, "lane_readings_agree", metric="precision, readings agree"),
                "lane_please_check": acc(S20R, "lane_please_check", metric="precision, please check"),
                "by_type": {"cells": [{"cell": k, "n": v["n"], "value": v["acc"], "ci95": v["ci"], **({"small": True} if v["n"] < 20 else {})}
                                      for k, v in s20["by_type"].items()], "at": loc(S20R, "by_type")}},
    split="all 2,437 affairs of OGD dataset 100086, pre-registered; nothing tuned", prereg=pre(PB, "— S20 Basel-Stadt topics"),
    sources=[S20R, f"{QE}/s20/analyze.py", f"{QE}/s20/keywords_frozen.json"], build=s20["build"], model=MODEL, date="2026-10-14"))

s21 = g(S21R)
tests.append(dict(
    id="basel_themes_examples", gold="human", subject="Apertus",
    title_de="Basel-Stadt: dieselben 46 Themen mit fünf Basler Beispielen (andere Hälfte), gepaart gegen S20",
    title_fr="Bâle-Ville : les mêmes 46 thèmes avec cinq exemples bâlois (autre moitié), apparié à S20",
    n=s21["n"], design="zwei Hälften nach OPD-ID-Parität; je fünf ähnlichste Geschäfte der anderen Hälfte (BM25, S9-D3-Abruf) mit ihrem «Thema 1» "
    "als Beispiele; Lesart mit Beispielen + permutierte S20-Lesart ohne, Mittel (D4-Form); kein Training",
    result=acc(S21R, "s21_top1", metric="top-1 = Thema 1"),
    results_more=[{"metric": "paired Δ top-1 vs S20 (same items)", "value": s21["diff_vs_s20"]["diff"], "ci95": s21["diff_vs_s20"]["ci"],
                   "method": "paired bootstrap 2,000", "at": loc(S21R, "diff_vs_s20")},
                  {"metric": "top-1 ∈ {Thema 1, Thema 2}", "value": s21["s21_t1_or_t2"], "at": loc(S21R, "s21_t1_or_t2")},
                  {"metric": "top-3 contains Thema 1", "value": s21["s21_top3"], "at": loc(S21R, "s21_top3")}],
    baselines=[{"name": "S20 names only, same items", "value": s21["s20_top1_same_items"], "at": loc(S21R, "s20_top1_same_items")}],
    breakdowns={"lane_agree": acc(S21R, "lane_agree", metric="precision, readings agree"),
                "lane_disagree": acc(S21R, "lane_disagree", metric="precision, readings disagree (please check)")},
    split="2 folds by affair-id parity (examples always from the other fold), pre-registered",
    prereg=pre(PB, "— S21 Basel-Stadt with the canton's own labels"),
    sources=[S21R, f"{QE}/s21/analyze.py", f"{QE}/s21/raw.jsonl"], build=s21["builds"][0], model=MODEL, date="2026-10-14"))

# ---------------------------------------------------------------- S29: Ticino Gran Consiglio, the canton's own lead department, Italian
S29R, S29S = f"{QE}/s29/results.json", f"{QE}/s29/SOURCES.md"
s29 = g(S29R)
assert s29["test"] == "S29" and s29["build"] == BUILD and s29["missing"] == 0 and s29["other_build"] == 0, s29["build"]
assert s29["n_scored"] == s29["n_items"] and s29["primary"]["n"] == s29["n_primary_items"], (s29["n_scored"], s29["n_items"])
N29, N29A = s29["n_primary_items"], s29["n_items"]
N29X = N29A - N29   # inputs that name one of the six units (mostly Messaggi, whose header prints the competent department)
TI_NONE = "Nessuno di questi (Consiglio di Stato nel suo insieme o Gran Consiglio stesso)"


def s29k(*keys, metric):
    """a {k, n, acc, ci} block of eval/s29/results.json: acc = k / n truncated at 4 decimals and ci = Wilson 95% rounded outward at 4
    decimals (eval/s29/analyze.py), both re-checked here from k and n; the interval is re-rounded outward at 3 decimals."""
    b = g(S29R, *keys); k, n = b["k"], b["n"]
    assert b["acc"] == math.floor(k / n * 10 ** 4) / 10 ** 4, (keys, b)
    lo_, hi_ = wilson_exact(k, n)
    assert list(b["ci"]) == [float(F.q(max(lo_, 0.0), 4, F.ROUND_FLOOR)), float(F.q(min(hi_, 1.0), 4, F.ROUND_CEILING))], (keys, b, lo_, hi_)
    out = {"metric": metric, "value": b["acc"], "ci95": [float(F.q(max(lo_, 0.0), 3, F.ROUND_FLOOR)), float(F.q(min(hi_, 1.0), 3, F.ROUND_CEILING))],
           "ci95_source": list(b["ci"]), "k": k, "n": n, "kn": f"{k}/{n}",
           "ci_method": "Wilson 95% from k and n, bounds rounded outward at 3 decimals (eval/s29/analyze.py stores them outward at 4; "
                        "re-checked by build_pruefstand.py)"}
    if "share" in b: out["share"] = b["share"]
    if "label" in b: out["label"] = b["label"]
    out["at"] = loc(S29R, *keys)
    return out


def s29d(*keys, metric):
    b = g(S29R, *keys)
    assert b["ci"][0] <= b["diff"] <= b["ci"][1], (keys, b)
    return {"metric": metric, "value": b["diff"], "ci95": list(b["ci"]),
            "method": "paired bootstrap 2,000, percentile, random.Random(2026), bounds rounded outward (eval/s29/analyze.py)",
            "value_note": "the file stores the difference truncated at 4 decimals; shown truncated at 3", "at": loc(S29R, *keys)}


def s29set(sub, label):
    """the full block of one population of eval/s29/results.json (primary, secondary_all_items, secondary_gold_in_5_departments)."""
    d_ = g(S29R, sub); n_ = d_["n"]
    assert sum(d_["gold_dist"].values()) == n_ == sum(d_["pred_dist"].values()), (sub, n_)
    assert d_["lane_readings_agree"]["n"] + d_["lane_please_check"]["n"] == n_, sub
    o = {"n": n_, "label": label,
         "top1": s29k(sub, "top1", metric=f"top-1 = lead department ({label})"),
         "top2": s29k(sub, "top2", metric=f"top-2 contains the lead department ({label})"),
         "top3": s29k(sub, "top3", metric=f"top-3 contains the lead department ({label})"),
         "keyword": s29k(sub, "keyword", metric=f"frozen keyword stems, title only ({label})"),
         "majority": s29k(sub, "majority", metric=f"majority lead department ({label})"),
         "minus_keyword": s29d(sub, "minus_keyword", metric=f"paired Δ top-1 Apertus − keyword ({label})"),
         "lane_readings_agree": s29k(sub, "lane_readings_agree", metric=f"precision, the two code orders agree ({label})"),
         "lane_please_check": s29k(sub, "lane_please_check", metric=f"precision, the orders disagree → please check ({label})"),
         "by_type": {"cells": [dict(s29k(sub, "by_type", k_, metric=f"top-1, affair type {k_} ({label})"), cell=k_,
                                    **({"small": True} if v_["n"] < 20 else {})) for k_, v_ in d_["by_type"].items()],
                     "at": loc(S29R, sub, "by_type")},
         "by_gold": {"cells": [dict(s29k(sub, "by_gold", k_, metric=f"recall of the lead department {k_} ({label})"), cell=k_,
                                    **({"small": True} if v_["n"] < 20 else {})) for k_, v_ in d_["by_gold"].items()],
                     "at": loc(S29R, sub, "by_gold")},
         "gold_dist": dict(d_["gold_dist"], at=loc(S29R, sub, "gold_dist")), "pred_dist": dict(d_["pred_dist"], at=loc(S29R, sub, "pred_dist"))}
    if "confusion_gold_to_pred" in d_:
        o["confusion_gold_to_pred"] = dict(d_["confusion_gold_to_pred"], at=loc(S29R, sub, "confusion_gold_to_pred"))
    return o


p29 = s29set("primary", f"primary, the {N29:,} inputs that name no unit")
a29 = s29set("secondary_all_items", f"secondary, all {N29A:,} inputs as fed")
f29 = s29set("secondary_gold_in_5_departments", "secondary, gold one of the 5 Dipartimenti")
assert len(p29["gold_dist"]) - 1 == g(S29R, "options") == 7 and TI_NONE in p29["gold_dist"], p29["gold_dist"]
tests.append(dict(
    id="ticino_departments", gold="human", subject="Apertus",
    title_de=f"Tessin: federführende Stelle (5 Departemente + Staatskanzlei, «keine davon») gegen das OPD-Feld leading_department, "
             f"Gran Consiglio 2023–26, italienisch, {F.t(N29, sep=chr(39))} Geschäfte, deren Input die Stelle nicht nennt (S29)",
    title_fr=f"Tessin : unité compétente (5 départements + Chancellerie, « aucune ») contre le champ OPD leading_department, Gran Consiglio "
             f"2023–26, en italien, {F.t(N29, sep=' ')} objets dont l'entrée ne nomme pas l'unité (S29)",
    n=N29, design="Schema-Datei schemes/ti-dipartimenti.yaml: die 6 Namen wörtlich auf Italienisch (5 Dipartimenti, Cancelleria dello Stato), "
    "alphabetisch, Codes A–F, dazu G = «Nessuno di questi (Consiglio di Stato nel suo insieme o Gran Consiglio stesso)»; keine "
    "Beschreibungen, nichts abgestimmt; Rahmen italienisch, nur die drei festen Blockbezeichnungen im Code bleiben deutsch («Geschäft:», "
    "«Titel:», «Text (Auszug):»); Produktions-Input (Titel, Langtitel, 1'500 Zeichen Text); zweite Reihenfolge bei p < 0.9, Entscheid = "
    "Spitze des Mittels; Gold = erste federführende Stelle im OPD-Export (contributors, role leading_department), «Consiglio di Stato» und "
    "«Gran Consiglio» → keine davon",
    result=dict(p29["top1"], display=f"{F.t(p29['top1']['value'])} [{F.lo(p29['top1']['ci95'][0])}, {F.hi(p29['top1']['ci95'][1])}]"),
    results_more=[p29["top2"], p29["top3"], p29["minus_keyword"], a29["top1"], a29["top2"], a29["top3"], f29["top1"]],
    baselines=[dict(p29["keyword"], name="frozen keyword stems, title only (eval/s29/keywords_frozen.json), same items"),
               dict(p29["majority"], name=f"majority lead department ({p29['majority']['label']})")],
    breakdowns={
        "lane_readings_agree": p29["lane_readings_agree"], "lane_please_check": p29["lane_please_check"],
        "by_type": p29["by_type"], "by_gold": p29["by_gold"], "gold_dist": p29["gold_dist"], "pred_dist": p29["pred_dist"],
        "confusion_gold_to_pred": p29["confusion_gold_to_pred"],
        "excluded_from_primary": {"value": N29X, "of": N29A, "derived": "n_items − n_primary_items (eval/s29/results.json)",
                                  "why": "the input names one of the six units: a Messaggio's header prints the competent department "
                                         "(«competenza»); measured on the inputs before any call",
                                  "messaggi": {"value": 487, "of": 512, "at": md(S29S, "589 of 2,274 inputs name one of the six units (487 of 512 Messaggi)")},
                                  "at": md(S29S, "589 of 2,274 inputs name one of the six units")},
        "secondary_all_items": a29, "secondary_gold_in_5_departments": f29,
        "second_order_share": {"value": g(S29R, "second_order_share"), "note": "share of the primary items that asked the second code order "
                               "(first top p < 0.9)", "at": loc(S29R, "second_order_share")},
        "beside": "S18 (Bern) and S20 (Basel-Stadt) are reported beside this result, not compared with it: schemes and chance rates differ"},
    split=f"every Gran Consiglio affair begun 1 Jan 2023–11 Oct 2026 with a lead department in OPD ({N29A:,}); primary = the {N29:,} whose "
          f"input names none of the six units ({N29X} inputs name one, mostly Messaggi, which print the competent department); "
          "pre-registered (S29); nothing tuned",
    prereg=pre(PB, "— S29 Ticino Gran Consiglio own scheme in Italian"),
    sources=[S29R, f"{QE}/s29/analyze.py", f"{QE}/s29/items.py", f"{QE}/s29/keywords_frozen.json", S29S,
             "src/querschnitt/schemes/ti-dipartimenti.yaml", PB],
    build=s29["build"] + " (run runs/s29)", model=s29["model"], date="2026-10-15"))
assert MODEL == s29["model"]

# ---------------------------------------------------------------- S32: neutrality of the shipped federal design (re-analysis, not pre-registered)
S32R, S32M = f"{QE}/s32/results.json", f"{QE}/s32/README.md"
s32 = g(S32R)
assert s32["test"] == "S32" and s32["prereg"] is None and s32["checks"]["s9_submitter_cells_equal_s14"], s32["checks"]
assert s32["checks"]["s25_top1"] == [t25["k"], t25["n"]] and s32["checks"]["s16_d4_top1"] == [d4["k"], N16], s32["checks"]
SM32 = s32["small_threshold"]


def s32gap(*keys, metric):
    b = g(S32R, *keys)
    assert b["ci"][0] <= b["diff"] <= b["ci"][1] and round(b["diff"], 4) == b["diff"], (keys, b)
    return {"metric": metric, "hi": b["hi"], "lo": b["lo"], "value": b["diff"], "diff": b["diff"], "ci95": list(b["ci"]),
            "ci95_raw": list(b["ci_raw"]), "basis": b["basis"],
            "ci_method": b["ci_method"] + " (eval/s32/analyze.py)", "at": loc(S32R, *keys)}


def s32cells(st, dim, m, label):
    """one S32 breakdown (cells k/n via knblock, test, largest gap) in the cells() layout the renderer's cell_table reads."""
    d_ = g(S32R, st, dim, m)
    cl = []
    for i_, c_ in enumerate(d_["cells"]):
        b_ = knblock(S32R, st, dim, m, "cells", i_, metric=f"{label}: {dim} {c_['cell']}", script="eval/s32/analyze.py")
        b_ = dict(b_, cell=c_["cell"])
        if c_["n"] < SM32: b_["small"] = True
        assert bool(c_.get("small")) == bool(b_.get("small")), (st, dim, m, c_)
        cl.append(b_)
    o = {"cells": cl, "overall": knblock(S32R, st, dim, m, "overall", metric=f"{label}: all", script="eval/s32/analyze.py"),
         "at": loc(S32R, st, dim, m)}
    t_ = d_.get("test")
    o["test"] = ({"p_perm": t_["p_perm"], "p_chi2": t_["p_chi2"], "df": t_["df"], "cells_tested": t_["cells_tested"],
                  "method": f"permutation 5,000 (seed 14) of Pearson's χ² across the tested cells (S14's perm_test)",
                  "at": loc(S32R, st, dim, m, "test")} if t_ else None)
    if d_.get("not_informative"): o["not_informative"] = {"what": d_["not_informative"], "at": loc(S32R, st, dim, m, "not_informative")}
    o["largest_gap"] = s32gap(st, dim, m, "gap", metric=f"{label}: largest {dim} gap, cells n ≥ {SM32}") if d_.get("gap") else None
    if d_.get("gap_all_tested_cells"):
        o["largest_gap_all_tested"] = s32gap(st, dim, m, "gap_all_tested_cells", metric=f"{label}: largest {dim} gap, every tested cell")
    return o


L32 = {"s9_prod": f"S9 prod, production rows ({s32['s9_prod']['n']:,} scored)", "s25": f"S25 held out ({s32['s25']['n']} affairs)",
       "pooled": f"S9 prod + S25 pooled ({s32['pooled']['n']:,})"}
bd32 = {}
for st_ in ("s9_prod", "s25"):
    for dim_, k_ in (("party", "party"), ("submitter kind", "submitter_kind"), ("instrument", "instrument"), ("language of the text", "language")):
        for m_, mk_ in (("top1", "top1"), ("kw", "keyword_top1")):
            bd32[f"{st_}_{k_}_{mk_}"] = s32cells(st_, dim_, m_, L32[st_] + (" keyword" if m_ == "kw" else ""))
    bd32[f"{st_}_party_top3"] = s32cells(st_, "party", "top3", L32[st_] + " top-3")
    at_ = g(S32R, st_, "party", "top1_all_categories_test")
    bd32[f"{st_}_all_submitter_categories_test"] = {"p_perm": at_["p_perm"], "p_chi2": at_["p_chi2"], "df": at_["df"],
                                                    "cells": len(at_["cells_tested"]), "at": loc(S32R, st_, "party", "top1_all_categories_test")}
for dim_, k_ in (("party", "party"), ("submitter kind", "submitter_kind"), ("instrument", "instrument")):
    d_ = g(S32R, "pooled", dim_)
    cl_ = [dict(knblock(S32R, "pooled", dim_, "cells", i_, metric=f"{L32['pooled']}: {dim_} {c_['cell']}", script="eval/s32/analyze.py"),
                cell=c_["cell"], **({"small": True} if c_["n"] < SM32 else {})) for i_, c_ in enumerate(d_["cells"])]
    bd32[f"pooled_{k_}_top1"] = {"cells": cl_, "overall": knblock(S32R, "pooled", dim_, "overall", metric=f"{L32['pooled']}: all", script="eval/s32/analyze.py"),
                                 "test": {"p_perm": d_["test"]["p_perm"], "p_chi2": d_["test"]["p_chi2"], "df": d_["test"]["df"],
                                          "cells_tested": d_["test"]["cells_tested"], "note": d_["test"]["p_chi2_note"],
                                          "at": loc(S32R, "pooled", dim_, "test")},
                                 "largest_gap": s32gap("pooled", dim_, "gap", metric=f"{L32['pooled']}: largest {dim_} gap, cells n ≥ {SM32}"),
                                 "at": loc(S32R, "pooled", dim_)}
for dim_, k_ in (("party", "party"), ("submitter kind", "submitter_kind"), ("instrument", "instrument")):
    d_ = g(S32R, "s16_d4_secondary", dim_, "top1")
    bd32[f"s16_d4_{k_}_top1"] = {"p_perm": d_["test"]["p_perm"], "p_chi2": d_["test"]["p_chi2"], "df": d_["test"]["df"],
                                 "largest_gap": s32gap("s16_d4_secondary", dim_, "top1", "gap", metric=f"S16 D4 (S9 input): largest {dim_} gap"),
                                 "at": loc(S32R, "s16_d4_secondary", dim_, "top1", "test")}
ns32 = g(S32R, "s9_prod", "not_scored")
bd32["s9_prod_not_scored"] = {"value": ns32["n"], "by_party": ns32["by_party"], "why": ns32["why"], "at": loc(S32R, "s9_prod", "not_scored", "n")}
p32 = bd32["s9_prod_party_top1"]; q32 = bd32["s25_party_top1"]; o32 = bd32["pooled_party_top1"]
tests.append(dict(
    id="neutrality_shipped_s32", gold="human", subject="Apertus",
    title_de="Neutralität des ausgelieferten Bundes-Designs (S32, APS-Redaktion): Partei, Einreichende, Instrument, Sprache — "
             "Produktionszeilen der S9-Geschäfte und die S25-Hold-out-Geschäfte (Neuauswertung, nicht vorregistriert)",
    title_fr="Neutralité du design fédéral livré (S32, rédaction APS) : parti, auteur, instrument, langue — lignes de production des objets "
             "S9 et objets hors échantillon S25 (réanalyse, non préenregistrée)",
    n=p32["overall"]["n"] + q32["overall"]["n"],
    design=f"keine neuen Aufrufe; S9 prod = die Produktionszeilen (eval/prod_gold, wie make eval: {p32['overall']['kn']}), S25 = "
           f"eval/s25/decisions.jsonl ({q32['overall']['kn']}); Partei, Einreichende und Instrument mit S14s eigenen Funktionen (s14lib.py) "
           "auf dem OPD-Export der Produktion (16.10.2026; S9-Zellen identisch mit S14); Sprache = text_lang des Produktions-Inputs; "
           f"Zellen n < {SM32} klein; Permutationstest 5'000 über die sechs Hauptparteien; grösste Lücke mit Bootstrap (2'000)",
    result=dict(p32["test"], metric="S9 prod: party test over the six main parties, permutation p", value=p32["test"]["p_perm"]),
    results_more=[dict(q32["test"], metric="S25 held out: party test over the six main parties, permutation p", value=q32["test"]["p_perm"]),
                  dict(o32["test"], metric="pooled: party test (permutation within set)", value=o32["test"]["p_perm"]),
                  p32["largest_gap"], q32["largest_gap"], o32["largest_gap"]],
    baselines=[{"name": "S14 on the earlier D1 design, same 1,357 S9 affairs (neutrality_s9)",
                "p_perm": g(S14, "S9", "party", "D1_top1", "test", "p_perm"), "at": loc(S14, "S9", "party", "D1_top1", "test", "p_perm")},
               {"name": "keyword top-1 per cell (in breakdowns)"}],
    breakdowns=bd32, small_threshold=SM32,
    split="re-analysis of existing measurements (S9 production rows, S25 held-out decisions, S16 raw); no new calls; not pre-registered "
          "(written after review round 8, J2 change 2)",
    prereg=None, not_preregistered="a re-analysis of existing measurements; nothing was tuned, no call was made",
    language_note="both sets are German: S9 prod 1,340/1,340 inputs, S25 926 of 927; the shipped federal design reads the German input, so "
                  "neither set measures a language effect (cells in breakdowns, no test)",
    sources=[S32R, S32M, f"{QE}/s32/analyze.py", "eval/prod_gold/topics.jsonl.gz", "eval/prod_gold/inputs.jsonl.gz", "eval/s25/decisions.jsonl",
             f"{I2}/s14-neutrality/scripts/s14lib.py", "data/eval/gold_aps_s9.csv"],
    build="no calls (rows: " + BUILD + ")", model=MODEL, date=s32["generated_utc"][:10]))

s17 = g(S17R)
tests.append(dict(
    id="aps_communal_production", gold="ai-judge", subject="Apertus",
    title_de="APS-Kapitel, Gemeindeparlamente 2026: ausgeliefertes Kapitel des Produktionslaufs gegen den KI-Richter",
    title_fr="Chapitre APS, parlements communaux 2026 : chapitre livré par la production contre le juge IA",
    n=s17["n"], design="200 kommunale Geschäfte 1.1.–11.10.2026, zufällig (Seed 20261017) unter denen mit ausgeliefertem Kapitel, ohne S6-Stichprobe; "
    "ausgeliefertes Kapitel = aus dem Unterthema zurückgelesen, ohne Beispiele; Richter: zwei blinde Claude-Läufe (S6-Leitfaden) + "
    "Stichentscheid bei Uneinigkeit",
    result=acc(S17R, "top1", metric="shipped chapter = consensus gold"),
    results_more=[acc(S17R, "top3", metric="gold in the top 3")],
    baselines=[dict(acc(S17R, "keyword", metric="keyword"), name="frozen S9 keyword baseline (APS subtopic words)"),
               {"name": f"majority chapter of the sample's gold ({s17['majority']['label']}, computed after)", "value": s17["majority"]["acc"],
                "at": loc(S17R, "majority", "acc")}],
    judge={"kappa_AB": s17["kappa_AB"], "agree_AB": s17["agree_AB"], "disagreements": s17["disagreements"], "tie_break_C": s17["C"],
           "at": loc(S17R, "kappa_AB")},
    breakdowns={k: acc(S17R, k, metric=m) for k, m in (("lang_de", "German"), ("lang_fr", "French"), ("lang_it", "Italian"),
                                                         ("lane_readings_agree", "lane: readings agree"), ("lane_please_check", "lane: please check"),
                                                         ("with_text", "with text"), ("title_only", "title only"))},
    split="random sample of the production run, pre-registered", prereg=pre(PB, "— S17 communal slice on the production run"),
    sources=[S17R, f"{QE}/s17/analyze.py", f"{QE}/s17/key.jsonl", f"{QE}/s17/ann_A.tsv", f"{QE}/s17/ann_B.tsv", f"{QE}/s17/ann_C.tsv"],
    build=BUILD + " (production run runs/main)", model=MODEL, judge_build="Claude (blind agent runs)", date="2026-10-14"))

s8f = g(S8F)
gp, gc = s8f["gold_AB_C"]["point"], s8f["gold_AB_C"]["ci"]
mp, mc = s8f["gold_majority_ABQ"]["point"], s8f["gold_majority_ABQ"]["ci"]
fs, fa = s8f["flags_swiss"], s8f["flags_all"]
tests.append(dict(
    id="dvs_2026_census", gold="ai-judge", subject="Apertus",
    title_de="«Digitalisierung» in Schweizer Parlamenten 2026, volle Erhebung, gegen den KI-Richter",
    title_fr="« Numérique » dans les parlements suisses en 2026, recensement complet, contre le juge IA",
    n=fs["n"], n_checked=sum(s8f["packet"].values()),
    design="jedes Schweizer Geschäft 1.1.–6.10.2026 mit Titel (S8-Fenster) entschieden: S8-Zeilen, sonst die Zeile des Produktionslaufs (gleicher "
    "Prompt, gleicher Build); Flags gezählt, nicht geschätzt; Präzision/Recall gegen denselben blinden Richter auf demselben S8-Paket "
    "(453 Schweizer Geschäfte), Gewichte je Schicht auf die Erhebung nachstratifiziert; Bootstrap in Schichten (2'000)",
    result={"metric": "precision vs the judge (Swiss)", "value": gp["a_P"], "ci95": gc["a_P"], "at": loc(S8F, "gold_AB_C", "point", "a_P"),
            "ci_at": loc(S8F, "gold_AB_C", "ci", "a_P")},
    results_more=[{"metric": "recall vs the judge (Swiss)", "value": gp["a_R"], "ci95": gc["a_R"], "at": loc(S8F, "gold_AB_C", "point", "a_R")},
                  {"metric": "Δ precision Apertus − keyword", "value": round(gp["a_P"] - gp["k_P"], 3), "derived": "difference of the two stored points",
                   "ci95": gc["dP"], "at": loc(S8F, "gold_AB_C", "ci", "dP")},
                  {"metric": "Δ recall Apertus − keyword", "value": round(gp["a_R"] - gp["k_R"], 3), "derived": "difference of the two stored points",
                   "ci95": gc["dR"], "at": loc(S8F, "gold_AB_C", "ci", "dR")},
                  {"metric": "affairs flagged (counted, Swiss)", "value": fs["apertus"], "at": loc(S8F, "flags_swiss", "apertus")},
                  {"metric": "estimated digitalisation affairs (judge positives, Swiss)", "value": gp["pos"], "ci95": gc["pos"],
                   "at": loc(S8F, "gold_AB_C", "point", "pos")},
                  {"metric": "gold = majority of Claude A, B, Qwen: precision / recall", "value": [mp["a_P"], mp["a_R"]],
                   "ci95": [mc["a_P"], mc["a_R"]], "at": loc(S8F, "gold_majority_ABQ")},
                  {"metric": "parliaments with at least one flag (Swiss)", "value": fs["parliaments_flagged"], "at": loc(S8F, "flags_swiss", "parliaments_flagged")},
                  {"metric": "flags in the please-check lane (Swiss)", "value": fs["please_check"], "at": loc(S8F, "flags_swiss", "please_check")}],
    baselines=[{"name": "keyword list (29 de/fr/it stems), same input", "precision": gp["k_P"], "precision_ci95": gc["k_P"],
                "recall": gp["k_R"], "recall_ci95": gc["k_R"], "flags": fs["keyword"], "both": fs["both"],
                "majority_gold": [mp["k_P"], mp["k_R"]], "majority_gold_ci95": [mc["k_P"], mc["k_R"]], "at": loc(S8F, "gold_AB_C", "point", "k_P")}],
    breakdowns={"flags_all_bodies_incl_LIE": dict(fa, at=loc(S8F, "flags_all")),
                "census": {"window": s8f["window"], "decided": s8f["decided"], "missing": s8f["missing"], "from_s8_rows": s8f["sources"]["s8"],
                           "from_production_run": s8f["sources"]["run"], "at": loc(S8F, "sources")},
                "packet_strata": dict(s8f["packet"], at=loc(S8F, "packet")),
                "census_strata_swiss": dict(s8f["census_strata_swiss"], at=loc(S8F, "census_strata_swiss")),
                "see_also": "language/level/party/canton cells and per-body flags: dvs_2026 (S8 snapshot, S14)"},
    supersedes={"id": "dvs_2026", "what": "counts and judge precision/recall of the S8 snapshot (8,139 of the window scored, flags estimated)"},
    split="pre-registered S8 design and gold, recomputed on the full census (no new prereg entry; cut-off p ≥ 0.5 unchanged)",
    prereg=pre(PRE, "## S8 — \"Digitalisierung\" over every affair of 2026"),
    sources=[S8F, f"{QE}/s8full/analyze.py", S8M, f"{I2}/s8-dvs/key.jsonl"], build=s8f["build"], model=MODEL,
    judge_build="Claude (blind agent runs); Qwen-SEA-LION aisingapore/Qwen-SEA-LION-v4-32B-IT", date="2026-10-14"))


# ---------------------------------------------------------------- S22 (Italian vs German, human gold) and S23 (evidence on production rows)
def exact_share(stored, n):
    """S22 stores shares rounded to 4 (or fewer) decimals. Recover the count k (the only integer with k/n within half a unit of the
    stored digits) and return (k, k/n): the exact share is what gets displayed (truncated), so a 0.70296 stored as 0.703 never
    shows as 0.703."""
    tol = 0.5 * 10 ** -max(_dec(stored), 1) + 1e-12
    ks = [k for k in range(n + 1) if abs(k / n - stored) <= tol]
    assert len(ks) == 1, (stored, n, ks)
    return ks[0], ks[0] / n


def exact_diff(stored, n):
    """paired differences / bootstrap percentiles of 0/1 outcomes are multiples of 1/n; recover them exactly."""
    j = round(stored * n)
    assert abs(j / n - stored) <= 0.5e-4 + 1e-12 and abs((j + 1) / n - stored) > 0.5e-4 and abs((j - 1) / n - stored) > 0.5e-4, (stored, n)
    return j / n


def _dec(x):
    s_ = repr(float(x)); return len(s_.split(".")[1]) if "." in s_ else 0


S22R, S23R = f"{QE}/s22/results.json", f"{QE}/s23/results.json"
s22 = g(S22R); N22 = s22["n"]
EXN = "value = k / n, k recovered from the stored share × n (unique); the stored rounding is kept as value_source"


def s22share(*keys, metric, n=None, ci=None):
    n = n or N22; stored = g(S22R, *keys)
    k, v = exact_share(stored, n)
    out = {"metric": metric, "value": v, "value_source": stored, "k": k, "n": n, "derived": EXN}
    if ci is not None: out["ci95"] = list(ci)
    out["at"] = loc(S22R, *keys)
    return out


dmi = s22["de_minus_it"]
tests.append(dict(
    id="aps_italian_vs_german", gold="human", subject="Apertus",
    title_de="Sprache, Bund (APS-Redaktion): Italienisch gegen Deutsch auf denselben S9-Geschäften (S22)",
    title_fr="Langue, Confédération (rédaction APS) : italien contre allemand sur les mêmes objets S9 (S22)",
    n=N22, design="die S9-Bundesgeschäfte, deren italienischer OPD-Titel vom französischen abweicht (1'350 von 1'357); Gold = APS-Kapitel der Redaktion; "
    "IT-Titel + IT-Langtitel + italienischer eingereichter Text (erste 1'500 Zeichen, wo er vom französischen abweicht, sonst nur Titel); "
    "D1 im italienischen Rahmen (Kapitelnamen italienisch, Unterthemen deutsch wie publiziert), beide Code-Reihenfolgen; "
    "gepaart gegen S9 D1 Deutsch auf denselben Geschäften",
    result=s22share("it_top1", "acc", metric="chapter top-1, Italian input (D1, Italian frame)", ci=s22["it_top1"]["ci"]),
    results_more=[{"metric": "paired Δ top-1 German − Italian (same items)", "value": exact_diff(dmi["diff"], N22), "value_source": dmi["diff"],
                   "ci95": [exact_diff(dmi["ci"][0], N22), exact_diff(dmi["ci"][1], N22)], "ci95_source": list(dmi["ci"]),
                   "method": "paired bootstrap 2,000, percentile (random.Random(2026))", "display_decimals": 4,
                   "derived": "difference and percentiles are multiples of 1/n; recovered exactly from the stored 4-decimal values",
                   "at": loc(S22R, "de_minus_it")},
                  s22share("it_top3", metric="chapter top-3, Italian"),
                  s22share("de_top3", metric="chapter top-3, German (S9 D1, same items)"),
                  dict(s22share("it_with_text", "acc", metric="top-1, Italian with submitted text", n=g(S22R, "it_with_text", "n")),
                       german_same_items=s22share("it_with_text", "de_same_items", metric="German, same items", n=g(S22R, "it_with_text", "n"))),
                  dict(s22share("it_title_only", "acc", metric="top-1, Italian title only", n=g(S22R, "it_title_only", "n")),
                       german_same_items=s22share("it_title_only", "de_same_items", metric="German, same items", n=g(S22R, "it_title_only", "n")))],
    baselines=[dict(s22share("de_top1", "acc", metric="chapter top-1, German", ci=s22["de_top1"]["ci"]),
                    name="German input, S9 D1 on the same items")],
    split="held-out S9 items, pre-registered; nothing tuned", prereg=pre(PB, "— S22 Italian on human labels"),
    sources=[S22R, f"{QE}/s22/analyze.py", f"{QE}/s22/raw.jsonl", S9R], build=s22["builds"][0], model=MODEL, date="2026-10-14"))

s23 = g(S23R)
P23 = lambda *keys, metric: dict(prop(S23R, *keys, value="rate", ci="ci95"), metric=metric)
tests.append(dict(
    id="evidence_support_production", gold="ai-judge", subject="Apertus",
    title_de="Beleg auf Produktionszeilen 2026: der gespeicherte Satz stützt das Thema (Produktionsprüfung, blinder KI-Richter)",
    title_fr="Preuve sur les lignes de production 2026 : la phrase enregistrée soutient le thème (contrôle de production, juge IA à l'aveugle)",
    n=s23["n_packet"], production_check=True,
    design="200 Belegzeilen des Korpuslaufs (runs/ev, runs/main), zufällig (random.Random(20261023)) unter Geschäften 2026 mit gespeichertem Zitat: "
    "100 Kapitel-Zitate (ausgeliefertes APS-Kapitel), 100 «Digitalisierung»-Zitate (markiert oder bitte prüfen); Paket wie das Modell es sah; "
    "Richter: zwei blinde Claude-Läufe (Y/N) + Stichentscheid; Code prüft die Teilzeichenkette an den gespeicherten Offsets",
    result=P23("support", "overall", metric="stored sentence supports the topic (both kinds)"),
    results_more=[P23("support", "chapter", metric="chapter quotes (shipped APS chapter)"),
                  P23("support", "digitalisierung", metric="«Digitalisierung» quotes"),
                  P23("substring", "input_unchanged", metric="quote is the exact substring at its stored offsets (inputs unchanged since the row)"),
                  P23("substring", "all_rows", metric="quote is the exact substring at its stored offsets (all rows)"),
                  dict(P23("ab_agreement", metric="judge run A = run B"), kappa=g(S23R, "ab_kappa"))],
    baselines=[{"name": "S12 spike (120 federal affairs, D1 chapter, German), descriptive comparison only, no test",
                "value": g(S23R, "s12_descriptive", "rate"), "n": g(S23R, "s12_descriptive", "n"), "at": loc(S23R, "s12_descriptive", "rate")}],
    judge={"kappa_AB": s23["ab_kappa"], "disagreements": s23["n_disagree"], "tie_broken_C": s23["n_tiebroken"], "unresolved": len(s23["unresolved"]),
           "rule": s23["tie_break_rule"], "at": loc(S23R, "ab_kappa")},
    breakdowns={"by_field": {"cells": [dict(prop(S23R, "by_field", f_, value="rate", ci="ci95"), cell=f_) for f_ in s23["by_field"]],
                             "at": loc(S23R, "by_field")},
                "by_level": {"cells": [dict(prop(S23R, "by_level", l_, value="rate", ci="ci95"), cell=l_,
                                            **({"small": True} if s23["by_level"][l_]["n"] < 20 else {})) for l_ in s23["by_level"]],
                             "at": loc(S23R, "by_level")},
                "per_annotator": {nm: [dict(prop(S23R, "per_annotator", nm, k_, value="rate", ci="ci95"), cell=k_)
                                       for k_ in ("overall", "chapter", "digitalisierung")] for nm in ("A", "B")},
                "input_changed_since_row": {"value": s23["substring"]["input_changed_since_row"], "at": loc(S23R, "substring", "input_changed_since_row")}},
    split="random sample of the production rows, pre-registered (drawn after the prereg entry)", prereg=pre(PB, "— S23 evidence on production rows"),
    sources=[S23R, f"{QE}/s23/analyze.py", f"{QE}/s23/build_packet.py", f"{QE}/s23/key.jsonl", f"{QE}/s23/ann_A.tsv", f"{QE}/s23/ann_B.tsv",
             f"{QE}/s23/ann_C.tsv"], build=s23["fingerprints"][0] + " (production run runs/ev, runs/main)", model=MODEL,
    judge_build="Claude (blind agent runs)", date="2026-10-14"))


# ---------------------------------------------------------------- S19 / S26 / S27: three new topics defined in one sentence, against the blind AI judge
S19R, S26R, S27R = f"{QE}/s19/results.json", f"{QE}/s26/results.json", f"{QE}/s27/results.json"
TOPICS19 = ("wolf", "hitze", "ki-schule")
TNAME = {"wolf": ("Wolf und Grossraubtiere", "loup et grands prédateurs", "wolf and large predators"),
         "hitze": ("Hitzeschutz / Hitzewellen", "protection contre la chaleur / canicules", "heat protection / heatwaves"),
         "ki-schule": ("Künstliche Intelligenz an Schulen", "intelligence artificielle à l'école", "AI in schools")}
AJ = "agreement with the AI judge"
BOOT_S = "stratified bootstrap 2,000 (percentile), bounds rounded outward in analyze.py"
BOOT_P = "paired bootstrap 2,000 (percentile), bounds rounded outward in analyze.py"
s19 = g(S19R); s26 = g(S26R); s27 = g(S27R)
N19 = {s_: sum(v["N"] for v in s19[s_]["strata"].values()) for s_ in TOPICS19}
assert len(set(N19.values())) == 1, N19
N19 = N19["wolf"]
C19 = f"{QE}/s19/ann_C.tsv"
TIE19 = sum(1 for l_ in open(os.path.join(ROOT, C19), encoding="utf-8") if l_.strip())


def kprop(rel, vkeys, n, metric, ci_keys=None, k=None):
    """share stored at vkeys (rounded to 4 decimals by analyze.py) with denominator n. k is the unique integer with round(k / n, 4) =
    stored (given or recovered); Wilson 95% recomputed exactly from k and n, bounds rounded outward and clamped to [0, 1]; a stored
    interval that differs is kept as ci95_source. Asserts the 3-decimal truncation of the stored share equals that of k / n."""
    stored = g(rel, *vkeys)
    if k is None: k = round(stored * n)
    assert round(k / n, 4) == stored, (rel, vkeys, stored, k, n)
    assert F.t(stored) == F.t(k / n), (rel, vkeys, stored, k, n)
    lo_, hi_ = wilson_exact(k, n)
    ci_ = [float(F.q(max(lo_, 0.0), 3, F.ROUND_FLOOR)), float(F.q(min(hi_, 1.0), 3, F.ROUND_CEILING))]
    out = {"metric": metric, "value": stored, "k": k, "n": n, "kn": f"{k}/{n}", "ci95": ci_,
           "ci_method": "Wilson 95% from k and n, bounds rounded outward"}
    if ci_keys is not None and list(g(rel, *ci_keys)) != ci_: out["ci95_source"] = list(g(rel, *ci_keys))
    out["at"] = loc(rel, *vkeys)
    return out


def boot(rel, pkeys, ckeys, metric, method=BOOT_S, **extra):
    return {"metric": metric, "value": g(rel, *pkeys), "ci95": list(g(rel, *ckeys)), "ci_method": method, **extra,
            "at": loc(rel, *pkeys), "ci_at": loc(rel, *ckeys)}


def multi_at(rel, *tail):
    return {"file": rel, "key": " | ".join(" > ".join((s_,) + tail) for s_ in TOPICS19)}


# S19: precision of flags (Wilson), recall weighted to the population, frozen keyword baseline
pt19 = {}
for s_ in TOPICS19:
    x_ = s19[s_]; pf_ = x_["precision_flags"]
    pt19[s_] = {
        "topic": s_, "name_de": TNAME[s_][0], "name_fr": TNAME[s_][1], "name_en": TNAME[s_][2], "scheme": f"src/querschnitt/schemes/adhoc/{s_}.yaml",
        "precision": kprop(S19R, (s_, "precision_flags", "value"), pf_["n"], f"precision of Apertus flags, {AJ}", (s_, "precision_flags", "ci"), k=pf_["k"]),
        "recall": boot(S19R, (s_, "weighted", "point", "a_R"), (s_, "weighted", "ci", "a_R"), f"recall of Apertus flags, {AJ} (weighted to the population)"),
        "precision_weighted": boot(S19R, (s_, "weighted", "point", "a_P"), (s_, "weighted", "ci", "a_P"), f"precision of Apertus flags, {AJ} (bootstrap)"),
        "keyword_precision": boot(S19R, (s_, "weighted", "point", "k_P"), (s_, "weighted", "ci", "k_P"), f"precision of keyword hits, {AJ}"),
        "keyword_recall": boot(S19R, (s_, "weighted", "point", "k_R"), (s_, "weighted", "ci", "k_R"), f"recall of keyword hits, {AJ} (weighted)"),
        "judge_positives": boot(S19R, (s_, "weighted", "point", "pos"), (s_, "weighted", "ci", "pos"), "estimated affairs relevant per the AI judge (population)"),
        "flags": {"metric": "affairs flagged by Apertus (counted)", "value": x_["flags"], "at": loc(S19R, s_, "flags")},
        "keyword_hits": {"metric": "affairs hit by the frozen keyword list (counted)", "value": x_["kw_hits"], "at": loc(S19R, s_, "kw_hits")},
        "n_checked": {"value": x_["n_packet"], "at": loc(S19R, s_, "n_packet")},
        "strata": {"cells": [{"cell": h_, "N": v_["N"], "n": v_["n"], "judge_Y": v_["gold_Y"], "kn": f"{v_['gold_Y']}/{v_['n']}"} for h_, v_ in x_["strata"].items()],
                   "note": "A = Apertus flag, K = keyword hit; every flagged or hit affair is checked (n = N), 'neither' is a random sample",
                   "at": loc(S19R, s_, "strata")}}
NCHK19 = sum(s19[s_]["n_packet"] for s_ in TOPICS19)
tests.append(dict(
    id="adhoc_new_topics", gold="ai-judge", subject="Apertus",
    title_de="Drei neue Themen aus einem Satz (Wolf, Hitzeschutz, KI an Schulen), Geschäfte 1.8.–6.10.2026, gegen den KI-Richter (S19)",
    title_fr="Trois nouveaux thèmes en une phrase (loup, chaleur, IA à l'école), objets du 1.8 au 6.10.2026, contre le juge IA (S19)",
    n=N19, n_checked=NCHK19, topics=list(TOPICS19),
    design="die drei S13-Themen, nie zum Abstimmen benutzt, je eine Frage in einem Satz (src/querschnitt/schemes/adhoc/*.yaml); jedes Geschäft "
    "mit Titel, begonnen 1.8.–6.10.2026; ausgelieferte Ja/Nein-Regel (Reihenfolge a; b bei 0.1 < p < 0.9; Flag bei mittlerem p ≥ 0.5); "
    "Stichwortlisten vor jedem Resultat eingefroren; geprüft: jedes von Apertus oder Stichwörtern markierte Geschäft + 120 zufällige "
    "unmarkierte je Thema; Richter: zwei blinde Claude-Läufe (A gemischt, B umgekehrt) + Stichentscheid C; Recall auf die Population "
    "zurückgewichtet (Schicht-Bootstrap 2'000)",
    result={"metric": f"precision of Apertus flags per topic (wolf / hitze / ki-schule), {AJ}",
            "value": [pt19[s_]["precision"]["value"] for s_ in TOPICS19], "ci95": [pt19[s_]["precision"]["ci95"] for s_ in TOPICS19],
            "kn": [pt19[s_]["precision"]["kn"] for s_ in TOPICS19], "topics": list(TOPICS19),
            "ci_method": "Wilson 95% per topic from k and n, bounds rounded outward", "at": multi_at(S19R, "precision_flags")},
    results_more=[{"metric": f"recall of Apertus flags per topic, {AJ} (weighted to the population)",
                   "value": [pt19[s_]["recall"]["value"] for s_ in TOPICS19], "ci95": [pt19[s_]["recall"]["ci95"] for s_ in TOPICS19],
                   "ci_method": BOOT_S, "at": multi_at(S19R, "weighted")},
                  {"metric": "affairs flagged by Apertus per topic (counted)", "value": [pt19[s_]["flags"]["value"] for s_ in TOPICS19],
                   "at": multi_at(S19R, "flags")}],
    baselines=[{"name": f"frozen keyword list (eval/s19/keywords_frozen.json), same input: {s_}", "topic": s_,
                "precision": pt19[s_]["keyword_precision"]["value"], "precision_ci95": pt19[s_]["keyword_precision"]["ci95"],
                "recall": pt19[s_]["keyword_recall"]["value"], "recall_ci95": pt19[s_]["keyword_recall"]["ci95"],
                "hits": pt19[s_]["keyword_hits"]["value"], "ci_method": BOOT_S, "at": loc(S19R, s_, "weighted")} for s_ in TOPICS19],
    judge={"runs": f"Claude A (shuffled) / B (reverse) + tie-break C on {TIE19}", "agree_AB": g(S19R, "agree_AB"), "tie_break_C": TIE19,
           "at": loc(S19R, "agree_AB"), "tie_break_at": {"file": C19, "rows": TIE19},
           "cross_check": "the Qwen-SEA-LION cross-check named in the pre-registration is not in eval/s19 (not reported)"},
    breakdowns={"per_topic": pt19,
                "unflagged_sample_note": "the 120 random unflagged affairs per topic hold no judge positive (strata > neither > gold_Y = 0), so the "
                                         "weighted recall is 1.0 with a bootstrap interval of [1.0, 1.0]; that interval does not cover relevant "
                                         "affairs the random sample missed"},
    split="pre-registered (S19); topics never used in tuning; cut-off p ≥ 0.5 fixed; keyword lists frozen before any decision",
    prereg=pre(PB, "— S19 three new ad-hoc topics"),
    sources=[S19R, f"{QE}/s19/analyze.py", f"{QE}/s19/build_packet.py", f"{QE}/s19/key.jsonl", f"{QE}/s19/keywords_frozen.json",
             f"{QE}/s19/ann_A.tsv", f"{QE}/s19/ann_B.tsv", C19], build=BUILD + " (run runs/s19)", model=MODEL,
    judge_build="Claude (blind agent runs)", date="2026-10-14"))

# S26: 30 editor decisions per topic as examples; paired against S19 on the same test items
pt26 = {}
for s_ in TOPICS19:
    x_ = s26[s_]; npos = x_["positives"]
    blk = {"topic": s_, "name_en": TNAME[s_][2], "test_items": {"value": x_["n_test"], "at": loc(S26R, s_, "n_test")},
           "editor_examples": {"value": x_["editor_examples"], "at": loc(S26R, s_, "editor_examples")},
           "judge_positives": {"value": npos, "at": loc(S26R, s_, "positives")}}
    for arm, nm in (("s19", "without examples (S19)"), ("s26", "with 30 editor decisions as examples")):
        a_ = x_[arm]
        blk[arm] = {"flags": {"value": a_["flags"], "at": loc(S26R, s_, arm, "flags")},
                    "precision": kprop(S26R, (s_, arm, "precision"), a_["flags"], f"precision of flags {nm}, {AJ}", (s_, arm, "ci")),
                    "recall": (kprop(S26R, (s_, arm, "recall"), npos, f"recall {nm}: share of the judge's positives among the test items flagged")
                               if a_["recall"] is not None else
                               {"metric": f"recall {nm}", "value": None, "not_measurable": f"not measurable (n {npos} judge positives)",
                                "at": loc(S26R, s_, arm, "recall")})}
    pd_ = x_["precision_diff"]
    if npos:
        blk["precision_diff"] = boot(S26R, (s_, "precision_diff", "value"), (s_, "precision_diff", "ci"),
                                     f"paired Δ precision of flags, with − without examples, {AJ}", method=BOOT_P)
    else:
        blk["precision_diff"] = {"metric": f"paired Δ precision of flags, with − without examples, {AJ}", "value": None,
                                 "not_measurable": f"not measurable (n {npos} judge positives among {x_['n_test']} test items)",
                                 "note": "precision is 0 in both arms, so the stored difference 0.0 [0.0, 0.0] carries no information",
                                 "value_source": pd_["value"], "ci95_source": pd_["ci"], "at": loc(S26R, s_, "precision_diff")}
    pt26[s_] = blk
tests.append(dict(
    id="adhoc_editor_examples", gold="ai-judge", subject="Apertus",
    title_de="Neue Themen aus einem Satz: 30 Entscheide einer Redaktion als Beispiele, gepaart gegen S19, gegen den KI-Richter (S26)",
    title_fr="Nouveaux thèmes en une phrase : 30 décisions d'une rédaction comme exemples, apparié à S19, contre le juge IA (S26)",
    n=sum(s26[s_]["n_test"] for s_ in TOPICS19), topics=list(TOPICS19),
    design="S19-Pakete und S19-Richtergold; je Thema 30 zufällig gezogene geprüfte Geschäfte (random.Random(26)) als erste Entscheide einer "
    "Redaktion (ihr Richterlabel Y/N); alle übrigen geprüften Geschäfte mit der ausgelieferten Ja/Nein-Regel neu bewertet, mit den 4 "
    "BM25-nächsten Entscheiden als Beispiele (examples.topic_examples); gepaart gegen die S19-Flags auf denselben Geschäften",
    result={"metric": f"paired Δ precision of flags, with − without editor examples, per topic (wolf / hitze / ki-schule), {AJ}",
            "value": [pt26[s_]["precision_diff"]["value"] for s_ in TOPICS19],
            "ci95": [pt26[s_]["precision_diff"].get("ci95") for s_ in TOPICS19], "topics": list(TOPICS19),
            "not_measurable": {s_: pt26[s_]["precision_diff"]["not_measurable"] for s_ in TOPICS19 if pt26[s_]["precision_diff"].get("not_measurable")},
            "ci_method": BOOT_P, "at": multi_at(S26R, "precision_diff")},
    results_more=[{"metric": f"precision of flags with editor examples per topic, {AJ}",
                   "value": [pt26[s_]["s26"]["precision"]["value"] for s_ in TOPICS19], "ci95": [pt26[s_]["s26"]["precision"]["ci95"] for s_ in TOPICS19],
                   "kn": [pt26[s_]["s26"]["precision"]["kn"] for s_ in TOPICS19],
                   "ci_method": "Wilson 95% per topic from k and n, bounds rounded outward", "at": multi_at(S26R, "s26", "precision")},
                  {"metric": "recall with editor examples per topic: share of the judge's positives among the test items flagged",
                   "value": [pt26[s_]["s26"]["recall"]["value"] for s_ in TOPICS19], "at": multi_at(S26R, "s26", "recall")}],
    baselines=[dict(pt26[s_]["s19"]["precision"], name=f"S19 flags without examples, same test items: {s_}", topic=s_) for s_ in TOPICS19],
    breakdowns={"per_topic": pt26,
                "recall_note": "the pre-registration names the weighted S19 recall as secondary; analyze.py reports recall among the judge's "
                               "positives in the test items, which equals it here because the S19 random sample of unflagged affairs holds "
                               "no judge positive (s19 results > strata > neither > gold_Y = 0)"},
    split="S19 packets: 30 judged items per topic as editor examples (random.Random(26) over the pid-sorted packet), the rest re-scored once; "
          "pre-registered (S26) after S19's annotations, before any S26 call; nothing tuned",
    prereg=pre(PB, "— S26 editor decisions as examples"),
    sources=[S26R, f"{QE}/s26/analyze.py", f"{QE}/s26/run.py", f"{QE}/s26/split.json", f"{QE}/s26/raw.jsonl", f"{QE}/s26/ledger.jsonl", S19R],
    build=BUILD, model=MODEL, judge_build="Claude (blind agent runs, S19 gold)", date="2026-10-14"))

# S27: a second, stricter question on every S19 flag; precision and recall with vs without
pt27 = {}
for s_ in TOPICS19:
    x_ = s27[s_]
    pt27[s_] = {"topic": s_, "name_en": TNAME[s_][2],
                "flags": {"value": x_["flags"], "at": loc(S27R, s_, "flags")}, "kept": {"value": x_["kept"], "at": loc(S27R, s_, "kept")},
                "judge_positives": {"value": x_["positives"], "at": loc(S27R, s_, "positives")},
                "precision_without": kprop(S27R, (s_, "precision_s19", "value"), x_["flags"], f"precision of S19 flags without the second question, {AJ}",
                                           (s_, "precision_s19", "ci")),
                "precision_with": kprop(S27R, (s_, "precision_verified", "value"), x_["kept"], f"precision of the flags kept by the second question, {AJ}",
                                        (s_, "precision_verified", "ci")),
                "recall_with": kprop(S27R, (s_, "recall_verified"), x_["positives"], f"recall with the second question: share of the judge's positives kept, {AJ}"),
                "precision_diff": boot(S27R, (s_, "diff", "value"), (s_, "diff", "ci"), f"paired Δ precision, with − without the second question, {AJ}",
                                       method=BOOT_P)}
    assert pt27[s_]["precision_with"]["k"] == pt27[s_]["recall_with"]["k"], s_   # kept positives: the same affairs in both shares
tests.append(dict(
    id="adhoc_verification", gold="ai-judge", subject="Apertus",
    title_de="Neue Themen aus einem Satz: zweite, strengere Frage auf den Markierungen («zentrales Thema?»), gegen den KI-Richter (S27)",
    title_fr="Nouveaux thèmes en une phrase : seconde question plus stricte sur les signalements (« thème central ? »), contre le juge IA (S27)",
    n=sum(s27[s_]["flags"] for s_ in TOPICS19), topics=list(TOPICS19),
    design="jedes S19-Flag erhält eine weitere geschlossene Frage, gleicher Rahmen und Input (Titel + Langtitel): «Ist «{name}» ein zentrales "
    "Thema dieses Geschäfts – nicht nur am Rande erwähnt oder bloss ähnlich?» A = Ja, zentral / B = Nein (Reihenfolge a; b bei 0.1 < p < 0.9; "
    "Flag bleibt bei mittlerem p ≥ 0.5); eine Formulierung, nicht abgestimmt, einmal auf die S19-Pakete angewandt; Gold = S19-Richter",
    result={"metric": f"precision of the flags kept by the second question per topic (wolf / hitze / ki-schule), {AJ}",
            "value": [pt27[s_]["precision_with"]["value"] for s_ in TOPICS19], "ci95": [pt27[s_]["precision_with"]["ci95"] for s_ in TOPICS19],
            "kn": [pt27[s_]["precision_with"]["kn"] for s_ in TOPICS19], "topics": list(TOPICS19),
            "ci_method": "Wilson 95% per topic from k and n, bounds rounded outward", "at": multi_at(S27R, "precision_verified")},
    results_more=[{"metric": f"paired Δ precision, with − without the second question, per topic, {AJ}",
                   "value": [pt27[s_]["precision_diff"]["value"] for s_ in TOPICS19], "ci95": [pt27[s_]["precision_diff"]["ci95"] for s_ in TOPICS19],
                   "ci_method": BOOT_P, "at": multi_at(S27R, "diff")},
                  {"metric": f"recall with the second question per topic: share of the judge's positives kept, {AJ}",
                   "value": [pt27[s_]["recall_with"]["value"] for s_ in TOPICS19], "kn": [pt27[s_]["recall_with"]["kn"] for s_ in TOPICS19],
                   "at": multi_at(S27R, "recall_verified")}],
    baselines=[dict(pt27[s_]["precision_without"], name=f"S19 flags without the second question: {s_}", topic=s_) for s_ in TOPICS19],
    breakdowns={"per_topic": pt27,
                "recall_note": "every judge positive was flagged in S19 (S19 weighted recall 1.0), so the share of positives kept is the recall "
                               "with the second question"},
    split="S19 packets held out; one pre-registered wording, no tuning, applied once (amendment before any S27 call: no dev step)",
    prereg=pre(PB, "— S27 a second, stricter check"), prereg_more=pre(PB, "Amendment 2026-10-14 23:10 CEST (before any S27 call)"),
    sources=[S27R, f"{QE}/s27/analyze.py", f"{QE}/s27/run.py", f"{QE}/s27/raw.jsonl", f"{QE}/s27/ledger.jsonl", "src/querschnitt/prompts.py", S19R],
    build=BUILD, model=MODEL, judge_build="Claude (blind agent runs, S19 gold)", date="2026-10-14"))

# S30: three further narrow one-sentence topics, held out; a generated scope as a third question on the confirmed flags (variant) vs the
# product before S30 (shipped = yes/no flag kept by the S27 question), against a fresh blind AI judge. The variant (V4) was chosen after
# seeing dev on the S19 packets (stated in the pre-registration).
S30R, S30D, S30T, S30S = (f"{QE}/s30/results.json", f"{QE}/s30/dev_results.json", f"{QE}/s30/topics.json", f"{QE}/s30/sentences.json")
TOPICS30 = ("licht", "drohnen", "pestizide")
EN30 = {"licht": "light pollution", "drohnen": "drones", "pestizide": "pesticides", "pooled": "all three"}
s30 = g(S30R)
N30 = {s_: sum(v_["N"] for v_ in s30[s_]["strata"].values()) for s_ in TOPICS30}
assert len(set(N30.values())) == 1 and sum(v_["N"] for v_ in s30["pooled"]["strata"].values()) == 3 * N30["licht"], N30
N30 = N30["licht"]
assert s30["pooled"]["n_items"] == sum(s30[s_]["n_items"] for s_ in TOPICS30)
BOOT30 = "stratified bootstrap 2,000 (percentile, random.Random(30)), bounds rounded outward at 3 decimals (eval/s30/analyze.py)"
BOOT30P = ("paired: both arms on the same stratified bootstrap 2,000 resamples (percentile, random.Random(30)), bounds rounded outward at "
           "3 decimals (eval/s30/analyze.py)")
ARMS30 = {"shipped": "shipped before S30 (yes/no flag kept by the S27 question)",
          "variant": "with the scope check (S27 question and scope question both yes)",
          "kw": "frozen keyword list (eval/s30/keywords_frozen.json)",
          "shipped_yn": "the yes/no step alone (secondary)",
          "yn_sc": "yes/no + scope question without the S27 question (secondary)"}


def s30k(*keys, metric):
    """precision {k, n, value, ci} of eval/s30/results.json: value = k / n truncated at 3 decimals (asserted, as analyze.py writes it);
    Wilson 95% recomputed exactly from k and n, bounds rounded outward at 3 decimals (the stored interval is kept as ci95_source when it
    differs)."""
    b = g(S30R, *keys); k, n = b["k"], b["n"]
    assert b["value"] == math.trunc(k / n * 1000) / 1000, (keys, b)
    lo_, hi_ = wilson_exact(k, n)
    ci_ = [float(F.q(max(lo_, 0.0), 3, F.ROUND_FLOOR)), float(F.q(min(hi_, 1.0), 3, F.ROUND_CEILING))]
    out = {"metric": metric, "value": b["value"], "k": k, "n": n, "kn": f"{k}/{n}", "ci95": ci_,
           "ci_method": "Wilson 95% from k and n, bounds rounded outward (eval/s30/analyze.py; re-checked by build_pruefstand.py)"}
    if list(b["ci"]) != ci_: out["ci95_source"] = list(b["ci"])
    out["at"] = loc(S30R, *keys)
    return out


def s30b(*keys, metric, method=BOOT30):
    b = g(S30R, *keys)
    out = {"metric": metric, "value": b["value"], "ci95": list(b["ci"]), "ci_method": method, "at": loc(S30R, *keys, "value"),
           "ci_at": loc(S30R, *keys, "ci")}
    if "n_boot" in b:
        out["n_boot"] = b["n_boot"]
        if b["n_boot"] < 2000: out["n_boot_note"] = "resamples where both arms flag at least one affair (the rest have no precision)"
    return out


pt30 = {}
for s_ in TOPICS30 + ("pooled",):
    x_ = s30[s_]
    assert x_["judge_pos_items"] == sum(v_["judge_Y"] for v_ in x_["strata"].values()), s_
    blk = {"topic": s_, "name_en": EN30[s_],
           "items_checked": {"metric": "affairs the judge checked", "value": x_["n_items"], "at": loc(S30R, s_, "n_items")},
           "judge_positives": {"metric": f"affairs relevant per the AI judge among the checked ({AJ})", "value": x_["judge_pos_items"],
                               "at": loc(S30R, s_, "judge_pos_items")},
           "relevant_est": s30b(s_, "relevant_est", metric="estimated affairs relevant per the AI judge (population)"),
           "strata": {"cells": [{"cell": h_, "N": v_["N"], "n": v_["n"], "judge_Y": v_["judge_Y"], "kn": f"{v_['judge_Y']}/{v_['n']}"}
                                for h_, v_ in x_["strata"].items()],
                      "note": "'any' = flagged by any arm or the keyword list (every such affair checked, n = N); 'neither' = a random sample",
                      "at": loc(S30R, s_, "strata")}}
    if s_ != "pooled":
        nm_ = g(S30T, s_, "shipped", "names")
        blk.update(name_de=nm_["de"], name_fr=nm_["fr"], topic_id=g(S30T, s_, "shipped", "id"), sentence=g(S30S, s_),
                   sentence_at=loc(S30S, s_))
    for arm_, lab_ in ARMS30.items():
        blk[arm_] = {"flags": {"metric": f"flags, {lab_} (counted)", "value": x_[arm_]["flags"], "at": loc(S30R, s_, arm_, "flags")},
                     "precision": s30k(s_, arm_, "precision", metric=f"precision of flags, {lab_}, {AJ}"),
                     "recall": s30b(s_, arm_, "recall_weighted", metric=f"recall, {lab_}, {AJ} (weighted to the population)")}
        assert blk[arm_]["precision"]["n"] == blk[arm_]["flags"]["value"], (s_, arm_)
    blk["precision_diff"] = s30b(s_, "diff_variant_minus_shipped_P", method=BOOT30P,
                                 metric=f"paired Δ precision of the confirmed flags, with − without the scope check, {AJ}")
    blk["recall_diff"] = s30b(s_, "diff_variant_minus_shipped_R", method=BOOT30P,
                              metric=f"paired Δ recall (weighted), with − without the scope check, {AJ}")
    blk["lost_judge_positives"] = {"metric": "judge positives the shipped design confirms and the scope check does not",
                                   "value": blk["shipped"]["precision"]["k"] - blk["variant"]["precision"]["k"], "at": loc(S30R, s_, "shipped", "precision", "k")}
    pt30[s_] = blk
# the scope check asks only on flags the shipped design confirms: its flags are a subset, so it can lose but never add a positive
assert all(pt30[s_]["variant"]["flags"]["value"] <= pt30[s_]["shipped"]["flags"]["value"] for s_ in pt30)
assert sum(pt30[s_]["judge_positives"]["value"] for s_ in TOPICS30) == pt30["pooled"]["judge_positives"]["value"]
# the pre-registered product rule: pooled precision-difference interval above 0, and no recall-difference interval (pooled or per topic) below 0
pdl30 = pt30["pooled"]["precision_diff"]["ci95"][0]
rdh30 = {s_: pt30[s_]["recall_diff"]["ci95"][1] for s_ in pt30}
RULE30 = {"text": "the variant goes into the product only if the pooled precision-difference interval lies above 0 and no recall-difference "
                  "interval (pooled or per topic) lies below 0; otherwise the product stays as it is",
          "pooled_precision_diff_ci_lo": pdl30, "recall_diff_ci_hi": rdh30, "met": pdl30 > 0 and all(v_ >= 0 for v_ in rdh30.values()),
          "narrowly": "the pooled precision interval starts just above 0 and the pooled and pesticides recall intervals end at 0",
          "at": md(PB, "Product rule: the variant goes into the product only if the pooled precision difference interval lies above 0")}
assert RULE30["met"] and pdl30 < 0.01 and min(rdh30.values()) == 0.0, RULE30   # met, narrowly (the text says so)
dev30 = g(S30D)
DEV30 = {"chosen": "V4_scope+S27", "chosen_at": md(PB, "Chosen after seeing dev (highest mean F1"),
         "note": "dev on the S19 packets with the S19 judge gold (not held out; four variants, tuning allowed); V4 = scope question + the S27 "
                 "question, chosen after seeing dev, as the pre-registration states",
         "topics": {t_: {a_: {"precision": v_["precision"], "recall": v_["recall"], "flags": v_["flags"], "tp": v_["tp"],
                              "at": loc(S30D, t_, a_)} for a_, v_ in dev30[t_].items()} for t_ in dev30}}
assert set(DEV30["topics"]) == set(TOPICS19) and all(DEV30["chosen"] in v_ for v_ in DEV30["topics"].values())
pp30 = pt30["pooled"]
tests.append(dict(
    id="adhoc_scope_check", gold="ai-judge", subject="Apertus",
    title_de="Neue Themen aus einem Satz, hold-out (Lichtverschmutzung, Drohnen, Pestizide): generierter Umfang als dritte Frage auf den "
             "Markierungen, gegen den KI-Richter (S30)",
    title_fr="Nouveaux thèmes en une phrase, hors échantillon (pollution lumineuse, drones, pesticides) : périmètre généré comme troisième "
             "question sur les signalements, contre le juge IA (S30)",
    n=N30, n_checked=pp30["items_checked"]["value"], topics=list(TOPICS30),
    design="drei neue Themen, je ein deutscher Satz (eval/s30/sentences.json), nie zuvor benutzt; Thema wie «Neues Thema» erzeugt "
    "(adhoc.TOPIC_PROMPT) und eine Generierung von Ein- und Ausschlusslisten de/fr/it (Umfang), beide vor dem Scoring eingefroren "
    "(eval/s30/topics.json); ausgeliefert = Ja/Nein-Flag (mittleres p ≥ 0.5), von der S27-Frage bestätigt; Variante = zusätzlich «Gehört das "
    "folgende parlamentarische Geschäft zum Thema «…»?» mit den Listen (mittleres p ≥ 0.5), nach Dev auf den S19-Paketen gewählt (V4); "
    "Population: jedes Geschäft mit Titel, begonnen 16.–31.3.2026; geprüft: jedes von einem Arm oder den eingefrorenen Stichwörtern "
    "markierte Geschäft + 120 zufällige übrige je Thema; Richter: zwei blinde Claude-Läufe (A gemischt, B umgekehrt), Stichentscheid C bei "
    "A ≠ B; Recall auf die Population zurückgewichtet (Schicht-Bootstrap 2'000)",
    result=dict(pp30["precision_diff"], metric=f"paired Δ precision of the confirmed flags, with − without the scope check, pooled over the "
                                               f"three topics, {AJ}"),
    results_more=[dict(pp30["variant"]["precision"], metric=f"precision of flags with the scope check, pooled, {AJ}"),
                  dict(pp30["recall_diff"], metric=f"paired Δ recall (weighted), with − without the scope check, pooled, {AJ}"),
                  dict(pp30["variant"]["recall"], metric=f"recall with the scope check, pooled, {AJ} (weighted)")],
    baselines=[dict(pp30["shipped"]["precision"], name="the product before S30 (yes/no flag kept by the S27 question), same affairs, pooled"),
               dict(pp30["kw"]["precision"], name="frozen keyword list (eval/s30/keywords_frozen.json), same affairs, pooled")],
    judge={"runs": "Claude A (shuffled) / B (reverse); tie-break C on A ≠ B", "agree_AB": s30["agree_AB"], "tie_break_C": s30["n_C"],
           "items": pp30["items_checked"]["value"], "at": loc(S30R, "agree_AB"), "tie_break_at": loc(S30R, "n_C")},
    breakdowns={"per_topic": pt30, "product_rule": RULE30, "dev": DEV30,
                "keyword_note": "the frozen keyword lists are more precise than both arms on these topics (pooled and per topic)",
                "lost_positives_note": "the two judge positives the scope check drops are pesticides affairs (P041 veterinary insecticides, "
                                       "P050 pests and plant diseases; eval/s30/key.jsonl, eval/s30/packet_A/pestizide/items.tsv)"},
    split="held out: three topics never used before, affairs begun 16–31 Mar 2026 (S19 used Aug–Oct), keyword lists and generated topics "
          "frozen before any test call; the variant (V4) was chosen after seeing dev on the S19 packets, as the pre-registration states; "
          "pre-registered (S30) before any test call; nothing tuned on the test",
    prereg=pre(PB, "— S30 narrow one-sentence topics"), prereg_more=RULE30["at"],
    sources=[S30R, f"{QE}/s30/analyze.py", f"{QE}/s30/run.py", f"{QE}/s30/run_common.py", f"{QE}/s30/common.py", f"{QE}/s30/flags.py",
             f"{QE}/s30/build_packet.py", f"{QE}/s30/key.jsonl", S30T, S30S, f"{QE}/s30/keywords_frozen.json", f"{QE}/s30/ann/",
             S30D, f"{QE}/s30/raw.jsonl", f"{QE}/s30/ledger.jsonl", "src/querschnitt/prompts.py", "src/querschnitt/adhoc.py"],
    build=BUILD, model=MODEL, judge_build="Claude (blind agent runs)", date="2026-10-15",
    shipped="new one-sentence topics with a scope ask the scope question on their confirmed flags (prompts.scope_check_prompt, "
            "adhoc.SCOPE_PROMPT); flags it does not confirm go to 'please check', not away; existing topics unchanged"))
NEW_ADHOC = ("adhoc_new_topics", "adhoc_editor_examples", "adhoc_verification")
for t_ in tests:
    if t_["id"] == "evidence_support":
        t_["production_check"] = {"id": "evidence_support_production", "what": "the same check on 200 stored quotes of the 2026 production run (S23)"}
for t_ in tests:
    if t_["id"] == "dvs_2026":
        t_["superseded_by"] = {"id": "dvs_2026_census", "what": "counts and judge precision/recall; kept as the snapshot's history "
                               "(breakdowns by language, level, party and canton are still on the snapshot)"}
        t_["title_de"] += " (S8-Momentaufnahme, ersetzt durch die volle Erhebung)"
        t_["title_fr"] += " (instantané S8, remplacé par le recensement complet)"

ORDER = ["aps_chapter_shipped_d4", "aps_chapter_heldout_s25", "aps_chapter_heldout_s28_no_prefill", "aps_chapter_heldout_s33_french", "aps_chapter_d4s", "aps_chapter_examples", "aps_chapter_readback", "aps_chapter_pooling", "aps_subtopic",
         "aps_hierarchical_d4", "aps_hierarchical_heldout_s25", "aps_design_search_s31",
         "aps_calibration_shipped", "aps_lane_rule", "aps_calibration", "dvs_human30", "curia_sachbereiche", "bern_directorates_production", "bern_directorates",
         "basel_themes_names", "basel_themes_examples", "ticino_departments", "judge_anchor_aps", "judge_dvs_human", "neutrality_shipped_s32", "neutrality_s9", "aps_italian_vs_german",
         "free_generation",
         "dvs_2026_census", "dvs_2026", "aps_communal_production", "dvs_correction_loop", "dvs_text_lever", "evidence_support",
         "evidence_support_production", "aps_cantonal_communal", "aps_bilingual", "adhoc_new_topics", "adhoc_editor_examples",
         "adhoc_verification", "adhoc_scope_check", "neutrality_judge_sets"]
assert sorted(ORDER) == sorted(t_["id"] for t_ in tests), set(ORDER) ^ {t_["id"] for t_ in tests}
tests.sort(key=lambda t_: ORDER.index(t_["id"]))
for t_ in tests:
    if t_["id"] == "aps_chapter_readback":
        t_["shipped"] = "where no APS-labelled examples exist (cantonal, communal); federal affairs ship D4 (S16)"
        t_["title_de"] = t_["title_de"].replace("(D1, ausgeliefert)", "(D1, ausgeliefert ohne APS-Beispiele)")
        t_["title_fr"] = t_["title_fr"].replace("(D1, livré)", "(D1, livré sans exemples APS)")
    if t_["id"] == "aps_chapter_examples":
        t_["shipped"] = "building block of D4 (federal affairs ship D4, S16)"

# ---------------------------------------------------------------- flat fields of CONTRACT.md §3 (test, n, design, result, interval, baseline, split, file)
def _short(bl):
    if not bl: return None
    x = bl[0]; v = x.get("value", x.get("precision", x.get("F1")))
    return {"name": x.get("name"), "value": v, "ci95": x.get("ci95", x.get("precision_ci95"))}


for t in tests:
    t["test"] = t["title_de"]
    t["interval"] = t["result"].get("ci95")
    t["baseline"] = _short(t.get("baselines"))
    at = t["result"].get("at") or {}
    t["file"] = at.get("file") or t["sources"][0]
    t["key"] = at.get("key") or (f"line {at['line']}: {at['text']}" if at.get("line") else None)

# ---------------------------------------------------------------- curves
cur = json.load(open(os.path.join(EVAL, "aps_curves.json")))
for k in ("aps_d3", "aps_d1"):
    cur[k]["design"] = "D3 five APS-labelled examples" if k == "aps_d3" else "D1 read back from the subtopic"
    cur[k]["source"] = "eval/aps_curves.json (recomputed by eval/scripts/aps_curves.py from S9 raw; 50/70/90/100% equal S9 results.json for D3)"
cur["aps_d3"]["check_vs_s9_results"] = [{"coverage": p["coverage"], "precision": p["precision"], "ci": p["ci"]}
                                        for p in g(S9R, "reliability", "D3", "coverage_precision")]
TD = {t_["id"]: t_ for t_ in tests}
lanes = TD["aps_chapter_shipped_d4"]["breakdowns"]["lanes"]
_lr = TD["aps_lane_rule"]["result"]
cur["aps_d4"] = {"n": N16, "design": "D4 shipped federal design (S16)", "points": TD["aps_chapter_shipped_d4"]["breakdowns"]["coverage_precision"]["points"],
                 "operating_point": {"coverage": _lr["coverage"], "precision": _lr["value"], "n": _lr["n"], "k": _lr["k"], "ci": _lr["ci95"],
                                     "note": "shipped operating point (14 Oct): pass when the recalibrated p ≥ 0.7 (2-fold cross-fitted on the "
                                     "S16 items); the rest go to 'please check'. Computed after S16 from its rows; tested held out in S25 "
                                     "(aps_chapter_heldout_s25 > breakdowns > lanes)",
                                     "at": _lr["at"]},
                 "operating_point_old": {"coverage": lanes["agree"]["share"], "precision": lanes["agree"]["precision"], "n": lanes["agree"]["n"],
                                         "ci": lanes["agree"]["ci95"], "note": "lane rule until 14 Oct: both readings agree", "at": loc(S16R, "lanes_D4")},
                 "source": "S16 results.json coverage_precision > aps-fed (one point per k = 1..1,357); grid points picked at k = round(c × n), "
                           "correct = precision × k, Wilson 95% computed by build_pruefstand.py (bounds rounded outward at 3 decimals)",
                 "at": loc(S16R, "coverage_precision", "aps-fed")}

# ---------------------------------------------------------------- Wilson intervals recomputed outward from k and n
# Every stored interval that IS a Wilson interval (it equals Wilson(k, n) at the stored precision) is replaced by the exact Wilson
# interval with the lower bound floored and the upper bound ceiled at 3 decimals; the stored one is kept as `<key>_source`.
# k comes from the block (k / correct / k1) or, when absent, from value × n (accepted only if it reproduces the stored value).
# Bootstrap intervals never match Wilson and are left as stored (the display floors / ceils them).
CI_POINT = {"ci95": ("value", "precision", "acc"), "ci": ("value", "precision", "acc", "p"), "top1_ci95": ("top1",),
            "share_ci95": ("share",), "precision_ci95": ("precision",)}
WILSON_LOG = []


def _wilson_out(v, ci_, n, k=None):
    if not (isinstance(v, (int, float)) and not isinstance(v, bool) and isinstance(n, int) and n > 0): return None
    if not (isinstance(ci_, (list, tuple)) and len(ci_) == 2 and all(isinstance(x, (int, float)) for x in ci_)): return None
    if not 0 <= v <= 1: return None
    if k is None:
        k = round(v * n)
        if abs(k / n - v) > 0.5 * 10 ** -max(_dec(v), 1) + 1e-12: return None
    elif abs(k / n - v) > 0.5 * 10 ** -max(_dec(v), 1) + 1e-12: return None
    lo_, hi_ = wilson_exact(k, n)
    tol = lambda x: 0.5 * 10 ** -max(_dec(x), 1) + 1e-9
    if abs(lo_ - ci_[0]) > tol(ci_[0]) or abs(hi_ - ci_[1]) > tol(ci_[1]): return None
    return [float(F.q(max(lo_, 0.0), 3, F.ROUND_FLOOR)), float(F.q(min(hi_, 1.0), 3, F.ROUND_CEILING))], k


def wilson_pass(o, path="", n_ctx=None):
    if isinstance(o, dict):
        n_here = o.get("n") if isinstance(o.get("n"), int) else n_ctx
        boot_ = "bootstrap" in str(o.get("ci_method") or "") + str(o.get("method") or "")   # declared bootstrap intervals are never Wilson
        for ck, pks in (() if boot_ else CI_POINT.items()):
            if ck not in o: continue
            ci_ = o[ck]
            if not any(pk in o for pk in pks) and isinstance(o.get("k"), int) and isinstance(o.get("n"), int) and o["n"]:
                r_ = _wilson_out(o["k"] / o["n"], ci_, o["n"], o["k"])
                if r_ and r_[0] != list(ci_):
                    o[ck + "_source"] = ci_; o[ck] = r_[0]; WILSON_LOG.append((path + "." + ck, ci_, r_[0]))
                if r_: o.setdefault("ci_method", "Wilson 95% recomputed from k and n, bounds rounded outward")
            for pk in pks:
                if pk not in o: continue
                v = o[pk]; k = next((o[x] for x in ("k", "correct", "k1") if isinstance(o.get(x), int)), None)
                if isinstance(v, list) and isinstance(ci_, list) and ci_ and isinstance(ci_[0], list):   # value lists with ci lists
                    new_, ch = [], False
                    for vi, ci_i in zip(v, ci_):
                        r_ = _wilson_out(vi, ci_i, n_here)
                        new_.append(r_[0] if r_ else ci_i); ch |= bool(r_ and r_[0] != list(ci_i))
                    if ch:
                        o[ck + "_source"] = ci_; o[ck] = new_; WILSON_LOG.append((path + "." + ck, ci_, new_))
                    break
                r_ = _wilson_out(v, ci_, n_here, k)
                if r_:
                    if r_[0] != list(ci_):
                        o[ck + "_source"] = ci_; o[ck] = r_[0]; WILSON_LOG.append((path + "." + ck, ci_, r_[0]))
                    o.setdefault("ci_method", "Wilson 95% recomputed from k and n, bounds rounded outward")
                break
        for kk, vv in list(o.items()):
            if kk.endswith("_source") or kk in cc.PATH_KEYS: continue
            wilson_pass(vv, path + "." + str(kk), n_here)
    elif isinstance(o, list):
        for i, vv in enumerate(o): wilson_pass(vv, f"{path}[{i}]", n_ctx)


for t_ in tests: wilson_pass(t_, t_["id"], t_.get("n") if isinstance(t_.get("n"), int) else None)
for k_ in ("aps_d3", "aps_d1"):
    for i_, p_ in enumerate(cur[k_]["points"]): wilson_pass(p_, f"curves.{k_}.points[{i_}]")
    cur[k_]["source"] += "; intervals recomputed exactly from correct and n by build_pruefstand.py, bounds rounded outward (aps_curves.json keeps nearest rounding)"
cur["aps_d4"]["operating_point"]["ci"] = TD["aps_lane_rule"]["result"]["ci95"]
cur["aps_d4"]["operating_point_old"]["ci"] = TD["aps_chapter_shipped_d4"]["breakdowns"]["lanes"]["agree"]["ci95"]
# S8b text lever: precision = tp/(tp+fp), recall = tp/(tp+fn), Wilson from those counts
_tx = TD["dvs_text_lever"]
for blk, key in ((_tx["result"], "title_text"), (_tx["baselines"][0], "title_only")):
    c_ = g(S8B, "all", key); pairs = [(c_["tp"], c_["tp"] + c_["fp"]), (c_["tp"], c_["tp"] + c_["fn"])]
    new_ = []
    for (k__, n__), old in zip(pairs, blk["ci95"]):
        lo_, hi_ = wilson_exact(k__, n__)
        assert abs(lo_ - old[0]) < 6e-4 and abs(hi_ - old[1]) < 6e-4, (key, old, lo_, hi_)
        new_.append([float(F.q(lo_, 3, F.ROUND_FLOOR)), float(F.q(min(hi_, 1.0), 3, F.ROUND_CEILING))])
    if new_ != blk["ci95"]:
        WILSON_LOG.append((f"dvs_text_lever.{key}.ci95", blk["ci95"], new_)); blk["ci95_source"] = blk["ci95"]; blk["ci95"] = new_
    blk["counts"] = {"precision": pairs[0], "recall": pairs[1], "at": loc(S8B, "all", key)}
    blk["ci_method"] = "Wilson 95% recomputed from tp, fp, fn, bounds rounded outward"
for t_ in tests: t_["interval"] = t_["result"].get("ci95")
print(f"Wilson intervals widened outward: {len(WILSON_LOG)}")
assert not [x for x in WILSON_LOG if x[0].split(".")[0] in NEW_ADHOC], [x for x in WILSON_LOG if x[0].split(".")[0] in NEW_ADHOC]
assert not [x for x in WILSON_LOG if x[0].split(".")[0] in ("aps_chapter_heldout_s25", "aps_hierarchical_heldout_s25", "aps_chapter_heldout_s28_no_prefill",
                                                            "ticino_departments", "adhoc_scope_check", "aps_design_search_s31",
                                                            "neutrality_shipped_s32")]
# S25 / S28 / S29 / S30 / S31 / S32 intervals are already outward (recomputed exactly from k and n above)

# ---------------------------------------------------------------- display forms (truncated points, outward bounds) so claims_check backs what is shown
BOUND = re.compile(r"(^|_)ci(95)?(_w)?$")


def _forms(v, bound):
    out = set()
    if isinstance(v, bool) or v is None or isinstance(v, str): return out
    if isinstance(v, float):
        for d in ((0, 1, 2, 3, 4) if abs(v) >= 100 else (1, 2, 3, 4)):
            out.add(cc.norm(F.t(v, d)))
        return out - cc.variants(v)
    if isinstance(v, list):
        if bound and len(v) == 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v):
            for d in (0, 1, 2, 3, 4) if max(abs(v[0]), abs(v[1])) >= 100 else (1, 2, 3, 4):
                out.add(cc.norm(F.lo(v[0], d))); out.add(cc.norm(F.hi(v[1], d)))
            return out - cc.variants(v[0]) - cc.variants(v[1])
        for x in v: out |= _forms(x, bound)
    return out


def shown_pass(o):
    if isinstance(o, dict):
        add = {}
        for k, v in list(o.items()):
            if k in cc.PATH_KEYS or k == "shown": continue
            f = _forms(v, bool(BOUND.search(k)))
            if f: add[k] = sorted(f)
            shown_pass(v)
        if add: o["shown"] = add
    elif isinstance(o, list):
        for v in o: shown_pass(v)


out = {
    "schema": "querschnitt/pruefstand@1",
    "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "paths_relative_to": "repository root (S1–S15 vendored under eval/spikes/)",
    "build": {"endpoint": "Public AI", "model": MODEL, "system_fingerprint": BUILD},
    "conventions": {"ci95": "Wilson for proportions; paired bootstrap 2,000 (percentile) for differences; stratified bootstrap for S8 population estimates",
                    "value": "as stored in the source file (JSON keeps 4 decimals where the source does)",
                    "display": "shown values are truncated toward zero, never rounded up; interval bounds are rounded outward, never inward "
                               "(eval/scripts/numfmt.py); `shown` lists those display forms next to the stored value",
                    "gold": "human = labels made by people (APS editors, Curia tags, DVS list, Grand Council field, Basel-Stadt themes, Ticino lead department); "
                            "ai-judge = blind Claude runs (+ Qwen cross-check)"},
    "tests": tests,
    "curves": {k: cur[k] for k in ("aps_d4", "aps_d3", "aps_d1")},
    "to_measure": [
        "FR/IT rows with the headline Curia design + BFH on the same items",
        "recalibration refit on the build that serves at the event",
        "ECE intervals (bootstrap)",
        "judge precision on human negatives",
        "a French-speaking parliament's own scheme (NE Grand Conseil leading_department; needs a mapping between department periods, eval/s29/SOURCES.md)",
        "a calibration map for the no-prefill fallback (its lane is the readings rule until then; S28)",
        f"one pre-registered look at the closest S31 candidate (V3, examples in both code orders) on the unspent S25 items (likely "
        f"inconclusive at n = {N25}, eval/s31/DEV.md), or fresh APS-labelled items (none new on Wayback, S31)",
        "a held-out Italian federal slice (S33 measured French on the S25 items; S22 measured Italian on the design set only)",
        "human labels for new one-sentence topics (§15, S19–S30, is measured against the AI judge only)",
        "Romansh"],
}
shown_pass(out["tests"]); shown_pass(out["curves"])
json.dump(out, open(os.path.join(EVAL, "pruefstand.json"), "w"), ensure_ascii=False, indent=1)
print(f"tests: {len(tests)} (human {sum(t['gold'] == 'human' for t in tests)}, ai-judge {sum(t['gold'] == 'ai-judge' for t in tests)})")

# ---------------------------------------------------------------- eval/pruefstand_app.json (the app's Prüfstand), derived from the tests above
FRD = re.compile(r"(?<=\d)\.(?=\d)")
fr = lambda s: FRD.sub(",", s)
p3 = lambda v, d=3: F.t(v, d, sep="'")
iv = lambda c: [float(F.q(c[0], 3, F.ROUND_FLOOR)), float(F.q(c[1], 3, F.ROUND_CEILING))] if c else None
civ = lambda c, d=3: f"[{F.lo(c[0], d)}, {F.hi(c[1], d)}]"
sciv = lambda c, d=3: f"[{F.signed(F.lo(c[0], d))}, {F.signed(F.hi(c[1], d))}]"
rel = lambda f: f[len("bern/"):] if f.startswith("bern/") else f
SPLIT_S9 = ("held-out, vorregistriert", "hors échantillon, préenregistré")
SPLIT_S16 = ("vorregistriert (S16), gemessen auf den S9-Geschäften; Design nach S9 auf denselben Geschäften gewählt (D4 = D1 + D3); "
             f"Hold-out-Test: S25 ({N25} neue Geschäfte, unten)",
             "préenregistré (S16), mesuré sur les objets S9 ; design choisi après S9 sur les mêmes objets (D4 = D1 + D3) ; "
             f"test hors échantillon : S25 ({F.t(N25, sep=' ')} nouveaux objets, ci-dessous)")
rows = []


def row(test, test_fr, gold, design, design_fr, n, result, interval, baseline, baseline_fr, split, split_fr, file, result_fr=None):
    r = dict(test=test, test_fr=test_fr, gold="judge" if gold == "ai-judge" else gold, design=design, design_fr=design_fr, n=n, result=result)
    r["result_fr"] = result_fr or fr(result)
    r.update(interval=interval, baseline=baseline, baseline_fr=baseline_fr, split=split, split_fr=split_fr, file=rel(file))
    rows.append(r)


T4, T4s, T3, T1, T2, TS = (TD[k] for k in ("aps_chapter_shipped_d4", "aps_chapter_d4s", "aps_chapter_examples", "aps_chapter_readback",
                                           "aps_chapter_pooling", "aps_subtopic"))
D0, KW, MJ = s9b
bl_de = f"Listen-Prompt {p3(D0['value'])} · Stichwort {p3(KW['value'])} · Mehrheit {p3(MJ['value'])}"
bl_fr = fr(f"liste {p3(D0['value'])} · mots-clés {p3(KW['value'])} · majorité {p3(MJ['value'])}")
APS = ("APS-Kapitel vs. APS-Redaktion, 1'357 Bundesgeschäfte (Design-Set, S9/S16)", "Chapitre APS vs rédaction APS, 1 357 objets fédéraux (jeu de conception, S9/S16)")
r4 = T4["results_more"]
row(*APS, "human", "Beispiele + Rücklesen, beide Lesarten (D4, ausgeliefert)", "exemples + relecture, deux lectures (D4, livré)", N16,
    f"top-1 {p3(T4['result']['value'])} · top-3 {p3(r4[0]['value'])}", iv(T4["result"]["ci95"]), bl_de, bl_fr,
    *SPLIT_S16, T4["file"])
la, ld = T4["breakdowns"]["lanes"]["agree"], T4["breakdowns"]["lanes"]["disagree"]
TL = TD["aps_lane_rule"]; lp_, lc_ = TL["result"], TL["results_more"][0]; lo_ = TL["baselines"][0]
SPLIT_LANE = ("nach S16 aus seinen Zeilen gewählt, 2-fach kreuzangepasst; hold-out getestet in S25 (unten)",
              "choisie après S16 à partir de ses lignes, validation croisée à 2 plis ; testée hors échantillon dans S25 (ci-dessous)")
row(*APS, "human", f"D4, ausgeliefert: rekalibriertes p ≥ 0.7 ({F.pct(lp_['coverage'])} der Geschäfte)",
    fr(f"D4, livré : p recalibré ≥ 0.7 ({F.pct(lp_['coverage'])} des objets)"), lp_["n"], p3(lp_["value"]), iv(lp_["ci95"]),
    f"p < 0.7 → bitte prüfen: {p3(lc_['value'])} {civ(lc_['ci95'])} (n {lc_['n']}) · Lesarten einig {p3(lo_['value'])} {civ(lo_['ci95'])}",
    fr(f"p < 0.7 → à vérifier : {p3(lc_['value'])} {civ(lc_['ci95'])} (n {lc_['n']}) · lectures concordantes {p3(lo_['value'])} {civ(lo_['ci95'])}"),
    *SPLIT_LANE, TL["file"], result_fr=fr(p3(lp_["value"])))
row(*APS, "human", f"D4, Lesarten einig (bisherige Regel; {F.pct(la['share'])} der Geschäfte)",
    f"D4, lectures concordantes (règle précédente ; {fr(F.pct(la['share']))} des objets)",
    la["n"], f"{p3(la['precision'])}", iv(la["ci95"]), f"uneinig → bitte prüfen: {p3(ld['precision'])} {civ(ld['ci95'])} (n {ld['n']})",
    fr(f"discordantes → à vérifier : {p3(ld['precision'])} {civ(ld['ci95'])} (n {ld['n']})"),
    *SPLIT_S16, T4["file"], result_fr=fr(p3(la["precision"])))
c4 = T4["breakdowns"]["calibration"]
row(*APS, "human", "D4, Konfidenz nach isotoner Rekalibrierung (ECE)", "D4, confiance après recalibration isotone (ECE)", c4["n"],
    f"ECE {p3(c4['ece_crossfit'], 4)}", None, f"roh {p3(c4['ece_raw'], 4)}", fr(f"brute {p3(c4['ece_raw'], 4)}"),
    "2-fach kreuzangepasst (S16)", "validation croisée à 2 plis (S16)", c4["file"])
rs = T4s["results_more"]
row(*APS, "human", "wie D4, zweite Lesart nur unter p 0.9 (D4s, sekundär)", "comme D4, seconde lecture seulement sous p 0,9 (D4s, secondaire)", N16,
    f"top-1 {p3(T4s['result']['value'])} · top-3 {p3(rs[0]['value'])}", iv(T4s["result"]["ci95"]), f"D3 {p3(T4s['baselines'][0]['value'])}",
    fr(f"D3 {p3(T4s['baselines'][0]['value'])}"), *SPLIT_S16, T4s["file"])
row(*APS, "human", "fünf APS-Beispiele (D3)", "cinq exemples APS (D3)", T3["n"],
    f"top-1 {p3(T3['result']['value'])} · top-3 {p3(T3['results_more'][0]['value'])}", iv(T3["result"]["ci95"]), bl_de, bl_fr, *SPLIT_S9, T3["file"])
row(*APS, "human", "Kapitel aus Unterthema, ohne Beispiele (D1; ausgeliefert, wo keine APS-Beispiele)",
    "chapitre déduit du sous-thème, sans exemples (D1 ; livré sans exemples APS)", T1["n"],
    f"top-1 {p3(T1['result']['value'])} · top-3 {p3(T1['results_more'][0]['value'])}", iv(T1["result"]["ci95"]),
    f"Listen-Prompt {p3(D0['value'])}", fr(f"liste {p3(D0['value'])}"), *SPLIT_S9, T1["file"])
row(*APS, "human", "Listen-Prompt, zwei Reihenfolgen (D0)", "liste, deux ordres (D0)", D0["n"], f"top-1 {p3(D0['value'])}", iv(D0["ci95"]),
    "—", "—", *SPLIT_S9, D0["at"]["file"])
d2d = T2["results_more"][1]
row(*APS, "human", "DE + FR gemittelt (D2)", "DE + FR moyennés (D2)", T2["n"], f"top-1 {p3(T2['result']['value'])}", iv(T2["result"]["ci95"]),
    f"Δ vs D0 {F.signed(p3(d2d['value']))} {sciv(d2d['ci95'])}", fr(f"Δ vs D0 {F.signed(p3(d2d['value']))} {sciv(d2d['ci95'])}"), *SPLIT_S9, T2["file"])
row(*APS, "human", "Unterthema, durchgehend", "sous-thème, de bout en bout", TS["n"],
    f"top-1 {p3(TS['result']['value'])} · top-3 {p3(TS['results_more'][0]['value'])}", iv(TS["result"]["ci95"]), "—", "—", *SPLIT_S9, TS["file"])
TH = TD["aps_hierarchical_d4"]; mh = {x["metric"]: x for x in TH["results_more"]}; bh = {x["name"]: x for x in TH["baselines"]}
SPLIT_H = ("nach S16 aus seinen Zeilen berechnet", "calculé après S16 à partir de ses lignes")
s1, s3_, sg = (mh[f"subtopic {k} (D4)"] for k in ("top-1 end to end", "top-3 end to end", "top-1 given the chapter is right"))
row(*APS, "human", "Unterthema, durchgehend, ausgeliefertes Design (D4)", "sous-thème, de bout en bout, design livré (D4)", TH["n"],
    f"top-1 {p3(s1['value'])} · top-3 {p3(s3_['value'])} · bei richtigem Kapitel {p3(sg['value'])}", iv(s1["ci95"]),
    f"D1 {p3(bh['D1 subtopic top-1']['value'])} · D0 {p3(bh['D0 subtopic top-1']['value'])}",
    fr(f"D1 {p3(bh['D1 subtopic top-1']['value'])} · D0 {p3(bh['D0 subtopic top-1']['value'])}"), *SPLIT_H, TH["file"],
    result_fr=fr(f"top-1 {p3(s1['value'])} · top-3 {p3(s3_['value'])} · si chapitre juste {p3(sg['value'])}"))
mf = mh["per-chapter F1, macro over the chapters present (D4)"]
hf_b = {d: bh[n]["value"] for d, n in (("D1", "D1 read back from the subtopic, no examples (same items)"),
                                        ("D0", "D0 plain list prompting, best subtopic within its chapter (same items)"),
                                        ("kw", "keyword (APS subtopic words, frozen; chapter only)"))}
row(*APS, "human", "D4, hierarchisches F1 (Kapitel + Unterthema) · Kapitel-F1 makro", "D4, F1 hiérarchique (chapitre + sous-thème) · F1 macro par chapitre",
    TH["n"], f"hF {p3(TH['result']['value'])} · Makro-F1 {p3(mf['value'])} (alle {p3(mf['n'])})", iv(TH["result"]["ci95"]),
    f"hF D1 {p3(hf_b['D1'])} · D0 {p3(hf_b['D0'])} · Stichwort {p3(hf_b['kw'])}",
    fr(f"hF D1 {p3(hf_b['D1'])} · D0 {p3(hf_b['D0'])} · mots-clés {p3(hf_b['kw'])}"), *SPLIT_H, TH["file"],
    result_fr=fr(f"hF {p3(TH['result']['value'])} · F1 macro {p3(mf['value'])} (les {F.t(mf['n'], sep=' ')})"))
# S31: the design search on the design set (dev only, not pre-registered): one row in the design-set table
T31 = TD["aps_design_search_s31"]; r31 = T31["result"]; v131 = T31["results_more"][0]; d431 = T31["baselines"][0]
s4 = lambda v: F.signed(F.t(v, 4))
row(*APS, "human", "Design-Suche (S31): 5 Varianten gegen D4, keine besser; bestes V3 (Beispiele in beiden Code-Reihenfolgen)",
    "recherche de design (S31) : 5 variantes contre D4, aucune meilleure ; la meilleure, V3 (exemples dans les deux ordres de codes)", T31["n"],
    f"Δ top-1 V3 − D4 {s4(r31['value'])} {sciv(r31['ci95'], 4)}", iv(r31["ci95"]),
    f"Schwelle ≥ +0.02 mit Intervall über 0: von keiner erreicht · V1 {s4(v131['value'])} {sciv(v131['ci95'], 4)} · D4 mit derselben Regel "
    f"{p3(d431['value'])} (S16-Regel {p3(T4['result']['value'])})",
    fr(f"seuil ≥ +0.02 avec intervalle au-dessus de 0 : atteint par aucune · V1 {s4(v131['value'])} {sciv(v131['ci95'], 4)} · D4 avec la même "
       f"règle {p3(d431['value'])} (règle S16 {p3(T4['result']['value'])})"),
    "nur Dev auf dem Design-Set, Beispiele leave-one-out, nicht vorregistriert; kein Test gelaufen, die S25-Geschäfte bleiben unbenutzt",
    "dev seulement sur le jeu de conception, exemples leave-one-out, non préenregistré ; aucun test lancé, les objets S25 restent inutilisés",
    T31["file"], result_fr=fr(f"Δ top-1 V3 − D4 {s4(r31['value'])} {sciv(r31['ci95'], 4)}"))
# S25: the held-out test of the shipped design (its own table, right after the design set above)
T25 = TD["aps_chapter_heldout_s25"]; m25 = T25["results_more"]; b25 = T25["breakdowns"]; l25 = b25["lanes"]
d0b25, kw25 = T25["baselines"][0], T25["baselines"][1]
APS25 = (f"APS-Kapitel vs. APS-Redaktion, {p3(N25)} neue Bundesgeschäfte (hold-out, S25)",
         f"Chapitre APS vs rédaction APS, {F.t(N25, sep=' ')} nouveaux objets fédéraux (hors échantillon, S25)")
SPLIT_S25 = ("held-out, vorregistriert (S25): kein Geschäft in S5, S9 oder im Beispielpool; nichts darauf abgestimmt; Kalibrierkarte nur aus S16",
             "hors échantillon, préenregistré (S25) : aucun objet de S5, S9 ni du pool d'exemples ; rien d'ajusté ; carte de calibration tirée de S16 seulement")
dd25 = {c["cell"]: c for c in b25["by_design"]["cells"]}
row(*APS25, "human", f"Produktionspipeline wie ausgeliefert (D4; D1 ohne Beispiele: {dd25['D1']['n']} Geschäfte ohne passendes "
    "APS-Beispiel, einwortige Titel wie «Vereidigung»)",
    f"pipeline de production tel que livré (D4 ; D1 sans exemples : {dd25['D1']['n']} objets sans exemple APS adéquat, titres d'un mot "
    "comme « Vereidigung »)", N25,
    f"top-1 {p3(T25['result']['value'])} · top-3 {p3(m25[0]['value'])}", iv(T25["result"]["ci95"]),
    f"Listen-Prompt {p3(d0b25['value'])} (n {p3(d0b25['n'])}) · Stichwort {p3(kw25['value'])}",
    fr(f"liste {p3(d0b25['value'])} (n {F.t(d0b25['n'], sep=' ')}) · mots-clés {p3(kw25['value'])}"), *SPLIT_S25, T25["file"])
lp25, lc25, la25, ld25 = (l25[k] for k in ("pass", "please_check", "readings_agree", "readings_disagree"))
row(*APS25, "human", f"ausgeliefert: rekalibriertes p ≥ 0.7 ({F.pct(lp25['share'])} der Geschäfte)",
    fr(f"livré : p recalibré ≥ 0.7 ({F.pct(lp25['share'])} des objets)"), lp25["n"], p3(lp25["value"]), iv(lp25["ci95"]),
    f"p < 0.7 → bitte prüfen: {p3(lc25['value'])} {civ(lc25['ci95'])} (n {lc25['n']})",
    fr(f"p < 0.7 → à vérifier : {p3(lc25['value'])} {civ(lc25['ci95'])} (n {lc25['n']})"), *SPLIT_S25, T25["file"], result_fr=fr(p3(lp25["value"])))
row(*APS25, "human", f"Lesarten einig (bisherige Regel; {F.pct(la25['share'])} der Geschäfte)",
    f"lectures concordantes (règle précédente ; {fr(F.pct(la25['share']))} des objets)", la25["n"], p3(la25["value"]), iv(la25["ci95"]),
    f"uneinig: {p3(ld25['value'])} {civ(ld25['ci95'])} (n {ld25['n']})", fr(f"discordantes : {p3(ld25['value'])} {civ(ld25['ci95'])} (n {ld25['n']})"),
    *SPLIT_S25, T25["file"], result_fr=fr(p3(la25["value"])))
# S25 subtopic / hierarchy (not pre-registered; the same two rows as the design set's, with the design set's D4 figures for reference)
TH25 = TD["aps_hierarchical_heldout_s25"]; mh25 = {x["metric"]: x for x in TH25["results_more"]}
s1h, s3h, sgh = (mh25[f"subtopic {k} (shipped, held out)"] for k in ("top-1 end to end", "top-3 end to end", "top-1 given the chapter is right"))
mfh = mh25["per-chapter F1, macro over the chapters present (shipped, held out)"]
NPR = ("nicht vorregistriert, nach S25 berechnet", "non préenregistré, calculé après S25")
row(*APS25, "human", f"Unterthema, durchgehend, ausgeliefertes Design ({NPR[0]})", f"sous-thème, de bout en bout, design livré ({NPR[1]})", TH25["n"],
    f"top-1 {p3(s1h['value'])} · top-3 {p3(s3h['value'])} · bei richtigem Kapitel {p3(sgh['value'])}", iv(s1h["ci95"]),
    f"Design-Set (D4, zum Vergleich) {p3(s1['value'])}", fr(f"jeu de conception (D4, pour comparaison) {p3(s1['value'])}"),
    "nach S25 aus seinen Zeilen berechnet, nicht vorregistriert", "calculé après S25 à partir de ses lignes, non préenregistré", TH25["file"],
    result_fr=fr(f"top-1 {p3(s1h['value'])} · top-3 {p3(s3h['value'])} · si chapitre juste {p3(sgh['value'])}"))
row(*APS25, "human", f"hierarchisches F1 (Kapitel + Unterthema) · Kapitel-F1 makro ({NPR[0]})",
    f"F1 hiérarchique (chapitre + sous-thème) · F1 macro par chapitre ({NPR[1]})",
    TH25["n"], f"hF {p3(TH25['result']['value'])} · Makro-F1 {p3(mfh['value'])} (alle {p3(mfh['n'])})", iv(TH25["result"]["ci95"]),
    f"Design-Set (D4, zum Vergleich) hF {p3(TH['result']['value'])} · Makro-F1 {p3(mf['value'])}",
    fr(f"jeu de conception (D4, pour comparaison) hF {p3(TH['result']['value'])} · F1 macro {p3(mf['value'])}"),
    "nach S25 aus seinen Zeilen berechnet, nicht vorregistriert", "calculé après S25 à partir de ses lignes, non préenregistré", TH25["file"],
    result_fr=fr(f"hF {p3(TH25['result']['value'])} · F1 macro {p3(mfh['value'])} (les {F.t(mfh['n'], sep=' ')})"))
pa25, pb25 = m25[1], m25[2]
row(*APS25, "human", "vor dem Determinismus-Fix gesehen (alter Beispielabruf, zwei Auswertungen)",
    "vu avant la correction du déterminisme (ancienne recherche d'exemples, deux compositions)", None,
    f"top-1 {F.t(pa25['value'], 4)} ({pa25['kn']}) · {F.t(pb25['value'], 4)} ({pb25['kn']})", None,
    f"final {p3(T25['result']['value'])} ({T25['result']['kn']})", fr(f"final {p3(T25['result']['value'])} ({T25['result']['kn']})"),
    "Änderung vor dem finalen Score (vorregistriert)", "amendement avant le score final (préenregistré)", PB)
# S28: the same held-out affairs in no-prefill mode (an endpoint-capability check; its own small table right after S25's)
T28 = TD["aps_chapter_heldout_s28_no_prefill"]; m28 = T28["results_more"]; pf28_, d28_ = T28["baselines"][0], m28[1]
lp28, lc28 = (T28["breakdowns"]["lanes_no_prefill"][k] for k in ("pass", "please_check"))
APS28 = (f"APS-Kapitel, dieselben {p3(N25)} Bundesgeschäfte (hold-out): ohne Prefill, Endpunkt-Fallback (S28)",
         f"Chapitre APS, les mêmes {F.t(N25, sep=' ')} objets fédéraux (hors échantillon) : sans prefill, repli pour l'endpoint (S28)")
SPLIT_S28 = ("held-out (S25-Geschäfte), vorregistriert (S28); prüft die Endpunkt-Fähigkeit, kein neues Design; ausgeliefert bleibt Prefill",
             "hors échantillon (objets S25), préenregistré (S28) ; teste la capacité de l'endpoint, pas un nouveau design ; le prefill reste livré")
row(*APS28, "human", "ohne Prefill (QS_PREFILL=0), sonst Produktionspipeline wie ausgeliefert; Codes zu 100 % aus den Logprobs gelesen",
    "sans prefill (QS_PREFILL=0), sinon pipeline de production tel que livré ; codes lus à 100 % dans les logprobs", N25,
    f"top-1 {p3(T28['result']['value'])} · top-3 {p3(m28[0]['value'])}", iv(T28["result"]["ci95"]),
    f"mit Prefill (ausgeliefert, S25) {p3(pf28_['value'])} · Δ mit − ohne {F.signed(p3(d28_['value']))} {sciv(d28_['ci95'])}",
    fr(f"avec prefill (livré, S25) {p3(pf28_['value'])} · Δ avec − sans {F.signed(p3(d28_['value']))} {sciv(d28_['ci95'])}"),
    *SPLIT_S28, T28["file"])
row(*APS28, "human", f"ohne Prefill: Lesarten-Regel, keine Kalibrierung ({F.pct(lp28['share'])} durchgelassen)",
    fr(f"sans prefill : règle des lectures, sans calibration ({F.pct(lp28['share'])} passent)"), lp28["n"], p3(lp28["value"]), iv(lp28["ci95"]),
    f"bitte prüfen: {p3(lc28['value'])} {civ(lc28['ci95'])} (n {lc28['n']}) · mit Prefill, rekalibriertes p ≥ 0.7: {p3(lp25['value'])}",
    fr(f"à vérifier : {p3(lc28['value'])} {civ(lc28['ci95'])} (n {lc28['n']}) · avec prefill, p recalibré ≥ 0.7 : {p3(lp25['value'])}"),
    *SPLIT_S28, T28["file"], result_fr=fr(p3(lp28["value"])))
# S33: the same held-out affairs read from the French text (production's code path for French federal text), right after S28's table
T33 = TD["aps_chapter_heldout_s33_french"]; m33 = T33["results_more"]; de33_, d33_ = T33["baselines"][0], m33[1]
ro33_ = T33["breakdowns"]["same_design_readings_only"]; rof_, rog_, rod_ = ro33_["french"], ro33_["german"], ro33_["paired"]
APS33 = (f"APS-Kapitel, dieselben {p3(N25)} Bundesgeschäfte (hold-out): aus dem französischen Text gelesen (S33)",
         f"Chapitre APS, les mêmes {F.t(N25, sep=' ')} objets fédéraux (hors échantillon) : lus dans le texte français (S33)")
SPLIT_S33 = ("held-out (S25-Geschäfte), vorregistriert (S33); der Code-Pfad der Produktion für französischen Bundestext; ausgeliefert "
             "bleibt das Lesen aus dem deutschen Text",
             "hors échantillon (objets S25), préenregistré (S33) ; le chemin de production pour un texte fédéral français ; la "
             "production continue de lire le texte allemand")
row(*APS33, "human", "französischer Titel + eingereichter Text, ohne Beispiele (D1, französischer Rahmen; wie die Produktion "
    "französischen Bundestext liest)",
    "titre français + texte déposé, sans exemples (D1, cadre français ; comme la production lit un texte fédéral français)", N25,
    f"top-1 {p3(T33['result']['value'])} · top-3 {p3(m33[0]['value'])}", iv(T33["result"]["ci95"]),
    f"Deutsch, ausgeliefert (S25, D4) {p3(de33_['value'])} · Δ FR − DE {F.signed(p3(d33_['value']))} {sciv(d33_['ci95'])}",
    fr(f"allemand, livré (S25, D4) {p3(de33_['value'])} · Δ FR − DE {F.signed(p3(d33_['value']))} {sciv(d33_['ci95'])}"),
    *SPLIT_S33, T33["file"])
row(*APS33, "human", "gleiches Design in beiden Sprachen: nur die Kapitel-Lesarten ohne Beispiele, ohne Rücklesen",
    "même design dans les deux langues : seulement les lectures du chapitre sans exemples, sans relecture", rof_["n"],
    f"FR {p3(rof_['value'])} · DE {p3(rog_['value'])}", iv(rof_["ci95"]),
    f"Δ FR − DE {F.signed(p3(rod_['value']))} {sciv(rod_['ci95'])}", fr(f"Δ FR − DE {F.signed(p3(rod_['value']))} {sciv(rod_['ci95'])}"),
    *SPLIT_S33, T33["file"], result_fr=fr(f"FR {p3(rof_['value'])} · DE {p3(rog_['value'])}"))

dv = TD["dvs_human30"]
row("«Digitalisierung»: 30 handkuratierte DVS-Geschäfte (Recall)", "« numérique » : 30 objets DVS choisis à la main (rappel)", "human",
    "Ja/Nein mit Umfangnotiz", "oui/non avec note de portée", dv["n"], f"{dv['result']['k']}/{dv['result']['n']}", iv(dv["result"]["ci95"]),
    f"Stichwort {dv['baselines'][0]['k']}/{dv['baselines'][0]['n']} · KI-Richter {dv['results_more'][1]['k']}/{dv['results_more'][1]['n']}",
    f"mots-clés {dv['baselines'][0]['k']}/{dv['baselines'][0]['n']} · juge IA {dv['results_more'][1]['k']}/{dv['results_more'][1]['n']}",
    "alle öffentlichen Einträge", "toutes les entrées publiques", dv["file"])
cu = TD["curia_sachbereiche"]; bf = cu["baselines"][0]
row("Sachbereiche Bund vs. Curia-Tags", "Domaines fédéraux vs tags Curia", "human", "fünf getaggte Beispiele + Ja/Nein Top 6",
    "cinq exemples + oui/non top 6", cu["n"], f"micro-F1 {p3(cu['result']['value'])}", iv(cu["result"]["ci95"]),
    f"BFH (trainiert, 15'007) {p3(bf['value'])} {civ(bf['ci95'])}", fr(f"BFH (entraîné, 15 007) {p3(bf['value'])} {civ(bf['ci95'])}"),
    "nach BFH-Publikation eingereicht", "déposés après la publication du modèle BFH", cu["file"])
b20, b21 = TD["basel_themes_names"], TD["basel_themes_examples"]
BS = ("Basel-Stadt: Themen der Kantons- und Stadtentwicklung (46), Grossratsgeschäfte 2019–24",
      "Bâle-Ville : thèmes du développement cantonal et urbain (46), objets du Grand Conseil 2019–24")
m20 = b20["results_more"]
row(*BS, "human", "Schema-Datei: nur die 46 Themennamen, nichts abgestimmt", "fichier de schéma : les 46 noms de thèmes seulement, rien d'ajusté",
    b20["n"], f"top-1 {p3(b20['result']['value'])} · Thema 1 oder 2 {p3(m20[0]['value'])} · top-3 {p3(m20[1]['value'])}", iv(b20["result"]["ci95"]),
    f"Stichwort {p3(b20['baselines'][0]['value'])} · Mehrheit {p3(b20['baselines'][1]['value'])}",
    fr(f"mots-clés {p3(b20['baselines'][0]['value'])} · majorité {p3(b20['baselines'][1]['value'])}"),
    f"alle {p3(b20['n'])}, vorregistriert (S20)", f"les {F.t(b20['n'], sep=' ')}, préenregistré (S20)", b20["file"],
    result_fr=fr(f"top-1 {p3(b20['result']['value'])} · thème 1 ou 2 {p3(m20[0]['value'])} · top-3 {p3(m20[1]['value'])}"))
m21 = b21["results_more"]
row(*BS, "human", "+ fünf Basler Beispiele mit ihrem Thema (andere Hälfte), zwei Lesarten",
    "+ cinq exemples bâlois avec leur thème (autre moitié), deux lectures", b21["n"],
    f"top-1 {p3(b21['result']['value'])} · Thema 1 oder 2 {p3(m21[1]['value'])} · top-3 {p3(m21[2]['value'])}", iv(b21["result"]["ci95"]),
    f"nur Themennamen {p3(b21['baselines'][0]['value'])}: Δ {F.signed(p3(m21[0]['value']))} {sciv(m21[0]['ci95'])}",
    fr(f"noms seulement {p3(b21['baselines'][0]['value'])} : Δ {F.signed(p3(m21[0]['value']))} {sciv(m21[0]['ci95'])}"),
    "2 Hälften, vorregistriert (S21)", "2 moitiés, préenregistré (S21)", b21["file"],
    result_fr=fr(f"top-1 {p3(b21['result']['value'])} · thème 1 ou 2 {p3(m21[1]['value'])} · top-3 {p3(m21[2]['value'])}"))
# S29: Ticino, the canton's own lead department, Italian (its own table after Basel)
T29 = TD["ticino_departments"]; b29 = T29["breakdowns"]; m29 = {x["metric"]: x for x in T29["results_more"]}
k29, j29 = T29["baselines"][0], T29["baselines"][1]
TI = ("Tessin, federführende Stelle (6), Gran Consiglio 2023–26, italienisch",
      "Tessin, unité compétente (6), Gran Consiglio 2023–26, en italien")
SPLIT_S29 = (f"vorregistriert (S29), nichts abgestimmt; primär: die {p3(T29['n'])} Geschäfte, deren Input keine Stelle nennt "
             f"({b29['excluded_from_primary']['value']} Inputs nennen sie, v. a. Messaggi mit «competenza»)",
             f"préenregistré (S29), rien d'ajusté ; principal : les {F.t(T29['n'], sep=' ')} objets dont l'entrée ne nomme aucune unité "
             f"({b29['excluded_from_primary']['value']} entrées la nomment, surtout des Messaggi avec « competenza »)")
t2_, t3_ = T29["results_more"][0], T29["results_more"][1]; dk29 = T29["results_more"][2]
row(*TI, "human", "Schema-Datei: 6 Namen italienisch + «keine davon», nichts abgestimmt; Input nennt keine Stelle",
    "fichier de schéma : 6 noms en italien + « aucune », rien d'ajusté ; l'entrée ne nomme aucune unité", T29["n"],
    f"top-1 {p3(T29['result']['value'])} · top-2 {p3(t2_['value'])} · top-3 {p3(t3_['value'])}", iv(T29["result"]["ci95"]),
    f"Stichwort {p3(k29['value'])} · Mehrheit {p3(j29['value'])} · Δ − Stichwort {F.signed(p3(dk29['value']))} {sciv(dk29['ci95'])}",
    fr(f"mots-clés {p3(k29['value'])} · majorité {p3(j29['value'])} · Δ − mots-clés {F.signed(p3(dk29['value']))} {sciv(dk29['ci95'])}"),
    *SPLIT_S29, T29["file"])
la29, lc29 = b29["lane_readings_agree"], b29["lane_please_check"]
row(*TI, "human", f"Lesarten einig ({F.pct(la29['share'])} der Geschäfte)", fr(f"lectures concordantes ({F.pct(la29['share'])} des objets)"),
    la29["n"], p3(la29["value"]), iv(la29["ci95"]), f"uneinig → bitte prüfen: {p3(lc29['value'])} {civ(lc29['ci95'])} (n {lc29['n']})",
    fr(f"discordantes → à vérifier : {p3(lc29['value'])} {civ(lc29['ci95'])} (n {lc29['n']})"), *SPLIT_S29, T29["file"],
    result_fr=fr(p3(la29["value"])))
a29_ = b29["secondary_all_items"]
row(*TI, "human", f"alle {p3(a29_['n'])} Geschäfte wie eingegeben (sekundär; {b29['excluded_from_primary']['value']} Inputs nennen die Stelle)",
    f"les {F.t(a29_['n'], sep=' ')} objets tels quels (secondaire ; {b29['excluded_from_primary']['value']} entrées nomment l'unité)", a29_["n"],
    f"top-1 {p3(a29_['top1']['value'])} · top-2 {p3(a29_['top2']['value'])} · top-3 {p3(a29_['top3']['value'])}", iv(a29_["top1"]["ci95"]),
    f"Stichwort {p3(a29_['keyword']['value'])} · Mehrheit {p3(a29_['majority']['value'])}",
    fr(f"mots-clés {p3(a29_['keyword']['value'])} · majorité {p3(a29_['majority']['value'])}"), *SPLIT_S29, T29["file"])
f29_ = b29["secondary_gold_in_5_departments"]
row(*TI, "human", "Gold eines der 5 Departemente (sekundär, alle Inputs)", "l'or est l'un des 5 départements (secondaire, toutes les entrées)",
    f29_["n"], f"top-1 {p3(f29_['top1']['value'])} · top-3 {p3(f29_['top3']['value'])}", iv(f29_["top1"]["ci95"]),
    f"Stichwort {p3(f29_['keyword']['value'])} · Mehrheit {p3(f29_['majority']['value'])}",
    fr(f"mots-clés {p3(f29_['keyword']['value'])} · majorité {p3(f29_['majority']['value'])}"), *SPLIT_S29, T29["file"])
b18 = TD["bern_directorates_production"]; m18 = b18["results_more"]; k18 = b18["baselines"]
res18 = f"DE {p3(b18['result']['value'])} · FR {p3(m18[0]['value'])} · DE − FR {F.signed(p3(m18[1]['value']))} {sciv(m18[1]['ci95'])}"
row("Bern, Leitdirektion (8), Grossratsgeschäfte 2025–26, Produktionslauf", "Berne, direction compétente (8), objets du Grand Conseil 2025–26, production",
    "human", "Schema-Datei, Titel DE / FR", "fichier de schéma, titre DE / FR", b18["n"], res18, iv(b18["result"]["ci95"]),
    f"Stichwort {p3(k18[0]['value'])} / {p3(k18[1]['value'])} · Mehrheit {p3(k18[2]['value'])}",
    fr(f"mots-clés {p3(k18[0]['value'])} / {p3(k18[1]['value'])} · majorité {p3(k18[2]['value'])}"),
    "vorregistriert (S18), nichts abgestimmt", "préenregistré (S18), rien d'ajusté", b18["file"])
b6 = TD["bern_directorates"]; k6 = b6["baselines"]
row("Bern, Leitdirektion (8), Titel, DE / FR", "Berne, direction responsable (8), titres, DE / FR", "human", "Schema-Tausch", "changement de schéma",
    b6["n"], f"DE {p3(b6['result']['value'])} · FR {p3(b6['results_more'][0]['value'])}", iv(b6["result"]["ci95"]),
    f"Stichwort {p3(k6[0]['value'][0])} / {p3(k6[0]['value'][1])} · Mehrheit {p3(k6[1]['value'])}",
    fr(f"mots-clés {p3(k6[0]['value'][0])} / {p3(k6[0]['value'][1])} · majorité {p3(k6[1]['value'])}"),
    "Grossratsfeld, Geschäfte ab 2015", "champ du Grand Conseil, objets dès 2015", b6["file"])
t22 = TD["aps_italian_vs_german"]; d22 = t22["results_more"][0]; g22 = t22["baselines"][0]
dd22 = f"{F.signed(p3(d22['value'], 4))} {sciv(d22['ci95'])}"   # near-zero difference: 4 decimals (truncated), bounds outward at 3
row("APS-Kapitel, Bundesgeschäfte: Italienisch vs. Deutsch (gleiche Geschäfte)", "Chapitre APS, objets fédéraux : italien vs allemand (mêmes objets)",
    "human", "D1, italienischer Rahmen, IT-Titel + eingereichter Text", "D1, cadre italien, titre IT + texte déposé", t22["n"],
    f"IT {p3(t22['result']['value'])} · DE − IT {dd22}", iv(t22["result"]["ci95"]),
    f"Deutsch (S9 D1) {p3(g22['value'])} {civ(g22['ci95'])}", fr(f"allemand (S9 D1) {p3(g22['value'])} {civ(g22['ci95'])}"),
    "held-out S9-Geschäfte, vorregistriert (S22)", "objets S9 hors échantillon, préenregistré (S22)", t22["file"])
an = TD["judge_anchor_aps"]; ab = {x["name"]: x for x in an["baselines"]}
an_bl = f"Apertus D1 {p3(ab['Apertus D1 on the same 200']['value'])} · D3 {p3(ab['Apertus D3 on the same 200']['value'])}"
row("KI-Richter selbst vs. APS-Redaktion", "Le juge IA vs rédaction APS", "human", "Claude, blind, gleicher Input", "Claude, aveugle, même entrée",
    an["n"], p3(an["result"]["value"]), iv(an["result"]["ci95"]), an_bl, fr(an_bl), "Stichprobe aus S9", "échantillon tiré de S9", an["file"])

s8c = TD["dvs_2026_census"]; m8 = {x["metric"]: x for x in s8c["results_more"]}; k8 = s8c["baselines"][0]
DG = ("«Digitalisierung» 2026, Schweizer Parlamente vs. KI-Richter", "« numérique » 2026, parlements suisses vs juge IA")
SP8 = (f"volle Erhebung 2026, {s8c['n_checked']} geprüft, gewichtet", f"recensement complet 2026, {s8c['n_checked']} vérifiés, pondérés")
row(*DG, "ai-judge", "Präzision", "précision", s8c["n"], p3(s8c["result"]["value"]), iv(s8c["result"]["ci95"]),
    f"Stichwort {p3(k8['precision'])} {civ(k8['precision_ci95'])}", fr(f"mots-clés {p3(k8['precision'])} {civ(k8['precision_ci95'])}"), *SP8, s8c["file"])
rr = m8["recall vs the judge (Swiss)"]
row(*DG, "ai-judge", "Recall", "rappel", s8c["n"], p3(rr["value"]), iv(rr["ci95"]),
    f"Stichwort {p3(k8['recall'])} {civ(k8['recall_ci95'])}", fr(f"mots-clés {p3(k8['recall'])} {civ(k8['recall_ci95'])}"), *SP8, s8c["file"])
fl = m8["affairs flagged (counted, Swiss)"]; pf = m8["parliaments with at least one flag (Swiss)"]
row(*DG, "ai-judge", "markierte Geschäfte (gezählt)", "objets signalés (comptés)", s8c["n"],
    f"{p3(fl['value'])} in {pf['value']} Parlamenten", None, f"Stichwort {p3(k8['flags'])}", f"mots-clés {F.t(k8['flags'], sep=' ')}", *SP8, s8c["file"],
    result_fr=f"{F.t(fl['value'], sep=' ')} dans {pf['value']} parlements")
s17t = TD["aps_communal_production"]; j17 = s17t["judge"]
row("APS-Kapitel, Gemeindeparlamente 2026, Produktionslauf vs. KI-Richter", "Chapitre APS, parlements communaux 2026, production vs juge IA",
    "ai-judge", f"ausgeliefertes Kapitel (Rücklesen), Richter: 2 blinde Läufe + Stichentscheid, κ {p3(j17['kappa_AB'], 2)}",
    fr(f"chapitre livré (relecture), juge : 2 passages aveugles + départage, κ {p3(j17['kappa_AB'], 2)}"), s17t["n"],
    f"top-1 {p3(s17t['result']['value'])} · top-3 {p3(s17t['results_more'][0]['value'])}", iv(s17t["result"]["ci95"]),
    f"Stichwort {p3(s17t['baselines'][0]['value'])} · Mehrheit {p3(s17t['baselines'][1]['value'])}",
    fr(f"mots-clés {p3(s17t['baselines'][0]['value'])} · majorité {p3(s17t['baselines'][1]['value'])}"),
    "Zufallsstichprobe, vorregistriert (S17)", "échantillon aléatoire, préenregistré (S17)", s17t["file"])
ev = TD["evidence_support"]; evm = {x["metric"]: x for x in ev["results_more"]}; sb = evm["quote is an exact substring"]
row("Beleg stützt das Thema (blinder KI-Richter)", "L'extrait soutient le thème (juge IA aveugle)", "ai-judge", "zitierter Satz", "phrase citée",
    ev["n"], f"{p3(ev['result']['value'])} · Teilstring {sb['k']}/{sb['n']}", iv(ev["result"]["ci95"]), "—", "—", "Stichprobe aus S9", "échantillon tiré de S9",
    ev["file"], result_fr=fr(f"{p3(ev['result']['value'])} · sous-chaîne {sb['k']}/{sb['n']}"))
e23 = TD["evidence_support_production"]; m23 = {x["metric"]: x for x in e23["results_more"]}
c23, g23 = m23["chapter quotes (shipped APS chapter)"], m23["«Digitalisierung» quotes"]
u23 = m23["quote is the exact substring at its stored offsets (inputs unchanged since the row)"]; k23 = e23["judge"]["kappa_AB"]
row("Beleg stützt das Thema, Produktionszeilen 2026 (Produktionsprüfung)", "L'extrait soutient le thème, lignes de production 2026 (contrôle de production)",
    "ai-judge", f"gespeicherter Satz, 2 blinde Läufe + Stichentscheid, κ {p3(k23, 2)}",
    fr(f"phrase enregistrée, 2 passages aveugles + départage, κ {p3(k23, 2)}"), e23["n"],
    f"{p3(e23['result']['value'])} · Kapitel {p3(c23['value'])} · Digitalisierung {p3(g23['value'])} · Teilstring {u23['k']}/{u23['n']}",
    iv(e23["result"]["ci95"]), f"S12 (Stichprobe aus S9, beschreibend) {p3(e23['baselines'][0]['value'])}",
    fr(f"S12 (échantillon tiré de S9, descriptif) {p3(e23['baselines'][0]['value'])}"),
    "Zufallsstichprobe, vorregistriert (S23)", "échantillon aléatoire, préenregistré (S23)", e23["file"],
    result_fr=fr(f"{p3(e23['result']['value'])} · chapitre {p3(c23['value'])} · numérique {p3(g23['value'])} · sous-chaîne {u23['k']}/{u23['n']}"))
s6t = TD["aps_cantonal_communal"]; b6d = s6t["breakdowns"]
row("APS-Kapitel, kantonal + kommunal vs. KI-Richter", "Chapitre APS, cantonal + communal vs juge IA", "ai-judge", "Kapitel", "chapitre", s6t["n"],
    f"{p3(s6t['result']['value'])} · kantonal {p3(b6d['level_cantonal']['value'])} · kommunal {p3(b6d['level_communal']['value'])}",
    iv(s6t["result"]["ci95"]), "—", "—", f"zwei Läufe, κ {p3(s6t['judge']['kappa'], 2)}", fr(f"deux passages, κ {p3(s6t['judge']['kappa'], 2)}"),
    s6t["file"], result_fr=fr(f"{p3(s6t['result']['value'])} · cantonal {p3(b6d['level_cantonal']['value'])} · communal {p3(b6d['level_communal']['value'])}"))
s10 = TD["aps_bilingual"]; m10 = s10["results_more"]
BI = ("Zweisprachige Kantone, Titel, DE vs. FR", "Cantons bilingues, titres, DE vs FR")
row(*BI, "ai-judge", "Deutsch", "allemand", s10["n"], p3(s10["result"]["value"]), iv(s10["result"]["ci95"]), "—", "—", "vorregistriert", "préenregistré", s10["file"])
row(*BI, "ai-judge", "Französisch", "français", s10["n"], p3(m10[0]["value"]), iv(m10[0]["ci95"]),
    f"Differenz {F.signed(p3(m10[2]['value']))} {sciv(m10[2]['ci95'])}", fr(f"différence {F.signed(p3(m10[2]['value']))} {sciv(m10[2]['ci95'])}"),
    "vorregistriert", "préenregistré", s10["file"])
# S19 / S26 / S27: one row per topic; every figure is agreement with the AI judge. `topic` marks the saved ad-hoc topic as measured
# in the app (app/js/data.js).
T19, T26, T27 = (TD[k] for k in NEW_ADHOC)
NT19 = ("Neue Themen aus einem Satz (Wolf, Hitzeschutz, KI an Schulen) vs. KI-Richter, 1.8.–6.10.2026",
        "Nouveaux thèmes en une phrase (loup, chaleur, IA à l'école) vs juge IA, 1.8–6.10.2026")
SP19 = (f"alle {p3(T19['n'])} Geschäfte, {p3(T19['n_checked'])} geprüft, Recall gewichtet; vorregistriert (S19)",
        f"les {F.t(T19['n'], sep=' ')} objets, {T19['n_checked']} vérifiés, rappel pondéré ; préenregistré (S19)")
for s_ in TOPICS19:
    b_ = T19["breakdowns"]["per_topic"][s_]; P_, R_, kP_, kR_ = b_["precision"], b_["recall"], b_["keyword_precision"], b_["keyword_recall"]
    row(*NT19, "ai-judge", f"{TNAME[s_][0]}: Präzision der Markierungen / Recall, Übereinstimmung mit dem Richter",
        f"{TNAME[s_][1]} : précision des signalements / rappel, concordance avec le juge", P_["n"],
        f"{p3(P_['value'])} ({P_['kn']}) / {p3(R_['value'])}", iv(P_["ci95"]),
        f"Stichwort {p3(kP_['value'])} / {p3(kR_['value'])} ({b_['keyword_hits']['value']} Treffer)",
        fr(f"mots-clés {p3(kP_['value'])} / {p3(kR_['value'])} ({b_['keyword_hits']['value']} occurrences)"), *SP19, T19["file"])
    rows[-1]["topic"] = f"adhoc/{s_}"
NT26 = ("Neue Themen: 30 Entscheide einer Redaktion als Beispiele vs. KI-Richter (gleiche Geschäfte wie S19)",
        "Nouveaux thèmes : 30 décisions d'une rédaction comme exemples vs juge IA (mêmes objets que S19)")
SP26 = ("S19-Pakete ohne die 30 Beispiele, gepaart; vorregistriert (S26)", "paquets S19 sans les 30 exemples, apparié ; préenregistré (S26)")
for s_ in TOPICS19:
    b_ = T26["breakdowns"]["per_topic"][s_]; P_, P0_, d_ = b_["s26"]["precision"], b_["s19"]["precision"], b_["precision_diff"]
    if d_.get("value") is None:
        npos = b_["judge_positives"]["value"]
        dd_ = (f"Δ nicht messbar (n {npos} Richter-Positive)", f"Δ non mesurable (n {npos} positifs du juge)")
    else:
        dd_ = (f"Δ {F.signed(p3(d_['value']))} {sciv(d_['ci95'])}",) * 2
    row(*NT26, "ai-judge", f"{TNAME[s_][0]}: Präzision mit Beispielen, Übereinstimmung mit dem Richter",
        f"{TNAME[s_][1]} : précision avec exemples, concordance avec le juge", P_["n"], f"{p3(P_['value'])} ({P_['kn']}) · {dd_[0]}",
        iv(P_["ci95"]), f"ohne Beispiele (S19) {p3(P0_['value'])} ({P0_['kn']})", fr(f"sans exemples (S19) {p3(P0_['value'])} ({P0_['kn']})"),
        *SP26, T26["file"], result_fr=fr(f"{p3(P_['value'])} ({P_['kn']}) · {dd_[1]}"))
NT27 = ("Neue Themen: zweite Frage «zentrales Thema?» auf den Markierungen vs. KI-Richter",
        "Nouveaux thèmes : seconde question « thème central ? » sur les signalements vs juge IA")
SP27 = ("S19-Pakete, eine Formulierung, nicht abgestimmt; vorregistriert (S27)", "paquets S19, une formulation, rien d'ajusté ; préenregistré (S27)")
for s_ in TOPICS19:
    b_ = T27["breakdowns"]["per_topic"][s_]; P_, P0_, R_, d_ = b_["precision_with"], b_["precision_without"], b_["recall_with"], b_["precision_diff"]
    res_ = f"{p3(P_['value'])} ({P_['kn']}) / {p3(R_['value'])} ({R_['kn']}) · Δ {F.signed(p3(d_['value']))} {sciv(d_['ci95'])}"
    row(*NT27, "ai-judge", f"{TNAME[s_][0]}: Präzision / Recall mit zweiter Frage, Übereinstimmung mit dem Richter",
        f"{TNAME[s_][1]} : précision / rappel avec seconde question, concordance avec le juge", P_["n"], res_, iv(P_["ci95"]),
        f"ohne zweite Frage (S19) {p3(P0_['value'])} ({P0_['kn']})", fr(f"sans seconde question (S19) {p3(P0_['value'])} ({P0_['kn']})"),
        *SP27, T27["file"])
# S30: three further narrow topics held out, the generated scope check on the confirmed flags; one row per topic and one pooled
# (every figure is agreement with the AI judge; the S30 topics are not saved topics of the app, so no `topic` field)
T30 = TD["adhoc_scope_check"]; p30_ = T30["breakdowns"]["per_topic"]
NT30 = ("Neue Themen, hold-out (Lichtverschmutzung, Drohnen, Pestizide): generierter Umfang als dritte Frage auf den Markierungen vs. KI-Richter",
        "Nouveaux thèmes, hors échantillon (pollution lumineuse, drones, pesticides) : périmètre généré comme troisième question sur les "
        "signalements vs juge IA")
SP30 = (f"Geschäfte 16.–31.3.2026: alle {p3(T30['n'])}, {T30['n_checked']} geprüft, Recall gewichtet; hold-out, vorregistriert (S30); "
        "Variante nach Dev auf den S19-Paketen gewählt",
        f"objets du 16 au 31.3.2026 : les {F.t(T30['n'], sep=' ')}, {T30['n_checked']} vérifiés, rappel pondéré ; hors échantillon, préenregistré "
        "(S30) ; variante choisie après le dev sur les paquets S19")
DE30 = {"licht": ("Lichtverschmutzung", "pollution lumineuse"), "drohnen": ("Drohnen", "drones"), "pestizide": ("Pestizide", "pesticides"),
        "pooled": ("alle drei zusammen", "les trois ensemble")}
for s_ in TOPICS30 + ("pooled",):
    b_ = p30_[s_]; P_, P0_, R_, R0_ = b_["variant"]["precision"], b_["shipped"]["precision"], b_["variant"]["recall"], b_["shipped"]["recall"]
    dP_, dR_, kP_, kR_ = b_["precision_diff"], b_["recall_diff"], b_["kw"]["precision"], b_["kw"]["recall"]
    npos_ = b_["judge_positives"]["value"]
    dd_ = (f"Δ Präzision {F.signed(p3(dP_['value']))} {sciv(dP_['ci95'])} · Δ Recall {F.signed(p3(dR_['value']))} {sciv(dR_['ci95'])}",
           f"Δ précision {F.signed(p3(dP_['value']))} {sciv(dP_['ci95'])} · Δ rappel {F.signed(p3(dR_['value']))} {sciv(dR_['ci95'])}")
    row(*NT30, "ai-judge", f"{DE30[s_][0]}: Präzision / Recall mit Umfangsprüfung, Übereinstimmung mit dem Richter ({npos_} Richter-Positive)",
        f"{DE30[s_][1]} : précision / rappel avec contrôle du périmètre, concordance avec le juge ({npos_} positifs du juge)", P_["n"],
        f"{p3(P_['value'])} ({P_['kn']}) / {p3(R_['value'])} · {dd_[0]}", iv(P_["ci95"]),
        f"ohne Umfangsprüfung (ausgeliefert vor S30) {p3(P0_['value'])} ({P0_['kn']}) / {p3(R0_['value'])} · Stichwort {p3(kP_['value'])} "
        f"({kP_['kn']}) / {p3(kR_['value'])}",
        fr(f"sans contrôle du périmètre (livré avant S30) {p3(P0_['value'])} ({P0_['kn']}) / {p3(R0_['value'])} · mots-clés {p3(kP_['value'])} "
           f"({kP_['kn']}) / {p3(kR_['value'])}"), *SP30, T30["file"],
        result_fr=fr(f"{p3(P_['value'])} ({P_['kn']}) / {p3(R_['value'])} · {dd_[1]}"))

# the held-out test (S25) leads: its rows open the app's first human-label table (the highlighted, shipped row)
# S28 (the same held-out affairs without prefill) and S33 (the same affairs read from the French text) follow right after S25's table
LEAD = ("eval/s25/", "eval/s28/", "eval/s33/")
rows = [r for r in rows if r["file"].startswith(LEAD)] + [r for r in rows if not r["file"].startswith(LEAD)]
# the pre-fix S25 readings stay in docs/PRUEFSTAND.md (with the amendment); the app's lead table shows what ships
rows = [r for r in rows if not r["design"].startswith("vor dem Determinismus-Fix")]
app = {"rows": rows,
       "curve": {"test": "APS-Kapitel, 1'357 Bundesgeschäfte, ausgeliefertes Design (D4)", "test_fr": "Chapitre APS, 1 357 objets fédéraux, design livré (D4)",
                 "n": N16, "x": "coverage", "y": "precision", "points": g(S16R, "coverage_precision", "aps-fed"),
                 "op": {"coverage": lp_["coverage"], "precision": lp_["value"], "n": lp_["n"],
                        "label_de": "ausgeliefert: p ≥ 0.7", "label_fr": "livré : p ≥ 0,7", "file": rel(LR)},
                 "op_old": {"coverage": ln16["agree_share"], "precision": ln16["agree_precision"], "n": ln16["agree_n"],
                            "label_de": "Lesarten einig", "label_fr": "lectures concordantes", "file": rel(S16R)},
                 "file": rel(S16R)},
       "build": B16[-8:],
       "source": "derived from eval/pruefstand.json by eval/scripts/build_pruefstand.py (values truncated, interval bounds outward); "
                 "curve: S16 coverage_precision aps-fed; op = the shipped lane rule, pass at recalibrated p ≥ 0.7 (eval/lanes/results.json "
                 "D4 > calibrated_tau_0_7; chosen after S16 on its rows, tested held out in S25); op_old = readings agree (lanes_D4)"}
json.dump(app, open(os.path.join(EVAL, "pruefstand_app.json"), "w"), ensure_ascii=False, indent=1)
print(f"app rows: {len(rows)} in {len({r['test'] for r in rows})} tests")
