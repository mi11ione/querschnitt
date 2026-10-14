# S7: cross-family re-check of the S4 and S6 gold sets (13 Oct 2026)

## Setup
- Third annotator: `aisingapore/Qwen-SEA-LION-v4-32B-IT` (open weights, Qwen family), called via the budget gateway (tags `bern-s7-dvs`, `bern-s7-aps`), temperature 0, one user message per item (no system message), `full=True`.
- Prompt: the packet GUIDE with only the batch-file instructions removed (DVS scope definition verbatim; APS rules 1–6 and the full table of 24 chapters plus `0`, checked by an assert), then the single item, then a strict answer format (`Y`/`N`; one code or `0`, optionally a second code). The model saw only the packet files.
- Results: 460/460 items parsed on the first try (0 re-asks, 0 failures). The served `resp.model` matched the requested model on every call (0 rows dropped).
- Annotations and keys were read only after all calls had finished. `scripts/score.py` reuses S6's `read_ann`, `kappa`, `wilson` and `acc` and reproduces S6's 0.686 exactly.
- Files: `scripts/run.py` (calls), `scripts/score.py` (scoring), `raw/dvs.jsonl`, `raw/aps.jsonl` (raw answers, served model, cost), `score.json`.

## Set 1: DVS digitalisation (300 titles; Y vs not-Y, a Claude `?` counts as not-Y)
| Pair | Raw agreement | κ |
|---|---|---|
| Qwen vs Claude A | 296/300 = 0.987 | 0.898 |
| Qwen vs Claude B | 296/300 = 0.987 | 0.902 |
| Claude A vs B (same binarisation; S4 counted `?` as a third category: 296/300, κ 0.904) | 298/300 = 0.993 | 0.949 |

- Qwen marked 22 Y (A 20, B 22). Only Qwen said Y on T134 and T138 (B had `?` on T138). Qwen missed one item that both Claude annotators marked Y: T007, social networks and youth mental health, which Apertus also missed.
- Majority-of-3 gold differs from the S4 gold (Claude both Y) by exactly one item: T107 (re-election of the data protection officer) becomes positive.

| Gold variant | Gold n | Apertus P (tp/flags) | Apertus R | Keyword P (tp/flags) | Keyword R |
|---|---|---|---|---|---|
| Claude both Y (S4 gold) | 20 | 0.944 (17/18) | 0.850 | 0.833 (15/18) | 0.750 |
| Claude either Y | 22 | 1.000 (18/18) | 0.818 | 0.889 (16/18) | 0.727 |
| **Majority of 3 (A, B, Qwen)** | 21 | **1.000 (18/18)** | **0.857** | **0.889 (16/18)** | **0.762** |
| All 3 Y | 19 | 0.944 (17/18) | 0.895 | 0.833 (15/18) | 0.789 |
| Qwen alone | 22 | 1.000 (18/18) | 0.818 | 0.889 (16/18) | 0.727 |

- Keyword baseline: I recomputed it with the regex stored in `keyword_baseline.json` (case-insensitive) on title + long title. It gives 18 flags. S4's stored counts (21 flags, 16 tp → P 0.76, R 0.80) could not be reproduced: the same regex gives 18 flags both on the packet text and on S3's untruncated titles. The stored figures are also below Apertus. Wilson 95 % intervals at n ≈ 20 are wide (for example, Apertus recall on the majority gold is 0.857 with interval 0.65–0.95), so the Apertus–keyword gap is consistent across variants but not significant on this set alone.

## Set 2: cantonal and municipal APS chapters (160 affairs; first choice, 25 classes)
| Pair | n | Raw agreement | κ |
|---|---|---|---|
| Qwen vs Claude A / B | 160 | 0.675 / 0.694 | 0.648 / 0.668 |
| Qwen vs Claude consensus (strict, A1 = B1) | 153 | 0.699 | 0.674 |
| Qwen first choice in the Claude lenient set (overlap of A and B) | 160 | 0.775 | – |
| Claude A vs B (S6) | 160 | 0.956 | 0.952 |
| Qwen vs Apertus final | 160 | 0.625 | 0.596 |

- Qwen's most frequent departures from the Claude consensus: Verkehr → Raumplanung (4), and Institutionen → Rechtsordnung, Öffentliche Finanzen or Bildung (3, 3, 2). The first is the same confusion Apertus shows.

| Apertus final chapter vs | All | Cantonal | Municipal |
|---|---|---|---|
| (a) Claude strict consensus (S6 headline) | 0.686 (105/153) | 0.726 (69/95) | 0.621 (36/58) |
| (a′) Claude lenient (A and B sets overlap) | 0.750 (120/160) | 0.740 (74/100) | 0.767 (46/60) |
| (b) Qwen first choice | 0.625 (100/160) | 0.600 (60/100) | 0.667 (40/60) |
| (b′) Qwen set (first or second choice) | 0.688 (110/160) | 0.670 (67/100) | 0.717 (43/60) |
| **(c) Majority of 3 first choices (158 items have a majority)** | **0.684 (108/158)** | **0.714 (70/98)** | **0.633 (38/60)** |
| (d) All 3 annotators agree | 0.776 (83/107) | 0.783 (54/69) | 0.763 (29/38) |

Wilson 95 % interval for (c), all items: 0.61–0.75.

## Conclusion
The cross-family check leaves both conclusions unchanged.
- **Set 1:** Qwen agrees with each Claude annotator about as well as the two Claude annotators agree with each other (κ 0.90 vs 0.95 under the same binarisation). The majority-of-3 gold moves one item (T107), and that move favours Apertus: precision 18/18 and recall 0.86. Apertus beats the stored-regex keyword baseline on precision and recall under every gold variant (precision 0.94–1.00 vs 0.83–0.89; recall 0.82–0.90 vs 0.73–0.79).
- **Set 2:** Qwen is a much weaker match to the Claude pair (κ 0.67 against the consensus vs 0.95 between A and B). It disagrees most where the APS scheme itself is ambiguous: transport vs spatial planning, and institutions vs topic. Apertus agrees with Qwen less (0.625) than with Claude (0.686). Against the majority of the three annotators, the result is the same as S6: 0.684 overall, cantonal 0.71, municipal 0.63. The cantonal > municipal gap holds under Claude and majority gold and reverses only against Qwen alone. On the 107 items where all three annotators agree, Apertus reaches 0.776. Read the S6 figure of about 0.69 as a stable top-1 estimate under a cross-family gold, not as an artefact of Claude-only labelling. One discrepancy remains open: the stored S4 keyword counts (21/16) cannot be reproduced from the stored regex.

## Spend and processes
- Spend: `bern-s7-dvs` USD 0.018, `bern-s7-aps` USD 0.108, plus a 1-call probe (`bern-s7-probe`, about USD 0.00001). **Total about USD 0.13 of the USD 1.00 cap.** gw.py was not modified, and the gateway was the only network access.
- All `run.py` workers have exited; `pgrep -f run.py` finds none.
