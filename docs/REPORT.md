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
- **Two readings.** The chapter question is asked in two code orders; in bilingual parliaments the German and the French
  version are the two readings. Readings agree → `readings_agree`; they disagree → `please_check`.
- **Read-back.** One request over the subtopics of the top chapters; the chapter is read back from the chosen subtopic.
  Federal affairs see the five most similar APS-labelled affairs as examples.
- **Schemes are files.** APS, Bern's directorates, Basel-Stadt's own themes and ad-hoc topics run on the same engine from
  YAML files; nothing is trained.
- **Pre-registration.** Designs and analyses were written down and hashed before each result
  ([`eval/PREREG-BUILD.md`](../eval/PREREG-BUILD.md), earlier spikes in `ideation2/PREREG*.md`).

## 2. Results on human labels
| Test | n | Querschnitt | Baseline, same items |
|---|---|---|---|
| APS chapter vs APS editors, held-out federal affairs (S9/S16) | 1,357 | 0.740 [0.717, 0.763] as shipped; where the two readings agree (64% of affairs) 0.826 [0.800, 0.850] | plain list prompting 0.655 · keywords 0.192 · majority 0.080 |
| APS subtopic vs APS editors, end to end (S9) | 1,221 | top-1 0.521 · top-3 0.677 | chapter step → best subtopic 0.469 |
| Bern: lead directorate vs the Grand Council's own field, 2025–26 (S18) | 531 | 0.651 [0.610, 0.691] German titles · 0.650 French titles | keywords 0.525 / 0.512 · majority 0.214 |
| Basel-Stadt: the canton's own 46 themes vs its hand-assigned «Thema 1», 2019–24 (S20) | 2,437 | 0.498 [0.478, 0.518]; Thema 1 or 2: 0.605; top 3: 0.665 | keywords 0.181 · majority 0.053 |
| — with five of Basel's own labelled affairs as examples, other half of the data (S21) | 2,437 | 0.526 [0.507, 0.546]; paired +0.028 [+0.014, +0.043]; top 3: 0.711 | names only: 0.498 |
| "Digitalisierung": the 30 affairs DVS curates by hand (question written with them in view) | 30 | 27 recognised | keywords 21 |
| Federal Sachbereiche vs Parliament's own Curia tags (S3/S5) | 200 | micro-F1 0.654 | BFH model, trained on 15,007 tagged affairs: 0.687 |

The lanes do what they promise on every human-labelled set: on the federal APS affairs precision is 0.826 where the
readings agree and 0.586 where they disagree; on Basel-Stadt with examples 0.651 vs 0.373. A partner's own labels raise
accuracy without any training step: on Basel-Stadt by +0.028 (S21), on the federal APS affairs by +0.067 (S9).

## 3. Where no human labels exist: a blind AI judge
For "Digitalisierung" across all Swiss parliaments in 2026 and for cantonal and communal APS chapters, gold comes from a
blind AI judge (two runs of a Claude model + a tie-break run, cross-checked by the open-weights Qwen-SEA-LION). Against
human labels the judge matches APS editors on 0.790 of chapters and says yes to 27 of the 30 DVS items. Against that judge,
Querschnitt's "Digitalisierung" flags agree in 0.905 [0.865, 0.945] of cases (keyword hits: 0.756), over the full 2026
census of Swiss parliaments (14,512 affairs, 1 Jan–6 Oct): Querschnitt flags 651 affairs in 57 parliaments; the judge
estimates 894 [657, 1,190] digitalisation affairs in total.

On the production run itself, 200 random communal affairs of 2026 were judged blind (two runs, κ 0.94, tie-break on the
11 disagreements): the shipped chapter matches the judge's consensus in 0.640 [0.571, 0.703] (keywords 0.150, majority
0.135); where the readings agree 0.677, in the please-check lane 0.511; German 0.631, French 0.687, Italian 0.625.

## 4. Neutrality
No measurable difference between German and French: Bern directorates +0.002 [−0.030, +0.034] (same affairs, both
titles); federal APS chapters from German vs French text +0.017 [−0.003, +0.036]. No measurable difference in chapter
accuracy among the six main parties. What does differ is the submitter type: Federal Council business is easier than
members' motions (0.792 vs 0.654), and quality is reported per submitter type.

## 5. Runtime and cost
Over the first 27,904 requests of the corpus run, a request cost USD 0.000107 at Public AI list price (mean 1,072 prompt
tokens). Wall time, not money, sets the schedule: the shared key serves about 100 requests a minute. Per-affair cost and
wall time of the full 2025–26 slice are reported when the run completes.

## 6. Limits
- Subtopics are suggestions (0.521 top-1), never a lane of their own.
- Fine-grained cantonal schemes without descriptions are harder (Basel-Stadt 46 themes: 0.498); the lane separates the
  confident half from the rest.
- Title-only cantonal affairs are the hardest input; coverage and title-only share are reported per parliament.
- On the Federal Parliament's own multi-tag task the trained BFH model is ahead (0.687 vs 0.654, not significant).
- The DVS 27/30 is not held out: the yes/no question and its cut-off were written with those items in view.
- Where gold is the AI judge, figures are agreement with that judge and are labelled as such.
