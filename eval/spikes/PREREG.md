# ideation2 pre-registration (written 13 Oct 2026 evening, before any ideation2 result exists)

Hash of this file is recorded in `PREREG.sha256` right after writing; any later edit goes into `PREREG-ADDENDA.md` with a timestamp, never here.
All model calls: lean client `lib/pai.py` (own ledger, list-price cap USD 15 across bern2-* tags), route `swiss-ai/apertus-v1.5-8b`
unless stated, served model + `system_fingerprint` logged per call. A spike runs on one fingerprint; if the fingerprint changes
mid-spike the spike stops, reports the split, and no table mixes fingerprints. Comparisons with ideation-1 numbers (build `…dd237840`)
are only made if the ideation2 fingerprint equals it; otherwise every baseline is re-run on the new build inside the spike.
Intervals: Wilson (proportions), paired bootstrap 2,000 resamples (differences), stratified estimators where sampling is stratified.

## S8 — "Digitalisierung" over every affair of 2026 (all 89 bodies), the DVS finding
Population: all OPD affairs with begin_date in 2026-01-01 … 2026-10-06 (6 Oct export; n ≈ 14,791). Input = title + long title in
the affair's language (S3 E6 prompt, de/fr/it; rm/other → de prompt with the original title). Scoring: answer order yes=A for
every affair; the reversed order is added only when 0.1 < p(yes) < 0.9; final p = mean of the orders run. Flag = p ≥ 0.5 (the S3/S4 cut-off, not re-fitted).
Keyword baseline: the stored S4 regex (29 stems, `s4-blindcheck/keyword_baseline.json`) on the same input.
Strata: A∩K, A only, K only, neither. Blind sample: up to 120 from A∩K, 150 from A only, 100 from K only, 180 from neither
(seeded random within stratum), shuffled, opaque ids; annotators see parliament | type | date | title | long title only.
Gold: two blind Claude annotators (forward / reverse order, DVS-scope guide = S4 GUIDE.md unchanged) ; disagreements and `?` go to a third
blind Claude tie-break annotator; plus a Qwen-SEA-LION cross-family pass on all items (reported as a sensitivity row).
Primary outcomes (population-weighted estimators over strata):
  P8.1 Apertus precision and recall; keyword precision and recall; difference Apertus − keyword with bootstrap interval.
  P8.2 Recall on the 30 public DVS items (those with begin_date in the window counted separately).
  P8.3 Coverage: number of parliaments, levels and languages among blind-confirmed positives vs the 9 parliaments on the public DVS page;
       estimated number of digitalisation affairs in 2026 outside those 9 parliaments (stratified estimate with interval).
  P8.4 Weekly lane size (flags per ISO week; share in "please check" = orders disagree or 0.3 ≤ p < 0.7).
Secondary: P8.5 correction loop — the first 60 annotated items in a fixed random order act as an editor's first decisions (accept/reject);
  for every other annotated item the 4 most similar of those 60 (BM25 on titles) are shown as labelled examples in the same yes/no prompt
  (one order, yes=A). Outcome: F1 against the tie-broken gold on the remaining items, before vs after, paired bootstrap. Pre-declared:
  the loop is called a gain only if the F1 interval excludes 0.
  P8.6 throughput of the lean client at 3 workers (requests/s, HTTP p50/p95, 429 count) alongside the separate bulk job.
No threshold is tuned on S8 data. Examples for the pitch are picked only from blind-confirmed positives (both annotators or tie-break).

## S9 — APS extended held-out (federal; Wayback process captures not used in ideation 1)
Set: APS process captures joined to OPD CHE by Curia number (S2 method), excluding the 298 ideation-1 pages; target ≈ 1,400 affairs;
German and French title + submitted text from Curia OData (same fields as S3). Nothing is tuned on this set.
Designs (all on the same items, same build):
  D0 (v14 shipped): L1 variant (c) = chapter names + subtopic names, two code orders (identity + S1 permutation), geometric mean → chapter top-1.
  D1 readback: D0 arithmetic top-3/top-2 shortlist → joint L2 (top chapter first, 1 call) → chapter of chosen subtopic,
      times L1 prior (β = 1 fixed, as S5).
  D2 language pooling: L1 (c) identity order on the French text (FR prompt, FR chapter names, DE subtopic names) averaged (mean of probabilities)
      with D0's two German orders.
  D3 label memory: L1 (c) identity order with the 5 most similar other gold affairs (BM25 on DE titles, drawn from the ideation-1 298 +
      all other S9 items except the item itself) shown with their APS chapter as examples; averaged with D0's permuted order.
Hypotheses (one-sided interest, two-sided intervals): H9.1 D1 > D0 chapter top-1; H9.2 D2 > D0; H9.3 D3 > D0. A design "wins" only if its
paired interval excludes 0. Also reported for D0 and the winner: top-3, subtopic top-1/top-3 end to end, per-period strata
(pre-2010, 2010–19, 2020+), lane precision (orders agree / disagree), reliability table of p (10 bins, ECE) and coverage–precision curve.
Baselines on the same items: majority chapter; keyword (APS chapter keywords from the APS subtopic names, frozen before scoring).
If fewer than 600 items are obtained, all outcomes are still reported, labelled with n.

## S10 — bilingual cantonal parliaments, DE vs FR (Bern, Fribourg, Valais Grand Councils, 2025–2026)
Sample: 210 affairs (70 per canton), seeded random among affairs with both title_de and title_fr, begin_date ≥ 2025-01-01, excluding
elections/appointments by title regex (frozen). Input: title (+ long title) in each language separately.
Model: L1 variant (c), identity order, DE prompt on the German title and FR prompt on the French title; pooled = mean of probabilities.
Gold: two blind Claude annotators assign the APS chapter (S6 GUIDE, unchanged) — half of the items shown in German, half in French
(assignment seeded), so the gold is not tied to one language; tie-break annotator on first-choice disagreement.
Outcomes: accuracy DE, FR, pooled with paired intervals; DE–FR top-1 agreement; share where the two languages disagree ("please check")
and accuracy inside/outside it; per canton; weekly volume of the three parliaments (from OPD 2025–26 counts) × please-check share.

## Fixed reporting rules
Every number in the vision v2 links to a results file. Results that miss their hypothesis are reported as measured, in the evaluation
section, not on the first screens. Nothing post hoc is promoted into the pitch.
