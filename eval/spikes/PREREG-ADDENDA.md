# PREREG addenda (append-only)

## 2026-10-13 21:12 UTC — S11 annotator anchor (written before any S11 annotation exists)
Question: how well do the blind Claude annotators (the gold used in S6, S8, S10) agree with human editors' labels?
Items: 200 random S9 held-out federal affairs (seed 20261014), same input Apertus saw (DE title, long title, first 1,500 chars of submitted text).
Annotators: two blind Claude agents (forward / reverse), S6 GUIDE unchanged, packet only. No tie-break.
Outcomes: per annotator and for the A=B consensus, share whose first chapter equals the APS editors' chapter (Wilson 95%); share where the editors'
chapter is among the annotator's first or second code; Apertus D1 and D3 (where available) on the same items. Reported as measured, whatever the result.

## 2026-10-13 21:12 UTC — S8 reporting addition
"Swiss parliaments" figures are reported excluding Liechtenstein (LIE, an OPD body) next to the all-bodies figures; same estimator.

## 2026-10-13 21:20 UTC — S12, S13, S8b, S14, S9c (written before any of these results exist)
S12 evidence support: 120 random S9 held-out federal affairs with Curia DE text; Apertus picks one sentence (closed choice over the
numbered sentences of title + first 1,500 chars) as evidence for its D1 chapter; code checks exact substring. A blind Claude judge
(packet only: affair text, chapter name, quoted sentence; two runs + tie-break) answers "does the sentence support the chapter? Y/N".
Outcome: support rate (Wilson), separately when the chapter is right vs wrong per APS editors; substring-check pass rate.
S13 Neues Thema timing: three topics never used before ("Wolf und Grossraubtiere", "Hitzeschutz / Hitzewellen", "Künstliche Intelligenz an
Schulen"), each defined in one sentence; one yes/no call per affair (order yes=A) over all 577 affairs of the census week 30 Sep–6 Oct 2026;
outcomes: wall time to the first 50 decisions and to all 577 at 3 workers on the shared key, 429 count; flags per topic (no gold).
S8b text lever: S8 packet federal items whose Curia DE text is on disk (clean pool); one yes/no call (order a) on title + long title + first
1,500 chars of text; outcome: precision/recall vs the S8 gold, paired against the title-only order-a decision on the same items.
S14 neutrality (no calls): accuracy/precision/recall by language, level, canton and submitter party on S6, S8, S9, S10 data with intervals;
party from OPD contributors; reported whatever it shows.
S9c calibration (no calls): isotonic recalibration of D1/D3 confidence, 2-fold cross-fitted on the S9 items; outcome: ECE before/after.

## 2026-10-13 21:58 UTC — S15 judge check on the binary task (before any S15 annotation)
The 30 human-curated public DVS items mixed with 70 random 2026 affairs (not in the S8 packet), shuffled; the same blind Claude judge setup as S8
(two runs, GUIDE unchanged, packet only). Outcome: share of the 30 DVS items the judge marks Y (judge recall on human positives), per run.
