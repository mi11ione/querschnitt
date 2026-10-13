"""Build eval/pruefstand.json from the spike result files (read-only; no model calls, no network).
Every value is read from its source file by key (JSON) or located by an exact needle (Markdown line), so the record of where a
number sits is produced by the same code that copies it. Paths are relative to the hackapertus root.
Run: python3 -I querschnitt/eval/scripts/build_pruefstand.py   (from anywhere)"""
import json, os, re, time

ROOT = "/Users/mi11ion/Desktop/hackapertus"
EVAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = "vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840"
MODEL = "swiss-ai/apertus-v1.5-8b"
I2 = "bern/ideation2/spikes"
I1 = "bern/ideation/spikes"
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
PRE = "bern/ideation2/PREREG.md"
ADD = "bern/ideation2/PREREG-ADDENDA.md"


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
                "see_also": "neutrality_s9 (party, submitter kind, instrument on D1)"}))

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
                "training_size_at": md("bern/research/R1-parts/prior-art.md", "15,007 German training docs")}],
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
    title_de="Neutralität, Bund (S9, APS-Redaktion): Sprache, Partei, Einreichende, Instrument",
    title_fr="Neutralité, Confédération (S9, rédaction APS) : langue, parti, auteur, instrument",
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

# ---------------------------------------------------------------- flat fields of CONTRACT.md §3 (test, n, design, result, interval, baseline, split, file)
def _short(bl):
    if not bl: return None
    x = bl[0]; v = x.get("value", x.get("precision", x.get("F1")))
    return {"name": x.get("name"), "value": v, "ci95": x.get("ci95", x.get("precision_ci95"))}


for t in tests:
    t["test"] = t["title_de"]
    t["interval"] = t["result"].get("ci95")
    t["baseline"] = _short(t.get("baselines"))
    t["file"] = t["sources"][0]

# ---------------------------------------------------------------- curves
cur = json.load(open(os.path.join(EVAL, "aps_curves.json")))
for k in ("aps_d3", "aps_d1"):
    op = next(p for p in cur[k]["points"] if p["coverage"] == 0.7)
    cur[k]["operating_point"] = dict(op, note="shipped dial default: 70% of affairs pass (VISION §4.1); the rest go to 'please check'")
    cur[k]["design"] = "D3 five APS-labelled examples" if k == "aps_d3" else "D1 read back from the subtopic"
    cur[k]["source"] = "eval/aps_curves.json (recomputed by eval/scripts/aps_curves.py from S9 raw; 50/70/90/100% equal S9 results.json for D3)"
cur["aps_d3"]["check_vs_s9_results"] = [{"coverage": p["coverage"], "precision": p["precision"], "ci": p["ci"]}
                                        for p in g(S9R, "reliability", "D3", "coverage_precision")]

out = {
    "schema": "querschnitt/pruefstand@1",
    "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "paths_relative_to": "hackapertus root (~/Desktop/hackapertus)",
    "build": {"endpoint": "Public AI", "model": MODEL, "system_fingerprint": BUILD},
    "conventions": {"ci95": "Wilson for proportions; paired bootstrap 2,000 (percentile) for differences; stratified bootstrap for S8 population estimates",
                    "value": "as stored in the source file (JSON keeps 4 decimals where the source does; display = the results.md form)",
                    "gold": "human = labels made by people (APS editors, Curia tags, DVS list, Grand Council field); ai-judge = blind Claude runs (+ Qwen cross-check)"},
    "tests": tests,
    "curves": {k: cur[k] for k in ("aps_d3", "aps_d1")},
    "to_measure": [
        "Basel-Stadt oracle (2,437 hand-tagged motions) as human cantonal gold",
        "FR/IT rows with the headline Curia design + BFH on the same items",
        "municipal slice grown to ~200",
        "read-back combined with examples (D1 × D3) on the S9 items",
        "recalibration refit on the build that serves at the event",
        "S8 estimates recomputed on the full 2026 census (the census run had scored 8,139 affairs when it was paused)",
        "ECE intervals (bootstrap)",
        "judge precision on human negatives",
        "Romansh"],
}
json.dump(out, open(os.path.join(EVAL, "pruefstand.json"), "w"), ensure_ascii=False, indent=1)
print(f"tests: {len(tests)} (human {sum(t['gold'] == 'human' for t in tests)}, ai-judge {sum(t['gold'] == 'ai-judge' for t in tests)})")
