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
