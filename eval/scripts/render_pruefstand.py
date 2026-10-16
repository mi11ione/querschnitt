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
    if c[0] == c[1]: return " (no interval: the bootstrap saw no miss)"   # a collapsed percentile interval is not a 95% interval
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
  f"federal affairs ({L('PREREG-BUILD.md § S25', d4['prereg_more'])}). A later search of five design variants on these items (S31, §1d; "
  "dev only, not pre-registered) found none that beats D4.")
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
  f"{L(num(cs['results_more'][0]['value'], 4), cs['results_more'][0]['at'])}). These are in-sample; held out on the S25 affairs "
  f"(computed after the results, not pre-registered, §1g) the D4 map's error is "
  f"{L(num(T['aps_lanes_heldout_post_hoc']['result']['value'], 4), T['aps_lanes_heldout_post_hoc']['result']['at'])}.")
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
bl25 = {c["cell"]: c for c in b25["by_lang"]["cells"]}
d1_fr = bl25["fr"]["n"]; d1_de = dd25["D1"]["n"] - d1_fr          # every non-German affair is read without examples (D1)
lp25 = b25["list_prompting_s25b"]; d0_25, kw_25 = h25["baselines"][0], h25["baselines"][1]
w(f"### 1b · APS chapter held out — {num(h25['n'], 0)} fresh federal affairs, the shipped design as in production (S25, pre-registered)")
w("")
w(f"The held-out test of the shipped federal design. §1's {num(d4['n'], 0)} items are the set the design was chosen on; none of these "
  f"{num(h25['n'], 0)} was used while designing. Items: federal affairs with an APS editors' chapter recovered from Wayback captures of "
  "anneepolitique.swiss process pages, none in the S5 or S9 sets or in the example pool (the analysis asserts it), parsed with the S9 rules "
  f"([`eval/s25/FETCH.md`](../eval/s25/FETCH.md)). The production pipeline as shipped, unchanged: D4 (the five BM25-nearest APS-labelled "
  "examples from the S5+S9 pool + a second reading without examples, chapter read back from the subtopic) for the "
  f"{L(num(dd25['D4']['n']), dd25['D4']['at'])} affairs with German text and APS-labelled neighbours, D1 (no examples) for the "
  f"{L(num(dd25['D1']['n']), dd25['D1']['at'])} with no APS-labelled example: one-word procedural titles such as «Vereidigung» (also «Nachruf», "
  f"«Ordnungsantrag») have no BM25 neighbour in the pool ({num(d1_de)}), and one text is French ({L(num(d1_fr), bl25['fr']['at'])}); "
  "lanes by the recalibrated p with the calibration map fitted on S16 only; decisions composed exactly as "
  "the export composes them ([`eval/s25/analyze.py`](../eval/s25/analyze.py) → [`eval/s25/results.json`](../eval/s25/results.json); "
  f"one line per affair in [`eval/s25/decisions.jsonl`](../eval/s25/decisions.jsonl)). Pre-registration: {L('PREREG-BUILD.md § S25', h25['prereg'])} "
  f"and {L('its amendment', h25['prereg_more'])} (a determinism fix before the final score).")
w("")
w(f"| n = {num(h25['n'], 0)}, gold = APS editors' chapter | top-1 | top-3 |")
w("|---|---|---|")
w(f"| **production pipeline as shipped, held out** | **{r(h25['result'])}** ({L(h25['result']['kn'], h25['result']['at'])}) | {r(t25)} |")
w(f"| plain list prompting (S9 D0; S25b, pre-registered; {num(d0_25['n'], 0)} of the {num(h25['n'], 0)} affairs) | {r(d0_25)} "
  f"({L(d0_25['kn'], d0_25['at'])}) | — |")
w(f"| keyword (S9 frozen rule, same input) | {r(kw_25)} | — |")
w(f"| for reference: D4 on the design set (§1, other items, not held out) | {r(d4['result'])} | {r(m4[0])} |")
w("")
sh_, df_, ns_ = lp25["shipped_same_affairs"], lp25["paired_shipped_minus_D0"], lp25["not_scored"]
w(f"**Plain list prompting on the same affairs** ({L('PREREG-BUILD.md § S25b', lp25['prereg'])}, pre-registered after the S25 result, before "
  "any S25b call; [`eval/s25b/analyze.py`](../eval/s25b/analyze.py) → [`eval/s25b/results.json`](../eval/s25b/results.json)): S9's D0 — the "
  "chapter prompt without examples in two code orders, chapter = top of the geometric mean — on the same build and input. On the "
  f"{L(num(d0_25['n'], 0), d0_25['at'])} affairs where both readings exist, D0 reaches {r(d0_25)} ({L(d0_25['kn'], d0_25['at'])}) and the "
  f"shipped pipeline {r(sh_)} ({L(sh_['kn'], sh_['at'])}); paired, shipped − D0 = {r(df_, signed=True)} (paired bootstrap 2,000 over "
  f"affairs, bounds outward). Not scored: {L(num(ns_['value']), ns_['at'])} one-word procedural affairs read without examples whose first "
  "reading had p ≥ 0.9, so the production run asked no second reading, which D0 needs.")
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
w(f"By design: D4 (German text, five examples) {r(dd25['D4'])}, n {num(dd25['D4']['n'])}; D1 (no examples: no APS-labelled neighbour "
  f"for one-word procedural titles such as «Vereidigung», or a French text) {L(dd25['D1']['kn'], dd25['D1']['at'])}{ci(dd25['D1']['ci95'])} "
  f"(small). By Curia year: {L(num(cy['before_2015']), cy['at'])} affairs "
  f"submitted before 2015, {L(num(cy['from_2015']), cy['at'])} from 2015 on. Gold chapters ({L(str(gc['chapters']), gc['at'])} present): "
  + " · ".join(f"{c_} {L(str(v_), gc['at'])}" for c_, v_ in gc["counts"].items()) + ".")
w("")

th, t25h = T["aps_hierarchical_d4"], T["aps_hierarchical_heldout_s25"]
hm = {x["metric"]: x for x in th["results_more"]}; hb = {x["name"]: x for x in th["baselines"]}
hm25 = {x["metric"]: x for x in t25h["results_more"]}
MF4, MF25 = "per-chapter F1, macro over the chapters present (D4)", "per-chapter F1, macro over the chapters present (shipped, held out)"


def hrow25(name, bold=False):
    g_ = hm25["subtopic top-1 given the chapter is right (shipped, held out)"]
    s1_ = r(hm25["subtopic top-1 end to end (shipped, held out)"]); hf_ = r(t25h["result"])
    return (f"| {name} | {f'**{s1_}**' if bold else s1_} | {r(hm25['subtopic top-3 end to end (shipped, held out)'])} | {r(g_)} (n {num(g_['n'])}) | "
            f"{r(hm25['hierarchical precision (shipped, held out)'])} | {r(hm25['hierarchical recall (shipped, held out)'])} | "
            f"{f'**{hf_}**' if bold else hf_} | {r(hm25[MF25])} |")


def hrow4(name, bold=False):
    g4_ = hm["subtopic top-1 given the chapter is right (D4)"]
    s1_ = r(hm["subtopic top-1 end to end (D4)"]); hf_ = r(th["result"])
    return (f"| {name} | {f'**{s1_}**' if bold else s1_} | {r(hm['subtopic top-3 end to end (D4)'])} | {r(g4_)} (n {num(g4_['n'])}) | "
            f"{r(hm['hierarchical precision (D4)'])} | {r(hm['hierarchical recall (D4)'])} | {f'**{hf_}**' if bold else hf_} | {r(hm[MF4])} |")


HHEAD = ("| Design | subtopic top-1 | subtopic top-3 | subtopic top-1 when the chapter is right | hP | hR | hF | per-chapter macro-F1 |",
         "|---|---|---|---|---|---|---|---|")
w(f"**Subtopic and hierarchy, held out** — computed after the S25 result from its rows (not pre-registered; no new calls) by "
  f"[`eval/s25/hierarchical.py`](../eval/s25/hierarchical.py) → [`eval/s25/hierarchical.json`](../eval/s25/hierarchical.json), with the "
  f"definitions of [`eval/s16/hierarchical.py`](../eval/s16/hierarchical.py) (§2): the {num(t25h['n'], 0)} S25 affairs whose main subtopic "
  f"is among the 190 for the subtopic and hierarchical figures, per-chapter macro-F1 over the {L(str(hm25[MF25]['chapters']), hm25[MF25]['at'])} "
  f"chapters present on all {num(hm25[MF25]['n'], 0)} affairs. Wilson for the subtopic rates, percentile bootstrap 2,000 for hP/hR/hF and "
  f"macro-F1, bounds outward. The {L('S25b entry', t25h['prereg_more'])} notes these figures as not pre-registered.")
w("")
w(HHEAD[0]); w(HHEAD[1])
w(hrow25("**shipped, held out (S25; not pre-registered)**", bold=True))
w(hrow4("for reference: D4 on the design set (§2, other items, not held out)"))
w("")

# ------------------------------------------------------------------ S28: the same held-out affairs without prefill (endpoint fallback)
t28 = T["aps_chapter_heldout_s28_no_prefill"]; m28 = t28["results_more"]; b28 = t28["breakdowns"]
pf28, pf28t3 = t28["baselines"][0], t28["baselines"][1]
t28t3, d28, d28t3, same28 = m28[0], m28[1], m28[2], m28[3]
w(f"### 1c · Without prefill (endpoint fallback): the same {num(t28['n'], 0)} held-out affairs (S28, pre-registered)")
w("")
w("An endpoint-capability check, not a new design: what the labelled fallback costs if the serving endpoint cannot continue an assistant "
  "message (the shipped design pre-fills the JSON opening and reads the code from the next token). With `QS_PREFILL=0` the pipeline sends one "
  "user message, the measured prompt plus a line asking the answer to begin with the JSON opening, and reads the code from the "
  "`top_logprobs` of the first token after that opening. Everything else as shipped (D4 / D1 as in §1b), on the same build; no calibration "
  "map exists for this mode, so its lane is the readings rule (pass when the two code orders agree or one reading has top p ≥ 0.9). Paired "
  f"against the S25 final decisions on the same affairs ([`eval/s28/analyze.py`](../eval/s28/analyze.py) → "
  f"[`eval/s28/results.json`](../eval/s28/results.json)). Pre-registration: {L('PREREG-BUILD.md § S28', t28['prereg'])} and "
  f"{L('its amendment', t28['prereg_more'])} (a read fix after the first 20-item smoke run, whose 28 calls were never scored).")
w("")
w(f"| n = {num(t28['n'], 0)}, gold = APS editors' chapter | top-1 | top-3 |")
w("|---|---|---|")
w(f"| **no prefill (`QS_PREFILL=0`), otherwise as shipped** | **{r(t28['result'])}** ({L(t28['result']['kn'], t28['result']['at'])}) | {r(t28t3)} |")
w(f"| shipped prefill design (S25 final, §1b), same affairs | {r(pf28)} ({L(pf28['kn'], pf28['at'])}) | {r(pf28t3)} |")
w(f"| paired, prefill − no prefill (bootstrap 2,000, bounds outward) | {r(d28, signed=True)} | {r(d28t3, signed=True)} |")
w("")
lp28, lc28 = b28["lanes_no_prefill"]["pass"], b28["lanes_no_prefill"]["please_check"]
rp = b28["read_path"]
w(f"The two modes give the same chapter on {L(num(same28['k']), same28['at'])} of {num(same28['n'], 0)} affairs ({r(same28)}). "
  f"Lane without prefill (readings rule): {L(F.pct(lp28['share']), lp28['at'])} pass ({L(num(lp28['n']), lp28['at'])}), precision {r(lp28)}; "
  f"`please check` {L(num(lc28['n']), lc28['at'])}, precision {r(lc28)}. With prefill the shipped lane is the recalibrated p "
  f"(§1b: {L(F.pct(l25['pass']['share']), l25['pass']['at'])} pass, precision {r(l25['pass'])}). Read path: every step row's code came from "
  f"the logprobs ({L(num(rp['all_rows_logprobs']), rp['at'])} rows; {L(str(rp['affairs_with_a_text_read']), rp['at'])} affairs with a code "
  f"read from the generated text, {L(str(rp['affairs_with_an_unparseable_row']), rp['at'])} with an unparseable row).")
w("")

# ------------------------------------------------------------------ S31: a design search on the design set (dev only, not pre-registered)
t31 = T["aps_design_search_s31"]; b31 = t31["breakdowns"]; g31 = b31["gate"]; fi31 = b31["fresh_items"]; c31 = b31["calls"]
s1_31, s2_31, r9_31 = b31["stage1_sub400"], b31["stage2_all"], b31["stage2_rest957"]
n1_31, n9_31 = s1_31["n"], r9_31["n"]
w(f"### 1d · Design search on the design set: five variants against D4, none better (S31, dev only, not pre-registered)")
w("")
w(f"A documented search for a better federal design on §1's {num(t31['n'], 0)} items, the set D4 was chosen on. This is dev, not a test: "
  "it has no pre-registration entry and nothing in it is held out; it documents that the shipped design was not beaten there. Same input as "
  "S16; examples leave-one-out (every item's example list excludes the item itself); one decision rule for every design "
  "(`compose.chapter_decision` generalised to n readings). The gate was fixed before any S31 call: a paired difference vs D4 of at least "
  f"{L(sgn(g31['threshold'], 2), g31['threshold_at'])} on all {num(t31['n'], 0)} items, with the 95% interval above 0. Stage 1 scored the five "
  f"variants on a fixed random {L(num(n1_31['value']), n1_31['at'])} items (V5 was added after V1–V4 had been seen there, as their "
  f"combination); the best two went to all {num(t31['n'], 0)} ([`eval/s31/DEV.md`](../eval/s31/DEV.md); "
  "[`eval/s31/analyze.py`](../eval/s31/analyze.py) → [`eval/s31/results.json`](../eval/s31/results.json)). Gold: APS editors' chapter. "
  "Top-1 with Wilson 95% (bounds outward); Δ paired bootstrap 2,000 over items, bounds outward at 4 decimals.")
w("")
w(f"| Variant (what changes vs D4) | stage 1, {num(n1_31['value'])} items: top-1 | Δ vs D4, paired | all {num(t31['n'], 0)} items: top-1 | top-3 | "
  "Δ vs D4, paired | gate (≥ +0.02, interval above 0) |")
w("|---|---|---|---|---|---|---|")
st2_31 = {c_["design"]: c_ for c_ in s2_31["designs"]}
for c_ in s1_31["designs"]:
    d_ = c_["design"]; c2_ = st2_31.get(d_)
    name_ = "**D4 (shipped)**" if d_ == "D4" else f"{d_} {c_['what']}"
    d1_ = r(c_["minus_D4"], d=4, signed=True) if "minus_D4" in c_ else "—"
    if c2_:
        top2_, t3_ = r(c2_["top1"]), r(c2_["top3"])
        d2_ = r(c2_["minus_D4"], d=4, signed=True) if "minus_D4" in c2_ else "—"
        gate_ = "—" if d_ == "D4" else ("passes" if g31["finalists"][d_]["passes"] else "no")
    else:
        top2_, t3_, d2_, gate_ = "—", "—", "—", "not taken to stage 2"
    w(f"| {name_} | {r(c_['top1'])} | {d1_} | {top2_} | {t3_} | {d2_} | {gate_} |")
w("")
rest_ = {c_["design"]: c_ for c_ in r9_31["designs"]}
dn_ = b31["decision_rule_note"]; best_ = t31["result"]
w(f"Outcome: no variant cleared the gate. The closest, V3 (the five examples in both code orders), is {r(best_, d=4, signed=True)} on all "
  f"{num(t31['n'], 0)} items; on the {L(num(n9_31['value']), n9_31['at'])} items stage 1 did not see, V1 {r(rest_['V1']['minus_D4'], d=4, signed=True)} "
  f"and V3 {r(rest_['V3']['minus_D4'], d=4, signed=True)}, both smaller than in stage 1. V3 also lowers top-3. So no test was run and D4 stays; "
  f"the {num(h25['n'], 0)} S25 held-out affairs (§1b) were not used by any S31 call and stay unspent for one later pre-registered look at a "
  f"single winner. Under the common rule D4 scores {r(t31['baselines'][0])}; §1 reports {r(d4['result'])} with the S16 rule, which has no "
  f"«no policy topic» check ({L(str(dn_['items_differ']), dn_['at'])} items differ). Fresh items for a new test: a Wayback listing of APS process "
  f"pages from 11 Oct 2026 on found {L(str(fi31['new_process_ids_with_200_capture']['value']), fi31['new_process_ids_with_200_capture']['at'])} new "
  f"pages; of the {L(str(fi31['unjoined_s25_numbers']), fi31['also_at'])} unjoined S25 numbers, {L(str(fi31['match_newer_opd']), fi31['also_at'])} "
  f"match a newer OPD snapshot and {L(str(fi31['with_production_input']), fi31['also_at'])} of those has a production input "
  f"([`eval/s31/cdx_check/`](../eval/s31/cdx_check/)). Calls: {L(num(c31['calls']), c31['at'])} on the locked build, USD "
  f"{L(num(c31['usd_list_price'], 4), c31['at'])} at list price.")
w("")

# ------------------------------------------------------------------ S33: the same held-out affairs read from the French text
t33 = T["aps_chapter_heldout_s33_french"]; m33 = t33["results_more"]; b33 = t33["breakdowns"]
de33, de33t3 = t33["baselines"][0], t33["baselines"][1]
t33t3, d33, d33t3, same33 = m33[0], m33[1], m33[2], m33[3]
ro33 = b33["same_design_readings_only"]; in33 = b33["inputs"]; c33 = b33["cost"]; l33 = b33["lanes_french"]


def side(d_):
    """plain reading of a paired difference interval."""
    if d_["ci95"][0] > 0: return "French higher (the interval lies above 0)"
    if d_["ci95"][1] < 0: return "French lower (the interval lies below 0)"
    return "no difference measurable (the interval includes 0)"


w(f"### 1e · French text: the same {num(t33['n'], 0)} held-out affairs read in French (S33, pre-registered)")
w("")
w(f"Production reads federal affairs from the German text, so §1b says nothing about French. S33 reads the same {num(t33['n'], 0)} affairs "
  "from OPD's French title and the French submitted text («Texte déposé», first 1,500 characters) where OPD has one "
  f"({L(num(in33['with_french_text']), in33['at'])} affairs; {L(num(in33['french_title_only']), in33['at'])} French title only, "
  f"{L(num(in33['title_only_and_german_had_document_text']), in33['at'])} of them read in §1b with a German document text; no affair has a long "
  "title in either language). The design is what production runs for a French federal affair today: the APS-labelled examples are shown "
  "only for German federal text (`engine.ch1_prompt`), so French gets D1 — the chapter prompt in the French frame without examples (chapter "
  "names French, subtopic names German as published), a second code order when the first reading's top p < 0.9, one subtopic request, "
  "chapter read back — composed as the export composes it. Paired against the §1b decisions on the German text (D4). Gold: APS editors' "
  f"chapter. [`eval/s33/run.py`](../eval/s33/run.py) (inputs, batch runner) → [`eval/s33/analyze.py`](../eval/s33/analyze.py) → "
  f"[`eval/s33/results.json`](../eval/s33/results.json). Pre-registration: {L('PREREG-BUILD.md § S33', t33['prereg'])}. S33 selects "
  "nothing: it changes no design and spends no S25 item on a design choice.")
w("")
w(f"| n = {num(t33['n'], 0)}, gold = APS editors' chapter | top-1 | top-3 |")
w("|---|---|---|")
w(f"| **French text, D1 without examples (production's path for French)** | **{r(t33['result'])}** ({L(t33['result']['kn'], t33['result']['at'])}) | {r(t33t3)} |")
w(f"| German text, shipped D4 (S25 final, §1b), same affairs | {r(de33)} ({L(de33['kn'], de33['at'])}) | {r(de33t3)} |")
w(f"| paired, French − German (bootstrap 2,000, bounds outward) | {r(d33, signed=True)} | {r(d33t3, signed=True)} |")
w("")
rf_, rg_, rd_ = ro33["french"], ro33["german"], ro33["paired"]
w(f"Primary: French − German {r(d33, signed=True)}, {side(d33)}. Top-3 (secondary): {r(d33t3, signed=True)}, {side(d33t3)}. The two arms "
  f"differ in language and in design (German has the five examples, French has none). **Same design in both languages** (pre-registered secondary): the full German D1 read-back would need new "
  f"calls (the subtopic request for the D1 chapter set exists for {L(num(b33['same_design_read_back']['german_subtopic_rows_available']), b33['same_design_read_back']['at'])} "
  "of the affairs; the entry counted 171 before the 40 affairs whose input the 16 Oct rebuild changed were matched to their S25-time "
  "input), so it is skipped; at the level of the chapter readings "
  "(no examples, identity order and the second order where p < 0.9, top of the geometric mean, no read-back) French reaches "
  f"{r(rf_)} ({L(rf_['kn'], rf_['at'])}) and German {r(rg_)} ({L(rg_['kn'], rg_['at'])}): French − German {r(rd_, signed=True)}, {side(rd_)}.")
w("")
w("| S33 lane (French) | share of affairs (n) | precision |")
w("|---|---|---|")
for k_, nm_ in (("pass", "pass: recalibrated p ≥ 0.7 (production's lane; map fitted on S16)"), ("please_check", "`please check`: recalibrated p < 0.7"),
                ("readings_agree", "readings agree (one reading with p ≥ 0.9 counts as agree)"), ("readings_disagree", "readings disagree")):
    c_ = l33[k_]
    w(f"| {nm_} | {L(F.pct(c_['share']), c_['at'])} ({L(num(c_['n']), c_['at'])}) | {r(c_)} |")
w("")
w("| French input | n | French top-1 | German shipped, same affairs |")
w("|---|---|---|---|")
for c_ in b33["by_text"]["cells"]:
    w(f"| {c_['cell']} | {L(num(c_['n']), c_['at'])} | {r(c_)} | {r(c_['german_same_items'])} |")
w("")
w(f"French and German give the same chapter on {L(num(same33['k']), same33['at'])} of {num(same33['n'], 0)} affairs ({r(same33)}). Calls: "
  f"{L(num(c33['calls']), c33['at'])} on the locked build (S25's), USD {L(num(c33['usd'], 4), c33['at'])} at list price, including "
  f"{L(str(c33['first_launch_calls_not_written']), c33['at'])} calls of a first launch whose rows were not written (the run folder lacked its "
  "build directory) and were asked again.")
w("")

# ------------------------------------------------------------------ S34: the trained baseline on the same labels
t34 = T["aps_chapter_heldout_s34_trained"]; m34 = t34["results_more"]; b34 = t34["breakdowns"]
sh34, sh34t3 = t34["baselines"][0], t34["baselines"][1]
t34t3, d34 = m34[0], m34[1]
lc34 = b34["learning_curve"]["points"]; ln34 = b34["trained_by_shipped_lane"]; ag34 = b34["agreement"]; tr34 = b34["train"]
w(f"### 1f · The trained baseline on the same labels: a classifier fitted on the shipped design's {num(tr34['value'], 0)} APS labels, "
  f"the same {num(t34['n'], 0)} held-out affairs (S34, pre-registered)")
w("")
w("§1b compares the shipped design with keywords and with plain list prompting, not with a trained classifier. The shipped design already "
  f"holds {L(num(tr34['value'], 0), tr34['at'])} APS-labelled affairs: its example pool (`data/eval/aps_pool.jsonl`, the S9 and S5 affairs, "
  "none in S25). S34 trains a standard text classifier on exactly those labels and scores it on the §1b affairs: TF-IDF over word 1–2-grams "
  "and character 2–5-grams, logistic regression, C chosen by 5-fold cross-validation on the pool only "
  f"(C = {L(str(b34['cv_accuracy']['C']), b34['cv_accuracy']['at'])}), on the text the model sees (title, long title and text of the "
  "production inputs); nothing tuned on S25. Paired against the §1b decisions on the same affairs. No model calls; run on GitHub Actions "
  f"([`eval/s34/run.py`](../eval/s34/run.py) → [`eval/s34/results.json`](../eval/s34/results.json), "
  f"[`eval/s34/predictions.jsonl`](../eval/s34/predictions.jsonl); [`eval/s34/RUN.md`](../eval/s34/RUN.md)). Pre-registration: "
  f"{L('PREREG-BUILD.md § S34', t34['prereg'])}. Gold: APS editors' chapter.")
w("")
w(f"| n = {num(t34['n'], 0)}, gold = APS editors' chapter | top-1 | top-3 |")
w("|---|---|---|")
w(f"| trained classifier, {num(tr34['value'], 0)} pool labels | {r(t34['result'])} ({L(t34['result']['kn'], t34['result']['at'])}) | {r(t34t3)} |")
w(f"| **shipped design (S25 final, §1b), same affairs** | **{r(sh34)}** ({L(sh34['kn'], sh34['at'])}) | {r(sh34t3)} |")
w(f"| paired, shipped − trained (bootstrap 2,000, bounds outward) | {r(d34, signed=True)} | — |")
w("")
w(f"Primary: shipped − trained {r(d34, signed=True)}, the interval above 0 (shipped right where the classifier is wrong on "
  f"{L(num(d34['shipped_only_right']), d34['at'])} affairs, the reverse on {L(num(d34['trained_only_right']), d34['at'])}). "
  "**Learning curve** (secondary; stratified by chapter, same C): trained on "
  + " / ".join(L(num(p_['train'], 0), p_['at']) for p_ in lc34) + " pool affairs, top-1 "
  + " / ".join(r(p_) for p_ in lc34) + ". The curve is still rising at the full pool: S34 measures a classifier with the labels the "
  "shipped design has, and says nothing about one trained on many more.")
w("")
w("| shipped lane (§1b) | n | trained top-1 | shipped top-1 |")
w("|---|---|---|---|")
for k_, nm_ in (("pass", "pass: recalibrated p ≥ 0.7"), ("please_check", "`please check`: recalibrated p < 0.7")):
    c_ = ln34[k_]
    w(f"| {nm_} | {L(num(c_['n']), c_['at'])} | {r(c_)} | {r(c_['shipped'])} |")
w("")
sw_, dw_, tw_ = ag34["shipped_top1_where_same"], ag34["shipped_top1_where_different"], ag34["trained_top1_where_different"]
w(f"The two give the same chapter on {L(num(ag34['share']['value']), ag34['share']['at'])} of the affairs ({L(num(sw_['n']), sw_['at'])}); "
  f"there the chapter is right in {r(sw_)}. Where they differ ({L(num(dw_['n']), dw_['at'])}), the shipped chapter is right in {r(dw_)}, "
  f"the classifier's in {r(tw_)}.")
w("")

# ------------------------------------------------------------------ lanes and calibration beyond the fitted set (post hoc)
lh = T["aps_lanes_heldout_post_hoc"]; blh = lh["breakdowns"]; pcs = blh["please_check_share"]
s17ph = T["aps_communal_production"]["breakdowns"]["lanes_calibrated_post_hoc"]
w("### 1g · Lanes and calibration beyond the fitted set (computed after the results, not pre-registered)")
w("")
w(f"§1's calibration figures are in-sample: the isotonic map was fitted (2-fold cross-fitted) on the {num(d4['n'], 0)} items they are "
  f"measured on. The same map, fitted on S16 only, on the {num(lh['n'], 0)} S25 affairs of §1b: expected calibration error "
  f"**{L(num(lh['result']['value'], 4), lh['result']['at'])}** held out against {L(num(lh['result']['in_sample'], 4), lh['result']['in_sample_at'])} "
  "in-sample (10 equal-width bins, the same definition, `calibrate.ece`; no interval computed). "
  "[`eval/lanes/heldout.py`](../eval/lanes/heldout.py) → [`eval/lanes/heldout.json`](../eval/lanes/heldout.json); no model calls.")
w("")
w("| recalibrated p | n | mean recalibrated p | share right (APS editors) |")
w("|---|---|---|---|")
for c_ in blh["bins"]["cells"]:
    w(f"| {c_['cell']} | {L(num(c_['n']), c_['at'])} | {L(num(c_['mean_p']), c_['at'])} | {r(c_)}{' (small)' if c_.get('small') else ''} |")
w("")
w("The map is a step function; at its five steps with the most affairs the share right is "
  + " · ".join(f"p {L(num(c_['p_cal'], 4), c_['at'])}: {r(c_)} of {L(num(c_['n']), c_['at'])}" for c_ in blh["largest_steps"]["cells"])
  + ". Above 0.7 the held-out point shares sit below the mean recalibrated p of their bin: the pass lane is right somewhat less often "
  "than its p says.")
w("")
lv_ = [k_ for k_ in ("federal", "cantonal", "communal", "other") if k_ in pcs["by_level"]]
lg_ = [k_ for k_ in ("de", "fr", "it") if k_ in pcs["by_language"]]
w(f"**`please check` share in the shipped export** (export {pcs['export'][:10]}; the APS chapter lane of every affair that has one; a count, "
  "not an accuracy; cells with n ≥ 30):")
w("")
w("| level | all languages | " + " | ".join(lg_) + " |")
w("|---|---|" + "---|" * len(lg_))
for v_ in lv_:
    cells_ = []
    for g_ in lg_:
        c_ = pcs["by_level_and_language"].get(f"{v_} · {g_}")
        cells_.append(f"{r(c_)} (n {L(num(c_['n']), c_['at'])})" if c_ else "—")
    c_ = pcs["by_level"][v_]
    w(f"| {v_} | {r(c_)} (n {L(num(c_['n']), c_['at'])}) | " + " | ".join(cells_) + " |")
c_ = pcs["all"]
w(f"| **all** | {r(c_)} (n {L(num(c_['n']), c_['at'])}) | " + " | ".join(
    f"{r(pcs['by_language'][g_])} (n {L(num(pcs['by_language'][g_]['n']), pcs['by_language'][g_]['at'])})" for g_ in lg_) + " |")
w("")
fpf = pcs["by_level_and_language"]["federal · fr"]
w(f"French and Italian affairs go to a person more often than German ones at every level (federal French, n {num(fpf['n'])}, has an "
  "interval that overlaps the German one). Both calibration maps were fitted on federal affairs read in German (the S9 items).")
w("")
sp_, sc_ = s17ph["pass"], s17ph["please_check"]
w(f"**Communal affairs** (S17, §11; computed after S17, not pre-registered; gold is the AI judge, so these figures are agreement with it): "
  f"with the map fitted on federal items, the pass lane holds {L(F.pct(sp_['coverage']), sp_['at'])} of the 200 affairs and agrees with "
  f"the judge in {r(sp_)} ({L(sp_['kn'], sp_['at'])}); `please check` in {r(sc_)} ({L(sc_['kn'], sc_['at'])}). "
  f"([`eval/lanes/results.json`](../eval/lanes/results.json) → `S17_communal_post_hoc`; Wilson intervals computed here from k and n.)")
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
N_ALL = th["results_more"][-1]["n"]
w(f"**Hierarchical metrics of the shipped design D4** — computed after S16 from its rows (not pre-registered; no new calls) by "
  f"[`eval/s16/hierarchical.py`](../eval/s16/hierarchical.py). Same {num(th['n'], 0)} items as above (chapter + subtopic gold); "
  "hierarchical precision / recall / F1 after Kiritchenko et al. (predicted and gold sets augmented with their ancestors, levels "
  "chapter and subtopic, micro-averaged); per-chapter F1 is the chapter top-1, one vs rest, macro over the "
  f"{L(str(hm['per-chapter F1, macro over the chapters present (D4)']['chapters']), hm['per-chapter F1, macro over the chapters present (D4)']['at'])} "
  f"chapters present, on all {num(hm['per-chapter F1, macro over the chapters present (D4)']['n'], 0)} items. Intervals: Wilson for the subtopic "
  "rates, percentile bootstrap 2,000 for hP/hR/hF and macro-F1 (stratified by gold chapter), bounds rounded outward.")
w("")
w(HHEAD[0]); w(HHEAD[1])
w(hrow4("**D4 shipped**", bold=True))
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
w("For reference, the same metrics of the shipped design on the held-out S25 affairs (§1b; other items, computed after the S25 result, "
  "not pre-registered):")
w("")
w(HHEAD[0]); w(HHEAD[1])
w(hrow25(f"shipped, held out (S25, n {num(t25h['n'], 0)}; not pre-registered)"))
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

ti = T["ticino_departments"]; bt9 = ti["breakdowns"]; mt9 = ti["results_more"]
a9, f9, x9 = bt9["secondary_all_items"], bt9["secondary_gold_in_5_departments"], bt9["excluded_from_primary"]
w(f"### 6b · Ticino: the lead department vs the canton's own assignment, Gran Consiglio 2023–26, in Italian (S29, pre-registered)")
w("")
w(f"The first human-labelled test on an Italian-speaking parliament's own scheme. Gold: the lead department OPD carries for every Gran "
  "Consiglio affair (contributors, role `leading_department`, position 1), assigned by the cantonal administration; affairs begun "
  f"1 Jan 2023–11 Oct 2026, {num(a9['n'])} in all ([`eval/s29/SOURCES.md`](../eval/s29/SOURCES.md), "
  "[`eval/s29/items.py`](../eval/s29/items.py)). Scheme file [`ti-dipartimenti.yaml`](../src/querschnitt/schemes/ti-dipartimenti.yaml): "
  "the six unit names verbatim in Italian (five Dipartimenti and the Cancelleria dello Stato) plus «Nessuno di questi» for the Consiglio di "
  "Stato as a whole or the Gran Consiglio itself; no descriptions, nothing tuned. The prompt frame is Italian; the three fixed block labels "
  "in code («Geschäft:», «Titel:», «Text (Auszug):») stay German as shipped. Production input, second code order when p < 0.9 "
  f"([`eval/s29/analyze.py`](../eval/s29/analyze.py) → [`eval/s29/results.json`](../eval/s29/results.json); "
  f"{L('pre-registered', ti['prereg'])}).")
w("")
w(f"**Why the primary population excludes {L(num(x9['value']), x9['at'])} items.** A Messaggio (the government's message to the parliament) "
  "prints the competent department in its header («competenza»), so on those inputs the answer is in the text. "
  f"{L(num(x9['value']), x9['at'])} of the {num(a9['n'])} inputs name one of the six units ({L(str(x9['messaggi']['value']) + ' of ' + str(x9['messaggi']['of']) + ' Messaggi', x9['messaggi']['at'])}); "
  f"this was measured on the inputs before any call, and the primary result is on the {num(ti['n'])} that name none.")
w("")
w("| Population | n | top-1 = lead department | top-2 | top-3 | keyword stems (frozen, title only) | majority | Apertus − keyword, paired |")
w("|---|---|---|---|---|---|---|---|")
w(f"| **primary: input names no unit** | {num(ti['n'])} | **{r(ti['result'])}** | {r(mt9[0])} | {r(mt9[1])} | {r(ti['baselines'][0])} | "
  f"{r(ti['baselines'][1])} | {r(mt9[2], signed=True)} |")
w(f"| secondary: all inputs as fed | {num(a9['n'])} | {r(a9['top1'])} | {r(a9['top2'])} | {r(a9['top3'])} | {r(a9['keyword'])} | "
  f"{r(a9['majority'])} | {r(a9['minus_keyword'], signed=True)} |")
w(f"| secondary: gold one of the 5 Dipartimenti (all inputs) | {num(f9['n'])} | {r(f9['top1'])} | {r(f9['top2'])} | {r(f9['top3'])} | "
  f"{r(f9['keyword'])} | {r(f9['majority'])} | {r(f9['minus_keyword'], signed=True)} |")
w("")
la9, lc9 = bt9["lane_readings_agree"], bt9["lane_please_check"]
w(f"Majority = {ti['baselines'][1]['label']} (primary). Lanes (primary): the two code orders agree on {L(F.pct(la9['share']), la9['at'])} of "
  f"affairs ({L(num(la9['n']), la9['at'])}), precision {r(la9)}; they disagree on {L(num(lc9['n']), lc9['at'])}, precision {r(lc9)} "
  "(`please check`).")
w("")
EN9 = {"Dipartimento della sanità e della socialità": "health and social affairs (DSS)",
       "Dipartimento delle finanze e dell'economia": "finance and economy (DFE)", "Dipartimento del territorio": "territory (DT)",
       "Dipartimento delle istituzioni": "institutions (DI)", "Dipartimento dell'educazione, della cultura e dello sport": "education, culture and sport (DECS)",
       "Cancelleria dello Stato": "State Chancellery",
       "Nessuno di questi (Consiglio di Stato nel suo insieme o Gran Consiglio stesso)": "none of these (Consiglio di Stato as a whole or the Gran Consiglio)"}
bg9 = bt9["by_gold"]
w("Per lead department (primary; share of its affairs that Apertus assigns to it): " + " · ".join(
    f"{EN9.get(c['cell'], c['cell'])} {L(num(c['value']) + ci(c['ci95']) + ', n ' + str(c['n']), bg9['at'])}" for c in bg9["cells"]) + ".")
cf9 = bt9["confusion_gold_to_pred"]; NONE9 = "Nessuno di questi (Consiglio di Stato nel suo insieme o Gran Consiglio stesso)"
w(f"The weak spots are the two non-department classes: of the {num(sum(v for k, v in cf9[NONE9].items() if k != 'at'))} «none of these» "
  f"affairs, {L(str(cf9[NONE9]['Dipartimento delle istituzioni']), cf9['at'])} go to the Dipartimento delle istituzioni; of the "
  f"{num(sum(v for k, v in cf9['Cancelleria dello Stato'].items() if k != 'at'))} State Chancellery affairs, "
  f"{L(str(cf9['Cancelleria dello Stato']['Dipartimento delle istituzioni']), cf9['at'])} go there too.")
by9 = bt9["by_type"]
w("By affair type (primary): " + " · ".join(f"{c['cell']} {L(num(c['value']) + ci(c['ci95']) + ', n ' + str(c['n']), by9['at'])}"
                                            for c in by9["cells"] if not c.get("small")) + " (types with n < 20 not shown).")
w("")
w(f"Bern (§5, S18) and Basel-Stadt (§6, S20) are reported beside this result, not compared with it: the schemes differ, and so do the "
  "chance rates (majority and keyword rows above).")
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


def cell_table(title, blocks, labels, small_n=20):
    """blocks: cells() dicts (cell rows in order; the union of their cells is shown); labels: column names."""
    w(f"| {title} | " + " | ".join(labels) + " |")
    w("|---|" + "---|" * len(labels))
    names = []
    for bk in blocks:
        names += [c["cell"] for c in bk["cells"] if c["cell"] not in names]
    for nm in names:
        row = []
        for bk in blocks:
            c = next((x for x in bk["cells"] if x["cell"] == nm), None)
            row.append("—" if c is None else L(num(c["value"]) + ci(c["ci95"]) + f", n {c['n']}", c.get("at") or bk["at"]) + (" (small)" if c.get("small") else ""))
        w(f"| {nm} | " + " | ".join(row) + " |")
    tests = []
    for bk in blocks:
        t = bk["test"] or {}; g = bk.get("largest_gap") or {}
        s = f"p {t['p_perm']}" if t.get("p_perm") is not None else ""
        if g.get("diff") is not None:
            s += f"; gap {g['hi']} − {g['lo']} {sgn(g['diff'])}{ci(g['ci95'], signed=True)}"
        tests.append(L(s, t.get("at") or bk["at"]) if s else "—")
    w(f"| *test (cells n ≥ {small_n})* | " + " | ".join(tests) + " |")
    w("")


s32 = T["neutrality_shipped_s32"]; b32 = s32["breakdowns"]
p9, p25, ppo = b32["s9_prod_party_top1"], b32["s25_party_top1"], b32["pooled_party_top1"]
lg9, lg25 = b32["s9_prod_language_top1"], b32["s25_language_top1"]
nsc = b32["s9_prod_not_scored"]
w("### 8 · Neutrality on human labels (S32 shipped design; S14 earlier design D1; S22 Italian)")
w("")
w(f"**Shipped design (S32: a re-analysis of existing rows, not pre-registered, no new calls).** Gold: the APS editors' chapter. Two "
  f"sets. The S9 affairs' production rows ([`eval/prod_gold/`](../eval/prod_gold/rows.py), the rows `make eval` scores: "
  f"{L(p9['overall']['kn'], p9['overall']['at'])} scored, {L(str(nsc['value']), nsc['at'])} without a chapter row). The S25 held-out "
  f"affairs ([`eval/s25/decisions.jsonl`](../eval/s25/decisions.jsonl), {L(p25['overall']['kn'], p25['overall']['at'])}). Party, "
  "submitter type and instrument come from S14's own functions on the OPD export the production run reads; on the S9 affairs they give "
  f"exactly S14's cells. Cells with n < {s32['small_threshold']} are marked "
  "small. The party test is a permutation test (5,000) over the six main parties (pooled: shuffled within set); the largest gap is "
  f"among cells with n ≥ {s32['small_threshold']}, bootstrap (2,000). "
  "Script and notes: [`eval/s32/analyze.py`](../eval/s32/analyze.py), [`eval/s32/README.md`](../eval/s32/README.md).")
w("")
cell_table("S32 by party, top-1", [p9, p25, ppo], ["S9 prod", "S25 held out", "pooled"], s32["small_threshold"])
cell_table("S32 by submitter type, top-1", [b32["s9_prod_submitter_kind_top1"], b32["s25_submitter_kind_top1"], b32["pooled_submitter_kind_top1"]],
           ["S9 prod", "S25 held out", "pooled"], s32["small_threshold"])
cell_table("S32 by instrument, top-1", [b32["s9_prod_instrument_top1"], b32["s25_instrument_top1"], b32["pooled_instrument_top1"]],
           ["S9 prod", "S25 held out", "pooled"], s32["small_threshold"])
ga25 = p25["largest_gap_all_tested"]; ac9, ac25 = b32["s9_prod_all_submitter_categories_test"], b32["s25_all_submitter_categories_test"]
k16 = b32["s16_d4_party_top1"]
w(f"In S25 two party cells are small; over all six, the gap is {ga25['hi']} − {ga25['lo']} {L(sgn(ga25['diff']) + ci(ga25['ci95'], signed=True), ga25['at'])}. "
  f"Test over all submitter categories: S9 prod {L('p ' + str(ac9['p_perm']), ac9['at'])} ({ac9['cells']} cells), "
  f"S25 {L('p ' + str(ac25['p_perm']), ac25['at'])} ({ac25['cells']} cells). Secondary, S16 D4 on the S9 input: party "
  f"{L('p ' + str(k16['p_perm']), k16['at'])}, gap {k16['largest_gap']['hi']} − {k16['largest_gap']['lo']} "
  f"{L(sgn(k16['largest_gap']['diff']) + ci(k16['largest_gap']['ci95'], signed=True), k16['largest_gap']['at'])}.")
w("")
c9 = lg9["cells"]; c25 = {c["cell"]: c for c in lg25["cells"]}
w(f"**Language: not informative for the shipped design.** The S9 production inputs are German ({L(num(c9[0]['n']), c9[0]['at'])} of "
  f"{num(p9['overall']['n'])}). The S25 items are {L(num(c25['de']['n']), c25['de']['at'])} German and {L(num(c25['fr']['n']), c25['fr']['at'])} French. "
  "Federal affairs are read from the German input (no DE/FR two-readings lane), so neither set can show a language effect. The "
  "language evidence on human labels is S22 (Italian vs German, D1, below), Bern (DE vs FR titles, §5) and, held out, S33 (the S25 "
  f"affairs read from the French text, §1e: French − German shipped {r(d33, signed=True)}; same design, readings only, "
  f"{r(ro33['paired'], signed=True)}). A held-out Italian federal slice is still to measure.")
w("")
gmax = max((p9, p25, ppo), key=lambda x: x["largest_gap"]["ci95"][1])["largest_gap"]
kk9, ki9 = b32["s9_prod_submitter_kind_keyword_top1"]["test"], b32["s9_prod_instrument_keyword_top1"]["test"]
w("Reading (shipped design): among the six main parties, top-1 differs too little to measure with these sample sizes, both on the "
  "S9 production rows and held out in S25. This is not evidence of no difference: the gap intervals reach up to "
  f"{L(F.signed(F.hi(gmax['ci95'][1])), gmax['at'])}. The lowest party is not the same in the two sets (Mitte and SVP in S9 prod, SP in S25). "
  "Members' affairs score below committee and government business (pooled test above), as in "
  "S14. Unlike S14, the keyword baseline on the production input does not order the submitter types that way "
  f"(S9 prod keyword {L('p ' + str(kk9['p_perm']), kk9['at'])}), so «easier texts» is not shown for submitter type here; by "
  f"instrument it is (S9 prod keyword {L('p ' + str(ki9['p_perm']), ki9['at'])}, Parlamentarische Initiative highest and Postulat "
  "lowest, as for Apertus).")
w("")
w("**Earlier design (S14, «D1, earlier design»), same 1,357 S9 affairs, Curia input.**")
w("")
w(f"Language, same {num(ns['n'], 0)} affairs scored from the German vs the French text (paired, one identity-order chapter call each): German − French "
  f"{r(ns['result'], signed=True)}, McNemar p {ns['result']['p_mcnemar']}.")
w("")
cell_table("S9 by party (D1, earlier design)", [bd["party_D1_top1"], bd["party_keyword_top1"]], ["D1 top-1", "keyword top-1"])
cell_table("S9 by instrument (D1, earlier design)", [bd["instrument_D1_top1"], bd["instrument_keyword_top1"]], ["D1 top-1", "keyword top-1"])
w("Reading (D1): top-1 differs too little to measure with these sample sizes by language and among the six main parties (this is not "
  "evidence of no difference; the party gaps' intervals are wide). Government business scores higher than members' motions, and the "
  "keyword baseline shows the same order (easier texts, not a political tilt). Quality is reported per submitter type.")
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
w("The shipped lane rule (recalibrated p ≥ 0.7) on these rows, computed after S17 and not pre-registered: §1g (agreement with the judge).")
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
w("### 15 · New topics defined in one sentence: wolf, heat protection, AI in schools; held out: light pollution, drones, pesticides "
  "(S19, S26, S27, S30, pre-registered)")
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

# S30: three further narrow topics held out; a generated scope as a third question on the confirmed flags
a30 = T["adhoc_scope_check"]; p30 = a30["breakdowns"]["per_topic"]; TOP30 = a30["topics"]; j30 = a30["judge"]
rule30, dev30 = a30["breakdowns"]["product_rule"], a30["breakdowns"]["dev"]
nb30 = {s_: next(c for c in p30[s_]["strata"]["cells"] if c["cell"] == "neither") for s_ in TOP30}
pp = p30["pooled"]
w(f"**A generated scope as a third question on the flags (S30, held out, pre-registered).** Dev on the S19 packets above (four variants, "
  "tuning allowed; not held out) picked the variant: V4, chosen after its dev results were seen, as the pre-registration states "
  f"({L('PREREG-BUILD.md § S30', a30['prereg'])}, {L('dev choice', dev30['chosen_at'])}). One more plain generation request per topic writes "
  "an include and an exclude list in de/fr/it from the user's sentence, and every confirmed flag is asked «Gehört das folgende "
  "parlamentarische Geschäft zum Thema «…»?» with those lists (plus «affairs whose title does not show the topic» as an exclusion); a flag "
  "stays confirmed only if the S27 question and this one both say yes. Test: three new one-sentence topics, never used before "
  f"(«{p30['licht']['name_de']}», «{p30['drohnen']['name_de']}», «{p30['pestizide']['name_de']}» as generated from the sentences in "
  f"[`eval/s30/sentences.json`](../eval/s30/sentences.json)), every affair with a title begun 16–31 Mar 2026 "
  f"({L(num(a30['n']), p30['licht']['strata']['at'])}); generated topics and keyword lists frozen before any test call "
  "([`eval/s30/topics.json`](../eval/s30/topics.json), [`eval/s30/keywords_frozen.json`](../eval/s30/keywords_frozen.json)). Checked: every "
  f"affair any arm or keyword list flagged plus {L(str(nb30['licht']['n']), p30['licht']['strata']['at'])} random others per topic "
  f"({L(num(j30['items']), pp['items_checked']['at'])} in all), shown with title, long title and the start of the text. Judge: blind Claude "
  f"runs A (shuffled) and B (reversed) agree on every item (run A = run B {L(num(j30['agree_AB']), j30['at'])}, "
  f"{L(str(j30['tie_break_C']), j30['tie_break_at'])} tie-breaks); judge positives among the random others: "
  + ", ".join(f"{L(nb30[s_]['kn'], p30[s_]['strata']['at'])} ({p30[s_]['name_en']})" for s_ in TOP30) +
  ". Shipped = the product before S30 (yes/no flag kept by the S27 question). Precision of flags: Wilson 95% from k and n, bounds outward; "
  "recall weighted to the population and differences paired on the same resamples (stratified bootstrap 2,000) "
  "([`eval/s30/analyze.py`](../eval/s30/analyze.py) → [`eval/s30/results.json`](../eval/s30/results.json)).")
w("")
w("| S30, agreement with the AI judge, held out | judge positives (checked) | flags shipped / with scope check | precision shipped | "
  "precision with scope check | Δ precision, paired | recall shipped | recall with scope check | Δ recall, paired | "
  "keyword list: precision / recall |")
w("|---|---|---|---|---|---|---|---|---|---|")
for s_ in TOP30 + ["pooled"]:
    b_ = p30[s_]; sh_, va_, kw_ = b_["shipped"], b_["variant"], b_["kw"]
    nm_ = f"**{b_['name_en']}**" if s_ == "pooled" else b_["name_en"]
    w(f"| {nm_} | {cnt(b_['judge_positives'])} ({cnt(b_['items_checked'])}) | {cnt(sh_['flags'])} / {cnt(va_['flags'])} | {rk(sh_['precision'])} | "
      f"**{rk(va_['precision'])}** | {r(b_['precision_diff'], signed=True)} | {r(sh_['recall'])} | {r(va_['recall'])} | "
      f"{r(b_['recall_diff'], signed=True)} | {rk(kw_['precision'])} / {r(kw_['recall'])} |")
w("")
yn_, ys_ = pp["shipped_yn"], pp["yn_sc"]
w(f"Secondary arms (pre-registered), pooled: the yes/no step alone {rk(yn_['precision'])}, recall {r(yn_['recall'])}; yes/no + scope question "
  f"without the S27 question {rk(ys_['precision'])}, recall {r(ys_['recall'])}.")
w("")
pe_ = p30["pestizide"]
w(f"Reading, all against the AI judge: pooled over the three topics the scope check raises the precision of confirmed flags from "
  f"{L(num(pp['shipped']['precision']['value']), pp['shipped']['precision']['at'])} to {L(num(pp['variant']['precision']['value']), pp['variant']['precision']['at'])} "
  f"({r(pp['precision_diff'], signed=True)}) and costs recall ({L(num(pp['shipped']['recall']['value']), pp['shipped']['recall']['at'])} → "
  f"{L(num(pp['variant']['recall']['value']), pp['variant']['recall']['at'])}, {r(pp['recall_diff'], signed=True)}): it drops "
  f"{L(str(pp['lost_judge_positives']['value']), pp['lost_judge_positives']['at'])} judge positives, both pesticides affairs (veterinary insecticides; "
  "pests and plant diseases). It asks only on flags the shipped design already confirms, so recall can only fall. "
  f"{L('The pre-registered product rule', rule30['at'])} (pooled precision interval above 0, no recall interval below 0) is met, narrowly: the "
  f"precision interval starts at {L(sgn(rule30['pooled_precision_diff_ci_lo']), pp['precision_diff']['ci_at'])}, and the pooled and pesticides "
  f"recall intervals end at {L(num(rule30['recall_diff_ci_hi']['pooled']), pp['recall_diff']['ci_at'])}. So the product asks it for new topics "
  "with a scope (`prompts.scope_check_prompt`, `adhoc.SCOPE_PROMPT`); flags it does not confirm go to `please check`, not away; topic files "
  "without the lists (Digitalisierung, the S19 topics) are unchanged. The frozen keyword lists beat both arms on precision here: pooled "
  f"{rk(pp['kw']['precision'])} against {L(num(pp['variant']['precision']['value']), pp['variant']['precision']['at'])} with the scope check and "
  f"{L(num(pp['shipped']['precision']['value']), pp['shipped']['precision']['at'])} without (Wilson intervals overlap; not a paired test), at recall "
  f"{r(pp['kw']['recall'])}. Judge positives per topic are "
  + " / ".join(f"{cnt(p30[s_]['judge_positives'])}" for s_ in TOP30) +
  f" ({', '.join(p30[s_]['name_en'] for s_ in TOP30)}): too few to read any topic on its own; the rule and this reading rest on the pooled figures.")
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
  f"narrow topics: precision of flags {rk(p19['wolf']['precision'])} for wolf, {rk(p19['ki-schule']['precision'])} for AI in schools (§15). "
  f"On three further narrow topics held out (S30), the scope check (now asked for new topics with a scope) raises pooled precision from "
  f"{L(num(pp['shipped']['precision']['value']), pp['shipped']['precision']['at'])} to {L(num(pp['variant']['precision']['value']), pp['variant']['precision']['at'])} "
  f"({r(pp['precision_diff'], signed=True)}) at a recall cost ({r(pp['recall_diff'], signed=True)}), on {cnt(pp['judge_positives'])} judge positives "
  f"in all; the frozen keyword lists were more precise still ({L(num(pp['kw']['precision']['value']), pp['kw']['precision']['at'])}).")
w(f"- The federal design was chosen on the design set (§1). A search of five variants there (S31, §1d; dev only, not pre-registered) found none "
  f"that clears the gate (best {r(t31['result'], d=4, signed=True)}); the S25 held-out items stay unspent for one pre-registered look at a single "
  f"winner, and no fresh APS-labelled items were available (§1d).")
w(f"- The held-out test (S25, §1b) pre-registered the chapter, its lanes and plain list prompting (S25b); its subtopic and hierarchical "
  f"figures (subtopic top-1 {r(hm25['subtopic top-1 end to end (shipped, held out)'])}, hF {r(t25h['result'])}) were computed after the "
  f"result and are not pre-registered. Its D1 cell (no APS-labelled example: one-word procedural titles such as «Vereidigung», or a French "
  f"text) holds {num(dd25['D1']['n'])} affairs, too few to measure D1 held out.")
w(f"- Without prefill (the endpoint fallback `QS_PREFILL=0`, §1c) the chapter top-1 on the held-out affairs is {r(t28['result'])}, paired "
  f"prefill − no prefill {r(d28, signed=True)}; no calibration map exists for that mode, so its lane is the readings rule, not the "
  "recalibrated p. Measured on one build; another endpoint may tokenise the JSON opening differently (the S28 amendment).")
w(f"- French federal text (§1e, S33) is measured held out with production's French path, D1 without examples: French − German shipped "
  f"{r(d33, signed=True)} mixes language and design (German has the five examples). The same-design comparison ({r(ro33['paired'], signed=True)}) "
  "is at the level of the chapter readings only, without the subtopic read-back. Italian held out is not measured (S22 is on the design set).")
w(f"- Ticino (§6b, Italian, the canton's own lead department) is measured on the inputs that do not name the unit ({num(ti['n'])} of "
  f"{num(a9['n'])}). The State Chancellery and «none of these» are weak "
  f"({num(next(c for c in bg9['cells'] if c['cell'] == 'Cancelleria dello Stato')['value'])} and "
  f"{num(next(c for c in bg9['cells'] if c['cell'] == NONE9)['value'])}); the gold is OPD's lead-department field, and its licence is "
  "unconfirmed (SOURCES.md). No French-speaking parliament's own scheme is measured yet (Bern's French titles, §5, are the closest).")
w(f"- The trained baseline (§1f, S34) is fitted on the {num(tr34['value'], 0)} APS labels the shipped design holds; its learning curve is still "
  f"rising ({' / '.join(num(p_['value']) for p_ in lc34)}), so a classifier trained on many more labels is not measured.")
w(f"- The calibration is in-sample on the design set (ECE {num(lh['result']['in_sample'], 4)}); held out on the S25 affairs it is "
  f"{num(lh['result']['value'], 4)} (§1g, computed after the results, not pre-registered). French and Italian affairs go to `please check` "
  f"more often than German ones at every level of the shipped export (all levels: {num(pcs['by_language']['fr']['value'])} French, "
  f"{num(pcs['by_language']['it']['value'])} Italian, {num(pcs['by_language']['de']['value'])} German).")
w("- All Apertus rows come from one served build; cut-offs and recalibration are refitted per build. ECE intervals are not computed yet.")
w("")
w("## To measure")
w("")
for x in P["to_measure"]:
    w(f"- {x['item']} (pre-registered: {L('PREREG-BUILD.md § ' + x['item'].split(':')[0], x['prereg'])})" if isinstance(x, dict) else f"- {x}")
w("")
open(DOC, "w", encoding="utf-8").write("\n".join(out))
print("wrote", DOC, len(out), "lines")
