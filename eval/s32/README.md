# S32: neutrality of the shipped federal design (party, submitter, instrument, language)

**Not pre-registered.** This is a re-analysis of measurements that already exist. It makes no model calls and no network
requests, and costs USD 0. It was written after the round-8 review (J2, change 2), which noted that the party check
(S14, `eval/spikes/s14-neutrality`) ran on the earlier D1 design, not on the design that ships.
Script: `analyze.py` → `results.json`. The run takes about 3 minutes, mostly for the permutation tests.

## What is scored
- **S9 prod (primary):** the 1,357 S9 APS-labelled federal affairs, scored with the **production rows**:
  `eval/prod_gold/topics.jsonl.gz` and `inputs.jsonl.gz`, composed by `eval/prod_gold/rows.py` from `runs/main` and
  `runs/side` with the export's rule. These are the rows that `make eval GOLD=data/eval/gold_aps_s9.csv` scores. The
  script checks that it gets the same 963/1,340 (top-1) and 1,153 (top-3), and the same 17 affairs with no chapter row.
  This is what ships on the production path: D4 where the affair has APS-labelled neighbours, D1 otherwise
  (`compose.decide`). The input is the production input (title, long title, text).
- **S25 (held out):** the 927 fresh affairs in `eval/s25/decisions.jsonl`, the same composition as above (646/927 top-1,
  checked). 917 of them used examples (D4) and 10 did not (D1).
- **Pooled:** S9 prod and S25 together (2,267 affairs, top-1 only). The permutation test shuffles labels within each set.
- **Secondary:** S16 D4 on the S9 items (`eval/s16/raw.jsonl`, S9 input, 1,005/1,357, checked). This is the
  pre-registered S16 measurement of the design. It is not the production path, but it shows the result does not depend
  on which of the two is used.

Gold for every set is the APS editors' chapter.

## How each dimension is built (S14, unchanged)
- **Party, submitter type and instrument** come from S14's own functions. The script runs
  `eval/spikes/s14-neutrality/scripts/s14lib.py` unchanged, except for the one line that loads S14's OPD subset. That
  subset is not in the repository. Instead the rows come from the OpenParlData export the production run reads,
  `../data/opd-new` (16 Oct 2026; `affairs` and `contributors`, the fields S14's `extract.py` keeps).
- **Check:** on the S9 affairs, this export gives exactly S14's submitter cells: SVP 137, SP 174, FDP 146, Mitte 125,
  Grüne 95, GLP 45, other party 32, committee 222, government 274, canton 74, unknown 33. The script asserts this.
- **Language of the text** is `text_lang` of the production input.

## Statistics
The statistics follow S14:
- Wilson 95% for each cell.
- A permutation test (5,000, seed 14) of Pearson's χ² across cells, with the asymptotic p alongside. The party test runs
  over the six main parties, plus a secondary test over all submitter categories.
- **Largest gap:** the highest cell minus the lowest, among tested cells with n ≥ 30. Its 95% interval comes from
  independent bootstraps within each cell (2,000).

Points are truncated at 4 decimals. Wilson and bootstrap bounds are rounded outward at 3 decimals.

**Two deviations from S14:**
1. A cell counts as small below n = 30 (S14: 20). The gap rule uses the same threshold. Where small party cells exist
   (S25: Grüne 23, GLP 22), the file also gives the gap over all six parties (`gap_all_tested_cells`).
2. S14 measured language as a paired DE-vs-FR call on the same affairs. The shipped federal design reads only the German
   input, so that comparison has no shipped equivalent without new calls (see Language below).

## Results: chapter top-1 vs APS editors

**By party of the submitter (test over the 6 main parties)**

| cell | S9 prod (n 1,340) | S25 held out (n 927) | pooled (n 2,267) |
|---|---|---|---|
| SVP | 0.632 [0.548, 0.709] n 136 | 0.670 [0.571, 0.756] n 97 | 0.648 n 233 |
| SP | 0.721 [0.649, 0.784] n 169 | 0.595 [0.488, 0.694] n 84 | 0.679 n 253 |
| FDP | 0.689 [0.610, 0.760] n 145 | 0.638 [0.531, 0.734] n 83 | 0.671 n 228 |
| Mitte | 0.628 [0.539, 0.710] n 121 | 0.706 [0.606, 0.790] n 92 | 0.661 n 213 |
| Grüne | 0.695 [0.595, 0.781] n 92 | 0.565 [0.368, 0.744] n 23 (small) | 0.669 n 115 |
| GLP | 0.733 [0.589, 0.841] n 45 | 0.727 [0.518, 0.869] n 22 (small) | 0.731 n 67 |
| permutation p (χ² p) | 0.4317 (0.4125) | 0.5563 (0.5608) | 0.8726 |
| largest gap, cells n ≥ 30 | GLP − Mitte +0.105 [−0.059, +0.252] | Mitte − SP +0.111 [−0.037, +0.255] | GLP − SVP +0.083 [−0.043, +0.199] |

In S25, the gap over all six parties, small cells included, is GLP − Grüne +0.162 [−0.111, +0.429]. The test over all
submitter categories gives p 0.0338 for S9 prod (11 cells) and p 0.2983 for S25 (13 cells). The full intervals for the
pooled cells are in `results.json`.

**By submitter type**
- S9 prod: member/faction 0.679 [0.645, 0.713] (n 740), committee 0.791, government 0.747, canton 0.739; p 0.0064.
- S25: member/faction 0.652 [0.605, 0.697] (n 423), committee 0.728, government 0.736; p 0.1606.
- Pooled: p 0.0014, committee − member/faction +0.100 [+0.045, +0.151].

**By instrument**
- S9 prod: Parlamentarische Initiative 0.797, Regierungsgeschäft 0.747, Motion 0.691, Postulat 0.673; p 0.003. The
  keyword baseline puts the same instrument highest and the same one lowest (p 0.0006).
- S25: p 0.5623.

**Language of the text: not informative.** In S9 prod all 1,340 scored inputs are German. In S25, 926 are German and
1 is French. Federal affairs are not routed through the DE/FR two-readings lane: the shipped design reads the German text.
So neither set can measure a language effect of the shipped design. The cells are in the file and no test is run. The
language evidence on human labels comes from elsewhere and uses other designs: S22 compares Italian vs German on D1, and
Bern compares DE vs FR titles on its own scheme. A held-out French or Italian federal slice for the shipped design does
not exist yet.

**S16 D4 (secondary, S9 input):** party p 0.5659, largest gap SVP − Grüne +0.091 [−0.042, +0.211]; submitter type
p 0.0004; instrument p 0.0002.

## Reading
- **Party:** the six main parties show no difference in chapter accuracy that these sample sizes can detect. That holds in
  S9 prod, held out in S25, and pooled. It is not evidence that no difference exists, because the gap intervals reach
  up to +0.255.
- **The lowest party is not the same across sets:** Mitte and SVP in S9 prod, SP (and the small Grüne cell) in S25.
  A tilt against one party would show up as that party at the bottom in both sets. It does not here, but at these
  sample sizes that is weak evidence either way.
- **Submitter type:** members' affairs score below committee and government business, and the pooled test detects it.
  The earlier D1 analysis (S14) found the same. Unlike in S14, the keyword baseline on the production input does not
  order the submitter types that way: in S9 prod, member/faction 0.213, government 0.212, committee 0.171, p 0.3341. So
  this analysis does not show that the submitter-type gap comes from easier texts. By instrument it does: in S9 prod the
  keyword baseline also puts Parlamentarische Initiative highest and Postulat lowest (p 0.0006). Quality is reported per
  submitter type either way.
- **Compared with S14 (D1, earlier design, same 1,357 affairs):** S14 had party p 0.47 and largest gap SP − Grüne
  +0.122 [−0.007, +0.242].
