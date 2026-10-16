# Querschnitt — evaluation report

One topic field for every parliament in OpenParlData: an Année Politique Suisse (APS) chapter with ranked subtopics,
ad-hoc topics defined in one sentence, a lane that says when a person should check, and — where the affair has a text and the evidence step has run — a
quoted sentence from the affair.
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
| Ticino: the canton's own lead department (6 units), in Italian, vs the department it assigns, 2023–26, affairs whose text does not name it (S29) | 1,685 | 0.647 [0.624, 0.670]; readings agree (83%) 0.698, disagree 0.392 | keywords 0.219 · majority 0.194 |
| "Digitalisierung": the 30 affairs DVS curates by hand (question written with them in view) | 30 | 27 recognised | keywords 21 |
| Federal Sachbereiche vs Parliament's own Curia tags (S3/S5) | 200 | micro-F1 0.654 | BFH model, trained on 15,007 tagged affairs: 0.687 |

The held-out test (S25) is the shipped pipeline, unchanged, on 927 APS-labelled federal affairs that appear in no design
set and no example pool: 0.696 top-1, 0.839 top-3, ahead of plain list prompting on the same affairs by +0.041
[+0.016, +0.067] (pre-registered as S25b after the S25 result). A search over five design variants on the design set
(S31, leave-one-out) found none better by the pre-set margin (best +0.0117 [−0.0008, +0.0244]), so the held-out set was
not touched again. A classifier trained on the 1,654 APS labels the shipped design holds (TF-IDF + logistic regression, S34)
reaches 0.563 [0.530, 0.595] on these affairs, +0.133 [+0.098, +0.172] behind; its learning curve still rises (0.380,
0.474, 0.563 at 424, 836, 1,654 labels). The shipped top-1 is below the 0.740 on the affairs the design was chosen on, which is
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
every affair the judge marks relevant among the checked ones is flagged (recall outside them is not measured), but
narrow topics over-flag (precision of flags 0.225 / 0.670 / 0.136; keyword
hits 0.500 / 0.900 / 0.750, which miss some relevant affairs). Thirty editor decisions shown as examples help a little on heat
(+0.038 [+0.018, +0.060]) and not measurably on wolves. A second question on the flags only — is the topic central or merely
touched on? — raises precision to 0.444 / 0.770 / 0.250 (heat +0.100 [+0.069, +0.132]) and keeps 0.444 / 0.969 / 1.000 of the
relevant affairs; so unverified flags are not dropped but go to the please-check lane.

**A scope check for narrow topics (S30, held out):** on three further narrow topics, a generated include/exclude scope
asked on the flags raised precision of flags from 0.642 to 0.761, +0.119 [+0.005, +0.260] pooled, at a recall cost of
−0.099 [−0.250, 0.000]; the two dropped affairs go to a person. The pre-registered rule was met, narrowly, so new topics
carry the scope; keyword lists remain more precise on such topics (0.944) and reach recall 0.850 against 0.800.

## 4. Neutrality
**Party, on the design that ships (S32).** S32 is a re-analysis of rows that already exist; it is not pre-registered and
made no new calls. It scores two sets against the APS editors' chapter: the production rows of the 1,357 S9 federal affairs
(1,340 scored) and the 927 held-out S25 affairs. On the S9 rows, chapter accuracy across the six main parties ranges from
Mitte 0.628 (n 121) to GLP 0.733 (n 45), permutation p 0.4317. Held out, among the four parties with at least 30
affairs, it ranges from SP 0.595 (n 84) to Mitte 0.706 (n 92); Grüne and GLP have only 23 and 22 affairs there. The test
over all six gives p 0.5563. Pooled, p is 0.8726. The largest gaps between parties
with at least 30 affairs are GLP − Mitte +0.105 [−0.059, +0.252] and Mitte − SP +0.111 [−0.037, +0.255]. Both intervals
include zero, but they are wide, so a gap of that size is not ruled out. The lowest party is not the same in the two sets.
The earlier D1 design (S14, same S9 affairs) gave p 0.4655 and SP − Grüne +0.122 [−0.007, +0.242].

**Submitter type.** Members' affairs score below committee and Federal Council business. On the S9 rows: 0.679 vs 0.791
and 0.747 (p 0.0064). Held out: 0.652 vs 0.728 and 0.736 (p 0.1606). Pooled: p 0.0014. Quality is reported per submitter
type.

**Language.** Both shipped-design sets are German: all 1,340 scored S9 inputs, and 926 of the 927 S25 affairs. So they say
nothing about language. The language evidence on human labels comes from other designs:
- Italian vs German text on 1,350 federal affairs: 0.702 vs 0.703, difference +0.0007 [−0.020, +0.021] (S22, D1).
- Bern directorates, DE vs FR titles of the same affairs: +0.001 [−0.031, +0.034].
- Federal APS chapters from German vs French text, one chapter call each: +0.016 [−0.003, +0.037] (S14).

A held-out French or Italian federal slice for the shipped design is still to be measured.


Language on the held-out set (S33): read from the French text, the 927 held-out affairs get 0.675 against 0.696 from the
German, paired −0.021 [−0.050, +0.007]; with the same design in both languages the gap is −0.003 [−0.030, +0.024].
Top-3 is lower in French (−0.056 [−0.085, −0.029]).
## 5. Runtime and cost
Measured on the corpus run at Public AI list price ([`eval/cost/results.json`](../eval/cost/results.json)): USD 0.333 per
1,000 affairs for chapter, subtopic and one ad-hoc topic; about 61.5 minutes per 1,000 affairs at the job's own
0.969 requests/s on a shared key. Projection for all 326,123 OPD affairs (chapter and subtopic steps, not run):
843,173 requests, USD 102.24, about 241.8 h at that rate; wall time, not money, sets the schedule.

The nightly update reads OPD's published export, queues new and changed affairs, and scores the queue. Its first real
night (15 Oct) ran into a Public AI outage: the cut pass queued 49 affairs (33 new) without a model call, and once the
endpoint answered with the same build the drain scored all 49 in 9.6 min for USD 0.0215; 0 were left
([`eval/nightly/2026-10-15.json`](../eval/nightly/2026-10-15.json)).

## 6. Model roles
- **Apertus** (`swiss-ai/apertus-v1.5-8b` on Public AI) makes every topic decision that ships: chapter, subtopic, yes/no
  for an ad-hoc topic, the evidence sentence, and the topic name and search terms Neues Thema generates from one
  sentence. Every call is a user message (no system message); closed choices are read from next-token probabilities.
- **No other model decides anything in the product.** Example retrieval is BM25 in code; recalibration is isotonic
  regression fitted per build.
- **In the evaluation only**, where no human labels exist, blind Claude runs (two independent runs of one model,
  plus a tie-break) serve as the judge, cross-checked by the open-weights Qwen-SEA-LION; every figure measured against them is labelled as
  agreement with that judge (§3), and the judge was checked against APS editors (0.790 of chapters).
- The code was written with Claude Code.

## 7. Path to production at OpenParlData
- **Data model:** one `topics` table in OPD's naming, with migrations up and down, a seed for every scheme file, and an
  optional per-parliament switch for the public feed (`upstream/opd/migrations/`). Inferred and confirmed rows stay
  apart: a confirmation or rejection is a new row with who and when; nothing is overwritten.
- **Load and read:** an Apache Hop pipeline loads the bulk topics file, and a drop-in FastAPI router serves the
  specified endpoints; CI loads the full released file against Postgres on every push and compares every row with the
  reference converter (`upstream/hop/`, `upstream/opd/api/router.py`).
- **Nightly:** reads OPD's published export, queues new and changed affairs, scores the queue, and drains it when the
  endpoint answers again with the same build; editors' decisions become examples for their topics (§5).
- **Model build changes:** a run locks the build it starts with; the recalibration applies only to rows of the build it
  was fitted on; a new build means a refit and the Prüfstand re-run (`upstream/eval-task/`) before its rows ship.
- **Another endpoint:** the probe checks prefill and log-probabilities first; the labelled no-prefill mode scored 0.705
  against 0.696 on the held-out affairs (S28). Day-1 steps and rollback: `upstream/MERGE_REQUEST.md`.

## 8. Limits
- On fresh federal affairs the chapter is right in 0.696 and the pass lane in 0.812, below the 0.740 and 0.864 of the design
  set; the recalibration map was fitted on the design set and is refitted per build. Held out, its calibration error is
  0.0576 (in-sample 0.0211; computed after the results); French and Italian go to `please check` more often at every level.
- Subtopics are suggestions (0.520 top-1), never a lane of their own.
- Fine-grained cantonal schemes without descriptions are harder (Basel-Stadt 46 themes: 0.498), and title-only
  affairs are the hardest input; coverage and title-only share are reported per parliament.
- On the Federal Parliament's own multi-tag task the trained BFH model is ahead (0.687 vs 0.654, not significant).
- The DVS 27/30 is not held out (question and cut-off written with those items in view); where gold is the AI judge,
  figures are agreement with that judge.
