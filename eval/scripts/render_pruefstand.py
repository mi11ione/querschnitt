"""Render docs/PRUEFSTAND.md from eval/pruefstand.json (no calls). Every number links to the file it comes from.
Display: points truncated toward zero, interval bounds rounded outward (eval/scripts/numfmt.py).
Run: python3 -I eval/scripts/render_pruefstand.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numfmt as F  # noqa: E402

EVAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QS = os.path.dirname(EVAL)
DOC = os.path.join(QS, "docs", "PRUEFSTAND.md")
P = json.load(open(os.path.join(EVAL, "pruefstand.json"), encoding="utf-8"))
T = {t["id"]: t for t in P["tests"]}
UP = "../"  # docs/ -> repository root (every path in pruefstand.json is repository-relative)


def href(at):
    if isinstance(at, dict):
        f = at["file"]; ln = at.get("line") or (at.get("lines") or [None])[0]
        return UP + f + (f"#L{ln}" if ln else "")
    return UP + at


def num(v, d=3):
    """point value, truncated (never rounded up); counts ≥ 100 shown as whole affairs (d = 0) or 1 decimal."""
    if v is None: return "—"
    if isinstance(v, bool): return str(v)
    if isinstance(v, int): return f"{v:,}"
    if abs(v) >= 100: return F.t(v, 0) if d == 0 else (F.t(v, 1) if v != int(v) else f"{int(v):,}")
    return F.t(v, d)


def sgn(v, d=3):
    return F.signed(num(v, d))


def ci(c, d=3, signed=False):
    """interval, bounds rounded outward."""
    if not c: return ""
    a, b = (F.lo(c[0], d), F.hi(c[1], d)) if not (abs(c[0]) >= 100 or abs(c[1]) >= 100) else (F.lo(c[0], 0), F.hi(c[1], 0))
    if signed: a, b = F.signed(a), F.signed(b)
    return f" [{a}, {b}]"


def L(text, at):
    return f"[{text}]({href(at)})"


def r(block, d=3, signed=False):
    """value [lo, hi] linked to block['at']."""
    v = block.get("value")
    txt = (sgn(v, d) if signed else num(v, d)) + ci(block.get("ci95"), d, signed)
    return L(txt, block["at"]) if "at" in block else txt


def kn(k, n, at):
    return L(f"{k}/{n}", at)


out = []
w = out.append
b = P["build"]
w("# Prüfstand")
w("")
w(f"Every measured test behind Querschnitt, as one ruled table each. Human labels first, then the blind AI judge. Model `{b['model']}` on "
  f"{b['endpoint']}, build `…{b['system_fingerprint'][-8:]}` on every Apertus call. Intervals are 95%: Wilson for proportions, paired "
  "bootstrap (2,000) for differences, stratified bootstrap for population estimates. Shown values are truncated, never rounded up. "
  "Every Wilson interval is recomputed exactly from k and n with the lower bound floored and the upper bound ceiled at 3 decimals "
  "(the result files store them rounded to the nearest 0.001; pruefstand.json keeps that as `ci95_source`); bootstrap percentiles are "
  "floored / ceiled as stored. Machine-readable: "
  "[`eval/pruefstand.json`](../eval/pruefstand.json) (file and key for every value); claims register: [`eval/claims.tsv`](../eval/claims.tsv); "
  "check any text with `python3 -I tools/claims_check.py FILE`. Links point into [`eval/spikes/`](../eval/spikes/) for the "
  "pre-registered spikes S1–S15 (vendored evidence: results, scripts, annotations, raw model outputs) and into `eval/` for the build-week tests (pre-registered in [`eval/PREREG-BUILD.md`](../eval/PREREG-BUILD.md)).")
w("")

# ------------------------------------------------------------------ human
w("## Human labels")
w("")
d4, d4s = T["aps_chapter_shipped_d4"], T["aps_chapter_d4s"]
d3, d1, d2 = T["aps_chapter_examples"], T["aps_chapter_readback"], T["aps_chapter_pooling"]
h25 = T["aps_chapter_heldout_s25"]
w(f"### 1 · APS chapter vs APS editors — {num(d4['n'], 0)} federal affairs, pre-registered (S9, S16)")
w("")
w(f"Wayback process pages not used before; German title + submitted text. "
  f"Pre-registration: {L('PREREG.md § S9', d1['prereg'])}; the shipped federal design and its decision rule: {L('PREREG-BUILD.md § S16', d4['prereg'])}. "
  "D0–D3 are held out on these items (S9, nothing tuned on them). D4 is pre-registered (S16) and measured on the same S9 items, but its "
  f"design was chosen after S9 on those items (D4 combines D1 and D3): these {num(d4['n'], 0)} items are the set the shipped design was "
  f"chosen on, so its row is not a held-out result. The held-out test of the shipped design is §1b: S25, {num(h25['n'], 0)} fresh "
  f"federal affairs ({L('PREREG-BUILD.md § S25', d4['prereg_more'])}).")
w("")
w("| Design | top-1 | top-3 | Δ top-1, paired | |")
w("|---|---|---|---|---|")
m4, m4s = d4["results_more"], d4s["results_more"]
w(f"| **D4 five APS-labelled examples + chapter read back from the subtopic, both code orders always** | **{r(d4['result'])}** | {r(m4[0])} | "
  f"vs D3 {r(m4[1], signed=True)} · vs D1 {r(m4[2], signed=True)} | **shipped, federal affairs** (S16) |")
w(f"| D4s as D4, second code order only when p < 0.9 | {r(d4s['result'])} | {r(m4s[0])} | vs D3 {r(m4s[1], signed=True)} · vs D1 "
  f"{r(m4s[2], signed=True)} | secondary, reported, not shipped (S16) |")
for t, name, ship in ((d3, "D3 chapter step with five APS-labelled examples", "building block of D4 (S9)"),
                      (d1, "D1 chapter read back from the subtopic, no examples", "shipped where no APS examples exist (S9)"),
                      (d2, "D2 German + French averaged", "dropped for the label (S9)")):
    w(f"| {name} | {r(t['result'])} | {r(t['results_more'][0])} | vs D0 {r(t['results_more'][1], signed=True)} | {ship} |")
bl = d1["baselines"]
w(f"| D0 plain list prompting (v14) | {r(bl[0])} | — | — | baseline |")
w(f"| keyword (APS subtopic words, frozen) | {r(bl[1])} | — | — | baseline |")
w(f"| majority chapter | {r(bl[2])} | — | — | baseline |")
w("")
dec = d4["decision"]
w(f"Decision ({L('S16 results', d4['decision_at'])}): {dec}")
w("")
ln4 = d4["breakdowns"]["lanes"]; la, ld = ln4["agree"], ln4["disagree"]
w(f"**Lanes of D4** (the reading with examples and the reading without agree / disagree on the chapter): readings agree on "
  f"{L(F.pct(la['share']), ln4['at'])} of affairs ({L(num(la['n']), ln4['at'])}), precision {L(num(la['precision']) + ci(la['ci95']), ln4['at'])}; "
  f"they disagree on {L(num(ld['n']), ln4['at'])}, precision {L(num(ld['precision']) + ci(ld['ci95']), ln4['at'])}. "
  "This was the lane rule until 14 Oct; the shipped rule is now the recalibrated p (below).")
w("")
lr = T["aps_lane_rule"]; lrm = {x["metric"]: x for x in lr["results_more"]}; lrb = {x["name"]: x for x in lr["baselines"]}
w(f"**Lane rule: `please check` when the recalibrated p < 0.7** — computed after S16 from its rows (not pre-registered; no new calls); "
  f"tested held out in S25 ({L('PREREG-BUILD.md § S25', lr['prereg_more'])}, §1b). The isotonic map is 2-fold "
  f"cross-fitted on the {num(lr['n'], 0)} S16 items, so every affair's recalibrated p comes from the half it was not fitted on "
  "([`eval/lanes/analyze.py`](../eval/lanes/analyze.py) → [`eval/lanes/results.json`](../eval/lanes/results.json)). The threshold was "
  "chosen on these same items, so the numbers below are in-sample for the choice of rule (held out: §1b). In production the rule is "
  "`LANE_TAU` in [`src/querschnitt/compose.py`](../src/querschnitt/compose.py); a bilingual parliament whose German and French readings "
  "disagree still goes to `please check`.")
w("")
w("| Design | rule | passed (share of affairs, n) | precision of the passed | `please check`: precision (n) |")
w("|---|---|---|---|---|")
for d in ("D4", "D1"):
    tp = lr["result"] if d == "D4" else lrm["D1: precision passed at recalibrated p ≥ 0.7"]
    tc = lrm["D4: precision of the rest (recalibrated p < 0.7 → please check)" if d == "D4" else "D1: precision of the rest (please check)"]
    ra = lrb["D4 readings agree (lane rule until 14 Oct)" if d == "D4" else "D1 readings agree"]
    sc = lrm["D4: recalibrated p, top affairs at the readings-agree coverage" if d == "D4" else "D1: recalibrated p at the readings-agree coverage"]
    nm = "**D4** (federal)" if d == "D4" else "D1 (no APS examples)"
    w(f"| {nm} | **recalibrated p ≥ 0.7 (shipped)** | {L(F.pct(tp['coverage']), tp['at'])}, {L(num(tp['n']), tp['at'])} | **{r(tp)}** | "
      f"{r(tc)} ({L(num(tc['n']), tc['at'])}) |")
    w(f"| {nm} | readings agree (rule until 14 Oct) | {L(F.pct(ra['coverage']), ra['at'])}, {L(num(ra['n']), ra['at'])} | {r(ra)} | — |")
    w(f"| {nm} | recalibrated p, same share as readings agree | {L(F.pct(sc['coverage']), sc['at'])}, {L(num(sc['n']), sc['at'])} | {r(sc)} | — |")
w("")
cal4 = d4["breakdowns"]["calibration"]; cs = T["aps_calibration_shipped"]
w(f"**Calibration of D4** ({L('S16', cal4['at'])}; isotonic, 2-fold cross-fitted, n {num(cal4['n'])}; the map the production run reads, "
  f"[`eval/calibration.json`](../eval/calibration.json)): expected calibration error {L(num(cal4['ece_raw'], 4), cal4['at'])} raw → "
  f"{L(num(cal4['ece_crossfit'], 4), cal4['at'])} recalibrated (D1, same file: {L(num(cs['results_more'][0]['raw'], 4), cs['results_more'][0]['at'])} → "
  f"{L(num(cs['results_more'][0]['value'], 4), cs['results_more'][0]['at'])}).")
w("")
st = d3["breakdowns"]["period_and_join"]
w("Per period, D3: " + " · ".join(f"{c['cell']} {L(num(c['value']) + ci(c['ci95']) + ', n ' + str(c['n']), st['at'])}" for c in st["cells"][:3]) + ".")
ln = d3["breakdowns"]["lanes_orders_agree_disagree"]
w("Lanes of D3 (S9; the two code orders agree / disagree): " + " · ".join(
    f"{c['cell']} {L(num(c['share']), ln['at'])} of affairs, D3 precision {L(num(c['precision']) + ci(c['ci95']), ln['at'])}" for c in ln["cells"]) + ".")
pc1, pc3 = d1["breakdowns"]["per_chapter"], d3["breakdowns"]["per_chapter"]
w(f"Per chapter: macro-F1 {L(num(pc1['macro_F1']), pc1['at'])} (D1), {L(num(pc3['macro_F1']), pc3['at'])} (D3) over the "
  f"{L(str(pc1['chapters']), pc1['at'])} chapters present.")
w("")

cal = T["aps_calibration"]
w("**Confidence (S9c, 2-fold cross-fitted isotonic recalibration, no new calls).** Expected calibration error:")
w("")
w("| | D0 | D1 | D3 |")
w("|---|---|---|---|")
rm = {x["metric"].split()[1]: x for x in cal["results_more"]}
w("| raw p | " + " | ".join(L(num(rm[d]["raw"]), rm[d]["at"]) for d in ("D0", "D1", "D3")) + " |")
w("| recalibrated | " + " | ".join(L(num(rm[d]["value"]), rm[d]["at"]) for d in ("D0", "D1", "D3")) + " |")
w("")
cur = P["curves"]
GRID = (0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
w("**Coverage–precision** (top-1 precision on the affairs that pass, ranked by confidence; the rest go to `please check`).")
w("")
w("| coverage | " + " | ".join(f"{int(c * 100)}%" for c in GRID) + " |")
w("|---|" + "---|" * len(GRID))
cf = "../eval/aps_curves.json"
for k, nm, link in (("aps_d4", "**D4 shipped** (S16)", href(cur["aps_d4"]["at"])), ("aps_d3", "D3 examples (S9)", cf), ("aps_d1", "D1 read-back (S9)", cf)):
    pts = [p for p in cur[k]["points"] if p["coverage"] in GRID]
    w(f"| {nm} | " + " | ".join(f"[{num(p['precision'])}{ci(p['ci'])}]({link})" for p in pts) + " |")
w("")
op, oo = cur["aps_d4"]["operating_point"], cur["aps_d4"]["operating_point_old"]
w(f"D4 points are read from {L('S16 coverage_precision', cur['aps_d4']['at'])} (one point per affair). "
  f"S9 rows recomputed from S9 raw logs by [`eval/scripts/aps_curves.py`](../eval/scripts/aps_curves.py) (full curve in 5% steps); the D3 precisions at "
  f"50, 70, 90 and 100% equal {L('S9 results.json', {'file': 'eval/spikes/s9-aps/results.json'})}. The app's chart is the D4 curve with "
  f"the shipped operating point marked: recalibrated p ≥ 0.7, coverage {L(F.pct(op['coverage']), op['at'])}, precision "
  f"{L(num(op['precision']) + ci(op['ci']), op['at'])} (chosen after S16 on these items; tested held out in S25, §1b); the earlier point, readings "
  f"agree, is shown for comparison: coverage {L(F.pct(oo['coverage']), oo['at'])}, precision {L(num(oo['precision']) + ci(oo['ci']), oo['at'])}.")
w("")

# ------------------------------------------------------------------ S25: the shipped design held out
m25 = h25["results_more"]; b25 = h25["breakdowns"]; l25 = b25["lanes"]; t25, pa25, pb25 = m25[0], m25[1], m25[2]
dd25 = {c["cell"]: c for c in b25["by_design"]["cells"]}
w(f"### 1b · APS chapter held out — {num(h25['n'], 0)} fresh federal affairs, the shipped design as in production (S25, pre-registered)")
w("")
w(f"The held-out test of the shipped federal design. §1's {num(d4['n'], 0)} items are the set the design was chosen on; none of these "
  f"{num(h25['n'], 0)} was used while designing. Items: federal affairs with an APS editors' chapter recovered from Wayback captures of "
  "anneepolitique.swiss process pages, none in the S5 or S9 sets or in the example pool (the analysis asserts it), parsed with the S9 rules "
  f"([`eval/s25/FETCH.md`](../eval/s25/FETCH.md)). The production pipeline as shipped, unchanged: D4 (the five BM25-nearest APS-labelled "
  "examples from the S5+S9 pool + a second reading without examples, chapter read back from the subtopic) for the "
  f"{L(num(dd25['D4']['n']), dd25['D4']['at'])} affairs with German text, D1 (no examples) for the {L(num(dd25['D1']['n']), dd25['D1']['at'])} "
  "whose text is French or Italian; lanes by the recalibrated p with the calibration map fitted on S16 only; decisions composed exactly as "
  "the export composes them ([`eval/s25/analyze.py`](../eval/s25/analyze.py) → [`eval/s25/results.json`](../eval/s25/results.json); "
  f"one line per affair in [`eval/s25/decisions.jsonl`](../eval/s25/decisions.jsonl)). Pre-registration: {L('PREREG-BUILD.md § S25', h25['prereg'])} "
  f"and {L('its amendment', h25['prereg_more'])} (a determinism fix before the final score).")
w("")
w(f"| n = {num(h25['n'], 0)}, gold = APS editors' chapter | top-1 | top-3 |")
w("|---|---|---|")
w(f"| **production pipeline as shipped, held out** | **{r(h25['result'])}** ({L(h25['result']['kn'], h25['result']['at'])}) | {r(t25)} |")
w(f"| keyword (S9 frozen rule, same input) | {r(h25['baselines'][0])} | — |")
w(f"| for reference: D4 on the design set (§1, other items, not held out) | {r(d4['result'])} | {r(m4[0])} |")
w("")
w(f"**Before the fix** ({L('amendment', h25['prereg_more'])}): the BM25 example retrieval summed over a Python set, whose order is "
  "randomised per process, so a restarted run could ask different examples for the same affair. Two compositions of the finished run "
  f"were seen with the old retrieval before the fix: {L(num(pa25['n']), pa25['at'])} scored, top-1 {L(num(pa25['value'], 4) + ' (' + pa25['kn'] + ')', pa25['at'])}"
  f"{ci(pa25['ci95'])}, and {L(num(pb25['n']), pb25['at'])} scored, {L(num(pb25['value'], 4) + ' (' + pb25['kn'] + ')', pb25['at'])}{ci(pb25['ci95'])} "
  "(Wilson intervals computed here from k and n). The final score above is the fixed code on all "
  f"{num(h25['n'], 0)} affairs, scored once.")
w("")
lr_pass, lr_chk = lr["result"], lrm["D4: precision of the rest (recalibrated p < 0.7 → please check)"]
lr_agree = lrb["D4 readings agree (lane rule until 14 Oct)"]
DS = {"pass": lr_pass, "please_check": lr_chk, "readings_agree": lr_agree,
      "readings_disagree": {"value": ld["precision"], "ci95": ld["ci95"], "n": ld["n"], "at": ln4["at"]}}
w(f"| S25 lane, held out | share of affairs (n) | precision | design set, for reference (§1, {num(d4['n'], 0)} items: n, precision) |")
w("|---|---|---|---|")
for k_, nm_ in (("pass", "**pass: recalibrated p ≥ 0.7 (shipped)**"), ("please_check", "`please check`: recalibrated p < 0.7"),
                ("readings_agree", "readings agree (earlier rule)"), ("readings_disagree", "readings disagree")):
    c_ = l25[k_]; ref_ = DS[k_]
    pv = f"**{r(c_)}**" if k_ == "pass" else r(c_)
    w(f"| {nm_} | {L(F.pct(c_['share']), c_['at'])} ({L(num(c_['n']), c_['at'])}) | {pv} | {L(num(ref_['n']), ref_['at'])}, {r(ref_)} |")
w("")
w("The design-set figures of the recalibrated rule are in-sample for the choice of the 0.7 threshold (2-fold cross-fitted map); in S25 the map "
  "is the one fitted on S16 and the threshold is fixed.")
w("")
rp = b25["routing_by_p_cal"]["points"]
w("**Routing by the recalibrated p** (S25, held out; coverage = share of affairs at or above the threshold, precision of those):")
w("")
w("| recalibrated p ≥ | " + " | ".join(num(x["threshold"], 1) for x in rp) + " |")
w("|---|" + "---|" * len(rp))
w("| coverage | " + " | ".join(L(F.pct(x["coverage"]), x["at"]) for x in rp) + " |")
w("| precision | " + " | ".join(r(x) for x in rp) + " |")
w("| n | " + " | ".join(L(num(x["n"]), x["at"]) for x in rp) + " |")
w("")
cy = b25["curia_year"]; gc = b25["gold_chapters"]
w(f"By design: D4 (German text, five examples) {r(dd25['D4'])}, n {num(dd25['D4']['n'])}; D1 (French or Italian text, no examples) "
  f"{L(dd25['D1']['kn'], dd25['D1']['at'])}{ci(dd25['D1']['ci95'])} (small). By Curia year: {L(num(cy['before_2015']), cy['at'])} affairs "
  f"submitted before 2015, {L(num(cy['from_2015']), cy['at'])} from 2015 on. Gold chapters ({L(str(gc['chapters']), gc['at'])} present): "
  + " · ".join(f"{c_} {L(str(v_), gc['at'])}" for c_, v_ in gc["counts"].items()) + ".")
w("")

sub = T["aps_subtopic"]
w(f"### 2 · APS subtopic vs APS editors, end to end (S9)")
w("")
w("| n | top-1 | top-3 | gold chapter in the shortlist | baseline: D0 chapter → best subtopic |")
w("|---|---|---|---|---|")
w(f"| {num(sub['n'], 0)} | {r(sub['result'])} | {r(sub['results_more'][0])} | {r(sub['results_more'][1])} | {r(sub['baselines'][0])} |")
w("")
w("Subtopics ship as ranked suggestions, not as a lane.")
w("")
th = T["aps_hierarchical_d4"]
N_ALL = th["results_more"][-1]["n"]
hm = {x["metric"]: x for x in th["results_more"]}; hb = {x["name"]: x for x in th["baselines"]}
w(f"**Hierarchical metrics of the shipped design D4** — computed after S16 from its rows (not pre-registered; no new calls) by "
  f"[`eval/s16/hierarchical.py`](../eval/s16/hierarchical.py). Same {num(th['n'], 0)} items as above (chapter + subtopic gold); "
  "hierarchical precision / recall / F1 after Kiritchenko et al. (predicted and gold sets augmented with their ancestors, levels "
  "chapter and subtopic, micro-averaged); per-chapter F1 is the chapter top-1, one vs rest, macro over the "
  f"{L(str(hm['per-chapter F1, macro over the chapters present (D4)']['chapters']), hm['per-chapter F1, macro over the chapters present (D4)']['at'])} "
  f"chapters present, on all {num(hm['per-chapter F1, macro over the chapters present (D4)']['n'], 0)} items. Intervals: Wilson for the subtopic "
  "rates, percentile bootstrap 2,000 for hP/hR/hF and macro-F1 (stratified by gold chapter), bounds rounded outward.")
w("")
w("| Design | subtopic top-1 | subtopic top-3 | subtopic top-1 when the chapter is right | hP | hR | hF | per-chapter macro-F1 |")
w("|---|---|---|---|---|---|---|---|")
g4 = hm["subtopic top-1 given the chapter is right (D4)"]
w(f"| **D4 shipped** | **{r(hm['subtopic top-1 end to end (D4)'])}** | {r(hm['subtopic top-3 end to end (D4)'])} | {r(g4)} (n {num(g4['n'])}) | "
  f"{r(hm['hierarchical precision (D4)'])} | {r(hm['hierarchical recall (D4)'])} | **{r(th['result'])}** | "
  f"{r(hm['per-chapter F1, macro over the chapters present (D4)'])} |")
HN = {"D1": "D1 read back from the subtopic, no examples (same items)", "D0": "D0 plain list prompting, best subtopic within its chapter (same items)",
      "keyword": "keyword (APS subtopic words, frozen; chapter only)"}
for d, nm in (("D1", "D1 read-back, no examples"), ("D0", "D0 list prompting → best subtopic in its chapter"), ("keyword", "keyword (chapter only)")):
    if d == "keyword":
        sub_cells = "— | — | —"
    else:
        gx = hb[f"{d} subtopic top-1 given chapter right"]
        sub_cells = f"{r(hb[f'{d} subtopic top-1'])} | {r(hb[f'{d} subtopic top-3'])} | {r(gx)} (n {num(gx['n'])})"
    w(f"| {nm} | {sub_cells} | {r(hb[f'{d} hP'])} | {r(hb[f'{d} hR'])} | {r(hb[HN[d]])} | {r(hb[f'{d} per-chapter macro-F1'])} |")
w("")
ah = th["breakdowns"]["all_items_hF"]
w(f"D4 and D1 always name one chapter and one subtopic, so hP = hR = hF for them (the mean of chapter and subtopic top-1); "
  f"D0 predicts the chapter only when its chapter is not in the subtopic shortlist, the keyword baseline always. "
  f"The conditional rate is over each design's own correct-chapter items, so it is not a paired comparison. "
  f"On all {num(N_ALL, 0)} items (gold depth 1 where the main subtopic is not among the 190): D4 hF {r(ah)}.")
w("")

dv = T["dvs_human30"]
w("### 3 · “Digitalisierung”: the 30 affairs DVS curates by hand (recall)")
w("")
w("| | all 30 | begun in 2026 |")
w("|---|---|---|")
w(f"| Querschnitt (yes/no, p ≥ 0.5) | {L('27/30', dv['result']['at'])}{ci(dv['result']['ci95'])} | {L('23/24', dv['results_more'][0]['at'])}{ci(dv['results_more'][0]['ci95'])} |")
w(f"| keyword list (29 stems, de/fr/it) | {L('21/30', dv['baselines'][0]['at'])}{ci(dv['baselines'][0]['ci95'])} | {L('16/24', dv['baselines'][1]['at'])}{ci(dv['baselines'][1]['ci95'])} |")
w(f"| the AI judge, for reference (S15) | {L('27/30', dv['results_more'][1]['at'])}{ci(dv['results_more'][1]['ci95'])} | — |")
w("")
w(f"Split: {dv['split']}.")
w("")

cu = T["curia_sachbereiche"]
w("### 4 · Federal Sachbereiche vs Parliament's own Curia tags (all tags per affair)")
w("")
w("| n = 200, submitted after the BFH model | micro-F1 | macro-F1 | top-1 is a gold tag |")
w("|---|---|---|---|")
bf = cu["baselines"][0]
w(f"| Apertus: 5 retrieved tagged examples + yes/no check of the top 6 | {r(cu['result'])} | {r(cu['results_more'][0])} | "
  f"{r(cu['results_more'][1])} (no examples) |")
w(f"| BFH model, trained on {L('15,007', bf['training_size_at'])} tagged affairs | {r(bf)} | {L('0.577 [0.525, 0.642]', bf['at'])} | "
  f"{L(num(bf['top1']) + ci(bf['top1_ci95']), bf['at'])} |")
w("")
w(f"Paired micro-F1 difference Apertus − BFH: {L('−0.079 to +0.010', cu['results_more'][2]['at'])}. Split: {cu['split']}. "
  "Example pool: 52,408 affairs tagged before 6 Nov 2024.")
w("")

bp, be = T["bern_directorates_production"], T["bern_directorates"]
w("### 5 · Bern: lead directorate (8 directorates, scheme swap) vs the Grand Council's own field, titles only")
w("")
w(f"Production run, every affair begun 2025–26 with a lead directorate (S18, {L('pre-registered', bp['prereg'])}; nothing tuned), and the "
  "earlier random sample of affairs since 2015 (S6, one run).")
w("")
mp = bp["results_more"]; kp = bp["baselines"]
w("| | n | German title | French title | German − French, paired | keyword stems DE / FR | majority |")
w("|---|---|---|---|---|---|---|")
w(f"| **S18, 2025–26, production run** | {num(bp['n'])} | **{r(bp['result'])}** | {r(mp[0])} (n {num(mp[0]['n'])}) | {r(mp[1], signed=True)} "
  f"(n {num(mp[1]['n'])}) | {r(kp[0])} / {r(kp[1])} | {r(kp[2])} ({kp[2]['name'].split('(')[1].rstrip(')')}) |")
kb = be["baselines"][0]
w(f"| S6, since 2015, random 200 | {num(be['n'])} | {r(be['result'])} | {r(be['results_more'][0])} | {r(be['results_more'][2], signed=True)} | "
  f"{L(num(kb['value'][0]) + ci(kb['ci95'][0]), kb['at'])} / {L(num(kb['value'][1]) + ci(kb['ci95'][1]), kb['at'])} | {r(be['baselines'][1])} (BVD) |")
w("")
w(f"S6, German and French averaged: {r(be['results_more'][1])}. Directorate descriptions in the scheme file were written by the agent; "
  "keyword stems were frozen before any result.")
w("")

bs0, bs1 = T["basel_themes_names"], T["basel_themes_examples"]
w(f"### 6 · Basel-Stadt: the canton's own 46 themes vs its hand-assigned «Thema 1», all {num(bs0['n'])} Grand Council affairs 2019–24 (S20, S21)")
w("")
w(f"Gold: the themes the canton's Kantons- und Stadtentwicklung assigned by hand (OGD dataset 100086), joined to OpenParlData by number. "
  f"S20 hands over the 46 theme names as a scheme file, verbatim, no descriptions, nothing tuned ({L('pre-registered', bs0['prereg'])}). "
  f"S21 adds five of Basel's own labelled affairs as examples, always from the other half of the data, no training "
  f"({L('pre-registered', bs1['prereg'])}, paired against S20 on the same items).")
w("")
m0, m1 = bs0["results_more"], bs1["results_more"]
w("| Design | top-1 = Thema 1 | Thema 1 or 2 | top-3 | readings agree: share, precision | readings disagree: precision |")
w("|---|---|---|---|---|---|")
la0, lc0 = bs0["breakdowns"]["lane_readings_agree"], bs0["breakdowns"]["lane_please_check"]
la1, lc1 = bs1["breakdowns"]["lane_agree"], bs1["breakdowns"]["lane_disagree"]
w(f"| S20 theme names only | {r(bs0['result'])} | {r(m0[0])} | {r(m0[1])} | {L(F.pct(la0['share']), la0['at'])}, {r(la0)} | {r(lc0)} |")
w(f"| S21 + five Basel examples (two readings, D4 shape) | **{r(bs1['result'])}** | {r(m1[1])} | {r(m1[2])} | "
  f"{L(F.pct(la1['share']), la1['at'])}, {r(la1)} | {r(lc1)} |")
w(f"| keyword stems (frozen) | {r(bs0['baselines'][0])} | — | — | — | — |")
w(f"| majority theme ({bs0['baselines'][1]['name'].split('(')[1].rstrip(')')}) | {r(bs0['baselines'][1])} | — | — | — | — |")
w("")
w(f"S21 − S20, paired: {r(m1[0], signed=True)}. S20 − keyword, paired: {r(m0[2], signed=True)}.")
w("")
bt = bs0["breakdowns"]["by_type"]
w("S20 by affair type: " + " · ".join(f"{c['cell']} {L(num(c['value']) + ci(c['ci95']) + ', n ' + str(c['n']), bt['at'])}"
                                      for c in bt["cells"] if not c.get("small")) + " (types with n < 20 not shown).")
w("")

an, jd = T["judge_anchor_aps"], T["judge_dvs_human"]
w("### 7 · The AI judge itself against human labels")
w("")
w("| Test | n | AI judge (Claude, blind) | Apertus, same items |")
w("|---|---|---|---|")
bl = {x["name"]: x for x in an["baselines"]}
w(f"| APS chapter = APS editors' chapter (S11) | 200 | {r(an['result'])}; second code included {r(an['results_more'][2])}; "
  f"run A = run B {r(an['results_more'][1])} | D1 {r(bl['Apertus D1 on the same 200'])} · D3 {r(bl['Apertus D3 on the same 200'])} |")
w(f"| says yes to the 30 DVS items (S15) | 30 | {L('27/30', jd['result']['at'])}{ci(jd['result']['ci95'])} both runs "
  f"(run B {L('28 of 30', jd['results_more'][1]['at'])}) | {L('27/30', T['dvs_human30']['result']['at'])} |")
w("")
w("The judge's precision on human negatives is not measured (no human negatives exist).")
w("")

ns = T["neutrality_s9"]
bd = ns["breakdowns"]
w("### 8 · Neutrality on human labels (S9, no new calls; S22 Italian)")
w("")
w(f"Language, same {num(ns['n'], 0)} affairs scored from the German vs the French text (paired): German − French "
  f"{r(ns['result'], signed=True)}, McNemar p {ns['result']['p_mcnemar']}.")
w("")
it = T["aps_italian_vs_german"]; im = it["results_more"]; idf = im[0]; ide = it["baselines"][0]
iwt, ito = im[3], im[4]
w(f"**Italian vs German (S22, {L('pre-registered', it['prereg'])}).** The S9 affairs whose Italian title differs from the French one "
  f"({num(it['n'], 0)} of {num(ns['n'], 0)}), gold the APS editors' chapter; Italian title + long title + the Italian submitted text "
  "where it differs from the French, D1 in the Italian frame (chapter names Italian, subtopic names German as published), both code orders; "
  "paired against the S9 German D1 on the same affairs.")
w("")
w("| n = " + num(it["n"], 0) + " | Italian | German (S9 D1) | German − Italian, paired |")
w("|---|---|---|---|")
w(f"| chapter top-1 | **{r(it['result'])}** | {r(ide)} | {L(sgn(idf['value'], 4) + ci(idf['ci95'], 3, signed=True), idf['at'])} |")
w(f"| chapter top-3 | {r(im[1])} | {r(im[2])} | |")
w(f"| with Italian submitted text (n {num(iwt['n'])}) | {r(iwt)} | {r(iwt['german_same_items'])} | |")
w(f"| title only (n {num(ito['n'])}) | {r(ito)} | {r(ito['german_same_items'])} | |")
w("")
w("Shares are k / n recovered from the stored 4-decimal values and truncated; the difference is a paired bootstrap (2,000), "
  "shown at 4 decimals because it is near zero, bounds rounded outward.")
w("")


def cell_table(title, blocks, labels):
    """blocks: list of cells() dicts with the same cell order; labels: column names."""
    w(f"| {title} | " + " | ".join(labels) + " |")
    w("|---|" + "---|" * len(labels))
    names = [c["cell"] for c in blocks[0]["cells"]]
    for i, nm in enumerate(names):
        row = []
        for bk in blocks:
            c = next((x for x in bk["cells"] if x["cell"] == nm), None)
            row.append("—" if c is None else L(num(c["value"]) + ci(c["ci95"]) + f", n {c['n']}", bk["at"]) + (" (small)" if c.get("small") else ""))
        w(f"| {nm} | " + " | ".join(row) + " |")
    tests = []
    for bk in blocks:
        t = bk["test"]; g = bk.get("largest_gap") or {}
        s = f"p {t['p_perm']}" if t.get("p_perm") is not None else ""
        if g.get("diff") is not None:
            s += f"; gap {g['hi']} − {g['lo']} {sgn(g['diff'])}{ci(g['ci95'], signed=True)}"
        tests.append(L(s, bk["at"]) if s else "—")
    w("| *test (cells n ≥ 20)* | " + " | ".join(tests) + " |")
    w("")


cell_table("S9 by party", [bd["party_D1_top1"], bd["party_keyword_top1"]], ["D1 top-1", "keyword top-1"])
cell_table("S9 by instrument", [bd["instrument_D1_top1"], bd["instrument_keyword_top1"]], ["D1 top-1", "keyword top-1"])
w("Reading: top-1 differs too little to measure with these sample sizes by language and among the six main parties (this is not "
  "evidence of no difference; the party gaps' intervals are wide). Government business scores higher than members' motions, and the "
  "keyword baseline shows the same order (easier texts, not a political tilt). Quality is reported per submitter type.")
w("")

fg = T["free_generation"]
w("### 9 · Free naming without a list (rule check)")
w("")
w(f"Asked to name a topic freely, Apertus answered outside both the Curia 28 and the APS label sets in {L('36/40', fg['result']['at'])} "
  f"({num(fg['result']['value'])}{ci(fg['result']['ci95'])}) and never answered “no topic” ({L('0/40', fg['results_more'][0]['at'])}); with the list shown, "
  f"{L('0/40', fg['results_more'][1]['at'])} were off-list. Every shipped decision is a choice among listed codes.")
w("")

# ------------------------------------------------------------------ AI judge
w("## AI-judge rows")
w("")
w("Gold where no official labels exist: a blind AI judge (two runs of a Claude model + a tie-break run, cross-checked by the open-weights "
  "Qwen-SEA-LION). Its agreement with human labels is in §7 above. Every figure below is agreement with that judge.")
w("")
c8, s8 = T["dvs_2026_census"], T["dvs_2026"]
mc = {x["metric"]: x for x in c8["results_more"]}
kc = c8["baselines"][0]
cen = c8["breakdowns"]["census"]
w(f"### 10 · “Digitalisierung” in Swiss parliaments, 2026: full census (S8 design, pre-registered)")
w("")
w(f"Population: all {L(num(c8['n']), mc['affairs flagged (counted, Swiss)']['at'])} Swiss affairs begun 1 Jan–6 Oct 2026 with a title. Every one of the "
  f"{L(num(cen['window']), cen['at'])} affairs in the window (Liechtenstein included) is decided ({L(num(cen['from_s8_rows']), cen['at'])} from the S8 rows, {L(num(cen['from_production_run']), cen['at'])} from the production run with "
  f"the same prompt and build, {L(num(cen['missing']), cen['at'])} missing), so flags are counted, not estimated. Precision and recall use the same "
  f"{num(c8['n_checked'])} checked Swiss affairs and the same judge as S8, weights post-stratified to the census strata; flag at p ≥ 0.5, fixed before "
  f"the run ({L('PREREG.md § S8', c8['prereg'])}). Recomputed by [`eval/s8full/analyze.py`](../eval/s8full/analyze.py), no model calls.")
w("")
w("| full census, 95% interval | Querschnitt | keyword list (29 stems) | difference, bootstrap |")
w("|---|---|---|---|")
kat = {"file": kc["at"]["file"], "key": "gold_AB_C"}
w(f"| precision vs the judge | **{r(c8['result'])}** | {L(num(kc['precision']) + ci(kc['precision_ci95']), kat)} | "
  f"{r(mc['Δ precision Apertus − keyword'], signed=True)} |")
w(f"| recall vs the judge | {r(mc['recall vs the judge (Swiss)'])} | {L(num(kc['recall']) + ci(kc['recall_ci95']), kat)} | "
  f"{r(mc['Δ recall Apertus − keyword'], signed=True)} |")
fl, pf, pc = mc["affairs flagged (counted, Swiss)"], mc["parliaments with at least one flag (Swiss)"], mc["flags in the please-check lane (Swiss)"]
fa = c8["breakdowns"]["flags_all_bodies_incl_LIE"]
w(f"| affairs flagged (counted) | {r(fl)} in {r(pf)} parliaments ({r(pc)} in `please check`) | {L(num(kc['flags']), fl['at'])}; "
  f"both {L(num(kc['both']), fl['at'])} | |")
mq = mc["gold = majority of Claude A, B, Qwen: precision / recall"]
w(f"| gold = majority of Claude A, B and Qwen: precision / recall | {L(num(mq['value'][0]) + ci(mq['ci95'][0]) + ' / ' + num(mq['value'][1]) + ci(mq['ci95'][1]), mq['at'])} | "
  f"{L(num(kc['majority_gold'][0]) + ci(kc['majority_gold_ci95'][0]) + ' / ' + num(kc['majority_gold'][1]) + ci(kc['majority_gold_ci95'][1]), mq['at'])} | |")
w("")
pos = mc["estimated digitalisation affairs (judge positives, Swiss)"]
w(f"Estimated digitalisation affairs (judge positives): {L(num(pos['value'], 0) + ci(pos['ci95']), pos['at'])}. Including Liechtenstein: "
  f"{L(num(fa['apertus']), fa['at'])} flagged by Querschnitt, {L(num(fa['keyword']), fa['at'])} by keywords, of {L(num(fa['n']), fa['at'])}. "
  f"The differences are bootstrap intervals; their point is the difference of the two stored points. "
  f"Judge: run A = run B {L(num(s8['judge']['AB'][1]), s8['judge']['at'])} (κ {L(num(s8['judge']['AB'][2]), s8['judge']['at'])}); "
  f"Qwen vs the runs κ {L(num(s8['judge']['AQ'][2]), s8['judge']['at'])} / {L(num(s8['judge']['BQ'][2]), s8['judge']['at'])}.")
w("")
m = {x["metric"]: x for x in s8["results_more"]}
kb = s8["baselines"][0]
ch = {"file": "eval/spikes/s8-dvs/score_ch.json"}
af = m['estimated flags (Swiss)']; ps = m["estimated digitalisation affairs (judge positives, Swiss)"]
q = m["judge = Qwen alone: precision / recall"]
w(f"**History: the S8 snapshot** ({num(s8['n'])} Swiss affairs in the 6 Oct window, of which the census run had scored 8,139 when it was paused; "
  f"flags estimated from the last week in full and 5,338 of 14,212 earlier affairs at random). Superseded above for counts and judge precision/recall; kept for the record: precision {r(s8['result'])}, "
  f"recall {r(m['recall vs the judge (Swiss)'])}, estimated flags {L(num(af['value'], 0) + ci(af['ci95']), ch)} (keywords "
  f"{L(num(kb['flags'], 0) + ci(kb['flags_ci95']), ch)}), estimated positives {L(num(ps['value'], 0) + ci(ps['ci95']), ps['at'])}; keyword precision "
  f"{L(num(kb['precision']) + ci(kb['precision_ci95']), ch)}, recall {L(num(kb['recall']) + ci(kb['recall_ci95']), ch)}; judge = Qwen alone "
  f"{L(num(q['value'][0]) + ' / ' + num(q['value'][1]), q['at'])} (keywords {L(num(kb['qwen_only'][0]) + ' / ' + num(kb['qwen_only'][1]), q['at'])}). "
  "The breakdowns below are still on the snapshot's weights.")
w("")
bd = s8["breakdowns"]
pz = bd["positives_in_checked_sample"]
w(f"Judge-confirmed Swiss positives in the checked sample: {L(str(pz['n']), pz['at'])} from {L(str(pz['parliaments']), pz['at'])} parliaments — "
  + L(f"cantonal {pz['by_level']['cantonal']}, federal {pz['by_level']['federal']}, communal {pz['by_level']['communal']}; "
      f"German {pz['by_lang']['de']}, French {pz['by_lang']['fr']}, Italian {pz['by_lang']['it']}", pz['at']) + ".")
w("")
w("Per language and level (all 464 checked items incl. Liechtenstein, snapshot weights; S14):")
w("")
cell_table("S8 by language", [bd["language_precision"], bd["language_recall"]], ["precision", "recall"])
cell_table("S8 by level", [bd["level_precision"], bd["level_recall"]], ["precision", "recall"])
cell_table("S8 by submitter party", [bd["party_precision"], bd["party_keyword_precision"]], ["Querschnitt precision", "keyword precision"])
gp_ = bd["party_precision"]
w(f"The party test (p {gp_['test']['p_perm']}) comes from the small SVP cell (7 of 11 confirmed); keyword precision dips on the same items (7/20). "
  f"Among cells with n ≥ 20 the gap is {L(sgn(gp_['largest_gap']['diff']) + ci(gp_['largest_gap']['ci95'], signed=True), gp_['at'])}. "
  "Canton cells are below n = 20 except BS and are not read.")
w("")
pb = bd["per_body_flags"]
w(f"Per parliament (snapshot: flag counts in the scored sample, {L('S8 results', pb['at'])}; estimated flags point only, no per-body gold) — the ten largest:")
w("")
w("| body | level | affairs in 2026 | scored | flagged | est. flags | keyword hits |")
w("|---|---|---|---|---|---|---|")
for row in pb["rows"][:10]:
    w(f"| {row['body']} | {row['level']} | " + " | ".join(L(num(row[k], 1) if isinstance(row[k], float) else num(row[k], 0), pb['at'])
                                                          for k in ('N window', 'sample n', 'flags (sample)', 'est. flags', 'kw (sample)')) + " |")
w("")
w(f"All bodies: [`eval/pruefstand.json`](../eval/pruefstand.json) → `dvs_2026.breakdowns.per_body_flags`.")
w("")

s17 = T["aps_communal_production"]
b17 = s17["breakdowns"]; j17 = s17["judge"]
w("### 11 · APS chapter, communal parliaments 2026: the production run vs the judge (S17, pre-registered)")
w("")
w(f"200 communal affairs begun 1 Jan–11 Oct 2026, drawn at random among those with a shipped chapter (S6 items excluded); the chapter as "
  f"shipped by the production run (read back from the subtopic, no examples). Judge: two blind Claude runs on the exact production input, "
  f"tie-break run on the {L(str(j17['disagreements']), j17['at'])} disagreements; κ {L(num(j17['kappa_AB']), j17['at'])} "
  f"({L('PREREG-BUILD.md § S17', s17['prereg'])}).")
w("")
w("| n = 200 | top-1 | top-3 |")
w("|---|---|---|")
w(f"| shipped chapter | **{r(s17['result'])}** | {r(s17['results_more'][0])} |")
w(f"| frozen S9 keyword baseline | {r(s17['baselines'][0])} | — |")
w(f"| majority chapter of the sample's gold (computed after) | {r(s17['baselines'][1])} | — |")
w("")
w("| cell | top-1 | n |")
w("|---|---|---|")
for k, nm in (("lane_readings_agree", "lane: readings agree"), ("lane_please_check", "lane: please check"), ("lang_de", "German"),
              ("lang_fr", "French"), ("lang_it", "Italian"), ("with_text", "with text"), ("title_only", "title only")):
    c = b17[k]; w(f"| {nm} | {r(c)} | {L(str(c['n']), c['at'])} |")
w("")

lp, tx, ev = T["dvs_correction_loop"], T["dvs_text_lever"], T["evidence_support"]
w("### 12 · Correction loop, text input, evidence")
w("")
w("| Test | n | Result | Same items, without |")
w("|---|---|---|---|")
w(f"| Correction loop (simulated, P8.5): 60 judge labels shown as an editor's first decisions, 4 nearest per affair | {lp['n']} | "
  f"F1 {r(lp['result'])}; Δ {r(lp['results_more'][0], signed=True)} | F1 {L(num(lp['baselines'][0]['F1']), lp['baselines'][0]['at'])} |")
tv = tx["result"]; tb = tx["baselines"][0]
w(f"| Submitted text added to title (S8b, federal) | {tx['n']} | precision {L(num(tv['value'][0]) + ci(tv['ci95'][0]), tv['ci_at'])}, "
  f"recall {L(num(tv['value'][1]) + ci(tv['ci95'][1]), tv['ci_at'])}; Δ recall {r(tx['results_more'][0], signed=True)} | "
  f"title only: {L(num(tb['value'][0]) + ci(tb['ci95'][0]) + ', ' + num(tb['value'][1]) + ci(tb['ci95'][1]), tb['at'])} |")
em = {x["metric"]: x for x in ev["results_more"]}
w(f"| Evidence: the quoted sentence supports the chapter (S12) | {ev['n']} | {r(ev['result'])}; chapter right {r(em['when the chapter is right (APS editors)'])}, "
  f"wrong {r(em['when the chapter is wrong'])} | exact-substring check {L('120/120', em['quote is an exact substring']['at'])} |")
ep = T["evidence_support_production"]; pm = {x["metric"]: x for x in ep["results_more"]}
pu = pm["quote is the exact substring at its stored offsets (inputs unchanged since the row)"]
pa = pm["quote is the exact substring at its stored offsets (all rows)"]
w(f"| **Production check:** evidence on 200 stored quotes of the 2026 production run, the quoted sentence supports the topic (S23) | {ep['n']} | "
  f"**{r(ep['result'])}**; chapter quotes {r(pm['chapter quotes (shipped APS chapter)'])}, «Digitalisierung» quotes "
  f"{r(pm['«Digitalisierung» quotes'])} | exact substring at the stored offsets {L(str(pu['k']) + '/' + str(pu['n']), pu['at'])} "
  f"(inputs unchanged since the row; {L(str(pa['k']) + '/' + str(pa['n']), pa['at'])} of all rows) |")
w("")
w("The loop row is unweighted and on a sample that over-represents flagged affairs; text makes the model stricter, not more complete.")
w("")
pj = ep["judge"]; pb_ = ep["breakdowns"]
w(f"S23 ({L('PREREG-BUILD.md § S23', ep['prereg'])}) draws 100 chapter quotes (the shipped APS chapter) and 100 «Digitalisierung» quotes "
  f"(flagged or please-check rows) at random among 2026 affairs with a stored quote; the packet shows the input as the model saw it. "
  f"Judge: two blind Claude runs, run A = run B {r(pm['judge run A = run B'])}, κ {L(num(pj['kappa_AB'], 2), pj['at'])}; "
  f"{L(str(pj['disagreements']), pj['at'])} disagreements went to a tie-break run. S12 ({num(ep['baselines'][0]['value'])} on "
  f"{ep['baselines'][0]['n']} federal affairs) is a descriptive comparison only, not a test. By level: "
  + " · ".join(f"{c['cell']} {L(num(c['value']) + ci(c['ci95']) + ', n ' + str(c['n']), pb_['by_level']['at'])}" + (" (small)" if c.get("small") else "")
               for c in pb_["by_level"]["cells"]) + ".")
w("")

s6 = T["aps_cantonal_communal"]
bd = s6["breakdowns"]
w("### 13 · APS chapter, cantonal and communal (S6, cross-checked S7)")
w("")
w("| cell | top-1 vs the judge | n |")
w("|---|---|---|")
w(f"| all | {r(s6['result'])} | {L(str(s6['result']['n']), s6['result']['at'])} |")
for k, nm in (("level_cantonal", "cantonal"), ("level_communal", "communal"), ("lang_de", "German"), ("lang_fr", "French"), ("lang_it", "Italian"),
              ("with_text", "with text"), ("title_only", "title only"), ("first_reading_p_ge_0.9", "first reading p ≥ 0.9"),
              ("readings_disagree", "the two readings disagree")):
    c = bd[k]; w(f"| {nm} | {r(c)} | {L(str(c['n']), c['at'])} |")
mj = s6["results_more"][0]
w(f"| gold = majority of Claude ×2 + Qwen | {r(mj)} | {L(str(mj['n']), mj['at'])} |")
w("")
cell_table("S6 by canton", [bd["canton"]], ["top-1"])

s10 = T["aps_bilingual"]
bd = s10["breakdowns"]
w("### 14 · Bilingual cantons BE, FR, VS — German vs French titles (S10, pre-registered)")
w("")
w("| n = 210 | German | French | averaged |")
w("|---|---|---|---|")
w(f"| chapter top-1 | {r(s10['result'])} | {r(s10['results_more'][0])} | {r(s10['results_more'][1])} |")
t3 = s10["results_more"][3]
w(f"| gold in top 3 | {L(num(t3['value'][0]), t3['at'])} | {L(num(t3['value'][1]), t3['at'])} | {L(num(t3['value'][2]), t3['at'])} |")
for c in ("BE", "FR", "VS"):
    x = bd["canton"][c]
    w(f"| {c} | {r(x['de'])} | {r(x['fr'])} | {r(x['pooled'])} |")
w("")
ag = bd["languages_agree"]
w(f"German − French {r(s10['results_more'][2], signed=True)} (paired; no measurable gap at n = 210). The two languages agree on "
  f"{L('70.5%', ag['at'])}: chapter right {r(ag)}; where they disagree, German {r(bd['languages_disagree_de'])}, French "
  f"{r(bd['languages_disagree_fr'])} — that third goes to a person. Clerk load: {L(bd['clerk_load']['value'], bd['clerk_load']['at'])}.")
w("")

# ------------------------------------------------------------------ S19 / S26 / S27: new topics defined in one sentence
a19, a26, a27 = T["adhoc_new_topics"], T["adhoc_editor_examples"], T["adhoc_verification"]
TOP = a19["topics"]
p19, p26, p27 = a19["breakdowns"]["per_topic"], a26["breakdowns"]["per_topic"], a27["breakdowns"]["per_topic"]
EN = {s_: p19[s_]["name_en"] for s_ in TOP}


def rk(block, d=3):
    """value [lo, hi] (k/n), linked."""
    return L(num(block["value"], d) + ci(block.get("ci95"), d) + (f" ({block['kn']})" if block.get("kn") else ""), block["at"])


def cnt(block):
    return L(num(block["value"], 0), block["at"])


def nm(block):
    """a block that may be not measurable."""
    return block["not_measurable"] if block.get("value") is None else None


j19 = a19["judge"]; neither = {s_: next(c for c in p19[s_]["strata"]["cells"] if c["cell"] == "neither") for s_ in TOP}
w("### 15 · Three new topics defined in one sentence: wolf, heat protection, AI in schools (S19, S26, S27, pre-registered)")
w("")
w(f"The three S13 topics never used in any tuning, each a one-sentence question "
  f"([`src/querschnitt/schemes/adhoc/`](../src/querschnitt/schemes/adhoc/)): «{p19['wolf']['name_de']}», «{p19['hitze']['name_de']}», "
  f"«{p19['ki-schule']['name_de']}». Population: every affair with a title begun 1 Aug–6 Oct 2026 "
  f"({L(num(a19['n']), p19['wolf']['strata']['at'])}), decided with the shipped yes/no rule (flag at mean p ≥ 0.5). Checked: every affair flagged "
  f"by Apertus or by the frozen keyword list ([`eval/s19/keywords_frozen.json`](../eval/s19/keywords_frozen.json)), plus "
  f"{L(str(neither['wolf']['n']), p19['wolf']['strata']['at'])} random affairs flagged by neither, per topic ({num(a19['n_checked'])} in all). "
  f"Judge: two blind Claude runs (A shuffled, B reversed; run A = run B {L(num(j19['agree_AB']), j19['at'])}), a tie-break run on the "
  f"{L(str(j19['tie_break_C']), {'file': j19['tie_break_at']['file']})} disagreements. Recall is weighted back to the population (stratified "
  f"bootstrap 2,000). The Qwen-SEA-LION cross-check named in the pre-registration is not in the S19 results. Every figure in this section "
  f"is agreement with the AI judge, not with human labels ({L('PREREG-BUILD.md § S19', a19['prereg'])}, "
  f"{L('§ S26', a26['prereg'])}, {L('§ S27', a27['prereg'])} and {L('its amendment', a27['prereg_more'])}).")
w("")
w("| S19, agreement with the AI judge | flagged (counted) | precision of flags | recall, weighted | keyword list: precision / recall (hits) | relevant affairs, estimated |")
w("|---|---|---|---|---|---|")
for s_ in TOP:
    b_ = p19[s_]
    w(f"| {EN[s_]} | {cnt(b_['flags'])} | **{rk(b_['precision'])}** | {r(b_['recall'])} | {r(b_['keyword_precision'])} / "
      f"{r(b_['keyword_recall'])} ({cnt(b_['keyword_hits'])}) | {L(num(b_['judge_positives']['value'], 0) + ci(b_['judge_positives']['ci95'], 0), b_['judge_positives']['at'])} |")
w("")
w("Precision of flags: Wilson 95% from k and n; recall and keyword figures: stratified bootstrap. "
  + " · ".join(f"{EN[s_]}: judge positives among the random unflagged affairs {L(neither[s_]['kn'], p19[s_]['strata']['at'])}" for s_ in TOP)
  + ". So every affair the judge marks relevant is flagged, and the recall interval is [1.000, 1.000]; that interval does not cover "
  "relevant affairs the random sample missed.")
w("")
w(f"**Editor decisions as examples (S26).** Per topic, {L(num(p26['wolf']['editor_examples']['value']), p26['wolf']['editor_examples']['at'])} "
  "judged affairs drawn at random (`random.Random(26)`) act as an editor's first decisions (their judge label as Y/N); every other checked "
  "affair is decided again with the 4 nearest decisions as examples and compared with its S19 flag (paired bootstrap 2,000).")
w("")
w("| S26, agreement with the AI judge, same items | items (judge positives) | precision without examples (S19) | precision with 30 editor decisions | Δ precision, paired | recall without / with |")
w("|---|---|---|---|---|---|")
for s_ in TOP:
    b_ = p26[s_]; d_ = b_["precision_diff"]
    dtxt = nm(d_) or r(d_, signed=True)
    rec = (nm(b_["s19"]["recall"]) if b_["s19"]["recall"].get("value") is None
           else f"{rk(b_['s19']['recall'])} / {rk(b_['s26']['recall'])}")
    w(f"| {EN[s_]} | {cnt(b_['test_items'])} ({cnt(b_['judge_positives'])}) | {rk(b_['s19']['precision'])} | **{rk(b_['s26']['precision'])}** | "
      f"{dtxt} | {rec} |")
w("")
w(" ".join(f"{EN[s_]}: no judge positive among its {num(p26[s_]['test_items']['value'])} test items, so precision is "
           f"{num(p26[s_]['s19']['precision']['value'])} in both arms and neither the difference nor recall can be measured."
           for s_ in TOP if p26[s_]["precision_diff"].get("value") is None) + " "
  "The pre-registration names the weighted S19 recall as secondary; [`eval/s26/analyze.py`](../eval/s26/analyze.py) reports recall among the "
  "judge's positives in the test items, which equals it here because the random unflagged sample holds no judge positive.")
w("")
w("**A second question on the flags (S27).** Every S19 flag gets one more closed question, same input and frame: «Ist «{name}» ein zentrales "
  "Thema dieses Geschäfts – nicht nur am Rande erwähnt oder bloss ähnlich?»; the flag stays at mean p ≥ 0.5. One wording, no tuning, applied "
  "once to the S19 packets (the dev step was dropped by an amendment before any S27 call). Recall = share of the judge's positives that keep "
  "their flag (every positive was flagged in S19).")
w("")
w("| S27, agreement with the AI judge | flags | kept | precision without (S19) | precision with the second question | Δ precision, paired | recall with the second question |")
w("|---|---|---|---|---|---|---|")
for s_ in TOP:
    b_ = p27[s_]
    w(f"| {EN[s_]} | {cnt(b_['flags'])} | {cnt(b_['kept'])} | {rk(b_['precision_without'])} | **{rk(b_['precision_with'])}** | "
      f"{r(b_['precision_diff'], signed=True)} | {rk(b_['recall_with'])} |")
w("")
h27, w27 = p27["hitze"], p27["wolf"]
w(f"Reading: one sentence casts a wide net on narrow topics: every judge-relevant affair is flagged, and most flags for wolf and AI in schools are "
  f"not relevant per the judge. Editor examples change precision by little (heat protection {r(p26['hitze']['precision_diff'], signed=True)}; "
  f"wolf, interval includes 0). The second question raises precision on heat protection ({r(h27['precision_diff'], signed=True)}) and keeps "
  f"{L(h27['recall_with']['kn'], h27['recall_with']['at'])} of its judge positives; on wolf it keeps {L(w27['recall_with']['kn'], w27['recall_with']['at'])}. "
  "In the product, flags the second question does not confirm go to `please check`, not away.")
w("")

# ------------------------------------------------------------------ limits
w("## Limits")
w("")
rc = mc["recall vs the judge (Swiss)"]
w(f"- Recall for “Digitalisierung” on titles is {r(rc)} against the judge (full census); most of the interval comes from the few judge positives "
  "among checked affairs that neither method flagged (4 among 180 in the S8 packet). The 30 DVS items are the human recall check; the yes/no prompt "
  "and the 0.5 cut-off were set on those same items (S3), so a held-out human recall test is the partner's full list (`make eval GOLD=…`).")
w(f"- APS subtopics reach {r(sub['result'])} top-1 end to end and ship as ranked suggestions.")
b6_ = T["aps_cantonal_communal"]["breakdowns"]; s10_ = T["aps_bilingual"]
w(f"- Short, title-only cantonal and communal affairs are the hardest input ({num(s10_['result']['value'])} / {num(s10_['results_more'][0]['value'])} "
  f"on bilingual titles; S6 {num(b6_['title_only']['value'])} title-only vs {num(b6_['with_text']['value'])} with text). Communal affairs in production: "
  f"{r(s17['result'])} against the judge (S17).")
w(f"- With only the names of Basel-Stadt's 46 themes, the first theme is matched in {r(bs0['result'])} of affairs; five of Basel's own labelled "
  f"affairs as examples add {r(m1[0], signed=True)} (S21), without training.")
w("- On the Federal Parliament's own multi-tag task the trained BFH model is ahead (micro-F1 0.687 vs 0.654, paired −0.079 to +0.010); "
  "the Curia design was tuned on 100 dev items.")
w(f"- Where no official labels exist, the gold is the AI judge. It matches APS editors on {r(T['judge_anchor_aps']['result'])} of chapters and says yes to "
  "27/30 DVS items; its two Claude runs are close to one judge (0.99 agreement), and its precision on human negatives is not measured.")
w(f"- New topics defined in one sentence are measured against the AI judge only. They flag every judge-relevant affair in S19 but over-flag "
  f"narrow topics: precision of flags {rk(p19['wolf']['precision'])} for wolf, {rk(p19['ki-schule']['precision'])} for AI in schools (§15).")
w(f"- The held-out test (S25, §1b) scores the chapter and its lanes; subtopic and hierarchical figures of the shipped design (§2) are on the "
  f"design set only. Its D1 cell (French or Italian text) holds {num(dd25['D1']['n'])} affairs.")
w("- All Apertus rows come from one served build; cut-offs and recalibration are refitted per build. ECE intervals are not computed yet.")
w("")
w("## To measure")
w("")
for x in P["to_measure"]:
    w(f"- {x['item']} (pre-registered: {L('PREREG-BUILD.md § ' + x['item'].split(':')[0], x['prereg'])})" if isinstance(x, dict) else f"- {x}")
w("")
open(DOC, "w", encoding="utf-8").write("\n".join(out))
print("wrote", DOC, len(out), "lines")
