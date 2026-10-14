# S9: APS extended held-out (federal), status: interim

Generated 2026-10-13T21:21:53Z by `scripts/analyze.py` + `scripts/render_md.py`; numbers in `results.json`. Tags `bern2-s9-*`, spend **USD 0.9914** (pai.py ledger, list price; cap 5.00): bern2-s9-d0a 0.2188, bern2-s9-d0b 0.2188, bern2-s9-d1 0.0932, bern2-s9-d2fr 0.2140, bern2-s9-d3m 0.2434, bern2-s9-verify 0.0032.

## Setup
- **Set:** APS process captures joined to OPD CHE by Curia number in the slug (S2 method), ideation-1 298 pages and their affairs excluded. Items built so far: 1357 (periods {'2020+': 883, '2010-19': 446, 'pre-2010': 28}; join {'aps_link_in_page': 934, 'geschaeftsnr_on_page': 387, 'slug_only': 36}; 22 of 24 chapters present; main subtopic among the 190: 1221). Curia DE text on 1355, FR text on 1355.
- **Route/build:** `swiss-ai/apertus-v1.5-8b` via ideation2 `lib/pai.py`, S5 request shape (no system message, JSON-key prefill, `continue_final_message`, `max_tokens=1`, `top_logprobs=20`).
  Rows by phase/model/fingerprint: d0a 1357× vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840; d0b 1357× vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840; d1 1357× vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840; d2fr 1357× vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840; d3m 1357× vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840. Off-build rows: 0.
  Min code mass in top-20 per phase: {'d0a': 0.99827, 'd0b': 0.99651, 'd1': 0.99773, 'd2fr': 0.99689, 'd3m': 0.99809}. Mean prompt tokens per call: {'d0a': 1612.9, 'd0b': 1612.9, 'd1': 686.2, 'd2fr': 1577.7, 'd3m': 1794.7}.
- **Reuse check (20 of the ideation-1 297, identity order):** payload bytes POSTed by pai equal S5's payload for **20/20**; p reproduces S5 raw q1a within 1e-3 for **16/20** (max abs diff 0.2059; top-1 equal 19/20), same fingerprint `vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840`. The 4 deviating items show serving-side numerical drift on identical bytes and build (not a code difference); the one top-1 flip is a near tie (0.47 vs 0.53).
- **n per design** (items with all calls of that design): {'D0': 1357, 'D1': 1357, 'D2': 1357, 'D3': 1357}.

## Primary: chapter accuracy and paired difference vs D0 (H9.1–H9.3)
| Design | n | top-1 [95% CI] | top-3 [CI] | D0 top-1 same items | Δ top-1 vs D0 [paired 95%] | Δ top-3 [paired] | gain/loss | wins |
|---|---|---|---|---|---|---|---|---|
| D0 (v14: L1 (c), 2 orders, geo) | 1357 | 0.655 [0.629, 0.680] | 0.839 [0.819, 0.858] | — | — | — | — | — |
| D1 | 1357 | 0.704 [0.679, 0.727] | 0.843 [0.823, 0.861] | 0.655 | +0.049 [0.032, 0.066] | +0.004 [-0.007, 0.015] | 101/35 | yes |
| D2 | 1357 | 0.634 [0.609, 0.660] | 0.853 [0.834, 0.871] | 0.655 | -0.021 [-0.037, -0.004] | +0.014 [0.002, 0.026] | 54/82 | no |
| D3 | 1357 | 0.722 [0.698, 0.745] | 0.875 [0.856, 0.891] | 0.655 | +0.067 [0.049, 0.085] | +0.035 [0.022, 0.049] | 132/41 | yes |

Winners (paired interval excludes 0, positive): ['D1', 'D3']. Best Δ among D1–D3: D3.
On the 1357 items with all four designs: D0 top-1 0.655; D1 top-1 0.704; D2 top-1 0.634; D3 top-1 0.722.

## Baselines (same items as D0)
- Majority chapter (Rechtsordnung): top-1 0.080 [0.066, 0.095], n = 1357.
- Keyword (APS subtopic-name content words ≥5 chars, DE; `data/keywords_frozen.json`, frozen 2026-10-13T18:12:02Z before any scoring, sha256 76a35eb3d8a9…): top-1 0.192 [0.172, 0.213], n = 1357; 6 items with no keyword match (→ majority).

## Subtopic end to end (main subtopic among the 190)
Gold chapter inside the D1 shortlist: 1127/1357 = 0.831 [0.810, 0.850] (all D1 items).

| Pipeline | n | subtopic top-1 [CI] | subtopic top-3 [CI] |
|---|---|---|---|
| D1 (joint L2 x D0-arith prior, beta=1) [pre-registered pipeline] | 1221 | 0.521 [0.493, 0.549] | 0.677 [0.651, 0.703] |
| joint L2 alone (no prior) [derived] | 1221 | 0.527 [0.499, 0.554] | 0.676 [0.650, 0.702] |
| D0 chapter top-1 -> best joint-L2 subtopic within it [derived] | 1221 | 0.469 [0.441, 0.497] | 0.602 [0.574, 0.629] |
| joint L2 x D2 chapter vector [derived, exploratory] | 1221 | 0.523 [0.495, 0.551] | 0.674 [0.647, 0.700] |
| joint L2 x D3 chapter vector [derived, exploratory] | 1221 | 0.527 [0.499, 0.554] | 0.674 [0.647, 0.700] |

## Strata (chapter top-1)

**D0**

| Stratum | n | top-1 [CI] | top-3 [CI] |
|---|---|---|---|
| pre-2010 | 28 | 0.679 [0.493, 0.821] | 0.857 [0.685, 0.943] |
| 2010-19 | 446 | 0.646 [0.600, 0.689] | 0.818 [0.780, 0.851] |
| 2020+ | 883 | 0.659 [0.627, 0.690] | 0.849 [0.824, 0.871] |
| join strong | 1321 | 0.658 [0.632, 0.683] | 0.840 [0.820, 0.859] |
| join slug_only | 36 | 0.556 [0.396, 0.705] | 0.806 [0.650, 0.902] |

**D3**

| Stratum | n | top-1 [CI] | top-3 [CI] |
|---|---|---|---|
| pre-2010 | 28 | 0.679 [0.493, 0.821] | 0.893 [0.728, 0.963] |
| 2010-19 | 446 | 0.697 [0.653, 0.738] | 0.845 [0.809, 0.876] |
| 2020+ | 883 | 0.736 [0.706, 0.764] | 0.889 [0.867, 0.908] |
| join strong | 1321 | 0.725 [0.701, 0.749] | 0.874 [0.855, 0.891] |
| join slug_only | 36 | 0.611 [0.449, 0.752] | 0.889 [0.747, 0.956] |

## Lanes (D0 identity vs permuted order top-1 agree / disagree)
| Design | lane | n | share [CI] | precision [CI] |
|---|---|---|---|---|
| D0 | orders agree | 828 | 0.610 [0.584, 0.636] | 0.781 [0.752, 0.808] |
| D0 | orders disagree | 529 | 0.390 [0.364, 0.416] | 0.458 [0.415, 0.500] |
| D3 | orders agree | 828 | 0.610 [0.584, 0.636] | 0.813 [0.785, 0.838] |
| D3 | orders disagree | 529 | 0.390 [0.364, 0.416] | 0.580 [0.538, 0.622] |

## Reliability (top-1 confidence, 10 equal-width bins) and coverage–precision

**D0**: ECE = 0.2623

| p bin | n | mean p | accuracy [CI] |
|---|---|---|---|
| 0.0-0.1 | 0 | — | —  |
| 0.1-0.2 | 0 | — | —  |
| 0.2-0.3 | 4 | 0.262 | 0.250 [0.046, 0.699] |
| 0.3-0.4 | 16 | 0.369 | 0.188 [0.066, 0.430] |
| 0.4-0.5 | 29 | 0.463 | 0.379 [0.227, 0.560] |
| 0.5-0.6 | 47 | 0.554 | 0.447 [0.314, 0.588] |
| 0.6-0.7 | 64 | 0.650 | 0.344 [0.239, 0.466] |
| 0.7-0.8 | 63 | 0.754 | 0.349 [0.243, 0.472] |
| 0.8-0.9 | 91 | 0.850 | 0.472 [0.373, 0.574] |
| 0.9-1.0 | 1043 | 0.990 | 0.734 [0.707, 0.760] |

| coverage | n | p threshold | precision [CI] |
|---|---|---|---|
| 50% | 678 | 0.997 | 0.838 [0.808, 0.864] |
| 70% | 950 | 0.956 | 0.768 [0.741, 0.794] |
| 90% | 1221 | 0.666 | 0.685 [0.659, 0.711] |
| 100% | 1357 | 0.247 | 0.655 [0.629, 0.680] |

**D3**: ECE = 0.2212

| p bin | n | mean p | accuracy [CI] |
|---|---|---|---|
| 0.0-0.1 | 0 | — | —  |
| 0.1-0.2 | 0 | — | —  |
| 0.2-0.3 | 1 | 0.297 | 0.000 [0.000, 0.793] |
| 0.3-0.4 | 7 | 0.375 | 0.143 [0.026, 0.513] |
| 0.4-0.5 | 17 | 0.463 | 0.235 [0.096, 0.473] |
| 0.5-0.6 | 41 | 0.550 | 0.317 [0.196, 0.470] |
| 0.6-0.7 | 43 | 0.651 | 0.419 [0.284, 0.567] |
| 0.7-0.8 | 46 | 0.763 | 0.435 [0.302, 0.578] |
| 0.8-0.9 | 70 | 0.857 | 0.400 [0.293, 0.517] |
| 0.9-1.0 | 1132 | 0.993 | 0.791 [0.767, 0.814] |

| coverage | n | p threshold | precision [CI] |
|---|---|---|---|
| 50% | 678 | 1.000 | 0.895 [0.870, 0.916] |
| 70% | 950 | 0.990 | 0.842 [0.818, 0.864] |
| 90% | 1221 | 0.780 | 0.765 [0.740, 0.788] |
| 100% | 1357 | 0.297 | 0.722 [0.698, 0.745] |

## Exploratory
- D1 × D2 combination: not computed: D1 and D2 do not both win

## Design definitions as implemented
- **D0** (v14 shipped): L1 variant (c) (24 chapter names + their APS subtopic names, codes A–Y incl. "Kein Sachthema"), identity order (`d0a`) and the S1 permutation (`d0b`), geometric mean → chapter top-1. Prompt code is S5's `q1_prompt` verbatim (`scripts/s9lib.py`).
- **D1** readback: shortlist = top-3 chapters of the D0 *arithmetic* mean (top-2 if their subtopics total > 26; S5 rule), joint L2 over their subtopics, top chapter first, 1 call (`d1`; S5 `q2_prompt` verbatim). Chapter = chapter of argmax over subtopics of p_joint(sub) × P_arith(chapter) (β = 1, as S5; the "none" option is never chosen). Run on every item (not only on items with subtopic gold) so chapter top-1 is on the same items as D0.
- **D2** language pooling: S1 FR template, FR chapter names, DE subtopic names, identity order, on the Curia FR title + text (`d2fr`); averaged as the arithmetic mean of the three probability vectors (d0a, d0b, d2fr).
- **D3** label memory: identity order with the 5 BM25-nearest gold affairs (BM25 over DE titles of the ideation-1 297 + all other S9 items, query = title ×2 + first 400 text characters, S3 `build_data.py` BM25 verbatim), each shown as "- title / → Thema: <code> (<chapter name>)" in the S3 E3 shape (`d3m`); combined with D0's permuted order by geometric mean (D0's combiner). The pool is frozen when both fetchers have finished (`data/d3_neighbours.json`), so D3 runs last.
- **Top-3 / confidence for D1:** the shortlist chapters ranked by their best product score, then the other chapters in D0-arithmetic order; confidence = share of the normalised product mass on the chosen chapter.
- **Period** = year of the Curia number (YY.NNN → 19YY for YY ≥ 90, else 20YY).
- **Keyword baseline:** frozen rule and word lists in `data/keywords_frozen.json` (+ `.sha256`), written before the first model call of S9; majority order for ties = S9 gold frequency.
- **Subtopic gold** = page's main subtopic name exactly among the 190 DE names (ideation-1 rule). FR process pages carry FR subtopic names, so they count as "no subtopic gold"; they keep their chapter gold.

## Deviations
- 2026-10-13T18:22Z: the D2 averaging ("mean of probabilities with D0's two German orders") is implemented as the mean of the three vectors, and the D3 averaging ("averaged with D0's permuted order", combiner unstated) as the geometric mean (D0's combiner). Both choices were fixed and written here before any S9 item was scored.
- 2026-10-13T18:22Z: the reuse check reproduced S5's p within 1e-3 on 16/20, not 20/20, although the request bytes and fingerprint are identical. This is serving-side drift; it is reported, and the pre-registered analysis is unchanged.

## Files
`scripts/fetch_aps.py` (Wayback, parsing copied from ideation-1 `c_aps_fetch.py`), `scripts/fetch_curia.py` (Curia OData DE+FR), `scripts/build_items.py`, `scripts/freeze_keywords.py`, `scripts/verify_s5.py`, `scripts/run.py`, `scripts/analyze.py`, `scripts/render_md.py`; data `data/aps_ext.jsonl`, `data/curia_texts_{de,fr}.jsonl`, `data/items.json`, `data/robots_log.jsonl` (web.archive.org and ws.parlament.ch robots.txt both 404 → allow all under RFC 9309); raw `raw/{d0a,d0b,d1,d2fr,d3m}.jsonl`, `raw/errors.jsonl`. APS labels are used as evaluation facts only; no APS text is redistributed.

