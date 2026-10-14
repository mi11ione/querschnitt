# Prüfstand

Every measured test behind Querschnitt, as one ruled table each. Human labels first, then the blind AI judge. Model `swiss-ai/apertus-v1.5-8b` on Public AI, build `…dd237840` on every Apertus call. Intervals are 95%: Wilson for proportions, paired bootstrap (2,000) for differences, stratified bootstrap for population estimates. Shown values are truncated, never rounded up. Every Wilson interval is recomputed exactly from k and n with the lower bound floored and the upper bound ceiled at 3 decimals (the result files store them rounded to the nearest 0.001; pruefstand.json keeps that as `ci95_source`); bootstrap percentiles are floored / ceiled as stored. Machine-readable: [`eval/pruefstand.json`](../eval/pruefstand.json) (file and key for every value); claims register: [`eval/claims.tsv`](../eval/claims.tsv); check any text with `python3 -I tools/claims_check.py FILE`. Links point into the evaluation workspace (`bern/ideation*/spikes/`) and into `querschnitt/eval/` for the build-week tests (pre-registered in [`eval/PREREG-BUILD.md`](../eval/PREREG-BUILD.md)).

## Human labels

### 1 · APS chapter vs APS editors — 1,357 held-out federal affairs, pre-registered (S9, S16)

Wayback process pages not used before; German title + submitted text; nothing tuned on these items. Pre-registration: [PREREG.md § S9](../../../bern/ideation2/PREREG.md#L32); the shipped federal design and its decision rule: [PREREG-BUILD.md § S16](../../../bern/querschnitt/eval/PREREG-BUILD.md#L6).

| Design | top-1 | top-3 | Δ top-1, paired | |
|---|---|---|---|---|
| **D4 five APS-labelled examples + chapter read back from the subtopic, both code orders always** | **[0.740 [0.716, 0.764]](../../../bern/querschnitt/eval/s16/results.json)** | [0.883](../../../bern/querschnitt/eval/s16/results.json) | vs D3 [+0.018 [+0.002, +0.034]](../../../bern/querschnitt/eval/s16/results.json) · vs D1 [+0.036 [+0.021, +0.054]](../../../bern/querschnitt/eval/s16/results.json) | **shipped, federal affairs** (S16) |
| D4s as D4, second code order only when p < 0.9 | [0.748 [0.724, 0.772]](../../../bern/querschnitt/eval/s16/results.json) | [0.856](../../../bern/querschnitt/eval/s16/results.json) | vs D3 [+0.026 [+0.011, +0.042]](../../../bern/querschnitt/eval/s16/results.json) · vs D1 [+0.045 [+0.026, +0.063]](../../../bern/querschnitt/eval/s16/results.json) | secondary, reported, not shipped (S16) |
| D3 chapter step with five APS-labelled examples | [0.722 [0.697, 0.746]](../../../bern/ideation2/spikes/s9-aps/results.json) | [0.874 [0.856, 0.892]](../../../bern/ideation2/spikes/s9-aps/results.json) | vs D0 [+0.067 [+0.049, +0.085]](../../../bern/ideation2/spikes/s9-aps/results.json) | building block of D4 (S9) |
| D1 chapter read back from the subtopic, no examples | [0.703 [0.678, 0.728]](../../../bern/ideation2/spikes/s9-aps/results.json) | [0.843 [0.822, 0.862]](../../../bern/ideation2/spikes/s9-aps/results.json) | vs D0 [+0.048 [+0.032, +0.066]](../../../bern/ideation2/spikes/s9-aps/results.json) | shipped where no APS examples exist (S9) |
| D2 German + French averaged | [0.634 [0.608, 0.660]](../../../bern/ideation2/spikes/s9-aps/results.json) | [0.853 [0.833, 0.872]](../../../bern/ideation2/spikes/s9-aps/results.json) | vs D0 [−0.020 [−0.037, −0.004]](../../../bern/ideation2/spikes/s9-aps/results.json) | dropped for the label (S9) |
| D0 plain list prompting (v14) | [0.655 [0.629, 0.680]](../../../bern/ideation2/spikes/s9-aps/results.json) | — | — | baseline |
| keyword (APS subtopic words, frozen) | [0.191 [0.171, 0.214]](../../../bern/ideation2/spikes/s9-aps/results.json) | — | — | baseline |
| majority chapter | [0.079 [0.066, 0.096]](../../../bern/ideation2/spikes/s9-aps/results.json) | — | — | baseline |

Decision ([S16 results](../../../bern/querschnitt/eval/s16/results.json)): D4 shipped for federal affairs (pre-registered rule: D4 if its top-1 ≥ D3's). The corpus run uses D4 as registered: both code orders always, examples on the first. D4s (secondary) is reported, not shipped.

**Lanes of D4** (the reading with examples and the reading without agree / disagree on the chapter): readings agree on [64.1%](../../../bern/querschnitt/eval/s16/results.json) of affairs ([871](../../../bern/querschnitt/eval/s16/results.json)), precision [0.826 [0.800, 0.851]](../../../bern/querschnitt/eval/s16/results.json); they disagree on [486](../../../bern/querschnitt/eval/s16/results.json), precision [0.586 [0.542, 0.630]](../../../bern/querschnitt/eval/s16/results.json) — those go to `please check`. This lane is the shipped operating point.

**Calibration of D4** ([S16](../../../bern/querschnitt/eval/s16/results.json); isotonic, 2-fold cross-fitted, n 1,357; the map the production run reads, [`eval/calibration.json`](../eval/calibration.json)): expected calibration error [0.2463](../../../bern/querschnitt/eval/s16/results.json) raw → [0.0211](../../../bern/querschnitt/eval/s16/results.json) recalibrated (D1, same file: [0.2791](../../../bern/querschnitt/eval/s16/results.json) → [0.0319](../../../bern/querschnitt/eval/s16/results.json)).

Per period, D3: pre-2010 [0.678 [0.493, 0.821], n 28](../../../bern/ideation2/spikes/s9-aps/results.json) · 2010-19 [0.697 [0.653, 0.739], n 446](../../../bern/ideation2/spikes/s9-aps/results.json) · 2020+ [0.736 [0.706, 0.765], n 883](../../../bern/ideation2/spikes/s9-aps/results.json).
Lanes of D3 (S9; the two code orders agree / disagree): orders agree [0.610](../../../bern/ideation2/spikes/s9-aps/results.json) of affairs, D3 precision [0.812 [0.784, 0.838]](../../../bern/ideation2/spikes/s9-aps/results.json) · orders disagree [0.389](../../../bern/ideation2/spikes/s9-aps/results.json) of affairs, D3 precision [0.580 [0.537, 0.622]](../../../bern/ideation2/spikes/s9-aps/results.json).
Per chapter: macro-F1 [0.677](../../../bern/ideation2/spikes/s9c-calibration/perlevel.json) (D1), [0.692](../../../bern/ideation2/spikes/s9c-calibration/perlevel.json) (D3) over the [22](../../../bern/ideation2/spikes/s9c-calibration/perlevel.json) chapters present.

**Confidence (S9c, 2-fold cross-fitted isotonic recalibration, no new calls).** Expected calibration error:

| | D0 | D1 | D3 |
|---|---|---|---|
| raw p | [0.262](../../../bern/ideation2/spikes/s9c-calibration/results.json) | [0.279](../../../bern/ideation2/spikes/s9c-calibration/results.json) | [0.221](../../../bern/ideation2/spikes/s9c-calibration/results.json) |
| recalibrated | [0.035](../../../bern/ideation2/spikes/s9c-calibration/results.json) | [0.037](../../../bern/ideation2/spikes/s9c-calibration/results.json) | [0.017](../../../bern/ideation2/spikes/s9c-calibration/results.json) |

**Coverage–precision** (top-1 precision on the affairs that pass, ranked by confidence; the rest go to `please check`).

| coverage | 50% | 60% | 70% | 80% | 90% | 100% |
|---|---|---|---|---|---|---|
| **D4 shipped** (S16) | [0.890 [0.865, 0.913]](../../../bern/querschnitt/eval/s16/results.json) | [0.875 [0.851, 0.897]](../../../bern/querschnitt/eval/s16/results.json) | [0.850 [0.826, 0.872]](../../../bern/querschnitt/eval/s16/results.json) | [0.821 [0.797, 0.844]](../../../bern/querschnitt/eval/s16/results.json) | [0.781 [0.757, 0.804]](../../../bern/querschnitt/eval/s16/results.json) | [0.740 [0.716, 0.764]](../../../bern/querschnitt/eval/s16/results.json) |
| D3 examples (S9) | [0.895 [0.869, 0.917]](../eval/aps_curves.json) | [0.864 [0.839, 0.887]](../eval/aps_curves.json) | [0.842 [0.817, 0.864]](../eval/aps_curves.json) | [0.808 [0.783, 0.831]](../eval/aps_curves.json) | [0.764 [0.740, 0.788]](../eval/aps_curves.json) | [0.722 [0.697, 0.746]](../eval/aps_curves.json) |
| D1 read-back (S9) | [0.864 [0.836, 0.889]](../eval/aps_curves.json) | [0.845 [0.818, 0.869]](../eval/aps_curves.json) | [0.809 [0.783, 0.834]](../eval/aps_curves.json) | [0.787 [0.761, 0.811]](../eval/aps_curves.json) | [0.744 [0.719, 0.769]](../eval/aps_curves.json) | [0.703 [0.678, 0.728]](../eval/aps_curves.json) |

D4 points are read from [S16 coverage_precision](../../../bern/querschnitt/eval/s16/results.json) (one point per affair). S9 rows recomputed from S9 raw logs by [`eval/scripts/aps_curves.py`](../eval/scripts/aps_curves.py) (full curve in 5% steps); the D3 precisions at 50, 70, 90 and 100% equal [S9 results.json](../../../bern/ideation2/spikes/s9-aps/results.json). The app's chart is the D4 curve with the shipped operating point marked: readings agree, coverage [64.1%](../../../bern/querschnitt/eval/s16/results.json), precision [0.826](../../../bern/querschnitt/eval/s16/results.json).

### 2 · APS subtopic vs APS editors, end to end (S9)

| n | top-1 | top-3 | gold chapter in the shortlist | baseline: D0 chapter → best subtopic |
|---|---|---|---|---|
| 1,221 | [0.520 [0.492, 0.549]](../../../bern/ideation2/spikes/s9-aps/results.json) | [0.677 [0.650, 0.703]](../../../bern/ideation2/spikes/s9-aps/results.json) | [0.830 [0.809, 0.850]](../../../bern/ideation2/spikes/s9-aps/results.json) | [0.469 [0.441, 0.498]](../../../bern/ideation2/spikes/s9-aps/results.json) |

Subtopics ship as ranked suggestions, not as a lane.

**Hierarchical metrics of the shipped design D4** — computed after S16 from its rows (not pre-registered; no new calls) by [`eval/s16/hierarchical.py`](../eval/s16/hierarchical.py). Same 1,221 items as above (chapter + subtopic gold); hierarchical precision / recall / F1 after Kiritchenko et al. (predicted and gold sets augmented with their ancestors, levels chapter and subtopic, micro-averaged); per-chapter F1 is the chapter top-1, one vs rest, macro over the [22](../../../bern/querschnitt/eval/s16/hierarchical.json) chapters present, on all 1,357 items. Intervals: Wilson for the subtopic rates, percentile bootstrap 2,000 for hP/hR/hF and macro-F1 (stratified by gold chapter), bounds rounded outward.

| Design | subtopic top-1 | subtopic top-3 | subtopic top-1 when the chapter is right | hP | hR | hF | per-chapter macro-F1 |
|---|---|---|---|---|---|---|---|
| **D4 shipped** | **[0.538 [0.510, 0.567]](../../../bern/querschnitt/eval/s16/hierarchical.json)** | [0.699 [0.673, 0.725]](../../../bern/querschnitt/eval/s16/hierarchical.json) | [0.727 [0.697, 0.756]](../../../bern/querschnitt/eval/s16/hierarchical.json) (n 905) | [0.640 [0.616, 0.663]](../../../bern/querschnitt/eval/s16/hierarchical.json) | [0.640 [0.616, 0.663]](../../../bern/querschnitt/eval/s16/hierarchical.json) | **[0.640 [0.616, 0.663]](../../../bern/querschnitt/eval/s16/hierarchical.json)** | [0.705 [0.680, 0.729]](../../../bern/querschnitt/eval/s16/hierarchical.json) |
| D1 read-back, no examples | [0.520 [0.492, 0.549]](../../../bern/querschnitt/eval/s16/hierarchical.json) | [0.677 [0.650, 0.703]](../../../bern/querschnitt/eval/s16/hierarchical.json) | [0.740 [0.710, 0.769]](../../../bern/querschnitt/eval/s16/hierarchical.json) (n 859) | [0.612 [0.586, 0.637]](../../../bern/querschnitt/eval/s16/hierarchical.json) | [0.612 [0.586, 0.637]](../../../bern/querschnitt/eval/s16/hierarchical.json) | [0.612 [0.586, 0.637]](../../../bern/querschnitt/eval/s16/hierarchical.json) | [0.676 [0.651, 0.701]](../../../bern/querschnitt/eval/s16/hierarchical.json) |
| D0 list prompting → best subtopic in its chapter | [0.464 [0.436, 0.493]](../../../bern/querschnitt/eval/s16/hierarchical.json) | [0.596 [0.568, 0.624]](../../../bern/querschnitt/eval/s16/hierarchical.json) | [0.710 [0.678, 0.741]](../../../bern/querschnitt/eval/s16/hierarchical.json) (n 798) | [0.564 [0.539, 0.591]](../../../bern/querschnitt/eval/s16/hierarchical.json) | [0.558 [0.533, 0.585]](../../../bern/querschnitt/eval/s16/hierarchical.json) | [0.561 [0.535, 0.588]](../../../bern/querschnitt/eval/s16/hierarchical.json) | [0.625 [0.598, 0.652]](../../../bern/querschnitt/eval/s16/hierarchical.json) |
| keyword (chapter only) | — | — | — | [0.203 [0.181, 0.227]](../../../bern/querschnitt/eval/s16/hierarchical.json) | [0.101 [0.090, 0.114]](../../../bern/querschnitt/eval/s16/hierarchical.json) | [0.135 [0.121, 0.151]](../../../bern/querschnitt/eval/s16/hierarchical.json) | [0.165 [0.145, 0.185]](../../../bern/querschnitt/eval/s16/hierarchical.json) |

D4 and D1 always name one chapter and one subtopic, so hP = hR = hF for them (the mean of chapter and subtopic top-1); D0 predicts the chapter only when its chapter is not in the subtopic shortlist, the keyword baseline always. The conditional rate is over each design's own correct-chapter items, so it is not a paired comparison. On all 1,357 items (gold depth 1 where the main subtopic is not among the 190): D4 hF [0.628 [0.605, 0.653]](../../../bern/querschnitt/eval/s16/hierarchical.json).

### 3 · “Digitalisierung”: the 30 affairs DVS curates by hand (recall)

| | all 30 | begun in 2026 |
|---|---|---|
| Querschnitt (yes/no, p ≥ 0.5) | [27/30](../../../bern/ideation2/spikes/s8-dvs/results.md#L212) [0.743, 0.966] | [23/24](../../../bern/ideation2/spikes/s8-dvs/results.md#L214) [0.797, 0.993] |
| keyword list (29 stems, de/fr/it) | [21/30](../../../bern/ideation2/spikes/s8-dvs/results.md#L212) [0.521, 0.834] | [16/24](../../../bern/ideation2/spikes/s8-dvs/results.md#L214) [0.467, 0.821] |
| the AI judge, for reference (S15) | [27/30](../../../bern/ideation2/spikes/s15-judgecheck/results.json) [0.743, 0.966] | — |

Split: pre-registered re-run (P8.2); the yes/no prompt and the 0.5 cut-off were set on these 30 items in S3 E6.

### 4 · Federal Sachbereiche vs Parliament's own Curia tags (all tags per affair)

| n = 200, submitted after the BFH model | micro-F1 | macro-F1 | top-1 is a gold tag |
|---|---|---|---|
| Apertus: 5 retrieved tagged examples + yes/no check of the top 6 | [0.654 [0.623, 0.686]](../../../bern/ideation/spikes/s5-aps/results.md#L84) | [0.570 [0.520, 0.622]](../../../bern/ideation/spikes/s5-aps/results.md#L84) | [0.865 [0.810, 0.906]](../../../bern/ideation/spikes/s3-accuracy/results.md#L27) (no examples) |
| BFH model, trained on [15,007](../../../bern/research/R1-parts/prior-art.md#L10) tagged affairs | [0.687 [0.652, 0.722]](../../../bern/ideation/spikes/s3-accuracy/results.md#L35) | [0.577 [0.525, 0.642]](../../../bern/ideation/spikes/s3-accuracy/results.md#L35) | [0.855 [0.799, 0.898]](../../../bern/ideation/spikes/s3-accuracy/results.md#L35) |

Paired micro-F1 difference Apertus − BFH: [−0.079 to +0.010](../../../bern/ideation/spikes/s5-aps/results.md#L89). Split: test n = 200; rules, τ and λ tuned on 100 dev items (tuning split). Example pool: 52,408 affairs tagged before 6 Nov 2024.

### 5 · Bern: lead directorate (8 directorates, scheme swap) vs the Grand Council's own field, titles only

Production run, every affair begun 2025–26 with a lead directorate (S18, [pre-registered](../../../bern/querschnitt/eval/PREREG-BUILD.md#L28); nothing tuned), and the earlier random sample of affairs since 2015 (S6, one run).

| | n | German title | French title | German − French, paired | keyword stems DE / FR | majority |
|---|---|---|---|---|---|---|
| **S18, 2025–26, production run** | 531 | **[0.651 [0.610, 0.691]](../../../bern/querschnitt/eval/s18/results.json)** | [0.650 [0.608, 0.690]](../../../bern/querschnitt/eval/s18/results.json) (n 529) | [+0.001 [−0.031, +0.034]](../../../bern/querschnitt/eval/s18/results.json) (n 529) | [0.525 [0.482, 0.568]](../../../bern/querschnitt/eval/s18/results.json) / [0.512](../../../bern/querschnitt/eval/s18/results.json) | [0.214](../../../bern/querschnitt/eval/s18/results.json) (SID) |
| S6, since 2015, random 200 | 200 | [0.615 [0.545, 0.680]](../../../bern/ideation/spikes/s6-cantonal/results.md#L63) | [0.645 [0.576, 0.709]](../../../bern/ideation/spikes/s6-cantonal/results.md#L64) | [−0.030 [−0.085, +0.025]](../../../bern/ideation/spikes/s6-cantonal/results.md#L69) | [0.520 [0.451, 0.589]](../../../bern/ideation/spikes/s6-cantonal/results.md#L66) / [0.495 [0.426, 0.564]](../../../bern/ideation/spikes/s6-cantonal/results.md#L66) | [0.175 [0.128, 0.234]](../../../bern/ideation/spikes/s6-cantonal/results.md#L67) (BVD) |

S6, German and French averaged: [0.645 [0.576, 0.709]](../../../bern/ideation/spikes/s6-cantonal/results.md#L65). Directorate descriptions in the scheme file were written by the agent; keyword stems were frozen before any result.

### 6 · Basel-Stadt: the canton's own 46 themes vs its hand-assigned «Thema 1», all 2,437 Grand Council affairs 2019–24 (S20, S21)

Gold: the themes the canton's Kantons- und Stadtentwicklung assigned by hand (OGD dataset 100086), joined to OpenParlData by number. S20 hands over the 46 theme names as a scheme file, verbatim, no descriptions, nothing tuned ([pre-registered](../../../bern/querschnitt/eval/PREREG-BUILD.md#L48)). S21 adds five of Basel's own labelled affairs as examples, always from the other half of the data, no training ([pre-registered](../../../bern/querschnitt/eval/PREREG-BUILD.md#L59), paired against S20 on the same items).

| Design | top-1 = Thema 1 | Thema 1 or 2 | top-3 | readings agree: share, precision | readings disagree: precision |
|---|---|---|---|---|---|
| S20 theme names only | [0.498 [0.478, 0.518]](../../../bern/querschnitt/eval/s20/results.json) | [0.605 [0.586, 0.625]](../../../bern/querschnitt/eval/s20/results.json) | [0.665 [0.646, 0.685]](../../../bern/querschnitt/eval/s20/results.json) | [71.9%](../../../bern/querschnitt/eval/s20/results.json), [0.565 [0.542, 0.589]](../../../bern/querschnitt/eval/s20/results.json) | [0.325 [0.290, 0.362]](../../../bern/querschnitt/eval/s20/results.json) |
| S21 + five Basel examples (two readings, D4 shape) | **[0.526 [0.506, 0.547]](../../../bern/querschnitt/eval/s21/results.json)** | [0.631](../../../bern/querschnitt/eval/s21/results.json) | [0.711](../../../bern/querschnitt/eval/s21/results.json) | [54.9%](../../../bern/querschnitt/eval/s21/results.json), [0.651 [0.625, 0.677]](../../../bern/querschnitt/eval/s21/results.json) | [0.373 [0.345, 0.403]](../../../bern/querschnitt/eval/s21/results.json) |
| keyword stems (frozen) | [0.181 [0.166, 0.198]](../../../bern/querschnitt/eval/s20/results.json) | — | — | — | — |
| majority theme (Verwaltung) | [0.053](../../../bern/querschnitt/eval/s20/results.json) | — | — | — | — |

S21 − S20, paired: [+0.028 [+0.014, +0.043]](../../../bern/querschnitt/eval/s21/results.json). S20 − keyword, paired: [+0.316 [+0.293, +0.340]](../../../bern/querschnitt/eval/s20/results.json).

S20 by affair type: Interpellation [0.501 [0.467, 0.536], n 822](../../../bern/querschnitt/eval/s20/results.json) · Schriftliche Anfrage [0.465 [0.430, 0.501], n 789](../../../bern/querschnitt/eval/s20/results.json) · Anzug [0.546 [0.504, 0.588], n 549](../../../bern/querschnitt/eval/s20/results.json) · Motion [0.517 [0.435, 0.599], n 141](../../../bern/querschnitt/eval/s20/results.json) · Petition [0.419 [0.318, 0.529], n 81](../../../bern/querschnitt/eval/s20/results.json) · Budgetpostulat [0.400 [0.218, 0.614], n 20](../../../bern/querschnitt/eval/s20/results.json) (types with n < 20 not shown).

### 7 · The AI judge itself against human labels

| Test | n | AI judge (Claude, blind) | Apertus, same items |
|---|---|---|---|
| APS chapter = APS editors' chapter (S11) | 200 | [0.790 [0.728, 0.841]](../../../bern/ideation2/spikes/s11-anchor/anchor.json); second code included [0.900 [0.850, 0.935]](../../../bern/ideation2/spikes/s11-anchor/anchor.json); run A = run B [0.990 [0.964, 0.998]](../../../bern/ideation2/spikes/s11-anchor/anchor.json) | D1 [0.695 [0.628, 0.755]](../../../bern/ideation2/spikes/s11-anchor/anchor.json) · D3 [0.720 [0.654, 0.778]](../../../bern/ideation2/spikes/s11-anchor/anchor.json) |
| says yes to the 30 DVS items (S15) | 30 | [27/30](../../../bern/ideation2/spikes/s15-judgecheck/results.json) [0.743, 0.966] both runs (run B [28 of 30](../../../bern/ideation2/spikes/s15-judgecheck/results.json)) | [27/30](../../../bern/ideation2/spikes/s8-dvs/results.md#L212) |

The judge's precision on human negatives is not measured (no human negatives exist).

### 8 · Neutrality on human labels (S9, no new calls)

Language, same 1,357 affairs scored from the German vs the French text (paired): German − French [+0.016 [−0.003, +0.037]](../../../bern/ideation2/spikes/s14-neutrality/results.json), McNemar p 0.1133.

| S9 by party | D1 top-1 | keyword top-1 |
|---|---|---|
| SVP | [0.664 [0.581, 0.738], n 137](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.248 [0.183, 0.327], n 137](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| SP | [0.701 [0.629, 0.765], n 174](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.172 [0.123, 0.236], n 174](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| FDP | [0.671 [0.591, 0.743], n 146](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.178 [0.124, 0.249], n 146](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| Mitte | [0.632 [0.544, 0.712], n 125](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.144 [0.093, 0.217], n 125](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| Grüne | [0.578 [0.478, 0.674], n 95](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.200 [0.131, 0.292], n 95](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| GLP | [0.644 [0.498, 0.768], n 45](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.088 [0.035, 0.208], n 45](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| other party | [0.687 [0.514, 0.821], n 32](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.093 [0.032, 0.243], n 32](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| committee | [0.743 [0.681, 0.797], n 222](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.175 [0.131, 0.232], n 222](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| government | [0.792 [0.740, 0.836], n 274](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.237 [0.190, 0.292], n 274](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| canton | [0.729 [0.619, 0.818], n 74](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.202 [0.126, 0.308], n 74](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| unknown | [0.697 [0.526, 0.827], n 33](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.212 [0.106, 0.378], n 33](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| *test (cells n ≥ 20)* | [p 0.4655; gap SP − Grüne +0.122 [−0.007, +0.242]](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [p 0.1458; gap SVP − GLP +0.159 [+0.041, +0.263]](../../../bern/ideation2/spikes/s14-neutrality/results.json) |

| S9 by instrument | D1 top-1 | keyword top-1 |
|---|---|---|
| Motion | [0.653 [0.608, 0.696], n 459](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.180 [0.148, 0.219], n 459](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| Postulat | [0.658 [0.603, 0.711], n 296](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.141 [0.106, 0.187], n 296](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| Regierungsgeschäft | [0.792 [0.740, 0.836], n 274](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.237 [0.190, 0.292], n 274](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| Parlamentarische Initiative | [0.758 [0.700, 0.808], n 244](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.217 [0.170, 0.274], n 244](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| Standesinitiative | [0.729 [0.619, 0.818], n 74](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.202 [0.126, 0.308], n 74](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| other type | [0.400 [0.168, 0.688], n 10](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) | [0.200 [0.056, 0.510], n 10](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| *test (cells n ≥ 20)* | [p 0.0002; gap Regierungsgeschäft − Motion +0.138 [+0.068, +0.201]](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [p 0.0796; gap Regierungsgeschäft − Postulat +0.095 [+0.029, +0.160]](../../../bern/ideation2/spikes/s14-neutrality/results.json) |

Reading: no measurable difference by language or among the six main parties; government business scores higher than members' motions, and the keyword baseline shows the same order (easier texts, not a political tilt). Quality is reported per submitter type.

### 9 · Free naming without a list (rule check)

Asked to name a topic freely, Apertus answered outside both the Curia 28 and the APS label sets in [36/40](../../../bern/ideation/spikes/s3-accuracy/results.md#L116) (0.900 [0.769, 0.961]) and never answered “no topic” ([0/40](../../../bern/ideation/spikes/s3-accuracy/results.md#L116)); with the list shown, [0/40](../../../bern/ideation/spikes/s3-accuracy/results.md#L117) were off-list. Every shipped decision is a choice among listed codes.

## AI-judge rows

Gold where no official labels exist: a blind AI judge (two runs of a Claude model + a tie-break run, cross-checked by the open-weights Qwen-SEA-LION). Its agreement with human labels is in §7 above. Every figure below is agreement with that judge.

### 10 · “Digitalisierung” in Swiss parliaments, 2026: full census (S8 design, pre-registered)

Population: all [14,512](../../../bern/querschnitt/eval/s8full/results.json) Swiss affairs begun 1 Jan–6 Oct 2026 with a title. Every one of the [14,789](../../../bern/querschnitt/eval/s8full/results.json) affairs in the window (Liechtenstein included) is decided ([9,519](../../../bern/querschnitt/eval/s8full/results.json) from the S8 rows, [5,270](../../../bern/querschnitt/eval/s8full/results.json) from the production run with the same prompt and build, [0](../../../bern/querschnitt/eval/s8full/results.json) missing), so flags are counted, not estimated. Precision and recall use the same 453 checked Swiss affairs and the same judge as S8, weights post-stratified to the census strata; flag at p ≥ 0.5, fixed before the run ([PREREG.md § S8](../../../bern/ideation2/PREREG.md#L10)). Recomputed by [`eval/s8full/analyze.py`](../eval/s8full/analyze.py), no model calls.

| full census, 95% interval | Querschnitt | keyword list (29 stems) | difference, bootstrap |
|---|---|---|---|
| precision vs the judge | **[0.905 [0.865, 0.945]](../../../bern/querschnitt/eval/s8full/results.json)** | [0.756 [0.717, 0.793]](../../../bern/querschnitt/eval/s8full/results.json) | [+0.149 [+0.106, +0.192]](../../../bern/querschnitt/eval/s8full/results.json) |
| recall vs the judge | [0.659 [0.491, 0.900]](../../../bern/querschnitt/eval/s8full/results.json) | [0.584 [0.435, 0.795]](../../../bern/querschnitt/eval/s8full/results.json) | [+0.075 [+0.041, +0.123]](../../../bern/querschnitt/eval/s8full/results.json) |
| affairs flagged (counted) | [651](../../../bern/querschnitt/eval/s8full/results.json) in [57](../../../bern/querschnitt/eval/s8full/results.json) parliaments ([41](../../../bern/querschnitt/eval/s8full/results.json) in `please check`) | [690](../../../bern/querschnitt/eval/s8full/results.json); both [470](../../../bern/querschnitt/eval/s8full/results.json) | |
| gold = majority of Claude A, B and Qwen: precision / recall | [0.890 [0.845, 0.933] / 0.656 [0.486, 0.904]](../../../bern/querschnitt/eval/s8full/results.json) | [0.736 [0.696, 0.776] / 0.582 [0.428, 0.800]](../../../bern/querschnitt/eval/s8full/results.json) | |

Estimated digitalisation affairs (judge positives): [893 [656, 1,191]](../../../bern/querschnitt/eval/s8full/results.json). Including Liechtenstein: [670](../../../bern/querschnitt/eval/s8full/results.json) flagged by Querschnitt, [708](../../../bern/querschnitt/eval/s8full/results.json) by keywords, of [14,789](../../../bern/querschnitt/eval/s8full/results.json). The differences are bootstrap intervals; their point is the difference of the two stored points. Judge: run A = run B [0.976](../../../bern/ideation2/spikes/s8-dvs/score.json) (κ [0.951](../../../bern/ideation2/spikes/s8-dvs/score.json)); Qwen vs the runs κ [0.812](../../../bern/ideation2/spikes/s8-dvs/score.json) / [0.824](../../../bern/ideation2/spikes/s8-dvs/score.json).

**History: the S8 snapshot** (14,513 Swiss affairs in the 6 Oct window, of which the census run had scored 8,139 when it was paused; flags estimated from the last week in full and 5,338 of 14,212 earlier affairs at random). Superseded above for counts and judge precision/recall; kept for the record: precision [0.914 [0.876, 0.952]](../../../bern/ideation2/spikes/s8-dvs/score_ch.json), recall [0.654 [0.486, 0.894]](../../../bern/ideation2/spikes/s8-dvs/score_ch.json), estimated flags [653 [629, 676]](../../../bern/ideation2/spikes/s8-dvs/score_ch.json) (keywords [734 [711, 757]](../../../bern/ideation2/spikes/s8-dvs/score_ch.json)), estimated positives [913 [668, 1,218]](../../../bern/ideation2/spikes/s8-dvs/score_ch.json); keyword precision [0.753 [0.714, 0.790]](../../../bern/ideation2/spikes/s8-dvs/score_ch.json), recall [0.605 [0.451, 0.827]](../../../bern/ideation2/spikes/s8-dvs/score_ch.json); judge = Qwen alone [0.863 / 0.811](../../../bern/ideation2/spikes/s8-dvs/score_ch.json) (keywords [0.691 / 0.729](../../../bern/ideation2/spikes/s8-dvs/score_ch.json)). The breakdowns below are still on the snapshot's weights.

Judge-confirmed Swiss positives in the checked sample: [190](../../../bern/ideation2/spikes/s8-dvs/score_ch.json) from [45](../../../bern/ideation2/spikes/s8-dvs/score_ch.json) parliaments — [cantonal 87, federal 62, communal 41; German 141, French 35, Italian 14](../../../bern/ideation2/spikes/s8-dvs/score_ch.json).

Per language and level (all 464 checked items incl. Liechtenstein, snapshot weights; S14):

| S8 by language | precision | recall |
|---|---|---|
| de | [0.911 [0.866, 0.952], n 137](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.595 [0.423, 0.880], n 150](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| fr | [0.929 [0.848, 0.992], n 36](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.574 [0.281, 1.000], n 35](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| it | [0.944 [0.803, 1.000], n 13](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) | [0.894 [0.715, 1.000], n 14](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| *test (cells n ≥ 20)* | [p 0.8566; gap fr − de +0.018 [−0.078, +0.094]](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [p 0.8972; gap de − fr +0.021 [−0.501, +0.440]](../../../bern/ideation2/spikes/s14-neutrality/results.json) |

| S8 by level | precision | recall |
|---|---|---|
| federal | [0.877 [0.778, 0.961], n 57](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.443 [0.242, 0.900], n 62](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| cantonal | [0.936 [0.889, 0.978], n 80](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.724 [0.496, 0.934], n 87](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| communal | [0.907 [0.821, 0.973], n 43](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.929 [0.851, 0.985], n 41](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| other | [1.000 [1.000, 1.000], n 6](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) | [0.191 [0.038, 1.000], n 9](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| *test (cells n ≥ 20)* | [p 0.4593; gap cantonal − federal +0.059 [−0.038, +0.166]](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [p 0.1948; gap communal − federal +0.485 [+0.021, +0.692]](../../../bern/ideation2/spikes/s14-neutrality/results.json) |

| S8 by submitter party | Querschnitt precision | keyword precision |
|---|---|---|
| SVP | [0.636 [0.310, 0.929], n 11](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) | [0.417 [0.173, 0.645], n 20](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| SP | [0.943 [0.850, 1.000], n 24](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.764 [0.637, 0.874], n 38](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| FDP | [0.807 [0.564, 1.000], n 15](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) | [0.689 [0.438, 0.899], n 16](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| Mitte | [0.959 [0.859, 1.000], n 21](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.845 [0.668, 0.981], n 19](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| Grüne | [1.000 [1.000, 1.000], n 19](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) | [0.652 [0.430, 0.831], n 21](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| GLP | [0.913 [0.750, 1.000], n 15](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) | [0.927 [0.744, 1.000], n 11](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| other party | [1.000 [1.000, 1.000], n 22](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.859 [0.736, 0.956], n 29](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| party unknown | [0.975 [0.901, 1.000], n 12](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) | [0.865 [0.562, 1.000], n 7](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| government | [0.944 [0.854, 1.000], n 22](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.871 [0.728, 0.969], n 25](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| committee | [0.863 [0.370, 1.000], n 5](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) | [0.759 [0.306, 1.000], n 6](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| other group | [1.000 [1.000, 1.000], n 1](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) | [1.000 [1.000, 1.000], n 2](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| unknown | [0.835 [0.655, 0.967], n 19](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) | [0.683 [0.493, 0.847], n 24](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| *test (cells n ≥ 20)* | [p 0.018; gap Mitte − SP +0.016 [−0.105, +0.129]](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [p 0.0212; gap SP − SVP +0.347 [+0.074, +0.623]](../../../bern/ideation2/spikes/s14-neutrality/results.json) |

The party test (p 0.018) comes from the small SVP cell (7 of 11 confirmed); keyword precision dips on the same items (7/20). Among cells with n ≥ 20 the gap is [+0.016 [−0.105, +0.129]](../../../bern/ideation2/spikes/s14-neutrality/results.json). Canton cells are below n = 20 except BS and are not read.

Per parliament (snapshot: flag counts in the scored sample, [S8 results](../../../bern/ideation2/spikes/s8-dvs/results.md#L75); estimated flags point only, no per-body gold) — the ten largest:

| body | level | affairs in 2026 | scored | flagged | est. flags | keyword hits |
|---|---|---|---|---|---|---|
| CHE | federal | [3,162](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [1,457](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [91](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [177.1](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [104](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) |
| BS | cantonal | [919](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [349](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [17](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [44.8](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [23](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) |
| GE | cantonal | [612](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [240](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [9](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [24.2](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [10](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) |
| 261 | communal | [554](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [242](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [12](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [25.1](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [19](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) |
| VD | cantonal | [549](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [209](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [12](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [31.7](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [14](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) |
| TI | cantonal | [540](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [230](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [10](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [21.9](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [14](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) |
| BE | cantonal | [500](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [187](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [16](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [42.8](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [12](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) |
| BL | cantonal | [460](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [154](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [1](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [3.0](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [4](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) |
| ZH | cantonal | [440](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [168](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [5](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [13.1](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [7](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) |
| VS | cantonal | [393](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [136](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [9](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [26.0](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) | [10](../../../bern/ideation2/spikes/s8-dvs/results.md#L75) |

All bodies: [`eval/pruefstand.json`](../eval/pruefstand.json) → `dvs_2026.breakdowns.per_body_flags`.

### 11 · APS chapter, communal parliaments 2026: the production run vs the judge (S17, pre-registered)

200 communal affairs begun 1 Jan–11 Oct 2026, drawn at random among those with a shipped chapter (S6 items excluded); the chapter as shipped by the production run (read back from the subtopic, no examples). Judge: two blind Claude runs on the exact production input, tie-break run on the [11](../../../bern/querschnitt/eval/s17/results.json) disagreements; κ [0.940](../../../bern/querschnitt/eval/s17/results.json) ([PREREG-BUILD.md § S17](../../../bern/querschnitt/eval/PREREG-BUILD.md#L17)).

| n = 200 | top-1 | top-3 |
|---|---|---|
| shipped chapter | **[0.640 [0.571, 0.704]](../../../bern/querschnitt/eval/s17/results.json)** | [0.770 [0.706, 0.823]](../../../bern/querschnitt/eval/s17/results.json) |
| frozen S9 keyword baseline | [0.150 [0.107, 0.207]](../../../bern/querschnitt/eval/s17/results.json) | — |
| majority chapter of the sample's gold (computed after) | [0.135](../../../bern/querschnitt/eval/s17/results.json) | — |

| cell | top-1 | n |
|---|---|---|
| lane: readings agree | [0.677 [0.600, 0.746]](../../../bern/querschnitt/eval/s17/results.json) | [155](../../../bern/querschnitt/eval/s17/results.json) |
| lane: please check | [0.511 [0.370, 0.651]](../../../bern/querschnitt/eval/s17/results.json) | [45](../../../bern/querschnitt/eval/s17/results.json) |
| German | [0.631 [0.550, 0.707]](../../../bern/querschnitt/eval/s17/results.json) | [144](../../../bern/querschnitt/eval/s17/results.json) |
| French | [0.687 [0.514, 0.821]](../../../bern/querschnitt/eval/s17/results.json) | [32](../../../bern/querschnitt/eval/s17/results.json) |
| Italian | [0.625 [0.427, 0.789]](../../../bern/querschnitt/eval/s17/results.json) | [24](../../../bern/querschnitt/eval/s17/results.json) |
| with text | [0.636 [0.563, 0.704]](../../../bern/querschnitt/eval/s17/results.json) | [176](../../../bern/querschnitt/eval/s17/results.json) |
| title only | [0.666 [0.467, 0.821]](../../../bern/querschnitt/eval/s17/results.json) | [24](../../../bern/querschnitt/eval/s17/results.json) |

### 12 · Correction loop, text input, evidence

| Test | n | Result | Same items, without |
|---|---|---|---|
| Correction loop (simulated, P8.5): 60 judge labels shown as an editor's first decisions, 4 nearest per affair | 404 | F1 [0.906](../../../bern/ideation2/spikes/s8-dvs/loop.json); Δ [+0.040 [+0.007, +0.075]](../../../bern/ideation2/spikes/s8-dvs/loop.json) | F1 [0.866](../../../bern/ideation2/spikes/s8-dvs/loop.json) |
| Submitted text added to title (S8b, federal) | 120 | precision [1.000 [0.908, 1.000]](../../../bern/ideation2/spikes/s13-timing/results.md#L33), recall [0.678 [0.548, 0.786]](../../../bern/ideation2/spikes/s13-timing/results.md#L33); Δ recall [−0.089 [−0.170, −0.019]](../../../bern/ideation2/spikes/s13-timing/s8b.json) | title only: [0.895 [0.778, 0.955], 0.767 [0.642, 0.860]](../../../bern/ideation2/spikes/s13-timing/results.md#L32) |
| Evidence: the quoted sentence supports the chapter (S12) | 120 | [0.850 [0.775, 0.903]](../../../bern/ideation2/spikes/s12-evidence/results.json); chapter right [0.902 [0.819, 0.950]](../../../bern/ideation2/spikes/s12-evidence/results.json), wrong [0.736 [0.579, 0.851]](../../../bern/ideation2/spikes/s12-evidence/results.json) | exact-substring check [120/120](../../../bern/ideation2/spikes/s12-evidence/results.json) |

The loop row is unweighted and on a sample that over-represents flagged affairs; text makes the model stricter, not more complete.

### 13 · APS chapter, cantonal and communal (S6, cross-checked S7)

| cell | top-1 vs the judge | n |
|---|---|---|
| all | [0.686 [0.608, 0.755]](../../../bern/ideation/spikes/s6-cantonal/score.json) | [153](../../../bern/ideation/spikes/s6-cantonal/score.json) |
| cantonal | [0.726 [0.629, 0.806]](../../../bern/ideation/spikes/s6-cantonal/score.json) | [95](../../../bern/ideation/spikes/s6-cantonal/score.json) |
| communal | [0.621 [0.492, 0.735]](../../../bern/ideation/spikes/s6-cantonal/score.json) | [58](../../../bern/ideation/spikes/s6-cantonal/score.json) |
| German | [0.672 [0.552, 0.773]](../../../bern/ideation/spikes/s6-cantonal/score.json) | [67](../../../bern/ideation/spikes/s6-cantonal/score.json) |
| French | [0.708 [0.568, 0.818]](../../../bern/ideation/spikes/s6-cantonal/score.json) | [48](../../../bern/ideation/spikes/s6-cantonal/score.json) |
| Italian | [0.684 [0.525, 0.810]](../../../bern/ideation/spikes/s6-cantonal/score.json) | [38](../../../bern/ideation/spikes/s6-cantonal/score.json) |
| with text | [0.708 [0.621, 0.783]](../../../bern/ideation/spikes/s6-cantonal/score.json) | [120](../../../bern/ideation/spikes/s6-cantonal/score.json) |
| title only | [0.606 [0.436, 0.754]](../../../bern/ideation/spikes/s6-cantonal/score.json) | [33](../../../bern/ideation/spikes/s6-cantonal/score.json) |
| first reading p ≥ 0.9 | [0.742 [0.641, 0.822]](../../../bern/ideation/spikes/s6-cantonal/score.json) | [89](../../../bern/ideation/spikes/s6-cantonal/score.json) |
| the two readings disagree | [0.543 [0.381, 0.696]](../../../bern/ideation/spikes/s6-cantonal/score.json) | [35](../../../bern/ideation/spikes/s6-cantonal/score.json) |
| gold = majority of Claude ×2 + Qwen | [0.684 [0.607, 0.751]](../../../bern/ideation/spikes/s7-crossfamily/score.json) | [158](../../../bern/ideation/spikes/s7-crossfamily/score.json) |

| S6 by canton | top-1 |
|---|---|
| TI | [0.684 [0.525, 0.810], n 38](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| JU | [0.555 [0.337, 0.755], n 18](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| ZH | [0.714 [0.453, 0.883], n 14](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| AG | [0.400 [0.168, 0.688], n 10](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| VD | [0.700 [0.396, 0.893], n 10](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| SG | [0.777 [0.452, 0.937], n 9](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| VS | [0.888 [0.564, 0.981], n 9](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| GE | [0.666 [0.299, 0.904], n 6](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| TG | [0.500 [0.187, 0.813], n 6](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| BE | [0.800 [0.375, 0.964], n 5](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| BL | [0.600 [0.230, 0.883], n 5](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| LU | [1.000 [0.565, 1.000], n 5](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| SO | [1.000 [0.565, 1.000], n 5](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| FR | [0.750 [0.300, 0.955], n 4](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| NE | [1.000 [0.510, 1.000], n 4](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| BS | [0.500 [0.094, 0.906], n 2](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| GR | [0.000 [0.000, 0.794], n 1](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| SZ | [1.000 [0.206, 1.000], n 1](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| ZG | [0.000 [0.000, 0.794], n 1](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| *test (cells n ≥ 20)* | [p 0.3043; gap LU − AG +0.600 [+0.300, +0.900]](../../../bern/ideation2/spikes/s14-neutrality/results.json) |

### 14 · Bilingual cantons BE, FR, VS — German vs French titles (S10, pre-registered)

| n = 210 | German | French | averaged |
|---|---|---|---|
| chapter top-1 | [0.543 [0.475, 0.609]](../../../bern/ideation2/spikes/s10-bilingual/score.json) | [0.529 [0.461, 0.595]](../../../bern/ideation2/spikes/s10-bilingual/score.json) | [0.552 [0.484, 0.619]](../../../bern/ideation2/spikes/s10-bilingual/score.json) |
| gold in top 3 | [0.771](../../../bern/ideation2/spikes/s10-bilingual/secondary.txt#L1) | [0.738](../../../bern/ideation2/spikes/s10-bilingual/secondary.txt#L1) | [0.810](../../../bern/ideation2/spikes/s10-bilingual/secondary.txt#L1) |
| BE | [0.571 [0.454, 0.681]](../../../bern/ideation2/spikes/s10-bilingual/score.json) | [0.543 [0.426, 0.655]](../../../bern/ideation2/spikes/s10-bilingual/score.json) | [0.529 [0.413, 0.641]](../../../bern/ideation2/spikes/s10-bilingual/score.json) |
| FR | [0.529 [0.413, 0.641]](../../../bern/ideation2/spikes/s10-bilingual/score.json) | [0.543 [0.426, 0.655]](../../../bern/ideation2/spikes/s10-bilingual/score.json) | [0.571 [0.454, 0.681]](../../../bern/ideation2/spikes/s10-bilingual/score.json) |
| VS | [0.529 [0.413, 0.641]](../../../bern/ideation2/spikes/s10-bilingual/score.json) | [0.500 [0.385, 0.615]](../../../bern/ideation2/spikes/s10-bilingual/score.json) | [0.557 [0.440, 0.668]](../../../bern/ideation2/spikes/s10-bilingual/score.json) |

German − French [+0.014 [−0.043, +0.076]](../../../bern/ideation2/spikes/s10-bilingual/score.json) (paired; no measurable gap at n = 210). The two languages agree on [70.5%](../../../bern/ideation2/spikes/s10-bilingual/score.json): chapter right [0.622 [0.541, 0.696]](../../../bern/ideation2/spikes/s10-bilingual/score.json); where they disagree, German [0.355 [0.247, 0.480]](../../../bern/ideation2/spikes/s10-bilingual/score.json), French [0.306 [0.205, 0.430]](../../../bern/ideation2/spikes/s10-bilingual/score.json) — that third goes to a person. Clerk load: [0.2975 × weekly volume (median 10.0, mean 25.5, p90 76.7) = 3.0 / 7.6 / 22.8 a week](../../../bern/ideation2/spikes/s10-bilingual/results.md#L79).

## Limits

- Recall for “Digitalisierung” on titles is [0.659 [0.491, 0.900]](../../../bern/querschnitt/eval/s8full/results.json) against the judge (full census); most of the interval comes from the few judge positives among checked affairs that neither method flagged (4 among 180 in the S8 packet). The 30 DVS items are the human recall check; the yes/no prompt and the 0.5 cut-off were set on those same items (S3), so a held-out human recall test is the partner's full list (`make eval GOLD=…`).
- APS subtopics reach [0.520 [0.492, 0.549]](../../../bern/ideation2/spikes/s9-aps/results.json) top-1 end to end and ship as ranked suggestions.
- Short, title-only cantonal and communal affairs are the hardest input (0.543 / 0.529 on bilingual titles; S6 0.606 title-only vs 0.708 with text). Communal affairs in production: [0.640 [0.571, 0.704]](../../../bern/querschnitt/eval/s17/results.json) against the judge (S17).
- With only the names of Basel-Stadt's 46 themes, the first theme is matched in [0.498 [0.478, 0.518]](../../../bern/querschnitt/eval/s20/results.json) of affairs; five of Basel's own labelled affairs as examples add [+0.028 [+0.014, +0.043]](../../../bern/querschnitt/eval/s21/results.json) (S21), without training.
- On the Federal Parliament's own multi-tag task the trained BFH model is ahead (micro-F1 0.687 vs 0.654, paired −0.079 to +0.010); the Curia design was tuned on 100 dev items.
- Where no official labels exist, the gold is the AI judge. It matches APS editors on [0.790 [0.728, 0.841]](../../../bern/ideation2/spikes/s11-anchor/anchor.json) of chapters and says yes to 27/30 DVS items; its two Claude runs are close to one judge (0.99 agreement), and its precision on human negatives is not measured.
- All Apertus rows come from one served build; cut-offs and recalibration are refitted per build. ECE intervals are not computed yet.

## To measure

- S19: three new ad-hoc topics (wolf, heat protection, AI in schools) against a blind judge — running, no result yet (pre-registered: [PREREG-BUILD.md § S19](../../../bern/querschnitt/eval/PREREG-BUILD.md#L37))
- FR/IT rows with the headline Curia design + BFH on the same items
- recalibration refit on the build that serves at the event
- ECE intervals (bootstrap)
- judge precision on human negatives
- Romansh
