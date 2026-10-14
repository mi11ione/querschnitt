# S10: bilingual cantonal parliaments, DE vs FR (BE, FR, VS Grand Councils, 2025–2026)

Status 2026-10-13T18:26Z: model run complete, blind packet built, gold **TO MEASURE** (annotators not run; no annotation by this agent).
PREREG section S10 is binding; its primary analysis is `scripts/score.py` once `ann_A.tsv`, `ann_B.tsv` (+ `ann_C.tsv`) exist.

## Run facts
- Sample: 210 affairs, 70 each from BE, FR, VS. Seed 20261014. Frozen exclusion regex in `scripts/sample.py`
  (sha256 of the regex source `ed209116…393e7c`; file hashes in `FROZEN.sha256`, written before the first model call).
  Frame (begin_date ≥ 2025-01-01, both titles non-empty, de ≠ fr, no regex hit): BE 953, FR 435, VS 961 eligible.
  Excluded by regex: BE 189, FR 132, VS 20. Identical titles dropped: BE 5, FR 2, VS 34. VS missing a title: 53.
  The regex also removes about 30 policy affairs that only mention elections or naturalisation (motions on electoral law,
  naturalisation policy); they are outside the frame (about 1.3 % of 2,380 non-personnel affairs).
- Model: `swiss-ai/apertus-v1.5-8b`, L1 variant (c), identity order, 420 calls (210 × DE + FR) via `ideation2/lib/pai.py`.
  Served model and fingerprint for all 420: `swiss-ai/apertus-v1.5-8b` / `vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840`
  (expected build; no mixing). Minimum code mass in top-20 logprobs: 0.996.
- Spend: bern2-s10-l1de USD 0.0273, bern2-s10-l1fr USD 0.0268, total **USD 0.0541** (cap 1.00).
- Payload: the same as S6 (`gw.chat` → `pai.chat`, same dict). As in S6, the FR prompt lists the APS subtopic names in German
  (no FR subtopic names on disk).

## No-gold results (measured)
| quantity | n | value | 95 % CI |
|---|---|---|---|
| DE–FR top-1 agreement | 210 | 148/210 = 0.705 | Wilson 0.640–0.762 |
| "please check" share (DE top-1 ≠ FR top-1) | 210 | 62/210 = 0.295 | Wilson 0.238–0.360 |
| same, frame-weighted (BE 953 / FR 435 / VS 961) | 210 | 0.2975 | stratified bootstrap 0.236–0.362 |
| please check, BE | 70 | 17/70 = 0.243 | 0.158–0.355 |
| please check, FR | 70 | 20/70 = 0.286 | 0.193–0.401 |
| please check, VS | 70 | 25/70 = 0.357 | 0.255–0.474 |

Pooled top-1 equals DE top-1 in 171/210 items and FR top-1 in 187/210.
Most frequent disagreement pairs (DE → FR): 1.1.3.→1.1.2. (6), 1.7.1.→1.7.4. (6), 1.4.3.→1.6.4. (3), 1.7.1.→1.7.2. (3).

Secondary (post hoc, `scripts/langcheck.py`, not pre-registered): in 16/210 items one "language" field is in the other language
(15 untranslated: the same title in [brackets], 11 FR with French in the DE field, 4 VS with German in the FR field; 1 VS with a
French DE title). The prompt language alone still changes the top-1 in 5/16 of them. Excluding the 16: please-check share
57/194 = 0.294 (Wilson 0.234–0.361). The primary analysis keeps all 210 items.

## Weekly volume (OPD affairs.ndjson.gz, begin_date, 2024-12-30..2026-10-04 = 92 ISO weeks, zero weeks included)
| series | total | median/wk | mean/wk | p90/wk | max | zero weeks |
|---|---|---|---|---|---|---|
| all affairs, BE+FR+VS | 2,784 | 11.5 | 30.26 | 94.0 | 168 | 0 |
| S10 frame, BE+FR+VS | 2,349 | 10.0 | 25.53 | 76.7 | 141 | 0 |
| frame BE | 953 | 1.0 | 10.36 | 44.9 | 89 | 19 |
| frame FR | 435 | 4.0 | 4.73 | 9.0 | 17 | 8 |
| frame VS | 961 | 0.0 | 10.45 | 43.3 | 93 | 51 |

Volume comes in bursts around sessions (BE and VS median ≪ mean). Please-check load = frame volume × weighted share 0.2975
(0.236–0.362): median week 2.98 (2.36–3.62) affairs, mean week 7.60 (6.03–9.24), p90 week 22.82 (18.10–27.77) across the three
parliaments. Whether a disagreement flags an error better than chance needs gold (accuracy inside vs outside: TO MEASURE).

## Gold-based outcomes: TO MEASURE
Accuracy DE / FR / pooled with Wilson and frame-weighted CIs, paired stratified bootstrap differences (2,000), accuracy when the
languages agree vs disagree, per canton, by shown language, kappa A–B. Steps:
1. Two blind annotators get `packet/` only (GUIDE.md = S6 guide byte-identical; `README_S10.txt` = save location and id range);
   they write `ann_A.tsv`, `ann_B.tsv` into this folder.
2. `python3 -I scripts/score.py --c-template` → `packet/ann_C_TEMPLATE.tsv` (ids where A and B differ) → tie-break → `ann_C.tsv`.
3. `python3 -I scripts/score.py` → `score.json` (overwrites the current no-gold `score.json`).
score.py was smoke-tested on synthetic annotations (in the scratchpad dir, then deleted).

## Files
`scripts/sample.py` (frozen regex, sampling), `scripts/s10lib.py`, `scripts/run.py`, `scripts/build_packet.py`, `scripts/score.py`,
`scripts/volume.py`, `scripts/langcheck.py`; `sample.json`, `sample_meta.json`, `FROZEN.sha256`, `raw/l1.jsonl` (full 25-code
distributions DE/FR/pooled + per-call receipts), `key.jsonl` (outside packet), `packet/`, `volume.json`, `score.json` (no-gold part),
`langcheck.json`.

## Deviations
- 2026-10-13T18:26Z: none from PREREG S10. Additions: (1) shown-language halves balanced per canton (35/35), which is one way of
  doing the seeded half; (2) frame-weighted estimates reported next to unweighted ones (PREREG fixed rule for stratified samples);
  (3) post-hoc language-field check reported as secondary only.

## Gold-based results (lead, 18:29 UTC 13 Oct; scripts/score.py → score.json; secondary.txt)
Gold: blind Claude annotators A (forward) / B (reverse) from packet/ only; agreement 201/210 = 0.957, κ 0.954; 9 disagreements → blind tie-break C.
Pre-registered: accuracy DE 0.543 [0.475, 0.609], FR 0.529 [0.461, 0.595], pooled 0.552 [0.485, 0.618] (n 210, titles only).
DE−FR +0.014 [−0.043, +0.076] n.s. (parity); pooled−DE +0.010 [−0.038, +0.057] n.s.; pooled−FR +0.024 [−0.014, +0.062] n.s.
Lanes: languages agree (148, 70.5%): 0.622 [0.541, 0.696]; disagree (62, 29.5%): DE 0.355 / FR 0.306 / pooled 0.387.
Per canton (DE/FR/pooled): BE 0.571/0.543/0.529; FR 0.529/0.543/0.571; VS 0.529/0.500/0.557.
Secondary (not pre-registered; same definitions S6/S7 used): top-3 contains gold DE 0.771, FR 0.738, pooled 0.810 [0.751, 0.857];
model top-1 among any annotator code DE 0.652, FR 0.652, pooled 0.681.
Clerk load: please-check 0.2975 × weekly volume (median 10.0, mean 25.5, p90 76.7 affairs/week, BE+FR+VS) = 3.0 / 7.6 / 22.8 items a week.
