# S8 — "Digitalisierung" over 2026 OPD affairs (all bodies) — results
Model swiss-ai/apertus-v1.5-8b via ideation2/lib/pai.py; tags bern2-s8-check / -a / -b. Prompt = S3 E6 verbatim (M1: JSON-key prefill,
continue_final_message, max_tokens=1, top_logprobs=20, codes A/B). Flag = p >= 0.5 (not re-fitted). No item was read or judged by this agent.

## Step-1 check (check_dvs.py -> check_dvs.json, check_dvs_repeats.json)
- Prompt bytes for the 30 DVS items built by the S8 pipeline (language rule + OPD fields) vs S3 (dvs.json fields): 30/30 identical.
- Fresh uncached yes=A call vs S3 raw/e6a.jsonl (same fingerprint vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840, S3 run 13 Oct ~14:07 UTC):
  27/30 within 1e-3; 3 items differ: 338686 0.9399 vs 0.9526 (|d|=0.0127), 303401 0.3775 vs 0.2689 (0.1086), 253612 0.1480 vs 0.2689 (0.1209).
  Each of the 3 repeated 3x now: identical values every time (0.9399 / 0.3775 / 0.1480), so the endpoint is deterministic within a session but
  not bit-identical to S3's earlier session on the same fingerprint. No flag (p>=0.5) changes on any of the 30. The 1e-3 target is NOT met on 3/30.

## Definitions used
- Population: begin_date[:10] in 2026-01-01..2026-10-06 in affairs.ndjson.gz (6 Oct export): n = 14,790 (brief said ~14,791; 86 bodies, not 89).
  One affair (335541, Genève city) has no title in any language -> not scored (no input). The 6 DVS items outside the window are scored
  too (only for DVS recall "all 30"), never in population numbers.
- Prompt language: body `lang` (bodies.ndjson.gz) if the title in that language is non-empty, else first non-empty of de, fr, it; rm-only -> de prompt
  (did not occur). CHE and LIE have lang=null -> de first. Long title = title_long in the same language as the title.
- Level: CHE federal; canton with 2-letter key cantonal; numeric key (type city/municipality) communal; LIE other.
- Keyword: S4 regex (keyword_baseline.json, re.I) on title[:400] + long title[:400] (if different) = exactly the text the model sees.
- please-check: orders disagree (only defined where order B was run) or 0.3 <= p < 0.7.
- Strata/packet: rng = random.Random(20261014); strata in order A∩K, A only, K only, neither, each population sorted by affair id, rng.sample(min(cap,N));
  then rng.shuffle of the combined list; ids D001.. in shuffled order. loop_order.json: sorted ids shuffled with random.Random(60).

## Deviations
- 2026-10-13 18:14 UTC: packet items.txt includes a `level` column (per lead's brief); PREREG lists parliament | type | date | title | long title.
  Level is a function of the parliament (no item content), recorded here for transparency.
- 2026-10-13 18:23 UTC (lead's instruction, rate-limited shared key ~0.7-1 req/s): scoring order changed. Stopped the newest-first run at 509
  order-A rows (2026-10-01..06 complete, 2026-09-30 82/150). Then (make_order.py -> order.json, frozen): B readings for the already scored,
  the remaining 68 affairs of 2026-09-30 (so census days are whole), the 30 DVS items (for P8.2 only), then all 14,212 titled window affairs
  dated 2026-01-01..2026-09-29 in a seeded uniform random order (random.Random(20261015).shuffle of ids sorted ascending).
  Design for population estimates: census stratum C = all 577 titled affairs dated 2026-09-30..10-06 (lead's message said 2-6 Oct / 220;
  at the switch 30 Sep was partly done, so C was extended to whole days 30 Sep-6 Oct); stratum R = 14,212 affairs 1 Jan-29 Sep,
  sample = the contiguous scored prefix of the random order (n_R at the snapshot), weight N_R/n_R. DVS items scored out of order count in
  R estimates only if their rank is inside the prefix. Order B now runs right after A for the same affair (run2.py, one pool of 3 workers).
  Packet built at 20:30 UTC (lead, revised ~18:37 UTC; replaces "21:45 or >= 5,000") from that snapshot (snapshot/); runner continues toward the full census.

## Status at the packet snapshot (20:30:36 UTC)
- Wall time: first S8 model call 18:09:53 UTC (check), newest-first run from 18:11, packet snapshot 20:30:36 (2 h 21 min of model time; ~2.5 h incl. setup).
- Packet + key + loop_order are FROZEN from snapshot/ (a.jsonl/b.jsonl copies, snapshot.json). `python3 -I build.py resnap` regenerates the
  results below from snapshot/ and asserts the packet is byte-identical. Not interpreted: no flagged title was read by this agent.
- Runner run2.py keeps going in the background toward the full census (nohup; resumable; same order.json). Progress:
  `wc -l raw/a.jsonl raw/b.jsonl; tail -1 raw/throughput.jsonl; tail -2 raw/run2.log` ; live estimates: `python3 -I build.py live` -> results_live.md
  (never touches packet/key). Stop: `pkill -f "run2.py 3"`. Resume: `cd <this folder>; nohup python3 -I run2.py 3 > raw/run2.log 2>&1 &`.
  ETA full census at ~0.71 req/s: ~8,860 affairs left at 20:30 -> roughly 00:00 UTC 14 Oct (TO MEASURE). Fingerprint guard: stops and writes
  raw/foreign_fp.jsonl on any other build.
- P8.6 (3 workers, shared key with the bulk job and other spikes): 0.714 req/s overall (5,975 calls / 8,366 s), per-500 windows 0.607-0.894 req/s;
  pai seconds per call (incl. 429 backoff) p50 0.890 s, p95 31.990 s; 915 HTTP 429 responses; 442 calls needed a retry; 0 errors.

## Results (resnap, data as of 2026-10-13 20:30:36 UTC; source snapshot/)
- Window affairs (begin_date 2026-01-01..2026-10-06): 14790; titled: 14789; scored complete (A, plus B where 0.1<p_A<0.9) in window: 5932
- Order-A rows: 5938; order B needed among them: 37, B rows: 37
- Design sample: census C (2026-09-30..2026-10-06) N=n=577 (missing 0); SRS stratum R (2026-01-01..2026-09-30 excl.) N_R=14212, n_R=5338 (sampling fraction 0.3756, weight 2.662); scored affairs outside the design (DVS out-of-order, prefix gaps): 17
- Coverage: PARTIAL: estimates below are design-weighted
- Apertus flags (p>=0.5), estimated window total: 660.4 [587.5, 742.6] (census 48 + SRS 230/5338)
- Keyword flags, estimated window total: 742.2 [664.7, 829.0] (census 50 + SRS 260/5338)
- Please-check (orders disagree or 0.3<=p<0.7), estimated total: 28.6 [16.5, 51.0] (census 2 + SRS 10/5338)
- Both flags (A∩K): 501.3 [438.2, 573.9] (census 38 + SRS 174/5338); A only: 159.1 [124.9, 203.3] (census 10 + SRS 56/5338); K only: 241.0 [197.7, 294.2] (census 12 + SRS 86/5338)
- Distinct parliaments among Apertus flags in the design sample: 50 (of 86 parliaments present in the sample; of 86 in the window) — a lower bound for the window; among keyword flags: 50

### By level (estimated window totals; census + N_R,group x SRS share within group, Wilson 95%; post-stratified)
| level | N window | sample n | Apertus flags (sample) | est. flags [95%] | kw flags (sample) | est. kw [95%] |
|---|---|---|---|---|---|---|
| federal | 3162 | 1457 | 91 | 177.1 [144.9, 218.4] | 104 | 211.3 [175.0, 256.3] |
| cantonal | 7273 | 2741 | 120 | 320.1 [268.6, 381.1] | 139 | 369.7 [314.1, 434.5] |
| communal | 4077 | 1571 | 57 | 145.3 [112.4, 187.7] | 56 | 142.6 [110.1, 184.7] |
| other | 277 | 146 | 10 | 17.0 [10.0, 31.1] | 11 | 18.0 [11.0, 32.1] |

### By prompt language (estimated window totals; census + N_R,group x SRS share within group, Wilson 95%; post-stratified)
| lang | N window | sample n | Apertus flags (sample) | est. flags [95%] | kw flags (sample) | est. kw [95%] |
|---|---|---|---|---|---|---|
| de | 11160 | 4409 | 209 | 494.1 [431.8, 565.8] | 238 | 576.5 [508.4, 653.8] |
| fr | 2552 | 1075 | 54 | 129.0 [99.2, 167.8] | 56 | 126.1 [97.4, 163.9] |
| it | 1077 | 431 | 15 | 36.9 [22.5, 60.9] | 16 | 39.6 [24.5, 64.2] |

### By body (counts in the design sample; est. = census + N_R,body x SRS share within body, point only)
| body | level | N window | sample n | flags (sample) | est. flags | kw (sample) |
|---|---|---|---|---|---|---|
| CHE | federal | 3162 | 1457 | 91 | 177.1 | 104 |
| BS | cantonal | 919 | 349 | 17 | 44.8 | 23 |
| GE | cantonal | 612 | 240 | 9 | 24.2 | 10 |
| 261 | communal | 554 | 242 | 12 | 25.1 | 19 |
| VD | cantonal | 549 | 209 | 12 | 31.7 | 14 |
| TI | cantonal | 540 | 230 | 10 | 21.9 | 14 |
| BE | cantonal | 500 | 187 | 16 | 42.8 | 12 |
| BL | cantonal | 460 | 154 | 1 | 3.0 | 4 |
| ZH | cantonal | 440 | 168 | 5 | 13.1 | 7 |
| VS | cantonal | 393 | 136 | 9 | 26.0 | 10 |
| LU | cantonal | 387 | 154 | 1 | 2.5 | 6 |
| AG | cantonal | 342 | 127 | 2 | 5.4 | 2 |
| 1711 | communal | 318 | 124 | 3 | 7.7 | 1 |
| SG | cantonal | 293 | 94 | 5 | 15.8 | 4 |
| LIE | other | 277 | 146 | 10 | 17.0 | 11 |
| SO | cantonal | 268 | 88 | 5 | 15.2 | 6 |
| 351 | communal | 267 | 97 | 2 | 5.5 | 3 |
| FR | cantonal | 249 | 85 | 1 | 3.0 | 1 |
| 6621 | communal | 246 | 93 | 4 | 10.6 | 4 |
| NE | cantonal | 235 | 90 | 5 | 13.1 | 4 |
| 5192 | communal | 207 | 67 | 0 | 0.0 | 1 |
| 5586 | communal | 194 | 73 | 1 | 2.7 | 2 |
| JU | cantonal | 183 | 75 | 6 | 15.3 | 5 |
| TG | cantonal | 153 | 66 | 1 | 2.3 | 0 |
| ZG | cantonal | 152 | 56 | 4 | 10.9 | 4 |
| 1061 | communal | 131 | 38 | 0 | 0.0 | 0 |
| GR | cantonal | 104 | 41 | 0 | 0.0 | 1 |
| SH | cantonal | 103 | 36 | 5 | 14.3 | 6 |
| 2939 | communal | 102 | 42 | 0 | 0.0 | 1 |
| 2196 | communal | 101 | 40 | 1 | 2.5 | 1 |
| 5002 | communal | 100 | 34 | 1 | 3.2 | 1 |
| 6643 | communal | 100 | 41 | 2 | 4.0 | 1 |
| 3203 | communal | 100 | 37 | 0 | 0.0 | 0 |
| 230 | communal | 98 | 30 | 2 | 6.5 | 2 |
| 5254 | communal | 97 | 41 | 4 | 9.7 | 0 |
| 5113 | communal | 97 | 33 | 0 | 0.0 | 0 |
| 62 | communal | 83 | 30 | 3 | 8.3 | 1 |
| SZ | cantonal | 72 | 28 | 0 | 0.0 | 1 |
| GL | cantonal | 71 | 23 | 0 | 0.0 | 0 |
| 2829 | communal | 71 | 24 | 0 | 0.0 | 1 |
| UR | cantonal | 69 | 29 | 1 | 3.1 | 0 |
| 198 | communal | 69 | 28 | 2 | 4.9 | 2 |
| 942 | communal | 66 | 24 | 2 | 5.5 | 2 |
| OW | cantonal | 64 | 31 | 2 | 4.1 | 2 |
| 2703 | communal | 63 | 24 | 2 | 5.2 | 0 |
| 3427 | communal | 61 | 29 | 2 | 4.3 | 2 |
| 296 | communal | 58 | 22 | 0 | 0.0 | 0 |
| 1024 | communal | 54 | 17 | 1 | 3.3 | 1 |
| 3901 | communal | 50 | 20 | 0 | 0.0 | 0 |
| 4001 | communal | 50 | 23 | 1 | 2.2 | 1 |
| AI | cantonal | 43 | 14 | 0 | 0.0 | 0 |
| 4082 | communal | 41 | 17 | 0 | 0.0 | 0 |
| 361 | communal | 38 | 13 | 1 | 2.9 | 1 |
| 4045 | communal | 38 | 18 | 1 | 2.1 | 0 |
| NW | cantonal | 37 | 12 | 1 | 3.1 | 1 |
| 247 | communal | 36 | 16 | 0 | 0.0 | 0 |
| 2831 | communal | 36 | 16 | 0 | 0.0 | 0 |
| AR | cantonal | 35 | 19 | 2 | 3.9 | 2 |
| 1058 | communal | 34 | 15 | 0 | 0.0 | 0 |
| 4671 | communal | 33 | 9 | 0 | 0.0 | 0 |
| 66 | communal | 32 | 10 | 0 | 0.0 | 0 |
| 191 | communal | 31 | 15 | 0 | 0.0 | 0 |
| 6458 | communal | 30 | 16 | 2 | 3.8 | 1 |
| 2581 | communal | 30 | 15 | 0 | 0.0 | 0 |
| 243 | communal | 29 | 14 | 1 | 2.1 | 0 |
| 4566 | communal | 26 | 9 | 0 | 0.0 | 0 |
| 2937 | communal | 26 | 11 | 1 | 2.5 | 2 |
| 6421 | communal | 26 | 16 | 0 | 0.0 | 0 |
| 306 | communal | 26 | 10 | 0 | 0.0 | 0 |
| 1059 | communal | 25 | 7 | 0 | 0.0 | 0 |
| 121 | communal | 24 | 6 | 0 | 0.0 | 0 |
| 404 | communal | 21 | 6 | 0 | 0.0 | 0 |
| 3443 | communal | 20 | 8 | 2 | 5.0 | 1 |
| 293 | communal | 16 | 5 | 0 | 0.0 | 0 |
| 131 | communal | 15 | 6 | 0 | 0.0 | 1 |
| 6153 | communal | 15 | 5 | 0 | 0.0 | 0 |
| 53 | communal | 14 | 9 | 1 | 1.6 | 1 |
| 3001 | communal | 14 | 5 | 0 | 0.0 | 0 |
| 4401 | communal | 10 | 4 | 0 | 0.0 | 0 |
| 4289 | communal | 10 | 3 | 0 | 0.0 | 0 |
| 616 | communal | 10 | 3 | 1 | 3.3 | 1 |
| 6248 | communal | 10 | 2 | 0 | 0.0 | 0 |
| 743 | communal | 7 | 3 | 0 | 0.0 | 0 |
| 6037 | communal | 6 | 1 | 0 | 0.0 | 0 |
| 4201 | communal | 6 | 3 | 2 | 4.0 | 2 |
| 329 | communal | 5 | 2 | 0 | 0.0 | 0 |

### Weekly lane (P8.4), ISO week of begin_date; post-stratified by week: census part + N_R,week x (SRS share within week)
| week | N window | sample n | flags (sample) | est. flags | please-check (sample) | est. please-check | please-check share of flags (sample) |
|---|---|---|---|---|---|---|---|
| 2026-W01 | 56 | 21 | 0 | 0.0 | 0 | 0.0 | nan |
| 2026-W02 | 177 | 71 | 1 | 2.5 | 0 | 0.0 | 0.000 |
| 2026-W03 | 249 | 84 | 3 | 8.9 | 0 | 0.0 | 0.000 |
| 2026-W04 | 284 | 87 | 7 | 22.9 | 0 | 0.0 | 0.000 |
| 2026-W05 | 331 | 125 | 4 | 10.6 | 0 | 0.0 | 0.000 |
| 2026-W06 | 231 | 90 | 5 | 12.8 | 0 | 0.0 | 0.000 |
| 2026-W07 | 342 | 124 | 5 | 13.8 | 0 | 0.0 | 0.000 |
| 2026-W08 | 154 | 58 | 0 | 0.0 | 0 | 0.0 | nan |
| 2026-W09 | 259 | 97 | 2 | 5.3 | 0 | 0.0 | 0.000 |
| 2026-W10 | 676 | 249 | 13 | 35.3 | 1 | 2.7 | 0.077 |
| 2026-W11 | 531 | 194 | 15 | 41.1 | 0 | 0.0 | 0.000 |
| 2026-W12 | 748 | 301 | 15 | 37.3 | 1 | 2.5 | 0.067 |
| 2026-W13 | 438 | 163 | 5 | 13.4 | 0 | 0.0 | 0.000 |
| 2026-W14 | 291 | 121 | 6 | 14.4 | 0 | 0.0 | 0.000 |
| 2026-W15 | 106 | 47 | 5 | 11.3 | 0 | 0.0 | 0.000 |
| 2026-W16 | 251 | 95 | 4 | 10.6 | 0 | 0.0 | 0.000 |
| 2026-W17 | 376 | 157 | 5 | 12.0 | 1 | 2.4 | 0.000 |
| 2026-W18 | 282 | 101 | 7 | 19.5 | 1 | 2.8 | 0.143 |
| 2026-W19 | 523 | 210 | 6 | 14.9 | 1 | 2.5 | 0.167 |
| 2026-W20 | 255 | 102 | 3 | 7.5 | 0 | 0.0 | 0.000 |
| 2026-W21 | 329 | 105 | 1 | 3.1 | 0 | 0.0 | 0.000 |
| 2026-W22 | 250 | 92 | 4 | 10.9 | 0 | 0.0 | 0.000 |
| 2026-W23 | 679 | 276 | 17 | 41.8 | 0 | 0.0 | 0.000 |
| 2026-W24 | 707 | 235 | 11 | 33.1 | 2 | 6.0 | 0.182 |
| 2026-W25 | 772 | 288 | 19 | 50.9 | 0 | 0.0 | 0.000 |
| 2026-W26 | 518 | 179 | 4 | 11.6 | 0 | 0.0 | 0.000 |
| 2026-W27 | 387 | 152 | 4 | 10.2 | 1 | 2.5 | 0.000 |
| 2026-W28 | 180 | 66 | 1 | 2.7 | 0 | 0.0 | 0.000 |
| 2026-W29 | 78 | 32 | 2 | 4.9 | 0 | 0.0 | 0.000 |
| 2026-W30 | 54 | 17 | 0 | 0.0 | 0 | 0.0 | nan |
| 2026-W31 | 52 | 23 | 0 | 0.0 | 0 | 0.0 | nan |
| 2026-W32 | 84 | 32 | 2 | 5.2 | 0 | 0.0 | 0.000 |
| 2026-W33 | 171 | 66 | 2 | 5.2 | 0 | 0.0 | 0.000 |
| 2026-W34 | 359 | 142 | 6 | 15.2 | 0 | 0.0 | 0.000 |
| 2026-W35 | 417 | 157 | 6 | 15.9 | 0 | 0.0 | 0.000 |
| 2026-W36 | 462 | 179 | 8 | 20.6 | 0 | 0.0 | 0.000 |
| 2026-W37 | 539 | 190 | 9 | 25.5 | 0 | 0.0 | 0.000 |
| 2026-W38 | 797 | 307 | 10 | 26.0 | 1 | 2.6 | 0.000 |
| 2026-W39 | 611 | 224 | 9 | 24.5 | 1 | 2.7 | 0.111 |
| 2026-W40 | 751 | 624 | 51 | 57.4 | 2 | 2.0 | 0.039 |
| 2026-W41 | 32 | 32 | 1 | 1.0 | 0 | 0.0 | 0.000 |

Weekly est. flags: median 12.0, min 0.0, max 57.4 over 41 ISO weeks (2026-W01 and W41 partial). Please-check share among flags in the sample: 9/278; among all sampled: 12/5915.

- DVS recall (P8.2, all 30): Apertus 27/30 [0.744, 0.965]; keyword 21/30 [0.521, 0.833]

- DVS recall (P8.2, begin_date in window): Apertus 23/24 [0.798, 0.993]; keyword 16/24 [0.467, 0.820]

### Strata (design sample) and blind packet
| stratum | N in design sample | est. N window | sampled n |
|---|---|---|---|
| A∩K | 212 | 501.3 | 120 |
| A only | 66 | 159.1 | 66 |
| K only | 98 | 241.0 | 98 |
| neither | 5539 | 13887.7 | 180 |

(resnap: packet/key/loop_order regenerated from snapshot/ are byte-identical to the frozen ones: True)

Packet: 464 items D001..D464 (packet/items.txt, ann_TEMPLATE.tsv, GUIDE.md = byte copy of S4 GUIDE.md); key.jsonl outside packet/ (final_weight = design_weight x N_h/n_h for population-weighted P8.1); loop_order.json seed 60.

### Throughput, 3 workers, alongside the separate bulk job and other spikes (P8.6), one row per 500 calls
| UTC | orders | calls | wall s | req/s | HTTP p50 s | HTTP p95 s | 429s | errors |
|---|---|---|---|---|---|---|---|---|
| 18:23 | a | 500 | 730.2 | 0.685 | 0.79 | 32.08 | 76 | 0 |
| 18:36 | a494+b6 | 500 | 685.6 | 0.729 | 0.81 | 31.85 | 78 | 0 |
| 18:48 | a497+b3 | 500 | 767.3 | 0.652 | 0.83 | 31.84 | 80 | 0 |
| 19:01 | a496+b4 | 500 | 749.9 | 0.667 | 0.86 | 32.15 | 80 | 0 |
| 19:11 | a494+b6 | 500 | 599.9 | 0.833 | 1.05 | 3.03 | 34 | 0 |
| 19:25 | a495+b5 | 500 | 824.1 | 0.607 | 1.0 | 63.23 | 81 | 0 |
| 19:34 | a497+b3 | 500 | 559.0 | 0.894 | 0.86 | 3.0 | 55 | 0 |
| 19:46 | a499+b1 | 500 | 747.8 | 0.669 | 0.88 | 32.98 | 85 | 0 |
| 19:59 | a498+b2 | 500 | 768.5 | 0.651 | 0.92 | 33.53 | 82 | 0 |
| 20:10 | a499+b1 | 500 | 660.3 | 0.757 | 0.915 | 32.36 | 80 | 0 |
| 20:21 | a499+b1 | 500 | 624.5 | 0.801 | 1.03 | 31.57 | 97 | 0 |

Overall: 5975 calls in 8366 s = 0.714 req/s (incl. the 1 min restart at 18:23); pai secs per call (incl. backoff) p50 0.890 s, p95 31.990 s; 429 responses 915; calls needing a retry 442
Fingerprints: {'vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840': 5975}; served: {'swiss-ai/apertus-v1.5-8b': 5975}

Spend (pai ledger, list price): bern2-s8-a $0.1144, bern2-s8-b $0.0007, bern2-s8-check $0.0007; total $0.1158 of $3.00 cap

## Gold-based results (lead, 13 Oct ~21:00 UTC; score.py → score.json; loop.py → loop.json)
Gold: blind Claude annotators A (forward) / B (reverse), packet/ only; A–B agreement 0.976, κ 0.951 (460 comparable); 15 disagreements or "?" → blind tie-break C.
Cross-family: Qwen-SEA-LION on all 464 (κ vs A 0.812, vs B 0.824).
P8.1 population-weighted (window 1 Jan–6 Oct 2026, 14,790 affairs; bootstrap within strata, 2,000):
- est. digitalisation affairs 1,019 [740, 1,371]
- Apertus: est. flags 674; precision 0.917 [0.882, 0.951]; recall 0.606 [0.447, 0.815]
- Keyword (S4 29 stems): est. flags 755; precision 0.760 [0.725, 0.797]; recall 0.563 [0.416, 0.757]
- Apertus − keyword: precision +0.157 [+0.116, +0.197]; recall +0.042 [+0.012, +0.079]
- Sensitivity, gold = majority of A, B, Qwen: Apertus P 0.902 [0.861, 0.940], R 0.603; keyword P 0.741, R 0.561; ΔP +0.161 [0.121, 0.201]; ΔR +0.042 [0.012, 0.080]
- Strata confirmations: A∩K 117/120; A only 49/66; K only 29/98; neither 4/180.
P8.2 DVS public list: Apertus 27/30 (in window 23/24); keyword 21/30 (16/24).
P8.3 coverage: 199 blind-confirmed positives in the packet from 46 parliaments (38 outside the nine on the public DVS page); levels cantonal 87, federal 62, communal 41, LIE 9; languages de 150, fr 35, it 14.
  Est. positives outside the nine: 538 [347, 805]; by level (est.) federal 340, cantonal 422, communal 152, LIE 106; by language de 764, fr 205, it 51.
  Positives Apertus found and keyword missed: 49 in packet (est. 117); keyword found and Apertus missed: 29 (est. 74).
P8.4 weekly: est. flags median 12.0 per ISO week (0–57.4); please-check share among sampled flags 9/278.
P8.5 correction loop (pre-registered; unweighted, 404 packet items outside the first 60): F1 0.866 → 0.906, Δ +0.040 [+0.007, +0.075] → gain;
  precision 0.910 → 0.917, recall 0.826 → 0.895.
Examples (blind-confirmed, from the packet): data centres VD D029 (Jun, A only), GE D051 (Jun, A only), SH D139 (Jun), VD D162 (Sep, A only), BE D093 (Sep, A only),
  CHE D462 (16 Sep, A only), CHE D298 (30 Sep) — 5 of 7 missed by the keyword list; digital sovereignty: Stadtrat Bern D173 (12 Feb), Ville de Genève D326/D374 (Feb/Mar),
  Lenzburg D122 (Mar), CHE D195/D456 (19 Mar), D388/D459 (3 Jun), TI D414 (Apr), NE D355 (Jun), GE D164 (Aug), BE D069 (8 Sep), CHE D176 (30 Sep), TI D125 (1 Oct).
Census runner paused 20:49–21:00 UTC to give the loop and Qwen passes the shared key; resumed.

## Census runner stopped by the lead (2026-10-13 21:58 UTC)
Stopped to free the shared Public AI key (the bulk precompute job logged 429 back-off at 0.27 req/s while ideation2 spikes ran). Scored so far:     8139 order-A rows. Resume during the build from this folder:
`nohup python3 -I run2.py 3 > raw/run2.log 2>&1 &` (resumable; stops itself on a new fingerprint). Estimates in this file use the 20:30 UTC design sample.
