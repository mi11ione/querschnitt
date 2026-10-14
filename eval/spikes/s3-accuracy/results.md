# S3: Apertus closed-set topic accuracy vs free gold (Curia 28, APS 24, DVS) and vs the BFH baseline

Run 13 Oct 2026, 13:23–14:39 UTC, tags `bern-s3-*`. **Spend: USD 0.460** (4,561 ledger rows, 4.58 M prompt tokens).
**[M]** = measured here, **[D]** = derived by the arithmetic shown. Measurements only; nothing was built.
Scripts: `build_data.py`, `s3lib.py`, `run.py`, `analyze*.py`, `explore_*.py`, `fetch_aps_texts.py`, `probe_tok.py`. Raw: `raw/*.jsonl`. Numbers: `analysis*.json`, `hybrid.json`, `perlabel.json`, `codeslot.json`, `ensemble_bfh.json`.

## Setup
- **Route:** `swiss-ai/apertus-v1.5-8b` via `gw.chat(full=True)`, no system message. I reused S1's instrumented `call`; `gw.py` is untouched.
- **Build:** served model `swiss-ai/apertus-v1.5-8b` and fingerprint `vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840` on **4,564/4,564** rows [M]. Same build as S1, no change during the run, so no comparison mixes builds. 3 rows are gw cache replays from the same build.
- **HTTP** [M]: 4,561 × 200 and 338 × 429. 7 URLError, 3 timeouts and 1 disconnect were all retried; the one item that exhausted its retries was re-run. Throughput was about 0.5 requests/s at 8 workers (machine load ≈ 44 from other jobs, plus gw's per-call ledger scan).
- **Request shape:** S1 M1 (single request, single-token letter codes, prefill `{"sachbereich": "` with `continue_final_message`, `max_tokens=1`, `top_logprobs=20`).
  - Curia needs 29 codes (28 labels + "none"): A–Z plus Ä/Ö/Ü, each a single token (`probe_tok.py`). Label probabilities = renormalised exp(logprob) over the codes in the top 20 (mass ≥ 0.99).
- **Curia items:** 300 clean-pool affairs (submitted ≥ 2024-11-06), taken from **S2's 500 BFH items**.
  - Dev = BFH positions 0–99 (inside BFH's own dev); test = positions 150–349 (inside BFH's test). **Headline numbers are test, n = 200**; every rule, τ and α was tuned on dev.
  - Gold averages 2.38 tags per affair. Input = title + the first 1,500 chars of SubmittedText/InitialSituation + ReasonText.
- **Metrics:**
  - micro-F1; macro-F1 over the labels present in test gold (S2 convention); top-1 P = the top label is a gold tag; top-3 R = share of gold tags inside the top 3.
  - CIs: bootstrap (1,000 resamples) for F1, Wilson for proportions, paired bootstrap for differences.
- **Descriptions:** Parlamentsbibliothek sub-topics from BFH `topics_hierarchy.json` (Finanzplatz merged into Finanzwesen, Tierwelt into Umwelt, Geschichte dropped). FR/IT descriptions are our translation.

## E1–E3: Curia 28, DE, test n = 200 [M]
| Design (identity order unless stated) | Prompt tok/affair | micro-F1 [95% CI] | macro-F1 [CI] | P / R | top-1 P [CI] | top-3 R |
|---|---|---|---|---|---|---|
| E1 names, zero-shot | 581 | 0.486 [0.452, 0.518] | 0.414 [0.365, 0.459] | 0.49 / 0.48 | 0.755 [0.691, 0.809] | 0.544 |
| E1 names + descriptions | 1,290 | 0.554 [0.525, 0.583] | 0.464 [0.411, 0.512] | 0.64 / 0.49 | 0.825 [0.766, 0.871] | 0.547 |
| E2 desc, permuted order B | 1,290 | 0.511 [0.474, 0.549] | 0.421 [0.370, 0.475] | 0.54 / 0.49 | 0.820 | 0.517 |
| E2 desc, average of 2 orders (arith.) | 2,581 | 0.563 [0.527, 0.599] | 0.464 [0.405, 0.518] | 0.77 / 0.45 | 0.865 [0.811, 0.906] | 0.581 |
| E3 desc + memory k=5 | 1,493 | 0.569 [0.536, 0.603] | 0.484 [0.433, 0.534] | 0.65 / 0.50 | 0.860 [0.805, 0.901] | 0.604 |
| **E3 memory, average of 2 orders (arith.)** | 2,985 | **0.585 [0.551, 0.620]** | **0.511 [0.464, 0.561]** | 0.59 / 0.59 | **0.880 [0.828, 0.918]** | **0.642** |
| E3 memory, 2 orders (geo.) + kNN late fusion (α = 0.9) | 2,985 | 0.593 [0.560, 0.625] | 0.517 [0.460, 0.578] | 0.70 / 0.52 | 0.870 | 0.614 |
| E3 2 orders + generative list + kNN (hybrid) | 4,494 | 0.604 [0.573, 0.635] | 0.532 [0.485, 0.588] | 0.57 / 0.65 | 0.880 | — |
| Generative "all applicable codes", no memory (`e1m`, first 3) | 1,306 | 0.516 [0.482, 0.550] | 0.438 | 0.52 / 0.52 | 0.550 | — |
| Generative + memory (`e3m`, first 3) | 1,508 | 0.591 [0.558, 0.627] | 0.512 [0.461, 0.567] | 0.58 / 0.60 | 0.670 | — |
| kNN-5 memory only (BM25 titles, no LLM) | 0 | 0.449 [0.410, 0.488] | 0.375 | 0.46 / 0.44 | 0.580 | 0.483 |
| **BFH Omikuji, thr 0.25 (tuned on BFH's dev)** | — | **0.687 [0.652, 0.722]** | **0.577 [0.525, 0.642]** | 0.73 / 0.65 | 0.855 [0.800, 0.897] | 0.727 |
| BFH, best rule on our dev (top1 + thr 0.3) | — | 0.697 [0.661, 0.732] | 0.590 [0.533, 0.657] | 0.76 / 0.64 | 0.855 | 0.727 |

**Decoding:**
- M1's single softmax is peaked (median top-1 p 0.98–0.99), so the tuned rules are p ≥ τ with very low τ (0.005–0.03).
- Top-k decoding for E3 avg: top-1 0.524 (P 0.88), top-2 0.596, top-3 0.565. Top-2 is on par with the tuned rule.
- **Multi-label recall is the weakness:** the predictions hold 1.6–2.4 labels, against 2.38 in gold.

**Descriptions** add +0.07 micro-F1 and +0.07 top-1 P.

**Memory (E3)** shows 5 BM25 title neighbours with their gold tags in the prompt, drawn from 52,408 Curia-tagged affairs submitted before 2024-11-06.
- Gain: +0.015 F1 (single order) and +0.035 top-1 P, for +203 tokens.
- Memory alone (kNN-only) reaches just 0.45.

**E2, position/code bias** [M]:
- Top-1 agreement between identity order and permuted order B:
  - names + desc: **189/300 = 63.0 % [57.4, 68.3]**, rising to 78.6 % when p ≥ 0.9.
  - with memory: **235/300 = 78.3 % [73.3, 82.6]**, rising to 89.3 % when p ≥ 0.9.
- Averaging the two orders gives +2–4 points top-1 P and +0.01–0.02 F1 (CIs overlap).
- **The cause is that the three codes after Z are penalised.** Top-1 counts over 300 affairs:
  - Gesundheit 21 under `Ä` vs 40 under `T`; Staatspolitik 26 under `A` vs 0 under `Ü` (17 with memory); Europapolitik 6 under `D` vs 0 under `Ä`.
- Slot test on test items (names + desc, swapping the last three codes; `codeslot.json`):
  - `Ä Ö Ü`: 14 Gesundheit top-1, top-1 P 0.825. `1 2 3`: 13 and 0.825 (digits do not fix it). `a b c`: 19 and 0.865 (n.s.), the least bad.

## Apertus best design vs BFH on identical items (test n = 200) [M]
| | micro-F1 | macro-F1 | top-1 P | top-3 R | Precision at 70 % coverage | Paired Δ micro vs BFH 0.25 | Paired Δ macro |
|---|---|---|---|---|---|---|---|
| BFH thr 0.25 | 0.687 | 0.577 | 0.855 | 0.727 | 0.936 | — | — |
| E3 memory, 2 orders (arith.) | 0.585 | 0.511 | **0.880** | 0.642 | **0.957** | **−0.10 [−0.146, −0.055]** | −0.07 [−0.132, −0.006] |
| E3 hybrid | 0.604 | 0.532 | 0.880 | — | — | −0.08 [−0.129, −0.037] | −0.05 [−0.112, +0.022] |

- **Apertus does not beat the supervised BFH model on Curia multi-label F1.** The gap of 0.08–0.10 is significant.
- **On the main label it matches or slightly exceeds BFH:** top-1 P 0.88 vs 0.855 (CIs overlap).
- Per label (`perlabel.json`): Apertus is behind on Kultur, Steuer, Sozialer Schutz, Staatspolitik, Umwelt and Landwirtschaft, mostly the conventional secondary tags. It is ahead on Parlament and Zivilrecht, and level on Migration, Verkehr, Sicherheitspolitik and Medien.
- Ensemble BFH + Apertus: 0.699, Δ [−0.015, +0.039], so no gain.

## E4: languages (E3 design, identity order) [M]
Only affairs whose title and text are in that language.

| Language | n test | micro-F1 [CI] | macro-F1 | top-1 P [CI] | DE on same items (micro / top-1 P) | top-1 = DE | Jaccard vs DE | Tok/affair |
|---|---|---|---|---|---|---|---|---|
| FR | 186 | 0.590 [0.552, 0.628] | 0.475 | 0.833 [0.773, 0.880] | 0.570 / 0.860 | 69.9 % [63.0, 76.0] | 0.663 | 1,400 |
| IT | 121 | 0.604 [0.563, 0.643] | 0.520 | 0.893 [0.825, 0.936] | 0.560 / 0.868 | 70.2 % [61.6, 77.7] | 0.652 | 1,686 |

- FR and IT are **on par with DE**, but cross-language consistency is only about 70 % on top-1.
- Coverage: FR has real French text for 274 of the 300 items (25 are "Titre suit"). IT has Italian title and text for only 183, because Curia translates IT selectively.
- There is no BFH FR/IT baseline (S2 did not run it).

## E5: APS chapters (24 + none), 297 unique APS-gold affairs [M]
Input: Curia DE title + text (15 polite OData requests; 3 affairs are title-only). Prompt: S1 `m1_prompt` with codes A–Y.

| Variant | top-1 [CI] | top-3 [CI] | top-1 in any APS keyword chapter | Strong join (281) top-1 | Weak slug-only (16) top-1 |
|---|---|---|---|---|---|
| identity | 0.566 [0.509, 0.621] | 0.744 | 0.714 | 0.577 | 0.375 |
| permuted (S1 order) | 0.542 [0.485, 0.598] | 0.724 | 0.690 | 0.555 | 0.312 |
| **average of 2 orders** | **0.606 [0.549, 0.660]** | **0.805 [0.756, 0.846]** | 0.758 | 0.619 | 0.375 |

- The two orders agree on 196/297 = 66 % [D].
- Top confusions: Sozialversicherungen → Gesundheit (12), Soziale Gruppen → Gesundheit (7), Wirtschaftspolitik → Rechtsordnung (6), Energie → Umweltschutz (5), Institutionen → "Kein Sachthema" (5).
- **L2 given the true chapter:** **0.733 [0.676, 0.783]**, n = 262, 8.4 options on average. Strong join 0.743, weak 0.538 (n = 13).
- **L2 given the predicted chapter** (2-order average): the chapter is right on 160/262, and L2 is right on 114 of those (71 %). **End-to-end 0.435 [0.376, 0.496].**
  - No extra calls were needed: with the right chapter the prompt is identical to the true-chapter run, and with a wrong chapter the subtopic is wrong by construction.

## E6: ad-hoc topic "Digitalisierung" (2-code M1 yes/no, 2 code orders averaged, title + long title) [M]
The sets are 30 DVS positives and 300 random affairs, 10 per positive from the same body and year (BE 120, CHE 50, ZG 30, OW 30, TG 20, BS 20, ZH/AG/BL 10 each).

| p(yes) ≥ | Recall on DVS [CI] | Flag rate on random [CI] |
|---|---|---|
| 0.3 | 27/30 = 0.90 [0.74, 0.97] | 19/300 = 6.3 % [4.1, 9.7] |
| **0.5** | **27/30 = 0.90 [0.74, 0.97]** | **18/300 = 6.0 % [3.8, 9.3]** |
| 0.7 / 0.9 | 25/30 = 0.83 [0.66, 0.93] | 17/300 = 5.7 % |

- The two orders agree on 98.2 %. A single order gives recall 0.83–0.90 at a flag rate of 5.7–7.0 %. Cost: 187 tokens per order.
- Missed: "Wie weiter mit NFFS?" (BE); "Wärmeverbunde und Stromspeicher in Zonen für öffentliche Werke…" (BL); "Eine Strategie zur Bekämpfung von Desinformation" (CHE).
- Top-10 flagged random affairs, for the blind check (opd_affair_id body year: title; all p ≥ 0.99). Most read as genuinely digital by title [unverified], which would make 6 % an upper bound on false flags.
  1. 337409 BE 2026: Kantonspolizei Bern: Ausgabenbewilligung für die ICT-Grundversorgung … sowie Digitalisierung der Kantonsverwaltung · 2. 291435 ZG 2026: Schneller, näher, digital: Online-Polizeiposten der Zuger Kantonspolizei mit Videokonferenz
  3. 335267 ZG 2026: Schaffung der gesetzlichen Grundlagen für digitale Abstimmungssysteme an Gemeindeversammlungen · 4. 280520 CHE 2025: Digitalisierung der Führerausweise
  5. 335414 BE 2026: Aufbau Kompetenzzentrum BeLEARN für die digitale Transformation in der Bildung; Objektkredit 2027–2028 · 6. 335666 ZH 2026: Cyberbedrohung – wie schützt sich der Kanton Zürich
  7. 235277 CHE 2024: Einsatz Quantum Safe/quantensichere Kryptografie beim Bund · 8. 337093 BE 2026: Ausgabenbewilligung für die ICT-Ausgaben der Direktion für Inneres und Justiz (DIJ). Rahmenkredit 2027-2029
  9. 338773 BE 2026: Künstliche Intelligenz in der Kantonsverwaltung: Von Pilotprojekten zu messbaren Einsparungen · 10. 45382 BS 2020: Vertrauen durch Transparenz über Einwohnerdaten – Einführung eines "Reversed Big Brother Principle"
- **Free generation** (40 test affairs, DE):
  - With no list, **36/40 = 90 % [77, 96] of answers fall outside both the Curia 28 and the APS 24 + 190 sets**, and **0/40 say "kein Thema"**. Examples: "Energie-Contracting", "Tiefseebergbau", "KI-Sicherheit".
  - With the Curia list shown, 0/40 fall outside it, and 35/40 name one of the gold tags.

## E7: abstention, coverage vs top-1 precision (test n = 200) [M]
| Coverage | E1 desc: prec (p_min) | E3 memory id: prec (p_min) | E3 2 orders: prec (p_min) | BFH: prec (score_min) |
|---|---|---|---|---|
| 100 % | 0.825 | 0.860 | 0.880 [0.828, 0.918] | 0.855 |
| 90 % | 0.856 (0.56) | 0.889 (0.62) | 0.906 (0.52) | 0.883 (0.41) |
| 80 % | 0.881 (0.73) | 0.900 (0.77) | 0.931 (0.62) | 0.912 (0.61) |
| 70 % | 0.929 (0.84) | 0.943 (0.91) | **0.957 (0.80)** [0.910, 0.980] | 0.936 (0.76) |
| 60 % | 0.975 (0.92) | 0.967 (0.97) | 0.975 (0.87) | 0.950 (0.85) |
| 50 % | 0.990 (0.98) | 0.960 (0.99) | 0.990 (0.97) | 0.950 (0.91) |

The p_min values are read off the test set; fix the production threshold on dev.

## Tokens and USD per 1,000 affairs [M tokens; USD D at USD 0.10 per 1M prompt + 0.20 per 1M completion tokens]
| Design | Requests/affair | Prompt tok/affair | USD per 1,000 |
|---|---|---|---|
| E1 names / E1 names + desc | 1 | 581 / 1,290 | 0.058 / 0.129 |
| E3 desc + memory, 1 order | 1 | 1,493 | 0.149 |
| **E3 desc + memory, 2 orders (recommended)** | 2 | 2,985 | **0.299** |
| E3 hybrid (+ generative list, ≈ 9 completion tokens) | 3 | 4,494 | 0.451 |
| E5 APS L1 with 2 orders + L2 | 3 | 1,831 | 0.183 |
| E6 yes/no ad-hoc topic, 2 orders | 2 | 374 | 0.037 per topic |

At S1's 325,691 affairs [D]: E3 with 2 orders ≈ 972 M tokens ≈ **USD 97**; 1 order ≈ USD 49. The real cost is lower, because 44.8 % of affairs are title-only.

## Recommendation (design to build)
1. **Labels with descriptions: yes.** The largest gain: +0.07 F1 and +0.07 top-1 P, for +700 tokens.
2. **Label memory: yes, k = 5 BM25-title neighbours with their Curia tags.** It reuses the parliament's own past labels without training.
   - Gain: +0.015–0.03 F1, +0.035 top-1 P, and order stability up from 63 % to 78 %, for +200 tokens.
   - It does **not** close the multi-label gap to BFH.
3. **Permutation averaging over 2 orders: yes** for any user-facing top-1 or abstention. It adds +2–4 points top-1 P and gives an agreement flag.
   - Also drop the post-Z codes: at most 26 A–Z codes for frequent labels, with rare labels on `a b c`. This combination is untested.
4. **Decoding:**
   - Primary topic = top-1 of the 2-order average: precision 0.88, or 0.957 at 70 % coverage when abstaining below p ≈ 0.8 (calibrate on dev).
   - Secondary topics = labels with p ≥ τ (dev-tuned, about 0.005–0.05), or simply top-2. Show them as "suggested"; top-3 recall is 0.64.
   - Add the generative list only if recall matters: +0.02 F1 for +50 % cost.
5. **Where Apertus earns its place:** federal affairs already carry Curia gold, and BFH wins there on multi-label F1. Apertus is worth it for:
   - cantonal and communal affairs, which have no tags and no BFH model;
   - FR/IT, where it is on par with DE;
   - the APS scheme (top-3 0.81);
   - ad-hoc topics (DVS recall 0.90 at a 6 % flag rate, about 370 tokens per topic per affair).
   - **Never let free naming choose the topic:** 90 % of free answers fall outside every label set.

## Caveats
- Curia gold follows the Parliamentary Services' convention of about 2.4 tags, with liberal secondary tags (Staatspolitik, Wirtschaft). Part of the gap is convention, not error; the next step is a blind agent check of the disagreements.
- Samples are small: n = 200 (Curia), 297 (APS) and 30 DVS positives. τ, α and the 3 hybrid weights were tuned on 100 dev items, so the test numbers carry mild selection optimism. The permuted names-only run (E2) was skipped for throughput; E2 is measured on names + desc and on memory.
- APS comes from Wayback captures. 8 are French captures, mapped by chapter code and excluded from L2; 16 are weak slug-only joins. The APS gold is single-chapter, while 199/298 affairs carry keywords from several chapters.
- The E6 negatives are unverified and the inputs were titles only. Curia, E4 and E5 are federal only; accuracy on cantonal or communal text is unmeasured (no gold). The 0.5 req/s throughput reflects a loaded machine plus gw overhead, not a Public AI limit.

Spend by tag (USD) [M], total **0.460**:
e1n 0.018 · e1d 0.039 · e2d 0.039 · e3a 0.045 · e3b 0.045 · e1m 0.040 · e3m 0.046 · e4fra 0.038 · e4ita 0.031 · e5a 0.019 · e5b 0.019 · e5t 0.014 · e6a 0.006 · e6b 0.006 · e6f 0.004 · e1x1 0.026 · e1x2 0.026 · probe 0.0001.

Processes: all `run.py`, lane and fetch processes exited; `ps` shows none left.
