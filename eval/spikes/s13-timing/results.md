# S13 Neues Thema timing + S8b text lever — results (complete 2026-10-13)
Pre-registered: PREREG-ADDENDA.md 2026-10-13 21:20 UTC (S13, S8b). Model swiss-ai/apertus-v1.5-8b via lib/pai.py, nocache=True, order yes=A, logprob p(A)/(p(A)+p(B)).
Tags: bern2-s13-timing (cap 0.30), bern2-s8b-text (cap 0.25); combined cap 0.60.

## Design
- S13: three new topics (wolf, hitze, ki_schule), each one question sentence with a parenthetical scope in de/fr/it, E6 shape (s13.py TOPICS);
  item labels, "Nein, anderes Thema"/"Non, autre thème"/"No, altro tema" and JSON format line unchanged from E6.
  Population: items_cache.json date 2026-09-30..2026-10-06, in_window: n=577. Topics run sequentially, each at exactly 3 threads, shared key.
  pai.py retries 429 internally (sleep 10/20/30 s ...); all statuses logged per call.
- S8b: S8 packet federal items (141) -> oracle_curia (138 mapped) -> Curia DE clean-pool record (138) -> SubmittedText+ReasonText non-empty: n=120 (all prompt language de).
- S8b local (cantonal/communal, track_2a .work/text): attempted, only 1 of 323 local packet items reliably mappable -> not scored.

## S13 (n=577 per topic, one run each at exactly 3 threads, nocache, shared key; no gold, so no accuracy)
| topic | first 50 decisions | all 577 | decisions/s | HTTP attempts/s | HTTP 429 (calls hit) | other non-200 | latency median / p90 / max | flags p>=0.5 (p>=0.9) |
|---|---|---|---|---|---|---|---|---|
| wolf | 12.607 s | 456.822 s | 1.263 | 1.379 (630) | 53 (26) | 0 | 0.740 / 1.121 / 62.802 s | 4 (4) |
| hitze | 75.108 s | 506.690 s | 1.139 | 1.245 (631) | 54 (18) | 0 | 0.720 / 0.949 / 62.917 s | 24 (22) |
| ki_schule | 74.900 s | 505.673 s | 1.141 | 1.248 (631) | 54 (18) | 0 | 0.711 / 0.950 / 63.094 s | 5 (5) |

Flags by level/language (counts only): wolf cantonal/de 1, federal/de 2, federal/fr 1; hitze federal/de 15, federal/fr 5, cantonal/de 1,
cantonal/it 1, communal/de 1, other/de 1; ki_schule federal/de 4, communal/de 1.
Reading: an uncontended call takes ~0.7 s; wall time is set by 429 bursts on the shared key (pai.py backoff 10+20+30 s per affected call;
max latency ~63 s = three 429s). hitze/ki_schule hit a burst before decision 50 (75 s), wolf did not (12.6 s). One run per topic: no
interval on the timings (TO MEASURE: repeat runs / time-of-day variance). Served model swiss-ai/apertus-v1.5-8b, fingerprint expected on all 1,731 rows.
Spend bern2-s13-timing: USD 0.0367.

## S8b (federal packet items with Curia DE text; unweighted; gold = A if A==B in Y/N else C)
Join: 141 federal packet items -> 138 in oracle_curia -> 138 clean-pool DE records -> 120 with non-empty SubmittedText/ReasonText (all prompt de);
n=120, gold Y 56 / N 64. Text = HTML-stripped SubmittedText + ReasonText, first 1,500 chars, line "Text: ..." after Titel/Langtitel.
| variant (order a) | P [Wilson 95%] | R [Wilson 95%] | F1 | tp/fp/fn |
|---|---|---|---|---|
| title only (key p_a>=0.5) | 0.896 [0.778, 0.955] | 0.768 [0.642, 0.859] | 0.827 | 43/5/13 |
| title + text | 1.000 [0.908, 1.000] | 0.679 [0.548, 0.786] | 0.809 | 38/0/18 |
Paired bootstrap 2,000 (seed 13, percentile): dF1 = -0.018 [-0.083, +0.040]; dRecall = -0.089 [-0.170, -0.020].
Flips: 10 Y->N, 0 N->Y (5 of the Y->N were title-only false positives, 5 were true positives lost). Text makes the 8b stricter:
precision up, recall significantly down, F1 no detectable change. Spend bern2-s8b-text: USD 0.0055.

S8b local (cantonal/communal via track_2a .work/text): attempted, not scored. 262 of 323 local packet items have census doc rows, but
only 1 could be tied reliably to a cached text file by sha256 (docs_meta "h" is not the text-file hash); see s8b_local.json.

## Deviations
- None from the addenda. Note: S13 topics were run sequentially (each at exactly 3 threads); S8b ran after S13 so total concurrency never exceeded 3.

## Files
s13.py, s8b.py, analyse.py, results.json, s8b.json, s8b_local.json, raw/s13_{wolf,hitze,ki_schule}.jsonl, raw/s13_runs.jsonl, raw/s8b.jsonl, raw/local_sha_map.json
