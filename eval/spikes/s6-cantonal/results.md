# S6: cantonal and municipal level, and DE/FR parity (Bern directorates)

Run 13 Oct 2026, tags `bern-s6-*`. **Spend: USD 0.068** (789 calls) of the USD 1.50 cap.
**[M]** = measured here; **[D]** = derived from the raw outputs by the arithmetic stated. A1 has no gold yet, so it reports behaviour, not accuracy. Part B supplies the gold.
Scripts: `scripts/` (`opdtext.py`, `build_sample.py`, `s6lib.py`, `run_a1.py`, `be_scheme.py`, `run_a2.py`, `analyze.py`, `build_packet.py`, `score.py`).
Raw: `raw/a1.jsonl`, `raw/a2.jsonl`. Samples: `sample.json`, `a2_sample.json`. Numbers: `analysis.json`.

## Setup
- **Route:** `swiss-ai/apertus-v1.5-8b` via `gw.chat(full=True)`, through S1's instrumented `call`. No system message, `gw.py` untouched.
- **Build:** fingerprint `…-tp8-pp2-dd237840` on **789/789** calls, the S1/S3/S5 build. Every call is checked against it; a mismatch would have aborted the run. 2 A2 calls were cache replays (identical titles).
- **HTTP:** 787 × 200, plus 24 × 429 that were retried, with 0 failed rows.
- **Request shape:** S1 M1 everywhere (letter codes, JSON-key prefill, `max_tokens=1`, `top_logprobs=20`). Code mass in the top 20 was ≥ 0.985 on every L1 and A2 call (L2 mass not logged).
- **A1 design:** the S5 recommendation with the selective rule.
  - L1 variant (c) (chapter + subtopic names, codes A–Y, identity order); the S1-permuted second order runs **only if the first order's top p < 0.9**, then top-1 = geometric mean, shortlist = arithmetic mean.
  - Joint L2 then runs over the subtopics of the top-3 chapters (top-2 if those exceed 26 subtopics), top chapter first.
  - **Final chapter:** the chapter of the chosen subtopic. If L1 top-1 is "none", it stays none. If L2 picks "none of these", the final falls back to L1 top-1.
  - **Language:** prompts follow the affair's language, using S1's de/fr/it templates and chapter names. Subtopic names are DE in all prompts, since they are the only ones on disk. The L2 frame text was translated to FR/IT. For DE affairs both prompts are byte-identical to S5's (checked).

## A1 sample (160 affairs, begin_date ≥ 2015, disjoint from S1 except 7 Lausanne texts)
| Level | n | Bodies | de / fr / it | With text / title-only |
|---|---|---|---|---|
| Cantonal | 100 | 19 (SG SO ZH LU TG VS JU FR TI + BS AG BL BE ZG GR SZ GE VD NE) | 44 / 34 / 22 | 82 / 18 |
| Municipal | 60 | 23 (Aarau, Adliswil, Lausanne, Bellinzona, Locarno, Zürich, Bern, Genève, Lugano, …) | 28 / 15 / 17 | 45 / 15 |

- **Input:** title, plus the long title (≤ 400 chars), plus the first 1,500 chars of the text (S1 `affair_block`).
- **Title-only (33, flagged):** affairs with neither a substantive `texts` row nor an ok document in the OPD census.
- **What the on-disk texts are [M]:** since 2015 they are almost all **executive replies** ("Antwort des Regierungsrates", "Risposta del CdS/Municipio", "Réponse de la Municipalité").
  - 2,582 on-disk affairs, only 9 cantons and 10 municipalities. **Rule applied:** use a non-answer document if one exists (39 items). Otherwise use a reply only if its first 1,500 chars name the instrument and contain ≥ half of the title's long words (88 items, `text_kind=answer-doc-restating`); replies failing that test (answer-only) were skipped.
  - **Why the extra bodies are title-only:** the on-disk text covers too few bodies to reach ≥ 12 cantonal ones, so 10 cantons and 13 municipalities enter only through title-only items.

## A1 results [M]
| Stratum | n | 2nd order run (top p < 0.9) | Orders disagree | Abstain* [95% CI] | L1 top p < 0.5 | Final = none | Prompt tok/affair | Calls/affair |
|---|---|---|---|---|---|---|---|---|
| **All** | 160 | 0.431 | 0.237 | **0.237 [0.178, 0.309]** | 12 | 8 | 3,009 | 2.43 |
| Cantonal | 100 | 0.400 | 0.200 | 0.200 [0.133, 0.289] | 6 | 6 | 2,957 | 2.40 |
| Municipal | 60 | 0.483 | 0.300 | 0.300 [0.199, 0.425] | 6 | 2 | 3,095 | 2.48 |
| de | 72 | 0.403 | 0.208 | 0.208 [0.131, 0.316] | 1 | 5 | 2,970 | 2.40 |
| fr | 49 | 0.408 | 0.204 | 0.204 [0.115, 0.336] | 4 | 2 | 2,772 | 2.41 |
| it | 39 | 0.513 | 0.333 | 0.333 [0.206, 0.490] | 7 | 1 | 3,377 | 2.51 |
| With text | 127 | 0.449 | 0.260 | 0.260 | 11 | 7 | 3,234 | 2.45 |
| Title-only | 33 | 0.364 | 0.152 | 0.152 | 1 | 1 | 2,141 | 2.36 |
| *Ref: S5 federal DE (Curia text), 297* | | *0.256* | *0.162* | *0.162* | | | | |

\*Abstain = the two L1 orders disagree on top-1. Every affair with L1 top p < 0.5 also had disagreeing orders, so this flag covers both signals.

- **Confidence is lower than on federal affairs:** the second order is needed 1.7× as often as on S5's federal set (0.43 vs 0.26), and disagreement is 0.24 vs 0.16.
  - **Hardest strata:** municipal and Italian (longest inputs: TI letterheads fill the 1,500 chars). **Title-only** affairs are *more* confident than texts; that is not evidence of accuracy, and Part B will test it.
- **Median L1 top-1 p:** 0.985 overall (cantonal 0.989, municipal 0.974). Joint L2 pick p < 0.5 on 14/160.
- **Joint L2 effect:** it changed the L1 top-1 chapter on **21/160** (13 %) and picked "none of these subtopics" on 15.
- **Final chapter distribution, all 160:** 1.6.3 Raumplanung 19 · 1.1.3 Institutionen 17 · 1.6.4 Umweltschutz 15 · 1.6.2 Verkehr 13 · 1.8.1 Bildung 13 · 1.5 Öff. Finanzen 10 · 1.6.1 Energie 9 · 1.7.4 Soz. Gruppen 9 · 1.7.2 Gesundheit 8 · 1.1.2 Rechtsordnung 8 · none 8 · 1.4.3 Landwirtschaft 6 · 1.1.4 Föderativer Aufbau 6 · 1.7.3 Sozialvers. 5 · 1.7.1 Bev./Arbeit 4 · 1.8.3 Medien 3. Seven more chapters have 1 each, and 2.0.1 Parteien has 0.
  - **Cantonal top 3:** Institutionen 15, Bildung 10, Raumplanung 8. **Municipal top 4:** Raumplanung 11, Verkehr 8, Umweltschutz 8, Öff. Finanzen 7. This is the local-politics profile one would expect, but it is unverified.
- **The 8 "none" picks** include 2 that are clearly procedural (a question-time protocol, approval of council minutes). The other 6 are substantive, e.g. "Baueinsprachen: Mehr Transparenz", "Déménagement ORP Monthey", "Nouveau bâtiment HFR", the TI parking question and a cancelled Christmas market. They are candidate errors for Part B to confirm.

## A2: Bern directorates as a scheme swap (200 Grand Council affairs) [M]
- **Sample:** a simple random draw (seeded) from 4,530 eligible affairs (`geschaeft_nr`/submission year ≥ 2015, DE + FR titles, lead in the 8 directorates; GR/blank/JL excluded).
  - Lead counts: BVD 35, GSI 31, SID 28, BKD 23, WEU 23, DIJ 23, STA 20, FIN 17. Types: Motion 89, Interpellation 53, Kreditgeschäft 17, others 41.
- **Scheme:** 8 directorates, each with a one-line remit (DE and FR), plus "none", as codes A–I in one fixed order (alphabetical by DE abbreviation).
  - **The remits were written by the agent from general knowledge of the post-2020 Bern administration** (`scripts/be_scheme.py`). They are not an official text.
- **Inputs and baselines:** the model sees the title only, DE and FR separately, each with a prompt in its own language. The keyword stems (de/fr per directorate) were frozen in `be_scheme.py` before any result existed.

| Method | Accuracy vs lead directorate [95% CI] |
|---|---|
| **Apertus, DE title** | **0.615 [0.546, 0.680]** |
| **Apertus, FR title (FR prompt)** | **0.645 [0.577, 0.708]** |
| Apertus, DE + FR pooled (mean of probabilities) | 0.645 [0.577, 0.708] |
| Keyword stems, DE / FR | 0.520 [0.451, 0.588] / 0.495 [0.426, 0.564] |
| Majority class (BVD) | 0.175 [0.129, 0.234] |

- **DE/FR parity gap (DE − FR): −0.030, paired bootstrap [−0.085, +0.025], n.s.**
  - DE-only correct 13, FR-only correct 19. FR is not worse than DE on this task.
- **DE–FR top-1 agreement: 153/200 = 0.765 [0.702, 0.818].**
  - When both languages agree, accuracy is 0.719; on the 47 disagreements: DE 0.28, FR 0.40, pooled 0.40.
- **Gains from pooling and over the baselines:**
  - Pooled vs DE: +0.030 [−0.005, +0.065], n.s. Apertus DE vs keywords DE: **+0.095 [+0.025, +0.165]**. Keywords fire on 115 DE / 119 FR titles.
- **Per directorate (DE / FR correct of n):**
  - Strong: BKD 20/19 of 23; GSI 26/23 of 31; FIN 13/15 of 17; WEU 17/15 of 23. Middling: BVD 21/25 of 35. Weak: STA 9/11 of 20; SID 12/12 of 28; DIJ 5/9 of 23.
- **Main confusions:** STA → none (DE 8, FR 6); SID → GSI (6, 7); DIJ → BVD (6, 5); SID → FIN (4, 4). "none" is predicted 13× per language.
  - DIJ's remit (municipalities + spatial planning) competes with BVD/WEU on infrastructure titles.
- **Breakdowns:**
  - By period: 2015–19 DE 0.547 / FR 0.581 (n = 86); 2020+ DE 0.667 / FR 0.693 (n = 114).
    - The 2020 reorganisation is one plausible reason: the OGD file labels all years with post-2020 directorates. Not tested.
  - By type (DE/FR): Motion 0.61/0.67, Interpellation 0.66/0.59, Kreditgeschäft 0.71/0.71.

## Cost per 1,000 affairs [M tokens; USD at 0.10 per 1M prompt + 0.20 per 1M completion; equals the ledger]
| Design | Calls/affair | Prompt tok/affair | USD per 1,000 |
|---|---|---|---|
| **A1: L1 (c) selective 2nd order + joint L2**, cantonal/municipal mix | 2.43 | 3,009 | **0.30** |
| of which title-only | 2.36 | 2,141 | 0.21 |
| ref S5: L1 (c) always 2 orders + joint L2 (federal) | 3 | 3,889 | 0.39 |
| **A2: directorates, one language (title only)** | 1 | 506 | **0.05** |
| A2: DE + FR pooled | 2 | 1,012 | 0.10 |

**Selective rule savings:** the rule saves 0.57 calls per affair against always running two orders, even though cantonal and municipal affairs trigger the second order far more often than federal ones (0.43 vs 0.26).

## Spend by tag (USD) [M]
a1l1a 0.0259 · a1l1b 0.0113 · a1l2 0.0110 · a2de 0.0102 · a2fr 0.0100 · **total 0.068**

## Part B: blind annotation, pending (no annotation done by the agent)
- **Packet:** `/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s6-cantonal/packet/`. It holds `GUIDE.md` (task, output format, rules, the 24 chapters with DE subtopics + `0` = no policy topic), `items.txt` (160 blocks `C001`–`C160`, shuffled with seed 20261013) and `ann_TEMPLATE.tsv`.
  - Each block gives the parliament, the type and the exact input Apertus saw. **The guide's rules 2–6 were written by the agent:** local-to-national mapping, cantonal/municipal finance → 1.5, 1.1.3 vs 1.1.4, use of `0`, and tie-breaking.
- **Key, kept outside the packet:** `/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s6-cantonal/key.jsonl`. It maps each opaque id to the affair id, level, language and text kind, plus the Apertus final, L1 top-1/p, L1 top-3, L2 subtopic/p, order disagreement and second-order flag.
- **Annotations go to** `/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s6-cantonal/ann_A.tsv` and `ann_B.tsv` (`<id>\t<code>\t<optional second code>`).
- **Scoring:** `python3 -I scripts/score.py` writes `score.json`. It reports:
  - Cohen κ A–B on the first choice; strict gold (both agree on the first choice) and lenient gold (any overlap).
  - Apertus final top-1, L1 top-1 and L1 top-3 accuracy, by level, language, text vs title-only and abstention stratum.
  - A–Apertus and B–Apertus agreement and κ, next to A–B. The code was smoke-tested on synthetic random annotations (deleted afterwards); no real annotations exist yet.

## Caveats
- **Texts are mostly replies:** cantonal and municipal "text" items are mostly the opening of an executive reply, not the members' text. This is what OPD/disk provides since 2015, and production inputs will look the same unless the submitted text is fetched.
- **Body coverage is uneven:** text items come from 9 cantons and 10 municipalities. The other bodies are represented by title-only items only.
- **A2 is a proxy task:** it measures the lead directorate from titles, which is not topic classification. The directorate is an administrative assignment, and the remits are agent-written. A2 is therefore a measured scheme-swap and parity check, not an APS accuracy figure.
- **Processes:** all `run_a1.py`/`run_a2.py` workers exited, and `pgrep` finds none running.

## Part B — scored against two blind Claude agent annotators (lead, 13 Oct; `python3 -I scripts/score.py`)
- Annotators read only packet/ (GUIDE, items, template); A forward, B reverse order. Agreement on first choice 0.956, κ 0.952 (same model family — a cross-family relabel is planned in the build). Consensus gold: 153/160 strict (both first choices equal).
- Apertus final chapter (from the joint subtopic step) vs consensus: **0.686 overall** (n 153); cantonal 0.726 (95), municipal 0.621 (58); de 0.672, fr 0.708, it 0.684; with text 0.708, title-only 0.606. Chapter top-3 (L1): 0.837.
- Annotator vs Apertus raw agreement 0.656 / 0.675 (κ 0.63 / 0.65), below annotator–annotator 0.956.
- Abstention signal works: first order p ≥ 0.9 → 0.742 (n 89); second order needed → 0.609; the two orders disagree → 0.543 (n 35).
- Top confusions (gold → Apertus): Verkehr → Raumplanung 5, Bildung → Föderativer Aufbau 3.
