# Prüfstand

Every measured test behind Querschnitt, as one ruled table each. Human labels first, then the blind AI judge. Model `swiss-ai/apertus-v1.5-8b` on Public AI, build `…dd237840` on every Apertus call. Intervals are 95%: Wilson for proportions, paired bootstrap (2,000) for differences, stratified bootstrap for population estimates. Shown values are truncated, never rounded up. Every Wilson interval is recomputed exactly from k and n with the lower bound floored and the upper bound ceiled at 3 decimals (the result files store them rounded to the nearest 0.001; pruefstand.json keeps that as `ci95_source`); bootstrap percentiles are floored / ceiled as stored. Machine-readable: [`eval/pruefstand.json`](../eval/pruefstand.json) (file and key for every value); claims register: [`eval/claims.tsv`](../eval/claims.tsv); check any text with `python3 -I tools/claims_check.py FILE`. Links point into [`eval/spikes/`](../eval/spikes/) for the pre-registered spikes S1–S15 (vendored evidence: results, scripts, annotations, raw model outputs) and into `eval/` for the build-week tests (pre-registered in [`eval/PREREG-BUILD.md`](../eval/PREREG-BUILD.md)).

## Human labels

### 1 · APS chapter vs APS editors — 1,357 federal affairs, pre-registered (S9, S16)

Wayback process pages not used before; German title + submitted text. Pre-registration: [PREREG.md § S9](../eval/spikes/PREREG.md#L32); the shipped federal design and its decision rule: [PREREG-BUILD.md § S16](../eval/PREREG-BUILD.md#L6). D0–D3 are held out on these items (S9, nothing tuned on them). D4 is pre-registered (S16) and measured on the same S9 items, but its design was chosen after S9 on those items (D4 combines D1 and D3): these 1,357 items are the set the shipped design was chosen on, so its row is not a held-out result. The held-out test of the shipped design is §1b: S25, 927 fresh federal affairs ([PREREG-BUILD.md § S25](../eval/PREREG-BUILD.md#L85)). A later search of five design variants on these items (S31, §1d; dev only, not pre-registered) found none that beats D4.

| Design | top-1 | top-3 | Δ top-1, paired | |
|---|---|---|---|---|
| **D4 five APS-labelled examples + chapter read back from the subtopic, both code orders always** | **[0.740 [0.716, 0.764]](../eval/s16/results.json)** | [0.883](../eval/s16/results.json) | vs D3 [+0.018 [+0.002, +0.034]](../eval/s16/results.json) · vs D1 [+0.036 [+0.021, +0.054]](../eval/s16/results.json) | **shipped, federal affairs** (S16) |
| D4s as D4, second code order only when p < 0.9 | [0.748 [0.724, 0.772]](../eval/s16/results.json) | [0.856](../eval/s16/results.json) | vs D3 [+0.026 [+0.011, +0.042]](../eval/s16/results.json) · vs D1 [+0.045 [+0.026, +0.063]](../eval/s16/results.json) | secondary, reported, not shipped (S16) |
| D3 chapter step with five APS-labelled examples | [0.722 [0.697, 0.746]](../eval/spikes/s9-aps/results.json) | [0.874 [0.856, 0.892]](../eval/spikes/s9-aps/results.json) | vs D0 [+0.067 [+0.049, +0.085]](../eval/spikes/s9-aps/results.json) | building block of D4 (S9) |
| D1 chapter read back from the subtopic, no examples | [0.703 [0.678, 0.728]](../eval/spikes/s9-aps/results.json) | [0.843 [0.822, 0.862]](../eval/spikes/s9-aps/results.json) | vs D0 [+0.048 [+0.032, +0.066]](../eval/spikes/s9-aps/results.json) | shipped where no APS examples exist (S9) |
| D2 German + French averaged | [0.634 [0.608, 0.660]](../eval/spikes/s9-aps/results.json) | [0.853 [0.833, 0.872]](../eval/spikes/s9-aps/results.json) | vs D0 [−0.020 [−0.037, −0.004]](../eval/spikes/s9-aps/results.json) | dropped for the label (S9) |
| D0 plain list prompting (v14) | [0.655 [0.629, 0.680]](../eval/spikes/s9-aps/results.json) | — | — | baseline |
| keyword (APS subtopic words, frozen) | [0.191 [0.171, 0.214]](../eval/spikes/s9-aps/results.json) | — | — | baseline |
| majority chapter | [0.079 [0.066, 0.096]](../eval/spikes/s9-aps/results.json) | — | — | baseline |

Decision ([S16 results](../eval/s16/results.json)): D4 shipped for federal affairs (pre-registered rule: D4 if its top-1 ≥ D3's). The corpus run uses D4 as registered: both code orders always, examples on the first. D4s (secondary) is reported, not shipped.

**Lanes of D4** (the reading with examples and the reading without agree / disagree on the chapter): readings agree on [64.1%](../eval/s16/results.json) of affairs ([871](../eval/s16/results.json)), precision [0.826 [0.800, 0.851]](../eval/s16/results.json); they disagree on [486](../eval/s16/results.json), precision [0.586 [0.542, 0.630]](../eval/s16/results.json). This was the lane rule until 14 Oct; the shipped rule is now the recalibrated p (below).

**Lane rule: `please check` when the recalibrated p < 0.7** — computed after S16 from its rows (not pre-registered; no new calls); tested held out in S25 ([PREREG-BUILD.md § S25](../eval/PREREG-BUILD.md#L85), §1b). The isotonic map is 2-fold cross-fitted on the 1,357 S16 items, so every affair's recalibrated p comes from the half it was not fitted on ([`eval/lanes/analyze.py`](../eval/lanes/analyze.py) → [`eval/lanes/results.json`](../eval/lanes/results.json)). The threshold was chosen on these same items, so the numbers below are in-sample for the choice of rule (held out: §1b). In production the rule is `LANE_TAU` in [`src/querschnitt/compose.py`](../src/querschnitt/compose.py); a bilingual parliament whose German and French readings disagree still goes to `please check`.

| Design | rule | passed (share of affairs, n) | precision of the passed | `please check`: precision (n) |
|---|---|---|---|---|
| **D4** (federal) | **recalibrated p ≥ 0.7 (shipped)** | [66.8%](../eval/lanes/results.json), [907](../eval/lanes/results.json) | **[0.864 [0.840, 0.886]](../eval/lanes/results.json)** | [0.491 [0.445, 0.538]](../eval/lanes/results.json) ([450](../eval/lanes/results.json)) |
| **D4** (federal) | readings agree (rule until 14 Oct) | [64.1%](../eval/lanes/results.json), [871](../eval/lanes/results.json) | [0.826 [0.800, 0.851]](../eval/lanes/results.json) | — |
| **D4** (federal) | recalibrated p, same share as readings agree | [64.1%](../eval/lanes/results.json), [871](../eval/lanes/results.json) | [0.866 [0.842, 0.888]](../eval/lanes/results.json) | — |
| D1 (no APS examples) | **recalibrated p ≥ 0.7 (shipped)** | [59.6%](../eval/lanes/results.json), [810](../eval/lanes/results.json) | **[0.843 [0.816, 0.867]](../eval/lanes/results.json)** | [0.497 [0.455, 0.540]](../eval/lanes/results.json) ([547](../eval/lanes/results.json)) |
| D1 (no APS examples) | readings agree (rule until 14 Oct) | [61.0%](../eval/lanes/results.json), [828](../eval/lanes/results.json) | [0.797 [0.768, 0.824]](../eval/lanes/results.json) | — |
| D1 (no APS examples) | recalibrated p, same share as readings agree | [61.0%](../eval/lanes/results.json), [828](../eval/lanes/results.json) | [0.839 [0.812, 0.863]](../eval/lanes/results.json) | — |

**Calibration of D4** ([S16](../eval/s16/results.json); isotonic, 2-fold cross-fitted, n 1,357; the map the production run reads, [`eval/calibration.json`](../eval/calibration.json)): expected calibration error [0.2463](../eval/s16/results.json) raw → [0.0211](../eval/s16/results.json) recalibrated (D1, same file: [0.2791](../eval/s16/results.json) → [0.0319](../eval/s16/results.json)).

Per period, D3: pre-2010 [0.678 [0.493, 0.821], n 28](../eval/spikes/s9-aps/results.json) · 2010-19 [0.697 [0.653, 0.739], n 446](../eval/spikes/s9-aps/results.json) · 2020+ [0.736 [0.706, 0.765], n 883](../eval/spikes/s9-aps/results.json).
Lanes of D3 (S9; the two code orders agree / disagree): orders agree [0.610](../eval/spikes/s9-aps/results.json) of affairs, D3 precision [0.812 [0.784, 0.838]](../eval/spikes/s9-aps/results.json) · orders disagree [0.389](../eval/spikes/s9-aps/results.json) of affairs, D3 precision [0.580 [0.537, 0.622]](../eval/spikes/s9-aps/results.json).
Per chapter: macro-F1 [0.677](../eval/spikes/s9c-calibration/perlevel.json) (D1), [0.692](../eval/spikes/s9c-calibration/perlevel.json) (D3) over the [22](../eval/spikes/s9c-calibration/perlevel.json) chapters present.

**Confidence (S9c, 2-fold cross-fitted isotonic recalibration, no new calls).** Expected calibration error:

| | D0 | D1 | D3 |
|---|---|---|---|
| raw p | [0.262](../eval/spikes/s9c-calibration/results.json) | [0.279](../eval/spikes/s9c-calibration/results.json) | [0.221](../eval/spikes/s9c-calibration/results.json) |
| recalibrated | [0.035](../eval/spikes/s9c-calibration/results.json) | [0.037](../eval/spikes/s9c-calibration/results.json) | [0.017](../eval/spikes/s9c-calibration/results.json) |

**Coverage–precision** (top-1 precision on the affairs that pass, ranked by confidence; the rest go to `please check`).

| coverage | 50% | 60% | 70% | 80% | 90% | 100% |
|---|---|---|---|---|---|---|
| **D4 shipped** (S16) | [0.890 [0.865, 0.913]](../eval/s16/results.json) | [0.875 [0.851, 0.897]](../eval/s16/results.json) | [0.850 [0.826, 0.872]](../eval/s16/results.json) | [0.821 [0.797, 0.844]](../eval/s16/results.json) | [0.781 [0.757, 0.804]](../eval/s16/results.json) | [0.740 [0.716, 0.764]](../eval/s16/results.json) |
| D3 examples (S9) | [0.895 [0.869, 0.917]](../eval/aps_curves.json) | [0.864 [0.839, 0.887]](../eval/aps_curves.json) | [0.842 [0.817, 0.864]](../eval/aps_curves.json) | [0.808 [0.783, 0.831]](../eval/aps_curves.json) | [0.764 [0.740, 0.788]](../eval/aps_curves.json) | [0.722 [0.697, 0.746]](../eval/aps_curves.json) |
| D1 read-back (S9) | [0.864 [0.836, 0.889]](../eval/aps_curves.json) | [0.845 [0.818, 0.869]](../eval/aps_curves.json) | [0.809 [0.783, 0.834]](../eval/aps_curves.json) | [0.787 [0.761, 0.811]](../eval/aps_curves.json) | [0.744 [0.719, 0.769]](../eval/aps_curves.json) | [0.703 [0.678, 0.728]](../eval/aps_curves.json) |

D4 points are read from [S16 coverage_precision](../eval/s16/results.json) (one point per affair). S9 rows recomputed from S9 raw logs by [`eval/scripts/aps_curves.py`](../eval/scripts/aps_curves.py) (full curve in 5% steps); the D3 precisions at 50, 70, 90 and 100% equal [S9 results.json](../eval/spikes/s9-aps/results.json). The app's chart is the D4 curve with the shipped operating point marked: recalibrated p ≥ 0.7, coverage [66.8%](../eval/lanes/results.json), precision [0.864 [0.840, 0.886]](../eval/lanes/results.json) (chosen after S16 on these items; tested held out in S25, §1b); the earlier point, readings agree, is shown for comparison: coverage [64.1%](../eval/s16/results.json), precision [0.826 [0.800, 0.851]](../eval/s16/results.json).

### 1b · APS chapter held out — 927 fresh federal affairs, the shipped design as in production (S25, pre-registered)

The held-out test of the shipped federal design. §1's 1,357 items are the set the design was chosen on; none of these 927 was used while designing. Items: federal affairs with an APS editors' chapter recovered from Wayback captures of anneepolitique.swiss process pages, none in the S5 or S9 sets or in the example pool (the analysis asserts it), parsed with the S9 rules ([`eval/s25/FETCH.md`](../eval/s25/FETCH.md)). The production pipeline as shipped, unchanged: D4 (the five BM25-nearest APS-labelled examples from the S5+S9 pool + a second reading without examples, chapter read back from the subtopic) for the [917](../eval/s25/results.json) affairs with German text and APS-labelled neighbours, D1 (no examples) for the [10](../eval/s25/results.json) with no APS-labelled example: one-word procedural titles such as «Vereidigung» (also «Nachruf», «Ordnungsantrag») have no BM25 neighbour in the pool (9), and one text is French ([1](../eval/s25/results.json)); lanes by the recalibrated p with the calibration map fitted on S16 only; decisions composed exactly as the export composes them ([`eval/s25/analyze.py`](../eval/s25/analyze.py) → [`eval/s25/results.json`](../eval/s25/results.json); one line per affair in [`eval/s25/decisions.jsonl`](../eval/s25/decisions.jsonl)). Pre-registration: [PREREG-BUILD.md § S25](../eval/PREREG-BUILD.md#L85) and [its amendment](../eval/PREREG-BUILD.md#L127) (a determinism fix before the final score).

| n = 927, gold = APS editors' chapter | top-1 | top-3 |
|---|---|---|
| **production pipeline as shipped, held out** | **[0.696 [0.666, 0.726]](../eval/s25/results.json)** ([646/927](../eval/s25/results.json)) | [0.839 [0.814, 0.862]](../eval/s25/results.json) |
| plain list prompting (S9 D0; S25b, pre-registered; 918 of the 927 affairs) | [0.654 [0.623, 0.685]](../eval/s25b/results.json) ([601/918](../eval/s25b/results.json)) | — |
| keyword (S9 frozen rule, same input) | [0.186 [0.162, 0.213]](../eval/s25/results.json) | — |
| for reference: D4 on the design set (§1, other items, not held out) | [0.740 [0.716, 0.764]](../eval/s16/results.json) | [0.883](../eval/s16/results.json) |

**Plain list prompting on the same affairs** ([PREREG-BUILD.md § S25b](../eval/PREREG-BUILD.md#L138), pre-registered after the S25 result, before any S25b call; [`eval/s25b/analyze.py`](../eval/s25b/analyze.py) → [`eval/s25b/results.json`](../eval/s25b/results.json)): S9's D0 — the chapter prompt without examples in two code orders, chapter = top of the geometric mean — on the same build and input. On the [918](../eval/s25b/results.json) affairs where both readings exist, D0 reaches [0.654 [0.623, 0.685]](../eval/s25b/results.json) ([601/918](../eval/s25b/results.json)) and the shipped pipeline [0.696 [0.665, 0.725]](../eval/s25b/results.json) ([639/918](../eval/s25b/results.json)); paired, shipped − D0 = [+0.041 [+0.016, +0.067]](../eval/s25b/results.json) (paired bootstrap 2,000 over affairs, bounds outward). Not scored: [9](../eval/s25b/results.json) one-word procedural affairs read without examples whose first reading had p ≥ 0.9, so the production run asked no second reading, which D0 needs.

**Before the fix** ([amendment](../eval/PREREG-BUILD.md#L127)): the BM25 example retrieval summed over a Python set, whose order is randomised per process, so a restarted run could ask different examples for the same affair. Two compositions of the finished run were seen with the old retrieval before the fix: [904](../eval/PREREG-BUILD.md#L132) scored, top-1 [0.7035 (636/904)](../eval/PREREG-BUILD.md#L132) [0.672, 0.733], and [905](../eval/PREREG-BUILD.md#L132) scored, [0.6994 (633/905)](../eval/PREREG-BUILD.md#L132) [0.668, 0.729] (Wilson intervals computed here from k and n). The final score above is the fixed code on all 927 affairs, scored once.

| S25 lane, held out | share of affairs (n) | precision | design set, for reference (§1, 1,357 items: n, precision) |
|---|---|---|---|
| **pass: recalibrated p ≥ 0.7 (shipped)** | [67.3%](../eval/s25/results.json) ([624](../eval/s25/results.json)) | **[0.812 [0.779, 0.842]](../eval/s25/results.json)** | [907](../eval/lanes/results.json), [0.864 [0.840, 0.886]](../eval/lanes/results.json) |
| `please check`: recalibrated p < 0.7 | [32.6%](../eval/s25/results.json) ([303](../eval/s25/results.json)) | [0.458 [0.403, 0.516]](../eval/s25/results.json) | [450](../eval/lanes/results.json), [0.491 [0.445, 0.538]](../eval/lanes/results.json) |
| readings agree (earlier rule) | [65.1%](../eval/s25/results.json) ([604](../eval/s25/results.json)) | [0.786 [0.751, 0.818]](../eval/s25/results.json) | [871](../eval/lanes/results.json), [0.826 [0.800, 0.851]](../eval/lanes/results.json) |
| readings disagree | [34.8%](../eval/s25/results.json) ([323](../eval/s25/results.json)) | [0.529 [0.474, 0.584]](../eval/s25/results.json) | [486](../eval/s16/results.json), [0.586 [0.542, 0.630]](../eval/s16/results.json) |

The design-set figures of the recalibrated rule are in-sample for the choice of the 0.7 threshold (2-fold cross-fitted map); in S25 the map is the one fitted on S16 and the threshold is fixed.

**Routing by the recalibrated p** (S25, held out; coverage = share of affairs at or above the threshold, precision of those):

| recalibrated p ≥ | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 |
|---|---|---|---|---|---|
| coverage | [80.1%](../eval/s25/results.json) | [78.1%](../eval/s25/results.json) | [67.3%](../eval/s25/results.json) | [56.8%](../eval/s25/results.json) | [27.1%](../eval/s25/results.json) |
| precision | [0.775 [0.743, 0.804]](../eval/s25/results.json) | [0.781 [0.750, 0.811]](../eval/s25/results.json) | [0.812 [0.779, 0.842]](../eval/s25/results.json) | [0.836 [0.802, 0.866]](../eval/s25/results.json) | [0.912 [0.871, 0.942]](../eval/s25/results.json) |
| n | [743](../eval/s25/results.json) | [724](../eval/s25/results.json) | [624](../eval/s25/results.json) | [527](../eval/s25/results.json) | [252](../eval/s25/results.json) |

By design: D4 (German text, five examples) [0.695 [0.665, 0.725]](../eval/s25/results.json), n 917; D1 (no examples: no APS-labelled neighbour for one-word procedural titles such as «Vereidigung», or a French text) [8/10](../eval/s25/results.json) [0.490, 0.944] (small). By Curia year: [244](../eval/s25/results.json) affairs submitted before 2015, [683](../eval/s25/results.json) from 2015 on. Gold chapters ([22](../eval/s25/results.json) present): Institutionen und Volksrechte [108](../eval/s25/results.json) · Aussenpolitik [93](../eval/s25/results.json) · Sozialversicherungen [92](../eval/s25/results.json) · Verkehr und Kommunikation [78](../eval/s25/results.json) · Soziale Gruppen [68](../eval/s25/results.json) · Rechtsordnung [57](../eval/s25/results.json) · Geld, Währung und Kredit [54](../eval/s25/results.json) · Wirtschaftspolitik [53](../eval/s25/results.json) · Gesundheit, Sozialhilfe, Sport [50](../eval/s25/results.json) · Öffentliche Finanzen [46](../eval/s25/results.json) · Umweltschutz [36](../eval/s25/results.json) · Landwirtschaft [35](../eval/s25/results.json) · Energie [28](../eval/s25/results.json) · Landesverteidigung [23](../eval/s25/results.json) · Bildung und Forschung [20](../eval/s25/results.json) · Raumplanung und Wohnungswesen [18](../eval/s25/results.json) · Bevölkerung und Arbeit [17](../eval/s25/results.json) · Politische Grundfragen [15](../eval/s25/results.json) · Kultur, Sprache, Kirchen [14](../eval/s25/results.json) · Föderativer Aufbau [11](../eval/s25/results.json) · Medien [8](../eval/s25/results.json) · Verbände [3](../eval/s25/results.json).

**Subtopic and hierarchy, held out** — computed after the S25 result from its rows (not pre-registered; no new calls) by [`eval/s25/hierarchical.py`](../eval/s25/hierarchical.py) → [`eval/s25/hierarchical.json`](../eval/s25/hierarchical.json), with the definitions of [`eval/s16/hierarchical.py`](../eval/s16/hierarchical.py) (§2): the 891 S25 affairs whose main subtopic is among the 190 for the subtopic and hierarchical figures, per-chapter macro-F1 over the [22](../eval/s25/hierarchical.json) chapters present on all 927 affairs. Wilson for the subtopic rates, percentile bootstrap 2,000 for hP/hR/hF and macro-F1, bounds outward. The [S25b entry](../eval/PREREG-BUILD.md#L138) notes these figures as not pre-registered.

| Design | subtopic top-1 | subtopic top-3 | subtopic top-1 when the chapter is right | hP | hR | hF | per-chapter macro-F1 |
|---|---|---|---|---|---|---|---|
| **shipped, held out (S25; not pre-registered)** | **[0.497 [0.464, 0.530]](../eval/s25/hierarchical.json)** | [0.650 [0.619, 0.682]](../eval/s25/hierarchical.json) | [0.708 [0.671, 0.744]](../eval/s25/hierarchical.json) (n 625) | [0.609 [0.580, 0.638]](../eval/s25/hierarchical.json) | [0.599 [0.570, 0.628]](../eval/s25/hierarchical.json) | **[0.604 [0.575, 0.633]](../eval/s25/hierarchical.json)** | [0.647 [0.611, 0.681]](../eval/s25/hierarchical.json) |
| for reference: D4 on the design set (§2, other items, not held out) | [0.538 [0.510, 0.567]](../eval/s16/hierarchical.json) | [0.699 [0.673, 0.725]](../eval/s16/hierarchical.json) | [0.727 [0.697, 0.756]](../eval/s16/hierarchical.json) (n 905) | [0.640 [0.616, 0.663]](../eval/s16/hierarchical.json) | [0.640 [0.616, 0.663]](../eval/s16/hierarchical.json) | [0.640 [0.616, 0.663]](../eval/s16/hierarchical.json) | [0.705 [0.680, 0.729]](../eval/s16/hierarchical.json) |

### 1c · Without prefill (endpoint fallback): the same 927 held-out affairs (S28, pre-registered)

An endpoint-capability check, not a new design: what the labelled fallback costs if the serving endpoint cannot continue an assistant message (the shipped design pre-fills the JSON opening and reads the code from the next token). With `QS_PREFILL=0` the pipeline sends one user message, the measured prompt plus a line asking the answer to begin with the JSON opening, and reads the code from the `top_logprobs` of the first token after that opening. Everything else as shipped (D4 / D1 as in §1b), on the same build; no calibration map exists for this mode, so its lane is the readings rule (pass when the two code orders agree or one reading has top p ≥ 0.9). Paired against the S25 final decisions on the same affairs ([`eval/s28/analyze.py`](../eval/s28/analyze.py) → [`eval/s28/results.json`](../eval/s28/results.json)). Pre-registration: [PREREG-BUILD.md § S28](../eval/PREREG-BUILD.md#L148) and [its amendment](../eval/PREREG-BUILD.md#L173) (a read fix after the first 20-item smoke run, whose 28 calls were never scored).

| n = 927, gold = APS editors' chapter | top-1 | top-3 |
|---|---|---|
| **no prefill (`QS_PREFILL=0`), otherwise as shipped** | **[0.705 [0.675, 0.734]](../eval/s28/results.json)** ([654/927](../eval/s28/results.json)) | [0.839 [0.814, 0.862]](../eval/s28/results.json) |
| shipped prefill design (S25 final, §1b), same affairs | [0.696 [0.666, 0.726]](../eval/s28/results.json) ([646/927](../eval/s28/results.json)) | [0.839 [0.814, 0.862]](../eval/s28/results.json) |
| paired, prefill − no prefill (bootstrap 2,000, bounds outward) | [−0.008 [−0.022, +0.004]](../eval/s28/results.json) | [0.000 [−0.011, +0.011]](../eval/s28/results.json) |

The two modes give the same chapter on [876](../eval/s28/results.json) of 927 affairs ([0.944 [0.928, 0.958]](../eval/s28/results.json)). Lane without prefill (readings rule): [64.2%](../eval/s28/results.json) pass ([596](../eval/s28/results.json)), precision [0.805 [0.771, 0.836]](../eval/s28/results.json); `please check` [331](../eval/s28/results.json), precision [0.525 [0.471, 0.579]](../eval/s28/results.json). With prefill the shipped lane is the recalibrated p (§1b: [67.3%](../eval/s25/results.json) pass, precision [0.812 [0.779, 0.842]](../eval/s25/results.json)). Read path: every step row's code came from the logprobs ([2,723](../eval/s28/results.json) rows; [0](../eval/s28/results.json) affairs with a code read from the generated text, [0](../eval/s28/results.json) with an unparseable row).

### 1d · Design search on the design set: five variants against D4, none better (S31, dev only, not pre-registered)

A documented search for a better federal design on §1's 1,357 items, the set D4 was chosen on. This is dev, not a test: it has no pre-registration entry and nothing in it is held out; it documents that the shipped design was not beaten there. Same input as S16; examples leave-one-out (every item's example list excludes the item itself); one decision rule for every design (`compose.chapter_decision` generalised to n readings). The gate was fixed before any S31 call: a paired difference vs D4 of at least [+0.02](../eval/s31/DEV.md#L4) on all 1,357 items, with the 95% interval above 0. Stage 1 scored the five variants on a fixed random [400](../eval/s31/results.json) items (V5 was added after V1–V4 had been seen there, as their combination); the best two went to all 1,357 ([`eval/s31/DEV.md`](../eval/s31/DEV.md); [`eval/s31/analyze.py`](../eval/s31/analyze.py) → [`eval/s31/results.json`](../eval/s31/results.json)). Gold: APS editors' chapter. Top-1 with Wilson 95% (bounds outward); Δ paired bootstrap 2,000 over items, bounds outward at 4 decimals.

| Variant (what changes vs D4) | stage 1, 400 items: top-1 | Δ vs D4, paired | all 1,357 items: top-1 | top-3 | Δ vs D4, paired | gate (≥ +0.02, interval above 0) |
|---|---|---|---|---|---|---|
| **D4 (shipped)** | [0.707 [0.661, 0.750]](../eval/s31/results.json) | — | [0.737 [0.713, 0.761]](../eval/s31/results.json) | [0.883](../eval/s31/results.json) | — | — |
| V1 k10: reading 1 shows the 10 nearest examples (frozen 5 + next 5) | [0.720 [0.674, 0.762]](../eval/s31/results.json) | [+0.0125 [−0.0050, +0.0300]](../eval/s31/results.json) | [0.745 [0.721, 0.768]](../eval/s31/results.json) | [0.890](../eval/s31/results.json) | [+0.0073 [−0.0030, +0.0170]](../eval/s31/results.json) | no |
| V2 subn: reading 1's five examples also name the editors' main subtopic | [0.700 [0.653, 0.743]](../eval/s31/results.json) | [−0.0075 [−0.0176, +0.0025]](../eval/s31/results.json) | — | — | — | not taken to stage 2 |
| V3 ex2: reading 2 (S1 code order) also shows the five examples | [0.720 [0.674, 0.762]](../eval/s31/results.json) | [+0.0125 [−0.0100, +0.0375]](../eval/s31/results.json) | [0.749 [0.725, 0.772]](../eval/s31/results.json) | [0.873](../eval/s31/results.json) | [+0.0117 [−0.0008, +0.0244]](../eval/s31/results.json) | no |
| V4 third: when readings 1 and 2 disagree, a third reading (five examples, a third code order) | [0.717 [0.671, 0.760]](../eval/s31/results.json) | [+0.0100 [0.0000, +0.0225]](../eval/s31/results.json) | — | — | — | not taken to stage 2 |
| V5 ex2+third: V3, plus V4's third reading when V3's two readings disagree (fixed after V1–V4 were seen on the 400) | [0.717 [0.671, 0.760]](../eval/s31/results.json) | [+0.0100 [−0.0100, +0.0325]](../eval/s31/results.json) | — | — | — | not taken to stage 2 |

Outcome: no variant cleared the gate. The closest, V3 (the five examples in both code orders), is [+0.0117 [−0.0008, +0.0244]](../eval/s31/results.json) on all 1,357 items; on the [957](../eval/s31/results.json) items stage 1 did not see, V1 [+0.0052 [−0.0074, +0.0178]](../eval/s31/results.json) and V3 [+0.0114 [−0.0032, +0.0262]](../eval/s31/results.json), both smaller than in stage 1. V3 also lowers top-3. So no test was run and D4 stays; the 927 S25 held-out affairs (§1b) were not used by any S31 call and stay unspent for one later pre-registered look at a single winner. Under the common rule D4 scores [0.737 [0.713, 0.761]](../eval/s31/results.json); §1 reports [0.740 [0.716, 0.764]](../eval/s16/results.json) with the S16 rule, which has no «no policy topic» check ([4](../eval/s31/results.json) items differ). Fresh items for a new test: a Wayback listing of APS process pages from 11 Oct 2026 on found [0](../eval/s31/results.json) new pages; of the [61](../eval/s31/results.json) unjoined S25 numbers, [4](../eval/s31/results.json) match a newer OPD snapshot and [0](../eval/s31/results.json) of those has a production input ([`eval/s31/cdx_check/`](../eval/s31/cdx_check/)). Calls: [4,272](../eval/s31/results.json) on the locked build, USD [0.6822](../eval/s31/results.json) at list price.

### 2 · APS subtopic vs APS editors, end to end (S9)

| n | top-1 | top-3 | gold chapter in the shortlist | baseline: D0 chapter → best subtopic |
|---|---|---|---|---|
| 1,221 | [0.520 [0.492, 0.549]](../eval/spikes/s9-aps/results.json) | [0.677 [0.650, 0.703]](../eval/spikes/s9-aps/results.json) | [0.830 [0.809, 0.850]](../eval/spikes/s9-aps/results.json) | [0.469 [0.441, 0.498]](../eval/spikes/s9-aps/results.json) |

Subtopics ship as ranked suggestions, not as a lane.

**Hierarchical metrics of the shipped design D4** — computed after S16 from its rows (not pre-registered; no new calls) by [`eval/s16/hierarchical.py`](../eval/s16/hierarchical.py). Same 1,221 items as above (chapter + subtopic gold); hierarchical precision / recall / F1 after Kiritchenko et al. (predicted and gold sets augmented with their ancestors, levels chapter and subtopic, micro-averaged); per-chapter F1 is the chapter top-1, one vs rest, macro over the [22](../eval/s16/hierarchical.json) chapters present, on all 1,357 items. Intervals: Wilson for the subtopic rates, percentile bootstrap 2,000 for hP/hR/hF and macro-F1 (stratified by gold chapter), bounds rounded outward.

| Design | subtopic top-1 | subtopic top-3 | subtopic top-1 when the chapter is right | hP | hR | hF | per-chapter macro-F1 |
|---|---|---|---|---|---|---|---|
| **D4 shipped** | **[0.538 [0.510, 0.567]](../eval/s16/hierarchical.json)** | [0.699 [0.673, 0.725]](../eval/s16/hierarchical.json) | [0.727 [0.697, 0.756]](../eval/s16/hierarchical.json) (n 905) | [0.640 [0.616, 0.663]](../eval/s16/hierarchical.json) | [0.640 [0.616, 0.663]](../eval/s16/hierarchical.json) | **[0.640 [0.616, 0.663]](../eval/s16/hierarchical.json)** | [0.705 [0.680, 0.729]](../eval/s16/hierarchical.json) |
| D1 read-back, no examples | [0.520 [0.492, 0.549]](../eval/s16/hierarchical.json) | [0.677 [0.650, 0.703]](../eval/s16/hierarchical.json) | [0.740 [0.710, 0.769]](../eval/s16/hierarchical.json) (n 859) | [0.612 [0.586, 0.637]](../eval/s16/hierarchical.json) | [0.612 [0.586, 0.637]](../eval/s16/hierarchical.json) | [0.612 [0.586, 0.637]](../eval/s16/hierarchical.json) | [0.676 [0.651, 0.701]](../eval/s16/hierarchical.json) |
| D0 list prompting → best subtopic in its chapter | [0.464 [0.436, 0.493]](../eval/s16/hierarchical.json) | [0.596 [0.568, 0.624]](../eval/s16/hierarchical.json) | [0.710 [0.678, 0.741]](../eval/s16/hierarchical.json) (n 798) | [0.564 [0.539, 0.591]](../eval/s16/hierarchical.json) | [0.558 [0.533, 0.585]](../eval/s16/hierarchical.json) | [0.561 [0.535, 0.588]](../eval/s16/hierarchical.json) | [0.625 [0.598, 0.652]](../eval/s16/hierarchical.json) |
| keyword (chapter only) | — | — | — | [0.203 [0.181, 0.227]](../eval/s16/hierarchical.json) | [0.101 [0.090, 0.114]](../eval/s16/hierarchical.json) | [0.135 [0.121, 0.151]](../eval/s16/hierarchical.json) | [0.165 [0.145, 0.185]](../eval/s16/hierarchical.json) |

D4 and D1 always name one chapter and one subtopic, so hP = hR = hF for them (the mean of chapter and subtopic top-1); D0 predicts the chapter only when its chapter is not in the subtopic shortlist, the keyword baseline always. The conditional rate is over each design's own correct-chapter items, so it is not a paired comparison. On all 1,357 items (gold depth 1 where the main subtopic is not among the 190): D4 hF [0.628 [0.605, 0.653]](../eval/s16/hierarchical.json).

For reference, the same metrics of the shipped design on the held-out S25 affairs (§1b; other items, computed after the S25 result, not pre-registered):

| Design | subtopic top-1 | subtopic top-3 | subtopic top-1 when the chapter is right | hP | hR | hF | per-chapter macro-F1 |
|---|---|---|---|---|---|---|---|
| shipped, held out (S25, n 891; not pre-registered) | [0.497 [0.464, 0.530]](../eval/s25/hierarchical.json) | [0.650 [0.619, 0.682]](../eval/s25/hierarchical.json) | [0.708 [0.671, 0.744]](../eval/s25/hierarchical.json) (n 625) | [0.609 [0.580, 0.638]](../eval/s25/hierarchical.json) | [0.599 [0.570, 0.628]](../eval/s25/hierarchical.json) | [0.604 [0.575, 0.633]](../eval/s25/hierarchical.json) | [0.647 [0.611, 0.681]](../eval/s25/hierarchical.json) |

### 3 · “Digitalisierung”: the 30 affairs DVS curates by hand (recall)

| | all 30 | begun in 2026 |
|---|---|---|
| Querschnitt (yes/no, p ≥ 0.5) | [27/30](../eval/spikes/s8-dvs/results.md#L212) [0.743, 0.966] | [23/24](../eval/spikes/s8-dvs/results.md#L214) [0.797, 0.993] |
| keyword list (29 stems, de/fr/it) | [21/30](../eval/spikes/s8-dvs/results.md#L212) [0.521, 0.834] | [16/24](../eval/spikes/s8-dvs/results.md#L214) [0.467, 0.821] |
| the AI judge, for reference (S15) | [27/30](../eval/spikes/s15-judgecheck/results.json) [0.743, 0.966] | — |

Split: pre-registered re-run (P8.2); the yes/no prompt and the 0.5 cut-off were set on these 30 items in S3 E6.

### 4 · Federal Sachbereiche vs Parliament's own Curia tags (all tags per affair)

| n = 200, submitted after the BFH model | micro-F1 | macro-F1 | top-1 is a gold tag |
|---|---|---|---|
| Apertus: 5 retrieved tagged examples + yes/no check of the top 6 | [0.654 [0.623, 0.686]](../eval/spikes/s5-aps/results.md#L84) | [0.570 [0.520, 0.622]](../eval/spikes/s5-aps/results.md#L84) | [0.865 [0.810, 0.906]](../eval/spikes/s3-accuracy/results.md#L27) (no examples) |
| BFH model, trained on [15,007](../eval/research/R1-parts/prior-art.md#L10) tagged affairs | [0.687 [0.652, 0.722]](../eval/spikes/s3-accuracy/results.md#L35) | [0.577 [0.525, 0.642]](../eval/spikes/s3-accuracy/results.md#L35) | [0.855 [0.799, 0.898]](../eval/spikes/s3-accuracy/results.md#L35) |

Paired micro-F1 difference Apertus − BFH: [−0.079 to +0.010](../eval/spikes/s5-aps/results.md#L89). Split: test n = 200; rules, τ and λ tuned on 100 dev items (tuning split). Example pool: 52,408 affairs tagged before 6 Nov 2024.

### 5 · Bern: lead directorate (8 directorates, scheme swap) vs the Grand Council's own field, titles only

Production run, every affair begun 2025–26 with a lead directorate (S18, [pre-registered](../eval/PREREG-BUILD.md#L28); nothing tuned), and the earlier random sample of affairs since 2015 (S6, one run).

| | n | German title | French title | German − French, paired | keyword stems DE / FR | majority |
|---|---|---|---|---|---|---|
| **S18, 2025–26, production run** | 531 | **[0.651 [0.610, 0.691]](../eval/s18/results.json)** | [0.650 [0.608, 0.690]](../eval/s18/results.json) (n 529) | [+0.001 [−0.031, +0.034]](../eval/s18/results.json) (n 529) | [0.525 [0.482, 0.568]](../eval/s18/results.json) / [0.512](../eval/s18/results.json) | [0.214](../eval/s18/results.json) (SID) |
| S6, since 2015, random 200 | 200 | [0.615 [0.545, 0.680]](../eval/spikes/s6-cantonal/results.md#L63) | [0.645 [0.576, 0.709]](../eval/spikes/s6-cantonal/results.md#L64) | [−0.030 [−0.085, +0.025]](../eval/spikes/s6-cantonal/results.md#L69) | [0.520 [0.451, 0.589]](../eval/spikes/s6-cantonal/results.md#L66) / [0.495 [0.426, 0.564]](../eval/spikes/s6-cantonal/results.md#L66) | [0.175 [0.128, 0.234]](../eval/spikes/s6-cantonal/results.md#L67) (BVD) |

S6, German and French averaged: [0.645 [0.576, 0.709]](../eval/spikes/s6-cantonal/results.md#L65). Directorate descriptions in the scheme file were written by the agent; keyword stems were frozen before any result.

### 6 · Basel-Stadt: the canton's own 46 themes vs its hand-assigned «Thema 1», all 2,437 Grand Council affairs 2019–24 (S20, S21)

Gold: the themes the canton's Kantons- und Stadtentwicklung assigned by hand (OGD dataset 100086), joined to OpenParlData by number. S20 hands over the 46 theme names as a scheme file, verbatim, no descriptions, nothing tuned ([pre-registered](../eval/PREREG-BUILD.md#L48)). S21 adds five of Basel's own labelled affairs as examples, always from the other half of the data, no training ([pre-registered](../eval/PREREG-BUILD.md#L59), paired against S20 on the same items).

| Design | top-1 = Thema 1 | Thema 1 or 2 | top-3 | readings agree: share, precision | readings disagree: precision |
|---|---|---|---|---|---|
| S20 theme names only | [0.498 [0.478, 0.518]](../eval/s20/results.json) | [0.605 [0.586, 0.625]](../eval/s20/results.json) | [0.665 [0.646, 0.685]](../eval/s20/results.json) | [71.9%](../eval/s20/results.json), [0.565 [0.542, 0.589]](../eval/s20/results.json) | [0.325 [0.290, 0.362]](../eval/s20/results.json) |
| S21 + five Basel examples (two readings, D4 shape) | **[0.526 [0.506, 0.547]](../eval/s21/results.json)** | [0.631](../eval/s21/results.json) | [0.711](../eval/s21/results.json) | [54.9%](../eval/s21/results.json), [0.651 [0.625, 0.677]](../eval/s21/results.json) | [0.373 [0.345, 0.403]](../eval/s21/results.json) |
| keyword stems (frozen) | [0.181 [0.166, 0.198]](../eval/s20/results.json) | — | — | — | — |
| majority theme (Verwaltung) | [0.053](../eval/s20/results.json) | — | — | — | — |

S21 − S20, paired: [+0.028 [+0.014, +0.043]](../eval/s21/results.json). S20 − keyword, paired: [+0.316 [+0.293, +0.340]](../eval/s20/results.json).

S20 by affair type: Interpellation [0.501 [0.467, 0.536], n 822](../eval/s20/results.json) · Schriftliche Anfrage [0.465 [0.430, 0.501], n 789](../eval/s20/results.json) · Anzug [0.546 [0.504, 0.588], n 549](../eval/s20/results.json) · Motion [0.517 [0.435, 0.599], n 141](../eval/s20/results.json) · Petition [0.419 [0.318, 0.529], n 81](../eval/s20/results.json) · Budgetpostulat [0.400 [0.218, 0.614], n 20](../eval/s20/results.json) (types with n < 20 not shown).

### 6b · Ticino: the lead department vs the canton's own assignment, Gran Consiglio 2023–26, in Italian (S29, pre-registered)

The first human-labelled test on an Italian-speaking parliament's own scheme. Gold: the lead department OPD carries for every Gran Consiglio affair (contributors, role `leading_department`, position 1), assigned by the cantonal administration; affairs begun 1 Jan 2023–11 Oct 2026, 2,274 in all ([`eval/s29/SOURCES.md`](../eval/s29/SOURCES.md), [`eval/s29/items.py`](../eval/s29/items.py)). Scheme file [`ti-dipartimenti.yaml`](../src/querschnitt/schemes/ti-dipartimenti.yaml): the six unit names verbatim in Italian (five Dipartimenti and the Cancelleria dello Stato) plus «Nessuno di questi» for the Consiglio di Stato as a whole or the Gran Consiglio itself; no descriptions, nothing tuned. The prompt frame is Italian; the three fixed block labels in code («Geschäft:», «Titel:», «Text (Auszug):») stay German as shipped. Production input, second code order when p < 0.9 ([`eval/s29/analyze.py`](../eval/s29/analyze.py) → [`eval/s29/results.json`](../eval/s29/results.json); [pre-registered](../eval/PREREG-BUILD.md#L186)).

**Why the primary population excludes [589](../eval/s29/SOURCES.md#L45) items.** A Messaggio (the government's message to the parliament) prints the competent department in its header («competenza»), so on those inputs the answer is in the text. [589](../eval/s29/SOURCES.md#L45) of the 2,274 inputs name one of the six units ([487 of 512 Messaggi](../eval/s29/SOURCES.md#L45)); this was measured on the inputs before any call, and the primary result is on the 1,685 that name none.

| Population | n | top-1 = lead department | top-2 | top-3 | keyword stems (frozen, title only) | majority | Apertus − keyword, paired |
|---|---|---|---|---|---|---|---|
| **primary: input names no unit** | 1,685 | **[0.647 [0.624, 0.670]](../eval/s29/results.json)** | [0.807 [0.788, 0.826]](../eval/s29/results.json) | [0.878 [0.861, 0.894]](../eval/s29/results.json) | [0.219 [0.200, 0.240]](../eval/s29/results.json) | [0.194 [0.176, 0.215]](../eval/s29/results.json) | [+0.427 [+0.400, +0.454]](../eval/s29/results.json) |
| secondary: all inputs as fed | 2,274 | [0.722 [0.704, 0.741]](../eval/s29/results.json) | [0.848 [0.833, 0.863]](../eval/s29/results.json) | [0.905 [0.892, 0.917]](../eval/s29/results.json) | [0.232 [0.215, 0.251]](../eval/s29/results.json) | [0.188 [0.173, 0.206]](../eval/s29/results.json) | [+0.490 [+0.466, +0.514]](../eval/s29/results.json) |
| secondary: gold one of the 5 Dipartimenti (all inputs) | 1,359 | [0.743 [0.720, 0.767]](../eval/s29/results.json) | [0.875 [0.857, 0.893]](../eval/s29/results.json) | [0.912 [0.896, 0.927]](../eval/s29/results.json) | [0.248 [0.226, 0.273]](../eval/s29/results.json) | [0.241 [0.219, 0.265]](../eval/s29/results.json) | [+0.495 [+0.465, +0.526]](../eval/s29/results.json) |

Majority = Dipartimento della sanità e della socialità (primary). Lanes (primary): the two code orders agree on [83.3%](../eval/s29/results.json) of affairs ([1,405](../eval/s29/results.json)), precision [0.698 [0.673, 0.722]](../eval/s29/results.json); they disagree on [280](../eval/s29/results.json), precision [0.392 [0.337, 0.452]](../eval/s29/results.json) (`please check`).

Per lead department (primary; share of its affairs that Apertus assigns to it): health and social affairs (DSS) [0.896 [0.858, 0.925], n 328](../eval/s29/results.json) · finance and economy (DFE) [0.590 [0.533, 0.647], n 286](../eval/s29/results.json) · territory (DT) [0.793 [0.740, 0.839], n 262](../eval/s29/results.json) · institutions (DI) [0.624 [0.563, 0.681], n 258](../eval/s29/results.json) · none of these (Consiglio di Stato as a whole or the Gran Consiglio) [0.266 [0.214, 0.327], n 236](../eval/s29/results.json) · education, culture and sport (DECS) [0.795 [0.738, 0.844], n 225](../eval/s29/results.json) · State Chancellery [0.188 [0.121, 0.282], n 90](../eval/s29/results.json).
The weak spots are the two non-department classes: of the 236 «none of these» affairs, [75](../eval/s29/results.json) go to the Dipartimento delle istituzioni; of the 90 State Chancellery affairs, [39](../eval/s29/results.json) go there too.
By affair type (primary): Interrogazione [0.699 [0.665, 0.731], n 761](../eval/s29/results.json) · Interpellanza [0.630 [0.574, 0.684], n 295](../eval/s29/results.json) · Mozione [0.660 [0.600, 0.716], n 256](../eval/s29/results.json) · Iniziativa parlamentare elaborata [0.633 [0.559, 0.703], n 172](../eval/s29/results.json) · Rapporti vari [0.521 [0.405, 0.636], n 69](../eval/s29/results.json) · Iniziativa parlamentare generica [0.593 [0.471, 0.706], n 64](../eval/s29/results.json) · Iniziativa cantonale [0.296 [0.158, 0.485], n 27](../eval/s29/results.json) · Messaggio [0.200 [0.088, 0.392], n 25](../eval/s29/results.json) (types with n < 20 not shown).

Bern (§5, S18) and Basel-Stadt (§6, S20) are reported beside this result, not compared with it: the schemes differ, and so do the chance rates (majority and keyword rows above).

### 7 · The AI judge itself against human labels

| Test | n | AI judge (Claude, blind) | Apertus, same items |
|---|---|---|---|
| APS chapter = APS editors' chapter (S11) | 200 | [0.790 [0.728, 0.841]](../eval/spikes/s11-anchor/anchor.json); second code included [0.900 [0.850, 0.935]](../eval/spikes/s11-anchor/anchor.json); run A = run B [0.990 [0.964, 0.998]](../eval/spikes/s11-anchor/anchor.json) | D1 [0.695 [0.628, 0.755]](../eval/spikes/s11-anchor/anchor.json) · D3 [0.720 [0.654, 0.778]](../eval/spikes/s11-anchor/anchor.json) |
| says yes to the 30 DVS items (S15) | 30 | [27/30](../eval/spikes/s15-judgecheck/results.json) [0.743, 0.966] both runs (run B [28 of 30](../eval/spikes/s15-judgecheck/results.json)) | [27/30](../eval/spikes/s8-dvs/results.md#L212) |

The judge's precision on human negatives is not measured (no human negatives exist).

### 8 · Neutrality on human labels (S9, no new calls; S22 Italian)

Language, same 1,357 affairs scored from the German vs the French text (paired): German − French [+0.016 [−0.003, +0.037]](../eval/spikes/s14-neutrality/results.json), McNemar p 0.1133.

**Italian vs German (S22, [pre-registered](../eval/PREREG-BUILD.md#L69)).** The S9 affairs whose Italian title differs from the French one (1,350 of 1,357), gold the APS editors' chapter; Italian title + long title + the Italian submitted text where it differs from the French, D1 in the Italian frame (chapter names Italian, subtopic names German as published), both code orders; paired against the S9 German D1 on the same affairs.

| n = 1,350 | Italian | German (S9 D1) | German − Italian, paired |
|---|---|---|---|
| chapter top-1 | **[0.702 [0.678, 0.727]](../eval/s22/results.json)** | [0.703 [0.678, 0.728]](../eval/s22/results.json) | [+0.0007 [−0.020, +0.021]](../eval/s22/results.json) |
| chapter top-3 | [0.843](../eval/s22/results.json) | [0.842](../eval/s22/results.json) | |
| with Italian submitted text (n 1,074) | [0.697](../eval/s22/results.json) | [0.683](../eval/s22/results.json) | |
| title only (n 276) | [0.724](../eval/s22/results.json) | [0.782](../eval/s22/results.json) | |

Shares are k / n recovered from the stored 4-decimal values and truncated; the difference is a paired bootstrap (2,000), shown at 4 decimals because it is near zero, bounds rounded outward.

| S9 by party | D1 top-1 | keyword top-1 |
|---|---|---|
| SVP | [0.664 [0.581, 0.738], n 137](../eval/spikes/s14-neutrality/results.json) | [0.248 [0.183, 0.327], n 137](../eval/spikes/s14-neutrality/results.json) |
| SP | [0.701 [0.629, 0.765], n 174](../eval/spikes/s14-neutrality/results.json) | [0.172 [0.123, 0.236], n 174](../eval/spikes/s14-neutrality/results.json) |
| FDP | [0.671 [0.591, 0.743], n 146](../eval/spikes/s14-neutrality/results.json) | [0.178 [0.124, 0.249], n 146](../eval/spikes/s14-neutrality/results.json) |
| Mitte | [0.632 [0.544, 0.712], n 125](../eval/spikes/s14-neutrality/results.json) | [0.144 [0.093, 0.217], n 125](../eval/spikes/s14-neutrality/results.json) |
| Grüne | [0.578 [0.478, 0.674], n 95](../eval/spikes/s14-neutrality/results.json) | [0.200 [0.131, 0.292], n 95](../eval/spikes/s14-neutrality/results.json) |
| GLP | [0.644 [0.498, 0.768], n 45](../eval/spikes/s14-neutrality/results.json) | [0.088 [0.035, 0.208], n 45](../eval/spikes/s14-neutrality/results.json) |
| other party | [0.687 [0.514, 0.821], n 32](../eval/spikes/s14-neutrality/results.json) | [0.093 [0.032, 0.243], n 32](../eval/spikes/s14-neutrality/results.json) |
| committee | [0.743 [0.681, 0.797], n 222](../eval/spikes/s14-neutrality/results.json) | [0.175 [0.131, 0.232], n 222](../eval/spikes/s14-neutrality/results.json) |
| government | [0.792 [0.740, 0.836], n 274](../eval/spikes/s14-neutrality/results.json) | [0.237 [0.190, 0.292], n 274](../eval/spikes/s14-neutrality/results.json) |
| canton | [0.729 [0.619, 0.818], n 74](../eval/spikes/s14-neutrality/results.json) | [0.202 [0.126, 0.308], n 74](../eval/spikes/s14-neutrality/results.json) |
| unknown | [0.697 [0.526, 0.827], n 33](../eval/spikes/s14-neutrality/results.json) | [0.212 [0.106, 0.378], n 33](../eval/spikes/s14-neutrality/results.json) |
| *test (cells n ≥ 20)* | [p 0.4655; gap SP − Grüne +0.122 [−0.007, +0.242]](../eval/spikes/s14-neutrality/results.json) | [p 0.1458; gap SVP − GLP +0.159 [+0.041, +0.263]](../eval/spikes/s14-neutrality/results.json) |

| S9 by instrument | D1 top-1 | keyword top-1 |
|---|---|---|
| Motion | [0.653 [0.608, 0.696], n 459](../eval/spikes/s14-neutrality/results.json) | [0.180 [0.148, 0.219], n 459](../eval/spikes/s14-neutrality/results.json) |
| Postulat | [0.658 [0.603, 0.711], n 296](../eval/spikes/s14-neutrality/results.json) | [0.141 [0.106, 0.187], n 296](../eval/spikes/s14-neutrality/results.json) |
| Regierungsgeschäft | [0.792 [0.740, 0.836], n 274](../eval/spikes/s14-neutrality/results.json) | [0.237 [0.190, 0.292], n 274](../eval/spikes/s14-neutrality/results.json) |
| Parlamentarische Initiative | [0.758 [0.700, 0.808], n 244](../eval/spikes/s14-neutrality/results.json) | [0.217 [0.170, 0.274], n 244](../eval/spikes/s14-neutrality/results.json) |
| Standesinitiative | [0.729 [0.619, 0.818], n 74](../eval/spikes/s14-neutrality/results.json) | [0.202 [0.126, 0.308], n 74](../eval/spikes/s14-neutrality/results.json) |
| other type | [0.400 [0.168, 0.688], n 10](../eval/spikes/s14-neutrality/results.json) (small) | [0.200 [0.056, 0.510], n 10](../eval/spikes/s14-neutrality/results.json) (small) |
| *test (cells n ≥ 20)* | [p 0.0002; gap Regierungsgeschäft − Motion +0.138 [+0.068, +0.201]](../eval/spikes/s14-neutrality/results.json) | [p 0.0796; gap Regierungsgeschäft − Postulat +0.095 [+0.029, +0.160]](../eval/spikes/s14-neutrality/results.json) |

Reading: top-1 differs too little to measure with these sample sizes by language and among the six main parties (this is not evidence of no difference; the party gaps' intervals are wide). Government business scores higher than members' motions, and the keyword baseline shows the same order (easier texts, not a political tilt). Quality is reported per submitter type.

### 9 · Free naming without a list (rule check)

Asked to name a topic freely, Apertus answered outside both the Curia 28 and the APS label sets in [36/40](../eval/spikes/s3-accuracy/results.md#L116) (0.900 [0.769, 0.961]) and never answered “no topic” ([0/40](../eval/spikes/s3-accuracy/results.md#L116)); with the list shown, [0/40](../eval/spikes/s3-accuracy/results.md#L117) were off-list. Every shipped decision is a choice among listed codes.

## AI-judge rows

Gold where no official labels exist: a blind AI judge (two runs of a Claude model + a tie-break run, cross-checked by the open-weights Qwen-SEA-LION). Its agreement with human labels is in §7 above. Every figure below is agreement with that judge.

### 10 · “Digitalisierung” in Swiss parliaments, 2026: full census (S8 design, pre-registered)

Population: all [14,512](../eval/s8full/results.json) Swiss affairs begun 1 Jan–6 Oct 2026 with a title. Every one of the [14,789](../eval/s8full/results.json) affairs in the window (Liechtenstein included) is decided ([9,519](../eval/s8full/results.json) from the S8 rows, [5,270](../eval/s8full/results.json) from the production run with the same prompt and build, [0](../eval/s8full/results.json) missing), so flags are counted, not estimated. Precision and recall use the same 453 checked Swiss affairs and the same judge as S8, weights post-stratified to the census strata; flag at p ≥ 0.5, fixed before the run ([PREREG.md § S8](../eval/spikes/PREREG.md#L10)). Recomputed by [`eval/s8full/analyze.py`](../eval/s8full/analyze.py), no model calls.

| full census, 95% interval | Querschnitt | keyword list (29 stems) | difference, bootstrap |
|---|---|---|---|
| precision vs the judge | **[0.905 [0.865, 0.945]](../eval/s8full/results.json)** | [0.756 [0.717, 0.793]](../eval/s8full/results.json) | [+0.149 [+0.106, +0.192]](../eval/s8full/results.json) |
| recall vs the judge | [0.659 [0.491, 0.900]](../eval/s8full/results.json) | [0.584 [0.435, 0.795]](../eval/s8full/results.json) | [+0.075 [+0.041, +0.123]](../eval/s8full/results.json) |
| affairs flagged (counted) | [651](../eval/s8full/results.json) in [57](../eval/s8full/results.json) parliaments ([41](../eval/s8full/results.json) in `please check`) | [690](../eval/s8full/results.json); both [470](../eval/s8full/results.json) | |
| gold = majority of Claude A, B and Qwen: precision / recall | [0.890 [0.845, 0.933] / 0.656 [0.486, 0.904]](../eval/s8full/results.json) | [0.736 [0.696, 0.776] / 0.582 [0.428, 0.800]](../eval/s8full/results.json) | |

Estimated digitalisation affairs (judge positives): [893 [656, 1,191]](../eval/s8full/results.json). Including Liechtenstein: [670](../eval/s8full/results.json) flagged by Querschnitt, [708](../eval/s8full/results.json) by keywords, of [14,789](../eval/s8full/results.json). The differences are bootstrap intervals; their point is the difference of the two stored points. Judge: run A = run B [0.976](../eval/spikes/s8-dvs/score.json) (κ [0.951](../eval/spikes/s8-dvs/score.json)); Qwen vs the runs κ [0.812](../eval/spikes/s8-dvs/score.json) / [0.824](../eval/spikes/s8-dvs/score.json).

**History: the S8 snapshot** (14,513 Swiss affairs in the 6 Oct window, of which the census run had scored 8,139 when it was paused; flags estimated from the last week in full and 5,338 of 14,212 earlier affairs at random). Superseded above for counts and judge precision/recall; kept for the record: precision [0.914 [0.876, 0.952]](../eval/spikes/s8-dvs/score_ch.json), recall [0.654 [0.486, 0.894]](../eval/spikes/s8-dvs/score_ch.json), estimated flags [653 [629, 676]](../eval/spikes/s8-dvs/score_ch.json) (keywords [734 [711, 757]](../eval/spikes/s8-dvs/score_ch.json)), estimated positives [913 [668, 1,218]](../eval/spikes/s8-dvs/score_ch.json); keyword precision [0.753 [0.714, 0.790]](../eval/spikes/s8-dvs/score_ch.json), recall [0.605 [0.451, 0.827]](../eval/spikes/s8-dvs/score_ch.json); judge = Qwen alone [0.863 / 0.811](../eval/spikes/s8-dvs/score_ch.json) (keywords [0.691 / 0.729](../eval/spikes/s8-dvs/score_ch.json)). The breakdowns below are still on the snapshot's weights.

Judge-confirmed Swiss positives in the checked sample: [190](../eval/spikes/s8-dvs/score_ch.json) from [45](../eval/spikes/s8-dvs/score_ch.json) parliaments — [cantonal 87, federal 62, communal 41; German 141, French 35, Italian 14](../eval/spikes/s8-dvs/score_ch.json).

Per language and level (all 464 checked items incl. Liechtenstein, snapshot weights; S14):

| S8 by language | precision | recall |
|---|---|---|
| de | [0.911 [0.866, 0.952], n 137](../eval/spikes/s14-neutrality/results.json) | [0.595 [0.423, 0.880], n 150](../eval/spikes/s14-neutrality/results.json) |
| fr | [0.929 [0.848, 0.992], n 36](../eval/spikes/s14-neutrality/results.json) | [0.574 [0.281, 1.000], n 35](../eval/spikes/s14-neutrality/results.json) |
| it | [0.944 [0.803, 1.000], n 13](../eval/spikes/s14-neutrality/results.json) (small) | [0.894 [0.715, 1.000], n 14](../eval/spikes/s14-neutrality/results.json) (small) |
| *test (cells n ≥ 20)* | [p 0.8566; gap fr − de +0.018 [−0.078, +0.094]](../eval/spikes/s14-neutrality/results.json) | [p 0.8972; gap de − fr +0.021 [−0.501, +0.440]](../eval/spikes/s14-neutrality/results.json) |

| S8 by level | precision | recall |
|---|---|---|
| federal | [0.877 [0.778, 0.961], n 57](../eval/spikes/s14-neutrality/results.json) | [0.443 [0.242, 0.900], n 62](../eval/spikes/s14-neutrality/results.json) |
| cantonal | [0.936 [0.889, 0.978], n 80](../eval/spikes/s14-neutrality/results.json) | [0.724 [0.496, 0.934], n 87](../eval/spikes/s14-neutrality/results.json) |
| communal | [0.907 [0.821, 0.973], n 43](../eval/spikes/s14-neutrality/results.json) | [0.929 [0.851, 0.985], n 41](../eval/spikes/s14-neutrality/results.json) |
| other | [1.000 [1.000, 1.000], n 6](../eval/spikes/s14-neutrality/results.json) (small) | [0.191 [0.038, 1.000], n 9](../eval/spikes/s14-neutrality/results.json) (small) |
| *test (cells n ≥ 20)* | [p 0.4593; gap cantonal − federal +0.059 [−0.038, +0.166]](../eval/spikes/s14-neutrality/results.json) | [p 0.1948; gap communal − federal +0.485 [+0.021, +0.692]](../eval/spikes/s14-neutrality/results.json) |

| S8 by submitter party | Querschnitt precision | keyword precision |
|---|---|---|
| SVP | [0.636 [0.310, 0.929], n 11](../eval/spikes/s14-neutrality/results.json) (small) | [0.417 [0.173, 0.645], n 20](../eval/spikes/s14-neutrality/results.json) |
| SP | [0.943 [0.850, 1.000], n 24](../eval/spikes/s14-neutrality/results.json) | [0.764 [0.637, 0.874], n 38](../eval/spikes/s14-neutrality/results.json) |
| FDP | [0.807 [0.564, 1.000], n 15](../eval/spikes/s14-neutrality/results.json) (small) | [0.689 [0.438, 0.899], n 16](../eval/spikes/s14-neutrality/results.json) (small) |
| Mitte | [0.959 [0.859, 1.000], n 21](../eval/spikes/s14-neutrality/results.json) | [0.845 [0.668, 0.981], n 19](../eval/spikes/s14-neutrality/results.json) (small) |
| Grüne | [1.000 [1.000, 1.000], n 19](../eval/spikes/s14-neutrality/results.json) (small) | [0.652 [0.430, 0.831], n 21](../eval/spikes/s14-neutrality/results.json) |
| GLP | [0.913 [0.750, 1.000], n 15](../eval/spikes/s14-neutrality/results.json) (small) | [0.927 [0.744, 1.000], n 11](../eval/spikes/s14-neutrality/results.json) (small) |
| other party | [1.000 [1.000, 1.000], n 22](../eval/spikes/s14-neutrality/results.json) | [0.859 [0.736, 0.956], n 29](../eval/spikes/s14-neutrality/results.json) |
| party unknown | [0.975 [0.901, 1.000], n 12](../eval/spikes/s14-neutrality/results.json) (small) | [0.865 [0.562, 1.000], n 7](../eval/spikes/s14-neutrality/results.json) (small) |
| government | [0.944 [0.854, 1.000], n 22](../eval/spikes/s14-neutrality/results.json) | [0.871 [0.728, 0.969], n 25](../eval/spikes/s14-neutrality/results.json) |
| committee | [0.863 [0.370, 1.000], n 5](../eval/spikes/s14-neutrality/results.json) (small) | [0.759 [0.306, 1.000], n 6](../eval/spikes/s14-neutrality/results.json) (small) |
| other group | [1.000 [1.000, 1.000], n 1](../eval/spikes/s14-neutrality/results.json) (small) | [1.000 [1.000, 1.000], n 2](../eval/spikes/s14-neutrality/results.json) (small) |
| unknown | [0.835 [0.655, 0.967], n 19](../eval/spikes/s14-neutrality/results.json) (small) | [0.683 [0.493, 0.847], n 24](../eval/spikes/s14-neutrality/results.json) |
| *test (cells n ≥ 20)* | [p 0.018; gap Mitte − SP +0.016 [−0.105, +0.129]](../eval/spikes/s14-neutrality/results.json) | [p 0.0212; gap SP − SVP +0.347 [+0.074, +0.623]](../eval/spikes/s14-neutrality/results.json) |

The party test (p 0.018) comes from the small SVP cell (7 of 11 confirmed); keyword precision dips on the same items (7/20). Among cells with n ≥ 20 the gap is [+0.016 [−0.105, +0.129]](../eval/spikes/s14-neutrality/results.json). Canton cells are below n = 20 except BS and are not read.

Per parliament (snapshot: flag counts in the scored sample, [S8 results](../eval/spikes/s8-dvs/results.md#L75); estimated flags point only, no per-body gold) — the ten largest:

| body | level | affairs in 2026 | scored | flagged | est. flags | keyword hits |
|---|---|---|---|---|---|---|
| CHE | federal | [3,162](../eval/spikes/s8-dvs/results.md#L75) | [1,457](../eval/spikes/s8-dvs/results.md#L75) | [91](../eval/spikes/s8-dvs/results.md#L75) | [177.1](../eval/spikes/s8-dvs/results.md#L75) | [104](../eval/spikes/s8-dvs/results.md#L75) |
| BS | cantonal | [919](../eval/spikes/s8-dvs/results.md#L75) | [349](../eval/spikes/s8-dvs/results.md#L75) | [17](../eval/spikes/s8-dvs/results.md#L75) | [44.8](../eval/spikes/s8-dvs/results.md#L75) | [23](../eval/spikes/s8-dvs/results.md#L75) |
| GE | cantonal | [612](../eval/spikes/s8-dvs/results.md#L75) | [240](../eval/spikes/s8-dvs/results.md#L75) | [9](../eval/spikes/s8-dvs/results.md#L75) | [24.2](../eval/spikes/s8-dvs/results.md#L75) | [10](../eval/spikes/s8-dvs/results.md#L75) |
| 261 | communal | [554](../eval/spikes/s8-dvs/results.md#L75) | [242](../eval/spikes/s8-dvs/results.md#L75) | [12](../eval/spikes/s8-dvs/results.md#L75) | [25.1](../eval/spikes/s8-dvs/results.md#L75) | [19](../eval/spikes/s8-dvs/results.md#L75) |
| VD | cantonal | [549](../eval/spikes/s8-dvs/results.md#L75) | [209](../eval/spikes/s8-dvs/results.md#L75) | [12](../eval/spikes/s8-dvs/results.md#L75) | [31.7](../eval/spikes/s8-dvs/results.md#L75) | [14](../eval/spikes/s8-dvs/results.md#L75) |
| TI | cantonal | [540](../eval/spikes/s8-dvs/results.md#L75) | [230](../eval/spikes/s8-dvs/results.md#L75) | [10](../eval/spikes/s8-dvs/results.md#L75) | [21.9](../eval/spikes/s8-dvs/results.md#L75) | [14](../eval/spikes/s8-dvs/results.md#L75) |
| BE | cantonal | [500](../eval/spikes/s8-dvs/results.md#L75) | [187](../eval/spikes/s8-dvs/results.md#L75) | [16](../eval/spikes/s8-dvs/results.md#L75) | [42.8](../eval/spikes/s8-dvs/results.md#L75) | [12](../eval/spikes/s8-dvs/results.md#L75) |
| BL | cantonal | [460](../eval/spikes/s8-dvs/results.md#L75) | [154](../eval/spikes/s8-dvs/results.md#L75) | [1](../eval/spikes/s8-dvs/results.md#L75) | [3.0](../eval/spikes/s8-dvs/results.md#L75) | [4](../eval/spikes/s8-dvs/results.md#L75) |
| ZH | cantonal | [440](../eval/spikes/s8-dvs/results.md#L75) | [168](../eval/spikes/s8-dvs/results.md#L75) | [5](../eval/spikes/s8-dvs/results.md#L75) | [13.1](../eval/spikes/s8-dvs/results.md#L75) | [7](../eval/spikes/s8-dvs/results.md#L75) |
| VS | cantonal | [393](../eval/spikes/s8-dvs/results.md#L75) | [136](../eval/spikes/s8-dvs/results.md#L75) | [9](../eval/spikes/s8-dvs/results.md#L75) | [26.0](../eval/spikes/s8-dvs/results.md#L75) | [10](../eval/spikes/s8-dvs/results.md#L75) |

All bodies: [`eval/pruefstand.json`](../eval/pruefstand.json) → `dvs_2026.breakdowns.per_body_flags`.

### 11 · APS chapter, communal parliaments 2026: the production run vs the judge (S17, pre-registered)

200 communal affairs begun 1 Jan–11 Oct 2026, drawn at random among those with a shipped chapter (S6 items excluded); the chapter as shipped by the production run (read back from the subtopic, no examples). Judge: two blind Claude runs on the exact production input, tie-break run on the [11](../eval/s17/results.json) disagreements; κ [0.940](../eval/s17/results.json) ([PREREG-BUILD.md § S17](../eval/PREREG-BUILD.md#L17)).

| n = 200 | top-1 | top-3 |
|---|---|---|
| shipped chapter | **[0.640 [0.571, 0.704]](../eval/s17/results.json)** | [0.770 [0.706, 0.823]](../eval/s17/results.json) |
| frozen S9 keyword baseline | [0.150 [0.107, 0.207]](../eval/s17/results.json) | — |
| majority chapter of the sample's gold (computed after) | [0.135](../eval/s17/results.json) | — |

| cell | top-1 | n |
|---|---|---|
| lane: readings agree | [0.677 [0.600, 0.746]](../eval/s17/results.json) | [155](../eval/s17/results.json) |
| lane: please check | [0.511 [0.370, 0.651]](../eval/s17/results.json) | [45](../eval/s17/results.json) |
| German | [0.631 [0.550, 0.707]](../eval/s17/results.json) | [144](../eval/s17/results.json) |
| French | [0.687 [0.514, 0.821]](../eval/s17/results.json) | [32](../eval/s17/results.json) |
| Italian | [0.625 [0.427, 0.789]](../eval/s17/results.json) | [24](../eval/s17/results.json) |
| with text | [0.636 [0.563, 0.704]](../eval/s17/results.json) | [176](../eval/s17/results.json) |
| title only | [0.666 [0.467, 0.821]](../eval/s17/results.json) | [24](../eval/s17/results.json) |

### 12 · Correction loop, text input, evidence

| Test | n | Result | Same items, without |
|---|---|---|---|
| Correction loop (simulated, P8.5): 60 judge labels shown as an editor's first decisions, 4 nearest per affair | 404 | F1 [0.906](../eval/spikes/s8-dvs/loop.json); Δ [+0.040 [+0.007, +0.075]](../eval/spikes/s8-dvs/loop.json) | F1 [0.866](../eval/spikes/s8-dvs/loop.json) |
| Submitted text added to title (S8b, federal) | 120 | precision [1.000 [0.908, 1.000]](../eval/spikes/s13-timing/results.md#L33), recall [0.678 [0.548, 0.786]](../eval/spikes/s13-timing/results.md#L33); Δ recall [−0.089 [−0.170, −0.019]](../eval/spikes/s13-timing/s8b.json) | title only: [0.895 [0.778, 0.955], 0.767 [0.642, 0.860]](../eval/spikes/s13-timing/results.md#L32) |
| Evidence: the quoted sentence supports the chapter (S12) | 120 | [0.850 [0.775, 0.903]](../eval/spikes/s12-evidence/results.json); chapter right [0.902 [0.819, 0.950]](../eval/spikes/s12-evidence/results.json), wrong [0.736 [0.579, 0.851]](../eval/spikes/s12-evidence/results.json) | exact-substring check [120/120](../eval/spikes/s12-evidence/results.json) |
| **Production check:** evidence on 200 stored quotes of the 2026 production run, the quoted sentence supports the topic (S23) | 200 | **[0.815 [0.755, 0.863]](../eval/s23/results.json)**; chapter quotes [0.830 [0.744, 0.892]](../eval/s23/results.json), «Digitalisierung» quotes [0.800 [0.711, 0.867]](../eval/s23/results.json) | exact substring at the stored offsets [198/198](../eval/s23/results.json) (inputs unchanged since the row; [198/200](../eval/s23/results.json) of all rows) |

The loop row is unweighted and on a sample that over-represents flagged affairs; text makes the model stricter, not more complete.

S23 ([PREREG-BUILD.md § S23](../eval/PREREG-BUILD.md#L77)) draws 100 chapter quotes (the shipped APS chapter) and 100 «Digitalisierung» quotes (flagged or please-check rows) at random among 2026 affairs with a stored quote; the packet shows the input as the model saw it. Judge: two blind Claude runs, run A = run B [0.975 [0.942, 0.990]](../eval/s23/results.json), κ [0.92](../eval/s23/results.json); [5](../eval/s23/results.json) disagreements went to a tie-break run. S12 (0.850 on 120 federal affairs) is a descriptive comparison only, not a test. By level: cantonal [0.843 [0.760, 0.902], n 102](../eval/s23/results.json) · communal [0.666 [0.496, 0.803], n 33](../eval/s23/results.json) · federal [0.836 [0.723, 0.909], n 61](../eval/s23/results.json) · other [1.000 [0.510, 1.000], n 4](../eval/s23/results.json) (small).

### 13 · APS chapter, cantonal and communal (S6, cross-checked S7)

| cell | top-1 vs the judge | n |
|---|---|---|
| all | [0.686 [0.608, 0.755]](../eval/spikes/s6-cantonal/score.json) | [153](../eval/spikes/s6-cantonal/score.json) |
| cantonal | [0.726 [0.629, 0.806]](../eval/spikes/s6-cantonal/score.json) | [95](../eval/spikes/s6-cantonal/score.json) |
| communal | [0.621 [0.492, 0.735]](../eval/spikes/s6-cantonal/score.json) | [58](../eval/spikes/s6-cantonal/score.json) |
| German | [0.672 [0.552, 0.773]](../eval/spikes/s6-cantonal/score.json) | [67](../eval/spikes/s6-cantonal/score.json) |
| French | [0.708 [0.568, 0.818]](../eval/spikes/s6-cantonal/score.json) | [48](../eval/spikes/s6-cantonal/score.json) |
| Italian | [0.684 [0.525, 0.810]](../eval/spikes/s6-cantonal/score.json) | [38](../eval/spikes/s6-cantonal/score.json) |
| with text | [0.708 [0.621, 0.783]](../eval/spikes/s6-cantonal/score.json) | [120](../eval/spikes/s6-cantonal/score.json) |
| title only | [0.606 [0.436, 0.754]](../eval/spikes/s6-cantonal/score.json) | [33](../eval/spikes/s6-cantonal/score.json) |
| first reading p ≥ 0.9 | [0.742 [0.641, 0.822]](../eval/spikes/s6-cantonal/score.json) | [89](../eval/spikes/s6-cantonal/score.json) |
| the two readings disagree | [0.543 [0.381, 0.696]](../eval/spikes/s6-cantonal/score.json) | [35](../eval/spikes/s6-cantonal/score.json) |
| gold = majority of Claude ×2 + Qwen | [0.684 [0.607, 0.751]](../eval/spikes/s7-crossfamily/score.json) | [158](../eval/spikes/s7-crossfamily/score.json) |

| S6 by canton | top-1 |
|---|---|
| TI | [0.684 [0.525, 0.810], n 38](../eval/spikes/s14-neutrality/results.json) |
| JU | [0.555 [0.337, 0.755], n 18](../eval/spikes/s14-neutrality/results.json) (small) |
| ZH | [0.714 [0.453, 0.883], n 14](../eval/spikes/s14-neutrality/results.json) (small) |
| AG | [0.400 [0.168, 0.688], n 10](../eval/spikes/s14-neutrality/results.json) (small) |
| VD | [0.700 [0.396, 0.893], n 10](../eval/spikes/s14-neutrality/results.json) (small) |
| SG | [0.777 [0.452, 0.937], n 9](../eval/spikes/s14-neutrality/results.json) (small) |
| VS | [0.888 [0.564, 0.981], n 9](../eval/spikes/s14-neutrality/results.json) (small) |
| GE | [0.666 [0.299, 0.904], n 6](../eval/spikes/s14-neutrality/results.json) (small) |
| TG | [0.500 [0.187, 0.813], n 6](../eval/spikes/s14-neutrality/results.json) (small) |
| BE | [0.800 [0.375, 0.964], n 5](../eval/spikes/s14-neutrality/results.json) (small) |
| BL | [0.600 [0.230, 0.883], n 5](../eval/spikes/s14-neutrality/results.json) (small) |
| LU | [1.000 [0.565, 1.000], n 5](../eval/spikes/s14-neutrality/results.json) (small) |
| SO | [1.000 [0.565, 1.000], n 5](../eval/spikes/s14-neutrality/results.json) (small) |
| FR | [0.750 [0.300, 0.955], n 4](../eval/spikes/s14-neutrality/results.json) (small) |
| NE | [1.000 [0.510, 1.000], n 4](../eval/spikes/s14-neutrality/results.json) (small) |
| BS | [0.500 [0.094, 0.906], n 2](../eval/spikes/s14-neutrality/results.json) (small) |
| GR | [0.000 [0.000, 0.794], n 1](../eval/spikes/s14-neutrality/results.json) (small) |
| SZ | [1.000 [0.206, 1.000], n 1](../eval/spikes/s14-neutrality/results.json) (small) |
| ZG | [0.000 [0.000, 0.794], n 1](../eval/spikes/s14-neutrality/results.json) (small) |
| *test (cells n ≥ 20)* | [p 0.3043; gap LU − AG +0.600 [+0.300, +0.900]](../eval/spikes/s14-neutrality/results.json) |

### 14 · Bilingual cantons BE, FR, VS — German vs French titles (S10, pre-registered)

| n = 210 | German | French | averaged |
|---|---|---|---|
| chapter top-1 | [0.543 [0.475, 0.609]](../eval/spikes/s10-bilingual/score.json) | [0.529 [0.461, 0.595]](../eval/spikes/s10-bilingual/score.json) | [0.552 [0.484, 0.619]](../eval/spikes/s10-bilingual/score.json) |
| gold in top 3 | [0.771](../eval/spikes/s10-bilingual/secondary.txt#L1) | [0.738](../eval/spikes/s10-bilingual/secondary.txt#L1) | [0.810](../eval/spikes/s10-bilingual/secondary.txt#L1) |
| BE | [0.571 [0.454, 0.681]](../eval/spikes/s10-bilingual/score.json) | [0.543 [0.426, 0.655]](../eval/spikes/s10-bilingual/score.json) | [0.529 [0.413, 0.641]](../eval/spikes/s10-bilingual/score.json) |
| FR | [0.529 [0.413, 0.641]](../eval/spikes/s10-bilingual/score.json) | [0.543 [0.426, 0.655]](../eval/spikes/s10-bilingual/score.json) | [0.571 [0.454, 0.681]](../eval/spikes/s10-bilingual/score.json) |
| VS | [0.529 [0.413, 0.641]](../eval/spikes/s10-bilingual/score.json) | [0.500 [0.385, 0.615]](../eval/spikes/s10-bilingual/score.json) | [0.557 [0.440, 0.668]](../eval/spikes/s10-bilingual/score.json) |

German − French [+0.014 [−0.043, +0.076]](../eval/spikes/s10-bilingual/score.json) (paired; no measurable gap at n = 210). The two languages agree on [70.5%](../eval/spikes/s10-bilingual/score.json): chapter right [0.622 [0.541, 0.696]](../eval/spikes/s10-bilingual/score.json); where they disagree, German [0.355 [0.247, 0.480]](../eval/spikes/s10-bilingual/score.json), French [0.306 [0.205, 0.430]](../eval/spikes/s10-bilingual/score.json) — that third goes to a person. Clerk load: [0.2975 × weekly volume (median 10.0, mean 25.5, p90 76.7) = 3.0 / 7.6 / 22.8 a week](../eval/spikes/s10-bilingual/results.md#L79).

### 15 · New topics defined in one sentence: wolf, heat protection, AI in schools; held out: light pollution, drones, pesticides (S19, S26, S27, S30, pre-registered)

The three S13 topics never used in any tuning, each a one-sentence question ([`src/querschnitt/schemes/adhoc/`](../src/querschnitt/schemes/adhoc/)): «Wolf und Grossraubtiere», «Hitzeschutz / Hitzewellen», «Künstliche Intelligenz an Schulen». Population: every affair with a title begun 1 Aug–6 Oct 2026 ([4,305](../eval/s19/results.json)), decided with the shipped yes/no rule (flag at mean p ≥ 0.5). Checked: every affair flagged by Apertus or by the frozen keyword list ([`eval/s19/keywords_frozen.json`](../eval/s19/keywords_frozen.json)), plus [120](../eval/s19/results.json) random affairs flagged by neither, per topic (774 in all). Judge: two blind Claude runs (A shuffled, B reversed; run A = run B [0.963](../eval/s19/results.json)), a tie-break run on the [28](../eval/s19/ann_C.tsv) disagreements. Recall is weighted back to the population (stratified bootstrap 2,000). The Qwen-SEA-LION cross-check named in the pre-registration is not in the S19 results. Every figure in this section is agreement with the AI judge, not with human labels ([PREREG-BUILD.md § S19](../eval/PREREG-BUILD.md#L37), [§ S26](../eval/PREREG-BUILD.md#L96), [§ S27](../eval/PREREG-BUILD.md#L105) and [its amendment](../eval/PREREG-BUILD.md#L115)).

| S19, agreement with the AI judge | flagged (counted) | precision of flags | recall, weighted | keyword list: precision / recall (hits) | relevant affairs, estimated |
|---|---|---|---|---|---|
| wolf and large predators | [40](../eval/s19/results.json) | **[0.225 [0.123, 0.376] (9/40)](../eval/s19/results.json)** | [1.000 [1.000, 1.000]](../eval/s19/results.json) | [0.500 [0.300, 0.600]](../eval/s19/results.json) / [0.555 [0.363, 0.858]](../eval/s19/results.json) ([10](../eval/s19/results.json)) | [9 [5, 13]](../eval/s19/results.json) |
| heat protection / heatwaves | [346](../eval/s19/results.json) | **[0.670 [0.619, 0.718] (232/346)](../eval/s19/results.json)** | [1.000 [1.000, 1.000]](../eval/s19/results.json) | [0.900 [0.858, 0.938]](../eval/s19/results.json) / [0.741 [0.703, 0.781]](../eval/s19/results.json) ([191](../eval/s19/results.json)) | [232 [218, 245]](../eval/s19/results.json) |
| AI in schools | [22](../eval/s19/results.json) | **[0.136 [0.047, 0.334] (3/22)](../eval/s19/results.json)** | [1.000 [1.000, 1.000]](../eval/s19/results.json) | [0.750 [0.250, 1.000]](../eval/s19/results.json) / [1.000 [1.000, 1.000]](../eval/s19/results.json) ([4](../eval/s19/results.json)) | [3 [1, 4]](../eval/s19/results.json) |

Precision of flags: Wilson 95% from k and n; recall and keyword figures: stratified bootstrap. wolf and large predators: judge positives among the random unflagged affairs [0/120](../eval/s19/results.json) · heat protection / heatwaves: judge positives among the random unflagged affairs [0/120](../eval/s19/results.json) · AI in schools: judge positives among the random unflagged affairs [0/120](../eval/s19/results.json). So every affair the judge marks relevant is flagged, and the recall interval is [1.000, 1.000]; that interval does not cover relevant affairs the random sample missed.

**Editor decisions as examples (S26).** Per topic, [30](../eval/s26/results.json) judged affairs drawn at random (`random.Random(26)`) act as an editor's first decisions (their judge label as Y/N); every other checked affair is decided again with the 4 nearest decisions as examples and compared with its S19 flag (paired bootstrap 2,000).

| S26, agreement with the AI judge, same items | items (judge positives) | precision without examples (S19) | precision with 30 editor decisions | Δ precision, paired | recall without / with |
|---|---|---|---|---|---|
| wolf and large predators | [134](../eval/s26/results.json) ([7](../eval/s26/results.json)) | [0.205 [0.103, 0.368] (7/34)](../eval/s26/results.json) | **[0.218 [0.110, 0.388] (7/32)](../eval/s26/results.json)** | [+0.012 [−0.013, +0.047]](../eval/s26/results.json) | [1.000 [0.645, 1.000] (7/7)](../eval/s26/results.json) / [1.000 [0.645, 1.000] (7/7)](../eval/s26/results.json) |
| heat protection / heatwaves | [438](../eval/s26/results.json) ([216](../eval/s26/results.json)) | [0.670 [0.617, 0.720] (216/322)](../eval/s26/results.json) | **[0.709 [0.655, 0.758] (212/299)](../eval/s26/results.json)** | [+0.038 [+0.018, +0.060]](../eval/s26/results.json) | [1.000 [0.982, 1.000] (216/216)](../eval/s26/results.json) / [0.981 [0.953, 0.993] (212/216)](../eval/s26/results.json) |
| AI in schools | [112](../eval/s26/results.json) ([0](../eval/s26/results.json)) | [0.000 [0.000, 0.204] (0/15)](../eval/s26/results.json) | **[0.000 [0.000, 0.176] (0/18)](../eval/s26/results.json)** | not measurable (n 0 judge positives among 112 test items) | not measurable (n 0 judge positives) |

AI in schools: no judge positive among its 112 test items, so precision is 0.000 in both arms and neither the difference nor recall can be measured. The pre-registration names the weighted S19 recall as secondary; [`eval/s26/analyze.py`](../eval/s26/analyze.py) reports recall among the judge's positives in the test items, which equals it here because the random unflagged sample holds no judge positive.

**A second question on the flags (S27).** Every S19 flag gets one more closed question, same input and frame: «Ist «{name}» ein zentrales Thema dieses Geschäfts – nicht nur am Rande erwähnt oder bloss ähnlich?»; the flag stays at mean p ≥ 0.5. One wording, no tuning, applied once to the S19 packets (the dev step was dropped by an amendment before any S27 call). Recall = share of the judge's positives that keep their flag (every positive was flagged in S19).

| S27, agreement with the AI judge | flags | kept | precision without (S19) | precision with the second question | Δ precision, paired | recall with the second question |
|---|---|---|---|---|---|---|
| wolf and large predators | [40](../eval/s27/results.json) | [9](../eval/s27/results.json) | [0.225 [0.123, 0.376] (9/40)](../eval/s27/results.json) | **[0.444 [0.188, 0.734] (4/9)](../eval/s27/results.json)** | [+0.219 [−0.050, +0.550]](../eval/s27/results.json) | [0.444 [0.188, 0.734] (4/9)](../eval/s27/results.json) |
| heat protection / heatwaves | [346](../eval/s27/results.json) | [292](../eval/s27/results.json) | [0.670 [0.619, 0.718] (232/346)](../eval/s27/results.json) | **[0.770 [0.718, 0.816] (225/292)](../eval/s27/results.json)** | [+0.100 [+0.069, +0.132]](../eval/s27/results.json) | [0.969 [0.939, 0.986] (225/232)](../eval/s27/results.json) |
| AI in schools | [22](../eval/s27/results.json) | [12](../eval/s27/results.json) | [0.136 [0.047, 0.334] (3/22)](../eval/s27/results.json) | **[0.250 [0.088, 0.533] (3/12)](../eval/s27/results.json)** | [+0.113 [0.000, +0.273]](../eval/s27/results.json) | [1.000 [0.438, 1.000] (3/3)](../eval/s27/results.json) |

Reading: one sentence casts a wide net on narrow topics: every judge-relevant affair is flagged, and most flags for wolf and AI in schools are not relevant per the judge. Editor examples change precision by little (heat protection [+0.038 [+0.018, +0.060]](../eval/s26/results.json); wolf, interval includes 0). The second question raises precision on heat protection ([+0.100 [+0.069, +0.132]](../eval/s27/results.json)) and keeps [225/232](../eval/s27/results.json) of its judge positives; on wolf it keeps [4/9](../eval/s27/results.json). In the product, flags the second question does not confirm go to `please check`, not away.

**A generated scope as a third question on the flags (S30, held out, pre-registered).** Dev on the S19 packets above (four variants, tuning allowed; not held out) picked the variant: V4, chosen after its dev results were seen, as the pre-registration states ([PREREG-BUILD.md § S30](../eval/PREREG-BUILD.md#L216), [dev choice](../eval/PREREG-BUILD.md#L227)). One more plain generation request per topic writes an include and an exclude list in de/fr/it from the user's sentence, and every confirmed flag is asked «Gehört das folgende parlamentarische Geschäft zum Thema «…»?» with those lists (plus «affairs whose title does not show the topic» as an exclusion); a flag stays confirmed only if the S27 question and this one both say yes. Test: three new one-sentence topics, never used before («Lichtverschmutzung», «Drohnen-Einsatz», «Pestizide & Rückstände» as generated from the sentences in [`eval/s30/sentences.json`](../eval/s30/sentences.json)), every affair with a title begun 16–31 Mar 2026 ([1,316](../eval/s30/results.json)); generated topics and keyword lists frozen before any test call ([`eval/s30/topics.json`](../eval/s30/topics.json), [`eval/s30/keywords_frozen.json`](../eval/s30/keywords_frozen.json)). Checked: every affair any arm or keyword list flagged plus [120](../eval/s30/results.json) random others per topic ([399](../eval/s30/results.json) in all), shown with title, long title and the start of the text. Judge: blind Claude runs A (shuffled) and B (reversed) agree on every item (run A = run B [1.000](../eval/s30/results.json), [0](../eval/s30/results.json) tie-breaks); judge positives among the random others: [0/120](../eval/s30/results.json) (light pollution), [0/120](../eval/s30/results.json) (drones), [0/120](../eval/s30/results.json) (pesticides). Shipped = the product before S30 (yes/no flag kept by the S27 question). Precision of flags: Wilson 95% from k and n, bounds outward; recall weighted to the population and differences paired on the same resamples (stratified bootstrap 2,000) ([`eval/s30/analyze.py`](../eval/s30/analyze.py) → [`eval/s30/results.json`](../eval/s30/results.json)).

| S30, agreement with the AI judge, held out | judge positives (checked) | flags shipped / with scope check | precision shipped | precision with scope check | Δ precision, paired | recall shipped | recall with scope check | Δ recall, paired | keyword list: precision / recall |
|---|---|---|---|---|---|---|---|---|---|
| light pollution | [4](../eval/s30/results.json) ([127](../eval/s30/results.json)) | [3](../eval/s30/results.json) / [3](../eval/s30/results.json) | [0.666 [0.207, 0.939] (2/3)](../eval/s30/results.json) | **[0.666 [0.207, 0.939] (2/3)](../eval/s30/results.json)** | [0.000 [0.000, 0.000]](../eval/s30/results.json) | [0.500 [0.000, 1.000]](../eval/s30/results.json) | [0.500 [0.000, 1.000]](../eval/s30/results.json) | [0.000 [0.000, 0.000]](../eval/s30/results.json) | [1.000 [0.510, 1.000] (4/4)](../eval/s30/results.json) / [1.000 [1.000, 1.000]](../eval/s30/results.json) |
| drones | [2](../eval/s30/results.json) ([128](../eval/s30/results.json)) | [4](../eval/s30/results.json) / [3](../eval/s30/results.json) | [0.500 [0.150, 0.850] (2/4)](../eval/s30/results.json) | **[0.666 [0.207, 0.939] (2/3)](../eval/s30/results.json)** | [+0.166 [0.000, +0.667]](../eval/s30/results.json) | [1.000 [1.000, 1.000]](../eval/s30/results.json) | [1.000 [1.000, 1.000]](../eval/s30/results.json) | [0.000 [0.000, 0.000]](../eval/s30/results.json) | [0.666 [0.207, 0.939] (2/3)](../eval/s30/results.json) / [1.000 [1.000, 1.000]](../eval/s30/results.json) |
| pesticides | [14](../eval/s30/results.json) ([144](../eval/s30/results.json)) | [21](../eval/s30/results.json) / [15](../eval/s30/results.json) | [0.666 [0.453, 0.829] (14/21)](../eval/s30/results.json) | **[0.800 [0.548, 0.930] (12/15)](../eval/s30/results.json)** | [+0.133 [−0.008, +0.301]](../eval/s30/results.json) | [1.000 [1.000, 1.000]](../eval/s30/results.json) | [0.857 [0.666, 1.000]](../eval/s30/results.json) | [−0.142 [−0.334, 0.000]](../eval/s30/results.json) | [1.000 [0.741, 1.000] (11/11)](../eval/s30/results.json) / [0.785 [0.545, 1.000]](../eval/s30/results.json) |
| **all three** | [20](../eval/s30/results.json) ([399](../eval/s30/results.json)) | [28](../eval/s30/results.json) / [21](../eval/s30/results.json) | [0.642 [0.458, 0.793] (18/28)](../eval/s30/results.json) | **[0.761 [0.549, 0.894] (16/21)](../eval/s30/results.json)** | [+0.119 [+0.005, +0.260]](../eval/s30/results.json) | [0.900 [0.772, 1.000]](../eval/s30/results.json) | [0.800 [0.619, 0.953]](../eval/s30/results.json) | [−0.099 [−0.250, 0.000]](../eval/s30/results.json) | [0.944 [0.742, 0.991] (17/18)](../eval/s30/results.json) / [0.850 [0.681, 1.000]](../eval/s30/results.json) |

Secondary arms (pre-registered), pooled: the yes/no step alone [0.512 [0.361, 0.662] (20/39)](../eval/s30/results.json), recall [1.000 [1.000, 1.000]](../eval/s30/results.json); yes/no + scope question without the S27 question [0.642 [0.458, 0.793] (18/28)](../eval/s30/results.json), recall [0.900 [0.750, 1.000]](../eval/s30/results.json).

Reading, all against the AI judge: pooled over the three topics the scope check raises the precision of confirmed flags from [0.642](../eval/s30/results.json) to [0.761](../eval/s30/results.json) ([+0.119 [+0.005, +0.260]](../eval/s30/results.json)) and costs recall ([0.900](../eval/s30/results.json) → [0.800](../eval/s30/results.json), [−0.099 [−0.250, 0.000]](../eval/s30/results.json)): it drops [2](../eval/s30/results.json) judge positives, both pesticides affairs (veterinary insecticides; pests and plant diseases). It asks only on flags the shipped design already confirms, so recall can only fall. [The pre-registered product rule](../eval/PREREG-BUILD.md#L243) (pooled precision interval above 0, no recall interval below 0) is met, narrowly: the precision interval starts at [+0.005](../eval/s30/results.json), and the pooled and pesticides recall intervals end at [0.000](../eval/s30/results.json). So the product asks it for new topics with a scope (`prompts.scope_check_prompt`, `adhoc.SCOPE_PROMPT`); flags it does not confirm go to `please check`, not away; topic files without the lists (Digitalisierung, the S19 topics) are unchanged. The frozen keyword lists beat both arms on precision here: pooled [0.944 [0.742, 0.991] (17/18)](../eval/s30/results.json) against [0.761](../eval/s30/results.json) with the scope check and [0.642](../eval/s30/results.json) without (Wilson intervals overlap; not a paired test), at recall [0.850 [0.681, 1.000]](../eval/s30/results.json). Judge positives per topic are [4](../eval/s30/results.json) / [2](../eval/s30/results.json) / [14](../eval/s30/results.json) (light pollution, drones, pesticides): too few to read any topic on its own; the rule and this reading rest on the pooled figures.

## Limits

- Recall for “Digitalisierung” on titles is [0.659 [0.491, 0.900]](../eval/s8full/results.json) against the judge (full census); most of the interval comes from the few judge positives among checked affairs that neither method flagged (4 among 180 in the S8 packet). The 30 DVS items are the human recall check; the yes/no prompt and the 0.5 cut-off were set on those same items (S3), so a held-out human recall test is the partner's full list (`make eval GOLD=…`).
- APS subtopics reach [0.520 [0.492, 0.549]](../eval/spikes/s9-aps/results.json) top-1 end to end and ship as ranked suggestions.
- Short, title-only cantonal and communal affairs are the hardest input (0.543 / 0.529 on bilingual titles; S6 0.606 title-only vs 0.708 with text). Communal affairs in production: [0.640 [0.571, 0.704]](../eval/s17/results.json) against the judge (S17).
- With only the names of Basel-Stadt's 46 themes, the first theme is matched in [0.498 [0.478, 0.518]](../eval/s20/results.json) of affairs; five of Basel's own labelled affairs as examples add [+0.028 [+0.014, +0.043]](../eval/s21/results.json) (S21), without training.
- On the Federal Parliament's own multi-tag task the trained BFH model is ahead (micro-F1 0.687 vs 0.654, paired −0.079 to +0.010); the Curia design was tuned on 100 dev items.
- Where no official labels exist, the gold is the AI judge. It matches APS editors on [0.790 [0.728, 0.841]](../eval/spikes/s11-anchor/anchor.json) of chapters and says yes to 27/30 DVS items; its two Claude runs are close to one judge (0.99 agreement), and its precision on human negatives is not measured.
- New topics defined in one sentence are measured against the AI judge only. They flag every judge-relevant affair in S19 but over-flag narrow topics: precision of flags [0.225 [0.123, 0.376] (9/40)](../eval/s19/results.json) for wolf, [0.136 [0.047, 0.334] (3/22)](../eval/s19/results.json) for AI in schools (§15). On three further narrow topics held out (S30), the scope check (now asked for new topics with a scope) raises pooled precision from [0.642](../eval/s30/results.json) to [0.761](../eval/s30/results.json) ([+0.119 [+0.005, +0.260]](../eval/s30/results.json)) at a recall cost ([−0.099 [−0.250, 0.000]](../eval/s30/results.json)), on [20](../eval/s30/results.json) judge positives in all; the frozen keyword lists were more precise still ([0.944](../eval/s30/results.json)).
- The federal design was chosen on the design set (§1). A search of five variants there (S31, §1d; dev only, not pre-registered) found none that clears the gate (best [+0.0117 [−0.0008, +0.0244]](../eval/s31/results.json)); the S25 held-out items stay unspent for one pre-registered look at a single winner, and no fresh APS-labelled items were available (§1d).
- The held-out test (S25, §1b) pre-registered the chapter, its lanes and plain list prompting (S25b); its subtopic and hierarchical figures (subtopic top-1 [0.497 [0.464, 0.530]](../eval/s25/hierarchical.json), hF [0.604 [0.575, 0.633]](../eval/s25/hierarchical.json)) were computed after the result and are not pre-registered. Its D1 cell (no APS-labelled example: one-word procedural titles such as «Vereidigung», or a French text) holds 10 affairs, too few to measure D1 held out.
- Without prefill (the endpoint fallback `QS_PREFILL=0`, §1c) the chapter top-1 on the held-out affairs is [0.705 [0.675, 0.734]](../eval/s28/results.json), paired prefill − no prefill [−0.008 [−0.022, +0.004]](../eval/s28/results.json); no calibration map exists for that mode, so its lane is the readings rule, not the recalibrated p. Measured on one build; another endpoint may tokenise the JSON opening differently (the S28 amendment).
- Ticino (§6b, Italian, the canton's own lead department) is measured on the inputs that do not name the unit (1,685 of 2,274). The State Chancellery and «none of these» are weak (0.188 and 0.266); the gold is OPD's lead-department field, and its licence is unconfirmed (SOURCES.md). No French-speaking parliament's own scheme is measured yet (Bern's French titles, §5, are the closest).
- All Apertus rows come from one served build; cut-offs and recalibration are refitted per build. ECE intervals are not computed yet.

## To measure

- FR/IT rows with the headline Curia design + BFH on the same items
- recalibration refit on the build that serves at the event
- ECE intervals (bootstrap)
- judge precision on human negatives
- a French-speaking parliament's own scheme (NE Grand Conseil leading_department; needs a mapping between department periods, eval/s29/SOURCES.md)
- a calibration map for the no-prefill fallback (its lane is the readings rule until then; S28)
- one pre-registered look at the closest S31 candidate (V3, examples in both code orders) on the unspent S25 items (likely inconclusive at n = 927, eval/s31/DEV.md), or fresh APS-labelled items (none new on Wayback, S31)
- human labels for new one-sentence topics (§15, S19–S30, is measured against the AI judge only)
- Romansh
