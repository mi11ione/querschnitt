# Prüfstand

Every measured test behind Querschnitt, as one ruled table each. Human labels first, then the blind AI judge. Model `swiss-ai/apertus-v1.5-8b` on Public AI, build `…dd237840` on every Apertus call. Intervals are 95%: Wilson for proportions, paired bootstrap (2,000) for differences, stratified bootstrap for population estimates. Machine-readable: [`eval/pruefstand.json`](../eval/pruefstand.json) (file and key for every value); claims register: [`eval/claims.tsv`](../eval/claims.tsv); check any text with `python3 -I tools/claims_check.py FILE`. Links point into the evaluation workspace (`bern/ideation*/spikes/`).

## Human labels

### 1 · APS chapter vs APS editors — 1,357 held-out federal affairs, pre-registered (S9)

Wayback process pages not used before; German title + submitted text; nothing tuned on these items. Pre-registration: [PREREG.md § S9](../../../bern/ideation2/PREREG.md#L32).

| Design | top-1 | top-3 | Δ top-1 vs D0, paired | |
|---|---|---|---|---|
| D3 chapter step with five APS-labelled examples | [0.722 [0.698, 0.745]](../../../bern/ideation2/spikes/s9-aps/results.json) | [0.875 [0.856, 0.891]](../../../bern/ideation2/spikes/s9-aps/results.json) | [+0.067 [+0.049, +0.085]](../../../bern/ideation2/spikes/s9-aps/results.json) | shipped where examples exist |
| D1 chapter read back from the subtopic | [0.704 [0.679, 0.727]](../../../bern/ideation2/spikes/s9-aps/results.json) | [0.843 [0.823, 0.861]](../../../bern/ideation2/spikes/s9-aps/results.json) | [+0.049 [+0.032, +0.066]](../../../bern/ideation2/spikes/s9-aps/results.json) | shipped |
| D2 German + French averaged | [0.634 [0.609, 0.660]](../../../bern/ideation2/spikes/s9-aps/results.json) | [0.853 [0.834, 0.871]](../../../bern/ideation2/spikes/s9-aps/results.json) | [−0.021 [−0.037, −0.004]](../../../bern/ideation2/spikes/s9-aps/results.json) | dropped for the label |
| D0 plain list prompting (v14) | [0.655 [0.629, 0.680]](../../../bern/ideation2/spikes/s9-aps/results.json) | — | — | baseline |
| keyword (APS subtopic words, frozen) | [0.192 [0.172, 0.213]](../../../bern/ideation2/spikes/s9-aps/results.json) | — | — | baseline |
| majority chapter | [0.080 [0.066, 0.095]](../../../bern/ideation2/spikes/s9-aps/results.json) | — | — | baseline |

Per period, D3: pre-2010 [0.679 [0.493, 0.821], n 28](../../../bern/ideation2/spikes/s9-aps/results.json) · 2010-19 [0.697 [0.653, 0.738], n 446](../../../bern/ideation2/spikes/s9-aps/results.json) · 2020+ [0.736 [0.706, 0.764], n 883](../../../bern/ideation2/spikes/s9-aps/results.json).
Lanes (the two code orders agree / disagree): orders agree [0.610](../../../bern/ideation2/spikes/s9-aps/results.json) of affairs, D3 precision [0.813 [0.785, 0.838]](../../../bern/ideation2/spikes/s9-aps/results.json) · orders disagree [0.390](../../../bern/ideation2/spikes/s9-aps/results.json) of affairs, D3 precision [0.580 [0.538, 0.622]](../../../bern/ideation2/spikes/s9-aps/results.json).
Per chapter: macro-F1 [0.677](../../../bern/ideation2/spikes/s9c-calibration/perlevel.json) (D1), [0.692](../../../bern/ideation2/spikes/s9c-calibration/perlevel.json) (D3) over the [22](../../../bern/ideation2/spikes/s9c-calibration/perlevel.json) chapters present.

**Confidence (S9c, 2-fold cross-fitted isotonic recalibration, no new calls).** Expected calibration error:

| | D0 | D1 | D3 |
|---|---|---|---|
| raw p | [0.262](../../../bern/ideation2/spikes/s9c-calibration/results.json) | [0.279](../../../bern/ideation2/spikes/s9c-calibration/results.json) | [0.221](../../../bern/ideation2/spikes/s9c-calibration/results.json) |
| recalibrated | [0.035](../../../bern/ideation2/spikes/s9c-calibration/results.json) | [0.037](../../../bern/ideation2/spikes/s9c-calibration/results.json) | [0.017](../../../bern/ideation2/spikes/s9c-calibration/results.json) |

**Coverage–precision** (top-1 precision on the affairs that pass, ranked by confidence; the rest go to `please check`). Shipped dial default: 70% pass.

| coverage | 50% | 60% | 70% | 80% | 90% | 100% |
|---|---|---|---|---|---|---|
| D3 examples | [0.895 [0.870, 0.916]](../eval/aps_curves.json) | [0.865 [0.840, 0.887]](../eval/aps_curves.json) | [0.842 [0.818, 0.864]](../eval/aps_curves.json) ◀ | [0.808 [0.784, 0.831]](../eval/aps_curves.json) | [0.765 [0.740, 0.788]](../eval/aps_curves.json) | [0.722 [0.698, 0.745]](../eval/aps_curves.json) |
| D1 read-back | [0.864 [0.836, 0.888]](../eval/aps_curves.json) | [0.845 [0.819, 0.868]](../eval/aps_curves.json) | [0.809 [0.783, 0.833]](../eval/aps_curves.json) ◀ | [0.787 [0.762, 0.811]](../eval/aps_curves.json) | [0.745 [0.719, 0.768]](../eval/aps_curves.json) | [0.704 [0.679, 0.727]](../eval/aps_curves.json) |

Recomputed from S9 raw logs by [`eval/scripts/aps_curves.py`](../eval/scripts/aps_curves.py) (full curve in 5% steps); the D3 points at 50, 70, 90 and 100% equal [S9 results.json](../../../bern/ideation2/spikes/s9-aps/results.json).

### 2 · APS subtopic vs APS editors, end to end (S9)

| n | top-1 | top-3 | gold chapter in the shortlist | baseline: D0 chapter → best subtopic |
|---|---|---|---|---|
| 1,221 | [0.521 [0.493, 0.549]](../../../bern/ideation2/spikes/s9-aps/results.json) | [0.677 [0.651, 0.703]](../../../bern/ideation2/spikes/s9-aps/results.json) | [0.831 [0.810, 0.850]](../../../bern/ideation2/spikes/s9-aps/results.json) | [0.469 [0.441, 0.497]](../../../bern/ideation2/spikes/s9-aps/results.json) |

Subtopics ship as ranked suggestions, not as a lane.

### 3 · “Digitalisierung”: the 30 affairs DVS curates by hand (recall)

| | all 30 | begun in 2026 |
|---|---|---|
| Querschnitt (yes/no, p ≥ 0.5) | [27/30](../../../bern/ideation2/spikes/s8-dvs/results.md#L212) [0.744, 0.965] | [23/24](../../../bern/ideation2/spikes/s8-dvs/results.md#L214) [0.798, 0.993] |
| keyword list (29 stems, de/fr/it) | [21/30](../../../bern/ideation2/spikes/s8-dvs/results.md#L212) [0.521, 0.833] | [16/24](../../../bern/ideation2/spikes/s8-dvs/results.md#L214) [0.467, 0.820] |
| the AI judge, for reference (S15) | [27/30](../../../bern/ideation2/spikes/s15-judgecheck/results.json) [0.74, 0.97] | — |

Split: pre-registered re-run (P8.2); the yes/no prompt and the 0.5 cut-off were set on these 30 items in S3 E6.

### 4 · Federal Sachbereiche vs Parliament's own Curia tags (all tags per affair)

| n = 200, submitted after the BFH model | micro-F1 | macro-F1 | top-1 is a gold tag |
|---|---|---|---|
| Apertus: 5 retrieved tagged examples + yes/no check of the top 6 | [0.654 [0.623, 0.686]](../../../bern/ideation/spikes/s5-aps/results.md#L84) | [0.570 [0.520, 0.622]](../../../bern/ideation/spikes/s5-aps/results.md#L84) | [0.865 [0.811, 0.906]](../../../bern/ideation/spikes/s3-accuracy/results.md#L27) (no examples) |
| BFH model, trained on [15,007](../../../bern/research/R1-parts/prior-art.md#L10) tagged affairs | [0.687 [0.652, 0.722]](../../../bern/ideation/spikes/s3-accuracy/results.md#L35) | [0.577 [0.525, 0.642]](../../../bern/ideation/spikes/s3-accuracy/results.md#L35) | [0.855 [0.800, 0.897]](../../../bern/ideation/spikes/s3-accuracy/results.md#L35) |

Paired micro-F1 difference Apertus − BFH: [−0.079 to +0.010](../../../bern/ideation/spikes/s5-aps/results.md#L89). Split: test n = 200; rules, τ and λ tuned on 100 dev items (tuning split). Example pool: 52,408 affairs tagged before 6 Nov 2024.

### 5 · Bern: lead directorate (8 directorates, scheme swap) vs the Grand Council's own field, titles only

| n = 200 | German title | French title | DE + FR averaged |
|---|---|---|---|
| Apertus | [0.615 [0.546, 0.680]](../../../bern/ideation/spikes/s6-cantonal/results.md#L63) | [0.645 [0.577, 0.708]](../../../bern/ideation/spikes/s6-cantonal/results.md#L64) | [0.645 [0.577, 0.708]](../../../bern/ideation/spikes/s6-cantonal/results.md#L65) |
| keyword stems | [0.520 [0.451, 0.588]](../../../bern/ideation/spikes/s6-cantonal/results.md#L66) | [0.495 [0.426, 0.564]](../../../bern/ideation/spikes/s6-cantonal/results.md#L66) | — |
| majority class | [0.175 [0.129, 0.234]](../../../bern/ideation/spikes/s6-cantonal/results.md#L67) | | |

German − French, paired: [−0.030 [−0.085, +0.025]](../../../bern/ideation/spikes/s6-cantonal/results.md#L69).

### 6 · The AI judge itself against human labels

| Test | n | AI judge (Claude, blind) | Apertus, same items |
|---|---|---|---|
| APS chapter = APS editors' chapter (S11) | 200 | [0.790 [0.728, 0.841]](../../../bern/ideation2/spikes/s11-anchor/anchor.json); second code included [0.900 [0.851, 0.934]](../../../bern/ideation2/spikes/s11-anchor/anchor.json); run A = run B [0.990 [0.964, 0.997]](../../../bern/ideation2/spikes/s11-anchor/anchor.json) | D1 [0.695 [0.628, 0.755]](../../../bern/ideation2/spikes/s11-anchor/anchor.json) · D3 [0.720 [0.654, 0.778]](../../../bern/ideation2/spikes/s11-anchor/anchor.json) |
| says yes to the 30 DVS items (S15) | 30 | [27/30](../../../bern/ideation2/spikes/s15-judgecheck/results.json) [0.740, 0.970] both runs (run B [28 of 30](../../../bern/ideation2/spikes/s15-judgecheck/results.json)) | [27/30](../../../bern/ideation2/spikes/s8-dvs/results.md#L212) |

The judge's precision on human negatives is not measured (no human negatives exist).

### 7 · Neutrality on human labels (S9, no new calls)

Language, same 1,357 affairs scored from the German vs the French text (paired): German − French [+0.017 [−0.003, +0.036]](../../../bern/ideation2/spikes/s14-neutrality/results.json), McNemar p 0.1133.

| S9 by party | D1 top-1 | keyword top-1 |
|---|---|---|
| SVP | [0.664 [0.582, 0.738], n 137](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.248 [0.183, 0.327], n 137](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| SP | [0.701 [0.629, 0.764], n 174](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.172 [0.123, 0.235], n 174](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| FDP | [0.671 [0.592, 0.742], n 146](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.178 [0.124, 0.248], n 146](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| Mitte | [0.632 [0.545, 0.711], n 125](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.144 [0.093, 0.216], n 125](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| Grüne | [0.579 [0.478, 0.673], n 95](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.200 [0.132, 0.291], n 95](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| GLP | [0.644 [0.498, 0.768], n 45](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.089 [0.035, 0.207], n 45](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| other party | [0.688 [0.514, 0.821], n 32](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.094 [0.032, 0.242], n 32](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| committee | [0.743 [0.682, 0.796], n 222](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.176 [0.131, 0.231], n 222](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| government | [0.792 [0.740, 0.836], n 274](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.237 [0.191, 0.291], n 274](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| canton | [0.730 [0.619, 0.818], n 74](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.203 [0.127, 0.308], n 74](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| unknown | [0.697 [0.527, 0.826], n 33](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.212 [0.107, 0.378], n 33](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| *test (cells n ≥ 20)* | [p 0.4655; gap SP − Grüne +0.122 [−0.007, +0.242]](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [p 0.1458; gap SVP − GLP +0.159 [+0.041, +0.262]](../../../bern/ideation2/spikes/s14-neutrality/results.json) |

| S9 by instrument | D1 top-1 | keyword top-1 |
|---|---|---|
| Motion | [0.654 [0.609, 0.696], n 459](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.181 [0.148, 0.219], n 459](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| Postulat | [0.659 [0.603, 0.711], n 296](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.142 [0.107, 0.186], n 296](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| Regierungsgeschäft | [0.792 [0.740, 0.836], n 274](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.237 [0.191, 0.291], n 274](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| Parlamentarische Initiative | [0.758 [0.701, 0.808], n 244](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.217 [0.170, 0.273], n 244](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| Standesinitiative | [0.730 [0.619, 0.818], n 74](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.203 [0.127, 0.308], n 74](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| other type | [0.400 [0.168, 0.687], n 10](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) | [0.200 [0.057, 0.510], n 10](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| *test (cells n ≥ 20)* | [p 0.0002; gap Regierungsgeschäft − Motion +0.138 [+0.069, +0.200]](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [p 0.0796; gap Regierungsgeschäft − Postulat +0.095 [+0.029, +0.159]](../../../bern/ideation2/spikes/s14-neutrality/results.json) |

Reading: no measurable difference by language or among the six main parties; government business scores higher than members' motions, and the keyword baseline shows the same order (easier texts, not a political tilt). Quality is reported per submitter type.

### 8 · Free naming without a list (rule check)

Asked to name a topic freely, Apertus answered outside both the Curia 28 and the APS label sets in [36/40](../../../bern/ideation/spikes/s3-accuracy/results.md#L116) (90% [77%, 96%]) and never answered “no topic” ([0/40](../../../bern/ideation/spikes/s3-accuracy/results.md#L116)); with the list shown, [0/40](../../../bern/ideation/spikes/s3-accuracy/results.md#L117) were off-list. Every shipped decision is a choice among listed codes.

## AI-judge rows

Gold where no official labels exist: a blind AI judge (two runs of a Claude model + a tie-break run, cross-checked by the open-weights Qwen-SEA-LION). Its agreement with human labels is in §6 above. Every figure below is agreement with that judge.

### 9 · “Digitalisierung” in Swiss parliaments, 2026 (S8, pre-registered)

Population 14,513 Swiss affairs begun 1 Jan–6 Oct 2026; 453 checked by the judge across four strata, weighted back to the population. Flag at p ≥ 0.5, fixed before the run.

| estimated, 95% interval | Querschnitt | keyword list (29 stems) | difference |
|---|---|---|---|
| precision vs the judge | [0.914 [0.876, 0.952]](../../../bern/ideation2/spikes/s8-dvs/score_ch.json) | [0.753 [0.714, 0.790]](../../../bern/ideation2/spikes/s8-dvs/score_ch.json) | [+0.161 [+0.122, +0.202]](../../../bern/ideation2/spikes/s8-dvs/score_ch.json) |
| recall vs the judge | [0.654 [0.486, 0.894]](../../../bern/ideation2/spikes/s8-dvs/score_ch.json) | [0.605 [0.451, 0.827]](../../../bern/ideation2/spikes/s8-dvs/score_ch.json) | [+0.049 [+0.017, +0.090]](../../../bern/ideation2/spikes/s8-dvs/score_ch.json) |
| affairs flagged | [653 [629, 675]](../../../bern/ideation2/spikes/s8-dvs/score_ch.json) | [734 [712, 756]](../../../bern/ideation2/spikes/s8-dvs/score_ch.json) | |
| judge = Qwen alone: precision / recall | [0.863 / 0.811](../../../bern/ideation2/spikes/s8-dvs/score_ch.json) | [0.691 / 0.729](../../../bern/ideation2/spikes/s8-dvs/score_ch.json) | |

Estimated digitalisation affairs: [913 [669, 1,217]](../../../bern/ideation2/spikes/s8-dvs/score_ch.json). Judge: run A = run B [0.976](../../../bern/ideation2/spikes/s8-dvs/score.json) (κ [0.951](../../../bern/ideation2/spikes/s8-dvs/score.json)); Qwen vs the runs κ [0.812](../../../bern/ideation2/spikes/s8-dvs/score.json) / [0.824](../../../bern/ideation2/spikes/s8-dvs/score.json).

Judge-confirmed Swiss positives in the checked sample: [190](../../../bern/ideation2/spikes/s8-dvs/score_ch.json) from [45](../../../bern/ideation2/spikes/s8-dvs/score_ch.json) parliaments — [cantonal 87, federal 62, communal 41; German 141, French 35, Italian 14](../../../bern/ideation2/spikes/s8-dvs/score_ch.json).

Per language and level (all 464 checked items incl. Liechtenstein, weighted; S14):

| S8 by language | precision | recall |
|---|---|---|
| de | [0.911 [0.866, 0.952], n 137](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.595 [0.423, 0.879], n 150](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| fr | [0.929 [0.849, 0.991], n 36](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.574 [0.282, 1.000], n 35](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| it | [0.945 [0.803, 1.000], n 13](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) | [0.895 [0.716, 1.000], n 14](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| *test (cells n ≥ 20)* | [p 0.8566; gap fr − de +0.018 [−0.078, +0.093]](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [p 0.8972; gap de − fr +0.021 [−0.500, +0.440]](../../../bern/ideation2/spikes/s14-neutrality/results.json) |

| S8 by level | precision | recall |
|---|---|---|
| federal | [0.877 [0.778, 0.961], n 57](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.444 [0.242, 0.900], n 62](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| cantonal | [0.937 [0.889, 0.978], n 80](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.724 [0.496, 0.934], n 87](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| communal | [0.908 [0.822, 0.973], n 43](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.930 [0.851, 0.984], n 41](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| other | [1.000 [1.000, 1.000], n 6](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) | [0.192 [0.039, 1.000], n 9](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| *test (cells n ≥ 20)* | [p 0.4593; gap cantonal − federal +0.059 [−0.038, +0.166]](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [p 0.1948; gap communal − federal +0.486 [+0.022, +0.692]](../../../bern/ideation2/spikes/s14-neutrality/results.json) |

| S8 by submitter party | Querschnitt precision | keyword precision |
|---|---|---|
| SVP | [0.636 [0.310, 0.929], n 11](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) | [0.417 [0.173, 0.645], n 20](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| SP | [0.943 [0.850, 1.000], n 24](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.765 [0.638, 0.874], n 38](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| FDP | [0.807 [0.565, 1.000], n 15](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) | [0.690 [0.438, 0.899], n 16](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| Mitte | [0.959 [0.859, 1.000], n 21](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.846 [0.669, 0.981], n 19](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| Grüne | [1.000 [1.000, 1.000], n 19](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) | [0.653 [0.430, 0.831], n 21](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| GLP | [0.914 [0.750, 1.000], n 15](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) | [0.928 [0.744, 1.000], n 11](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| other party | [1.000 [1.000, 1.000], n 22](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.859 [0.736, 0.956], n 29](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| party unknown | [0.975 [0.901, 1.000], n 12](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) | [0.865 [0.562, 1.000], n 7](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| government | [0.944 [0.854, 1.000], n 22](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [0.871 [0.728, 0.969], n 25](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| committee | [0.863 [0.371, 1.000], n 5](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) | [0.759 [0.306, 1.000], n 6](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| other group | [1.000 [1.000, 1.000], n 1](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) | [1.000 [1.000, 1.000], n 2](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| unknown | [0.835 [0.655, 0.967], n 19](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) | [0.683 [0.494, 0.846], n 24](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| *test (cells n ≥ 20)* | [p 0.018; gap Mitte − SP +0.016 [−0.104, +0.128]](../../../bern/ideation2/spikes/s14-neutrality/results.json) | [p 0.0212; gap SP − SVP +0.347 [+0.074, +0.623]](../../../bern/ideation2/spikes/s14-neutrality/results.json) |

The party test (p 0.018) comes from the small SVP cell (7 of 11 confirmed); keyword precision dips on the same items (7/20). Among cells with n ≥ 20 the gap is +0.016 [−0.104, +0.128]. Canton cells are below n = 20 except BS and are not read.

Per parliament (flag counts in the scored sample, [S8 results](../../../bern/ideation2/spikes/s8-dvs/results.md#L75); estimated flags point only, no per-body gold) — the ten largest:

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

### 10 · Correction loop, text input, evidence

| Test | n | Result | Same items, without |
|---|---|---|---|
| Correction loop (simulated, P8.5): 60 judge labels shown as an editor's first decisions, 4 nearest per affair | 404 | F1 [0.906](../../../bern/ideation2/spikes/s8-dvs/loop.json); Δ [+0.040 [+0.007, +0.075]](../../../bern/ideation2/spikes/s8-dvs/loop.json) | F1 [0.866](../../../bern/ideation2/spikes/s8-dvs/loop.json) |
| Submitted text added to title (S8b, federal) | 120 | precision [1.000 [0.908, 1.000]](../../../bern/ideation2/spikes/s13-timing/results.md#L33), recall [0.679 [0.548, 0.786]](../../../bern/ideation2/spikes/s13-timing/results.md#L33); Δ recall [−0.089 [−0.170, −0.020]](../../../bern/ideation2/spikes/s13-timing/s8b.json) | title only: [0.896 [0.778, 0.955], 0.768 [0.642, 0.859]](../../../bern/ideation2/spikes/s13-timing/results.md#L32) |
| Evidence: the quoted sentence supports the chapter (S12) | 120 | [0.850 [0.775, 0.903]](../../../bern/ideation2/spikes/s12-evidence/results.json); chapter right [0.902 [0.819, 0.950]](../../../bern/ideation2/spikes/s12-evidence/results.json), wrong [0.737 [0.580, 0.850]](../../../bern/ideation2/spikes/s12-evidence/results.json) | exact-substring check [120/120](../../../bern/ideation2/spikes/s12-evidence/results.json) |

The loop row is unweighted and on a sample that over-represents flagged affairs; text makes the model stricter, not more complete.

### 11 · APS chapter, cantonal and communal (S6, cross-checked S7)

| cell | top-1 vs the judge | n |
|---|---|---|
| all | [0.686 [0.609, 0.754]](../../../bern/ideation/spikes/s6-cantonal/score.json) | [153](../../../bern/ideation/spikes/s6-cantonal/score.json) |
| cantonal | [0.726 [0.629, 0.806]](../../../bern/ideation/spikes/s6-cantonal/score.json) | [95](../../../bern/ideation/spikes/s6-cantonal/score.json) |
| communal | [0.621 [0.492, 0.734]](../../../bern/ideation/spikes/s6-cantonal/score.json) | [58](../../../bern/ideation/spikes/s6-cantonal/score.json) |
| German | [0.672 [0.553, 0.772]](../../../bern/ideation/spikes/s6-cantonal/score.json) | [67](../../../bern/ideation/spikes/s6-cantonal/score.json) |
| French | [0.708 [0.568, 0.818]](../../../bern/ideation/spikes/s6-cantonal/score.json) | [48](../../../bern/ideation/spikes/s6-cantonal/score.json) |
| Italian | [0.684 [0.525, 0.809]](../../../bern/ideation/spikes/s6-cantonal/score.json) | [38](../../../bern/ideation/spikes/s6-cantonal/score.json) |
| with text | [0.708 [0.622, 0.782]](../../../bern/ideation/spikes/s6-cantonal/score.json) | [120](../../../bern/ideation/spikes/s6-cantonal/score.json) |
| title only | [0.606 [0.437, 0.753]](../../../bern/ideation/spikes/s6-cantonal/score.json) | [33](../../../bern/ideation/spikes/s6-cantonal/score.json) |
| first reading p ≥ 0.9 | [0.742 [0.642, 0.821]](../../../bern/ideation/spikes/s6-cantonal/score.json) | [89](../../../bern/ideation/spikes/s6-cantonal/score.json) |
| the two readings disagree | [0.543 [0.382, 0.695]](../../../bern/ideation/spikes/s6-cantonal/score.json) | [35](../../../bern/ideation/spikes/s6-cantonal/score.json) |
| gold = majority of Claude ×2 + Qwen | [0.684 [0.607, 0.751]](../../../bern/ideation/spikes/s7-crossfamily/score.json) | [158](../../../bern/ideation/spikes/s7-crossfamily/score.json) |

| S6 by canton | top-1 |
|---|---|
| TI | [0.684 [0.525, 0.809], n 38](../../../bern/ideation2/spikes/s14-neutrality/results.json) |
| JU | [0.556 [0.337, 0.754], n 18](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| ZH | [0.714 [0.454, 0.883], n 14](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| AG | [0.400 [0.168, 0.687], n 10](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| VD | [0.700 [0.397, 0.892], n 10](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| SG | [0.778 [0.453, 0.937], n 9](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| VS | [0.889 [0.565, 0.980], n 9](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| GE | [0.667 [0.300, 0.903], n 6](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| TG | [0.500 [0.188, 0.812], n 6](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| BE | [0.800 [0.376, 0.964], n 5](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| BL | [0.600 [0.231, 0.882], n 5](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| LU | [1.000 [0.566, 1.000], n 5](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| SO | [1.000 [0.566, 1.000], n 5](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| FR | [0.750 [0.301, 0.954], n 4](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| NE | [1.000 [0.510, 1.000], n 4](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| BS | [0.500 [0.095, 0.905], n 2](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| GR | [0.000 [0.000, 0.793], n 1](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| SZ | [1.000 [0.206, 1.000], n 1](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| ZG | [0.000 [0.000, 0.793], n 1](../../../bern/ideation2/spikes/s14-neutrality/results.json) (small) |
| *test (cells n ≥ 20)* | [p 0.3043; gap LU − AG +0.600 [+0.300, +0.900]](../../../bern/ideation2/spikes/s14-neutrality/results.json) |

### 12 · Bilingual cantons BE, FR, VS — German vs French titles (S10, pre-registered)

| n = 210 | German | French | averaged |
|---|---|---|---|
| chapter top-1 | [0.543 [0.475, 0.609]](../../../bern/ideation2/spikes/s10-bilingual/score.json) | [0.529 [0.461, 0.595]](../../../bern/ideation2/spikes/s10-bilingual/score.json) | [0.552 [0.485, 0.618]](../../../bern/ideation2/spikes/s10-bilingual/score.json) |
| gold in top 3 | [0.771](../../../bern/ideation2/spikes/s10-bilingual/secondary.txt#L1) | [0.738](../../../bern/ideation2/spikes/s10-bilingual/secondary.txt#L1) | [0.810](../../../bern/ideation2/spikes/s10-bilingual/secondary.txt#L1) |
| BE | [0.571 [0.455, 0.681]](../../../bern/ideation2/spikes/s10-bilingual/score.json) | [0.543 [0.427, 0.654]](../../../bern/ideation2/spikes/s10-bilingual/score.json) | [0.529 [0.413, 0.641]](../../../bern/ideation2/spikes/s10-bilingual/score.json) |
| FR | [0.529 [0.413, 0.641]](../../../bern/ideation2/spikes/s10-bilingual/score.json) | [0.543 [0.427, 0.654]](../../../bern/ideation2/spikes/s10-bilingual/score.json) | [0.571 [0.455, 0.681]](../../../bern/ideation2/spikes/s10-bilingual/score.json) |
| VS | [0.529 [0.413, 0.641]](../../../bern/ideation2/spikes/s10-bilingual/score.json) | [0.500 [0.386, 0.614]](../../../bern/ideation2/spikes/s10-bilingual/score.json) | [0.557 [0.441, 0.668]](../../../bern/ideation2/spikes/s10-bilingual/score.json) |

German − French [+0.014 [−0.043, +0.076]](../../../bern/ideation2/spikes/s10-bilingual/score.json) (paired; no measurable gap at n = 210). The two languages agree on [70.5%](../../../bern/ideation2/spikes/s10-bilingual/score.json): chapter right [0.622 [0.541, 0.696]](../../../bern/ideation2/spikes/s10-bilingual/score.json); where they disagree, German [0.355 [0.247, 0.479]](../../../bern/ideation2/spikes/s10-bilingual/score.json), French [0.306 [0.206, 0.430]](../../../bern/ideation2/spikes/s10-bilingual/score.json) — that third goes to a person. Clerk load: [0.2975 × weekly volume (median 10.0, mean 25.5, p90 76.7) = 3.0 / 7.6 / 22.8 a week](../../../bern/ideation2/spikes/s10-bilingual/results.md#L79).

## Limits

- Recall for “Digitalisierung” on titles is 0.654 [0.486, 0.894] against the judge; most of the interval comes from 4 judge positives among 180 checked affairs that neither method flagged. The 30 DVS items are the human recall check; the yes/no prompt and the 0.5 cut-off were set on those same items (S3), so a held-out human recall test is the partner's full list (`make eval GOLD=…`).
- APS subtopics reach 0.521 top-1 end to end and ship as ranked suggestions.
- Short, title-only cantonal and communal affairs are the hardest input (0.543 / 0.529 on bilingual titles; S6 0.606 title-only vs 0.708 with text).
- On the Federal Parliament's own multi-tag task the trained BFH model is ahead (micro-F1 0.687 vs 0.654, paired −0.079 to +0.010); the Curia design was tuned on 100 dev items.
- Where no official labels exist, the gold is the AI judge. It matches APS editors on 0.790 [0.728, 0.841] of chapters and says yes to 27/30 DVS items; its two Claude runs are close to one judge (0.99 agreement), and its precision on human negatives is not measured.
- All Apertus rows come from one served build; cut-offs and recalibration are refitted per build. ECE intervals are not computed yet.

## To measure

- Basel-Stadt oracle (2,437 hand-tagged motions) as human cantonal gold
- FR/IT rows with the headline Curia design + BFH on the same items
- municipal slice grown to ~200
- read-back combined with examples (D1 × D3) on the S9 items
- recalibration refit on the build that serves at the event
- S8 estimates recomputed on the full 2026 census (the census run had scored 8,139 affairs when it was paused)
- ECE intervals (bootstrap)
- judge precision on human negatives
- Romansh
