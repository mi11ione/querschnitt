# Querschnitt — evaluation report

One topic field for every Swiss parliament in OpenParlData: an Année Politique Suisse (APS) chapter with ranked subtopics,
ad-hoc topics defined in one sentence, a lane that says when a person should check, and a quoted sentence from the affair.
Every topic decision is made by Apertus (`swiss-ai/apertus-v1.5-8b` on Public AI, build `…dd237840` on every call reported
here). Full tables with intervals, baselines and source files: [PRUEFSTAND.md](PRUEFSTAND.md); every number in this report
is in [`eval/claims.tsv`](../eval/claims.tsv).

## 1. Method in brief
- **Closed choices.** Each step — chapter, subtopic, yes/no for an ad-hoc topic, evidence sentence — is a choice among
  listed codes, read from the next-token probabilities. A label outside the scheme cannot be stored. (Asked to name a topic
  freely, Apertus answered outside the scheme in 36 of 40 affairs; with the list shown, in 0 of 40.)
- **Two readings, one lane.** The chapter question is asked in two code orders; in bilingual parliaments the German and the
  French version are the two readings. The readings feed one recalibrated confidence; the lane is `please_check` when it is
  below 0.7 or the German and French readings disagree, otherwise `pass`. The readings stay visible as the explanation.
- **Read-back.** One request over the subtopics of the top chapters; the chapter is read back from the chosen subtopic.
  Federal affairs see the five most similar APS-labelled affairs as examples.
- **Schemes are files.** APS, Bern's directorates, Basel-Stadt's own themes and ad-hoc topics run on the same engine from
  YAML files; nothing is trained.
- **Pre-registration.** Designs and analyses were written down and hashed before each result
  ([`eval/PREREG-BUILD.md`](../eval/PREREG-BUILD.md), earlier spikes in [`eval/spikes/PREREG.md`](../eval/spikes/PREREG.md) and [`PREREG-ADDENDA.md`](../eval/spikes/PREREG-ADDENDA.md)).

## 2. Results on human labels
| Test | n | Querschnitt | Baseline, same items |
|---|---|---|---|
| APS chapter vs APS editors, 927 federal affairs never used while designing (S25, held out) | 927 | 0.696 [0.666, 0.726]; top 3 0.839; the 67.3% passing without a check (recalibrated p ≥ 0.7) 0.812 [0.779, 0.842], the rest 0.458; subtopic top 1 0.497, hierarchical F1 0.604, macro-F1 0.647 (computed after the result) | plain list prompting 0.654 [0.623, 0.685] (n 918), paired +0.041 [+0.016, +0.067] · keywords 0.186 |
| APS chapter vs APS editors, the 1,357 federal affairs the shipped design was chosen on (S9/S16) | 1,357 | 0.740 [0.716, 0.764] as shipped; the 66.8% passing without a check (cross-fitted) 0.864 [0.840, 0.886]; formerly: where the two readings agree (64% of affairs) 0.826 [0.800, 0.851] | plain list prompting 0.655 · keywords 0.191 · majority 0.079 |
| APS subtopic vs APS editors, end to end (S9) | 1,221 | top-1 0.520 · top-3 0.677 | chapter step → best subtopic 0.469 |
| Bern: lead directorate vs the Grand Council's own field, 2025–26 (S18) | 531 | 0.651 [0.610, 0.691] German titles · 0.650 French titles | keywords 0.525 / 0.512 · majority 0.214 |
| Basel-Stadt: the canton's own 46 themes vs its hand-assigned «Thema 1», 2019–24 (S20) | 2,437 | 0.498 [0.478, 0.518]; Thema 1 or 2: 0.605; top 3: 0.665 | keywords 0.181 · majority 0.053 |
| — with five of Basel's own labelled affairs as examples, other half of the data (S21) | 2,437 | 0.526 [0.506, 0.547]; paired +0.028 [+0.014, +0.043]; top 3: 0.711 | names only: 0.498 |
| "Digitalisierung": the 30 affairs DVS curates by hand (question written with them in view) | 30 | 27 recognised | keywords 21 |
| Federal Sachbereiche vs Parliament's own Curia tags (S3/S5) | 200 | micro-F1 0.654 | BFH model, trained on 15,007 tagged affairs: 0.687 |

The held-out test (S25) is the shipped pipeline, unchanged, on 927 APS-labelled federal affairs that appear in no design
set and no example pool: 0.696 top-1, 0.839 top-3, ahead of plain list prompting on the same affairs by +0.041
[+0.016, +0.067] (pre-registered as S25b after the S25 result). It is below the 0.740 on the affairs the design was chosen on, which is
the expected direction for a held-out set. The lane carries over: 67.3% pass without a check and are right in 0.812, the
rest go to a person (0.458). The lane separates confident from doubtful rows on every human-labelled set where it was
measured: on the 1,357 design affairs the 66.8% passing without a check (cross-fitted) are right in 0.864, the rest in 0.491; by reading agreement,
0.826 vs 0.586; on Basel-Stadt with examples, by reading agreement, 0.651 vs 0.373. A partner's own labels raise
accuracy without any training step: on Basel-Stadt by +0.028 (S21), on the federal APS affairs by +0.067 (S9).

## 3. Where no human labels exist: a blind AI judge
**Evidence on production rows (S23):** for 200 random stored quotes of 2026, a blind judge (two runs, κ 0.92, tie-break)
finds that the quoted sentence supports the topic in 0.815 [0.755, 0.863] of cases (chapter quotes 0.830, Digitalisierung
0.800); the quote is an exact substring at its stored offsets in 198 of 198 affairs whose text has not changed since.

For "Digitalisierung" across all Swiss parliaments in 2026 and for cantonal and communal APS chapters, gold comes from a
blind AI judge (two runs of a Claude model + a tie-break run, cross-checked by the open-weights Qwen-SEA-LION). Against
human labels the judge matches APS editors on 0.790 of chapters and says yes to 27 of the 30 DVS items. Against that judge,
Querschnitt's "Digitalisierung" flags agree in 0.905 [0.865, 0.945] of cases (keyword hits: 0.756), over the full 2026
census of Swiss parliaments (14,512 affairs, 1 Jan–6 Oct): Querschnitt flags 651 affairs in 57 parliaments; the judge
estimates 893 [656, 1,191] digitalisation affairs in total.

On the production run itself, 200 random communal affairs of 2026 were judged blind (two runs, κ 0.94, tie-break on the
11 disagreements): the shipped chapter matches the judge's consensus in 0.640 [0.571, 0.704] (keywords 0.150, majority
0.135); where the readings agree 0.677, in the please-check lane 0.511; German 0.631, French 0.687, Italian 0.625.

**New topics defined in one sentence (S19, S26, S27):** for wolves, heat protection and AI in schools over Aug–Oct 2026,
every affair the judge marks relevant is flagged, but narrow topics over-flag (precision of flags 0.225 / 0.670 / 0.136; keyword
hits 0.500 / 0.900 / 0.750, which miss some relevant affairs). Thirty editor decisions shown as examples help a little on heat
(+0.038 [+0.018, +0.060]) and not measurably on wolves. A second question on the flags only — is the topic central or merely
touched on? — raises precision to 0.444 / 0.770 / 0.250 (heat +0.100 [+0.069, +0.132]) and keeps 0.444 / 0.969 / 1.000 of the
relevant affairs; so unverified flags are not dropped but go to the please-check lane.

## 4. Neutrality
No measurable difference between the languages on human labels: the same 1,350 APS-labelled federal affairs scored from the
Italian text give 0.702, from the German text 0.703 (difference +0.0007 [−0.020, +0.021], S22). Between German and French: Bern directorates +0.001 [−0.031, +0.034] (same affairs, both
titles); federal APS chapters from German vs French text +0.016 [−0.003, +0.037]. Chapter accuracy across the six main
parties differs too little to measure with these sample sizes (SP 0.701 … Grüne 0.578 on n 95, overall p = 0.47). What does differ is the submitter type: Federal Council business is easier than
members' motions (0.792 vs 0.653), and quality is reported per submitter type.

## 5. Runtime and cost
Measured on the corpus run at Public AI list price ([`eval/cost/results.json`](../eval/cost/results.json)): USD 0.333 per
1,000 affairs for chapter, subtopic and one ad-hoc topic; about 61.5 minutes per 1,000 affairs at the job's own
0.969 requests/s on a shared key. Projection for all 326,123 OPD affairs (chapter step, not run):
843,173 requests, USD 102.24, about 241.8 h at that rate; wall time, not money, sets the schedule.

## 6. Limits
- On fresh federal affairs the chapter is right in 0.696 and the pass lane in 0.812, below the 0.740 and 0.864 of the design
  set; the recalibration map was fitted on the design set and is refitted per build.
- Subtopics are suggestions (0.520 top-1), never a lane of their own.
- Fine-grained cantonal schemes without descriptions are harder (Basel-Stadt 46 themes: 0.498); the lane separates the
  confident half from the rest.
- Title-only cantonal affairs are the hardest input; coverage and title-only share are reported per parliament.
- On the Federal Parliament's own multi-tag task the trained BFH model is ahead (0.687 vs 0.654, not significant).
- The DVS 27/30 is not held out: the yes/no question and its cut-off were written with those items in view.
- Where gold is the AI judge, figures are agreement with that judge and are labelled as such.
