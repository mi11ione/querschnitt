# S5: APS chapter/subtopic design, language pooling, multi-label verification

Run 13 Oct 2026, 14:48–15:52 UTC, tags `bern-s5-*`. **Spend: USD 0.294** (4,718 calls) of the USD 2.00 cap.
**[M]** = measured here; **[D]** = derived from raw outputs with no new calls (S3 or S5), by the arithmetic stated.
Scripts: `s5lib.py`, `run.py`, `analyze_q12.py`, `analyze_q3.py`, `analyze_q4.py`. Raw: `raw/q*.jsonl`. Numbers: `q12.json`, `q3.json`, `q4.json`.

## Setup
- **Route:** `swiss-ai/apertus-v1.5-8b` via `gw.chat(full=True)` (S1's instrumented `call`), no system message, `gw.py` untouched.
- **Build:** fingerprint `…-tp8-pp2-dd237840` on **4,718/4,718** calls, with 0 cache replays. This is the S1/S3 build, so every comparison with S3 raw data stays on one build.
- **HTTP:** 4,718 × 200, plus 262 × 429, 8 URLError, 3 timeouts and 1 disconnect, all retried. 0 rows failed.
- **Request shape:** S1 M1 everywhere (single-token letter codes, JSON-key prefill, `continue_final_message`, `max_tokens=1`, `top_logprobs=20`); codes in the top 20 carried ≥ 0.995 of the mass on every call.
- **Data:** S3's inputs, unchanged: 297 unique APS-gold affairs with Curia DE title + text (`s3-accuracy/data/aps.json`); Curia clean-pool dev 100 / test 200; S3 raw `e3a`/`e3b`/`e4fra`/`e5*`.
- **CIs:** Wilson for proportions, bootstrap (1,000 resamples) for F1, paired bootstrap (2,000 resamples) for differences.

## Q1: APS chapter accuracy, 297 affairs (strong join = 281)
Variant (a) appends each chapter's APS subtopic names in parentheses, e.g. `B = Rechtsordnung (Bürgerrecht; …; Privatrecht)`.
- **FR names:** none were used. APS FR subtopic names are not on disk (R1 parsed only the FR chapter names), and every input is Curia DE, so all prompts are DE.
- **Variant (b) is identical to (a):** S3 E5 already used codes A–Y (24 chapters + "none"), so the APS prompt never had post-Z codes. There was nothing separate to run.

| Variant | Source | top-1 [95% CI] | top-2 | top-3 [CI] | top-1 in any keyword chapter | strong: top-1 / top-3 | Tok/affair |
|---|---|---|---|---|---|---|---|
| S3 E5 names, identity | S3 raw | 0.566 [0.509, 0.621] | 0.684 | 0.744 | 0.714 | 0.577 / 0.747 | 649 |
| S3 E5 names, 2-order avg (geo) = **baseline** | S3 raw | 0.606 [0.549, 0.660] | 0.731 | 0.805 [0.756, 0.846] | 0.758 | 0.619 / 0.797 | 1,298 |
| (a) names + subtopics, identity | [M] | 0.650 [0.594, 0.702] | 0.747 | 0.805 | 0.798 | 0.658 / 0.804 | 1,605 |
| (a) names + subtopics, permuted (S1 order) | [M] | 0.653 [0.597, 0.705] | 0.764 | 0.808 | 0.795 | 0.665 / 0.808 | 1,605 |
| **(c) 2-order avg of (a), arithmetic** | [D] | 0.677 [0.622, 0.727] | **0.818** | **0.875 [0.833, 0.908]** | 0.832 | 0.687 / 0.879 | 3,210 |
| (c) 2-order avg of (a), geometric | [D] | **0.694 [0.639, 0.743]** | 0.811 | 0.852 | 0.835 | 0.698 / 0.854 | 3,210 |

- **Paired Δ top-1 vs baseline:** (c) arithmetic +0.071 [+0.024, +0.118]; (c) geometric +0.088 [+0.037, +0.138]; (a) single order +0.044 [−0.013, +0.104] (n.s.).
- **Subtopic descriptions help one order as much as two orders of names alone.** A single (a) call (0.65) is level with or above the 2-call names baseline (0.61).
- **Order stability is unchanged:** id and permuted agree on 195/297 here, against 196/297 for names only.
- **Remaining confusions** under (c): Wirtschaftspolitik → Rechtsordnung 6, Energie → Umweltschutz 6, Soziale Gruppen → Rechtsordnung 5, Sozialversicherungen → Gesundheit 4.
- **Recommended:** (c) chapter names + subtopic names, 2 orders. Use the arithmetic average for the top-3 shortlist (0.875) and the geometric for a stand-alone top-1 (0.694). For the final chapter, see Q2.

## Q2: joint L2 over the subtopics of the top-3/top-2 chapters, 262 affairs (main subtopic in the 190)
- **Shortlist** from Q1 (c) arithmetic: top-3 chapters when their subtopics total ≤ 26 (186 affairs), else top-2 (76); 21.9 options on average plus "Keines dieser Unterthemen passt", grouped under chapter headings. The gold chapter is in the shortlist for 227/262 = 0.866 [0.820, 0.902], which caps the result.
- **Orders:** order a lists the chapter blocks in L1 order (top chapter first); order b reverses them.
- **How the comparison rows work:** the "within top chapter" rows reuse S3's L2-given-true-chapter run (`e5t`). With a correct chapter the prompt is identical; with a wrong chapter the subtopic is wrong by construction.

| Design | Source | Calls | End-to-end subtopic acc [CI] | Chapter top-1 (derived from the subtopic) [CI] | Tok/affair |
|---|---|---|---|---|---|
| S3: L1 names 2-order → L2 within top chapter | S3 | 3 | 0.435 [0.376, 0.496] | 0.611 | 1,831 |
| Q1 (c) arith → L2 within top chapter | [D] | 3 | 0.511 [0.451, 0.571] | 0.691 | 3,743 |
| Q1 (c) geo → L2 within top chapter | [D] | 3 | 0.527 [0.466, 0.586] | 0.706 | 3,743 |
| **Q1 (c) → joint L2, order a (top chapter first)** | [M] | 3 | **0.538 [0.478, 0.598]** | **0.760 [0.704, 0.807]** | 3,889 |
| Q1 (c) → joint L2, order b (reversed) | [M] | 3 | 0.469 [0.410, 0.530] | 0.714 | 3,889 |
| Q1 (c) → joint L2, average of a + b | [D] | 4 | 0.542 [0.481, 0.601] | 0.737 | 4,568 |
| joint a × L1 prior (p_sub · p_ch^β, β = 1, fixed) | [D] | 3 | 0.534 | 0.775 [0.720, 0.821] | 3,889 |

- **Joint (a) vs S3's 0.435:** paired Δ **+0.103 [+0.042, +0.172]**. Most of it comes from the better L1: against within-top-chapter on the same L1, Δ +0.027 [−0.023, +0.084] (n.s.).
- **The joint step raises the chapter accuracy:** the chapter implied by the chosen subtopic is right on 0.760, against 0.691 for L1 top-1 on the same 262 affairs.
  Paired Δ +0.069 [0.000, +0.095]; 26 gained, 14 lost.
- **Order matters:** a and b agree on 172/262. Putting the top chapter last costs 0.07 ("none" wins 23× in b vs 6× in a); L1 order acts as a useful prior, and averaging both orders adds nothing (0.542).
- **Not measured:** chapter accuracy from the joint step on the 35 affairs without a subtopic in the 190 (no Q2 call was made for them).
- **Recommended:** L1 (c) 2 orders → joint L2 over the top-3/top-2 chapters, top chapter first, **1 call**. Take the chapter from the chosen subtopic, or from the β = 1 product, which is the same 3 calls with the prior applied.

## Q3: language pooling, Curia FR test set n = 186 (rule tuned on the 88 FR dev items) [D, no new calls]
Inputs are S3 `e3a` (DE, E3 memory design, identity order) and `e4fra` (FR, same design); both are on disk. DE and FR agree on top-1 for 130/186.

| Design | Calls | micro-F1 [CI] | macro-F1 | top-1 P [CI] | Dev-tuned rule | Tok/affair |
|---|---|---|---|---|---|---|
| DE only | 1 | 0.570 [0.533, 0.605] | 0.473 | 0.860 [0.803, 0.903] | thr 0.01 | 1,493 |
| FR only | 1 | 0.590 [0.552, 0.628] | 0.475 | 0.833 [0.773, 0.880] | thr 0.005 | 1,400 |
| **DE + FR, mean of probabilities** | 2 | **0.607 [0.572, 0.641]** | **0.510** | 0.860 [0.803, 0.903] | thr 0.005 | 2,893 |
| DE + FR, sum of log-probs | 2 | 0.597 [0.559, 0.631] | 0.486 | 0.849 | rel 0.01 | 2,893 |
| ref: DE 2 orders (S3 recommended) | 2 | 0.584 [0.547, 0.619] | 0.502 | 0.876 [0.821, 0.916] | thr 0.005 | 2,985 |
| DE 2 orders + FR, mean | 3 | 0.649 [0.611, 0.683] | 0.548 | 0.882 [0.827, 0.921] | rel 0.05 | 4,385 |

- **Paired Δ micro vs DE only:** DE + FR mean **+0.013 to +0.060** (significant; top-1 Δ [−0.038, +0.038], no change); DE 2 orders + FR +0.053 to +0.107.
- **DE + FR mean vs DE 2 orders**, at the same 2 calls: micro Δ [−0.008, +0.051], top-1 Δ [−0.054, +0.027]. Neither is significant.
- **Reading:** pooling languages adds label recall (the second language contributes secondary tags) but not main-label precision; permutation averaging helps the main label slightly. The 3-call combination is the best Curia micro-F1 measured so far (0.649), selected from 6 designs × 3 rules on 88 dev items (some selection optimism).
- **Recommended:** where an affair has a second official language text (federal, bilingual cantons), pool DE + FR (mean of probabilities) instead of a second DE order to gain recall. Where top-1 precision is the goal, keep the 2-order DE call. Monolingual cantonal affairs cannot pool.

## Q4: candidate verification, Curia DE test n = 200 (τ / λ tuned on the 100 dev items) [M]
- **Candidates:** the top-6 labels of S3 E3 2-order average ("none" excluded). They hold 77.1 % of the test gold tags, the recall ceiling.
- **Question:** one per candidate, in the E6 yes/no shape: "Betrifft dieses Geschäft … das Thema «X» (Beschreibung)?", A/B codes in both answer orders.
- **Volume:** 3,600 calls of 451 prompt tokens each. The two answer orders agree on 92.2 % of calls at p = 0.5.
- **Calibration:** mean p(yes) by candidate rank is 0.97 / 0.71 / 0.48 / 0.39 / 0.35 / 0.25, against gold rates of 0.88 / 0.42 / 0.22 / 0.13 / 0.13 / 0.06. The model says yes too easily, which is why the tuned τ sits at 0.99–0.999.

| Decoder | micro-F1 [CI] | macro-F1 [CI] | P / R | Labels per affair | Tok/affair (incl. E3) | USD per 1,000 |
|---|---|---|---|---|---|---|
| V1 verified: p(yes) ≥ 0.99, 2 orders | 0.622 [0.594, 0.649] | 0.558 [0.513, 0.611] | 0.60 / 0.64 | 2.53 | 8,397 | 0.84 |
| V2 E3 top-1 + verified (τ 0.999), 2 orders | 0.630 [0.601, 0.660] | 0.557 | 0.62 / 0.64 | 2.43 | 8,397 | 0.84 |
| **V3 fused: 0.9·p(yes) + 0.1·p_E3 ≥ 0.9, 2 orders** | **0.654 [0.623, 0.686]** | **0.570 [0.520, 0.622]** | 0.68 / 0.63 | 2.19 | 8,397 | 0.84 |
| **V3 fused, single answer order (yes = A)** | **0.653 [0.621, 0.685]** | 0.568 | 0.68 / 0.63 | 2.17 | 5,691 | **0.57** |
| S3 best: E3 2-order avg (thr 0.005) | 0.585 [0.551, 0.620] | 0.511 [0.464, 0.561] | 0.59 / 0.59 | 2.36 | 2,985 | 0.30 |
| BFH Omikuji thr 0.25 | 0.687 [0.652, 0.722] | 0.577 [0.525, 0.642] | 0.73 / 0.65 | 2.08 | — | — |

- **Paired Δ, V3 (2 orders):** vs S3 best micro **+0.039 to +0.098**, macro +0.012 to +0.097 (both significant); vs BFH micro **−0.079 to +0.010**, macro −0.078 to +0.059 (neither significant; macro level, 0.570 vs 0.577).
- **Selection caveat:** 5 decoders tuned on dev, λ = 0.9 on the grid edge. **One answer order is enough:** V3 single order 0.653 for 6 calls instead of 12.
- **Recommended:** E3 2 orders → verify the top-6 with one yes/no call each → fused score. It is the first Apertus design whose gap to BFH on Curia is not significant.
  Use it where recall matters (tag suggestions); for top-1 only, E3 alone is enough.

## Cost per 1,000 affairs [M tokens; USD D at USD 0.10 per 1M prompt + 0.20 per 1M completion]
| Design | Calls/affair | Prompt tok/affair | USD per 1,000 |
|---|---|---|---|
| APS L1, names, 2 orders (S3 baseline) | 2 | 1,298 | 0.13 |
| **APS L1 (c) names + subtopics, 2 orders** | 2 | 3,210 | **0.32** |
| **APS L1 (c) + joint L2 (1 call)** | 3 | 3,889 | **0.39** |
| Curia DE + FR pooled (= cost of DE 2 orders) | 2 | 2,893 | 0.29 |
| Curia DE 2 orders + FR | 3 | 4,385 | 0.44 |
| **Curia E3 2 orders + 6 verifications (V3, 1 answer order)** | 8 | 5,691 | **0.57** |
| Curia E3 2 orders + 12 verifications (V3, 2 answer orders) | 14 | 8,397 | 0.84 |

At S1's 325,691 affairs [D]:
- APS L1 + joint L2: ≈ 1.27 B tokens ≈ **USD 127**.
- Curia V3 with 1 answer order: ≈ USD 185.
- Both are upper bounds: 44.8 % of affairs are title-only and give shorter prompts.

## Spend by tag (USD) [M]
q1a 0.048 · q1b 0.048 · q2a 0.018 · q2b 0.018 · q4a 0.082 · q4b 0.082 · **total 0.294**. Q3 made no calls.

## Caveats
- **APS gold:** single-chapter, from Wayback captures; 16 affairs are weak slug-only joins.
- **Federal only:** every input is a federal DE text, so accuracy on cantonal and communal affairs is unmeasured.
- **Small, pre-specified samples:** Q1 n = 297 and Q2 n = 262, with no tuning except the fixed β; Q3 and Q4 were tuned on 88 and 100 dev items.
- **Q2 shortlist rule:** whether to use top-3 or top-2 depended on the subtopic count (≤ 26). Shortlists with exactly 26 subtopics used lowercase `a` for "none".
- **Processes:** all `run.py` lanes and their spawned workers exited; `pgrep` shows none of mine running.
