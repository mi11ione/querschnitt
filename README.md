# Querschnitt

**One topic field for every parliament in OpenParlData.** Querschnitt gives each OpenParlData affair — federal, cantonal and communal,
German, French and Italian — an Année Politique Suisse (APS) chapter with ranked subtopics, a lane that says when a person
should check, and, where the affair has a text and the evidence step has run, the sentence Apertus cites as evidence, quoted
at its exact place in the text. Every topic decision is made by [Apertus](https://www.swiss-ai.org/apertus), Switzerland's
open model. A new topic or a parliament's own scheme is a file: written once, applied to every parliament, no training.
Scored: nearly every affair since January 2025.

Built for Hack Apertus Liebefeld (18–19 Oct 2026), challenge «Topic classification for OpenParlData».
Live (static, read-only): https://querschnitt.mi11ion.io

![Überblick: one map per topic, cantons shaded by share](docs/img/ueberblick.png)

## Measured
Tests marked pre-registered were written down and hashed before their result ([eval/PREREG-BUILD.md](eval/PREREG-BUILD.md)).

| Test | n | Querschnitt | Baseline on the same items |
|---|---|---|---|
| APS chapter vs APS editors, federal affairs never used while designing (pre-registered) | 927 | **0.696** [0.666, 0.726]; top 3 0.839; the 67.3% that pass without a check (recalibrated p ≥ 0.7, a rule committed before the first call) 0.812 [0.779, 0.842], the rest 0.458 | plain list prompting 0.654 [0.623, 0.685] (n 918; paired +0.041 [+0.016, +0.067]) · TF-IDF classifier trained on the shipped design's 1,654 APS labels 0.563 [0.530, 0.595] (paired +0.133 [+0.098, +0.172]) · keywords 0.186 |
| The same 927, read from the French text | 927 | 0.675 [0.644, 0.705]; French − German −0.021 [−0.050, +0.007] | — |
| Bern's 8 directorates as a scheme file vs the Grand Council's lead directorate, DE / FR titles | 531 | 0.651 [0.610, 0.691] / 0.650 | keywords 0.525 / 0.512 · majority 0.214 |
| Basel-Stadt's 46 themes vs the canton's «Thema 1»; names only / with five of Basel's labelled affairs as examples | 2,437 | 0.498 [0.478, 0.518] / 0.526 [0.506, 0.547] | keywords 0.181 · majority 0.053 |
| Ticino, in Italian: its 6 lead units vs the one the canton assigns, where the text does not name it (pre-registered) | 1,685 | 0.647 [0.624, 0.670] | keywords 0.219 · majority 0.194 |
| "Digitalisierung" in every parliament, 2026: 14,512 affairs decided, 651 flagged; stratified sample, agreement with a blind AI judge (pre-registered) | 453 | precision 0.905 [0.865, 0.945]; recall 0.659 [0.491, 0.900] | keywords: precision 0.756 |
| Evidence on production rows: the stored quote supports the topic (blind AI judge) | 200 | 0.815 [0.755, 0.863]; exact substring at the stored offsets 198/198 | — |
| Three narrow topics defined in one sentence (light pollution · drones · pesticides), held out, with a generated scope check on the flags (pre-registered) | 399 judged | precision of flags 0.642 → 0.761, +0.119 [+0.005, +0.260]; recall −0.099 [−0.250, 0.000] | hand-written keywords: precision 0.944, recall 0.850 |
| "Digitalisierung": the 30 affairs DVS curated by hand (the question was written with these items in view) | 30 | 27 recognised | keywords 21 |
| Cost, corpus run, Public AI list price ([eval/cost/results.json](eval/cost/results.json)) | — | USD 0.333 per 1,000 affairs (chapter, subtopic, one ad-hoc topic) | — |

Further tests (design set, Italian, no prefill, three earlier narrow topics, neutrality): [docs/PRUEFSTAND.md](docs/PRUEFSTAND.md)
· short report: [docs/REPORT.md](docs/REPORT.md).

## Quick start
```sh
make install                # .venv, Python 3.12
make data                   # scored data from release `data-latest`
make run                    # API + app at http://127.0.0.1:8000 (SQLite; no model calls)
make test                   # fake model endpoint, no network
make eval GOLD=my.csv       # score any labelled CSV (affair_id,label)
make claims                 # every number in README and docs backed
```
Model calls need an OpenAI-compatible Apertus endpoint (`QS_BASE_URL`, `QS_MODEL`, `QS_API_KEY`) with assistant prefill
and `top_logprobs`; Public AI is the default. `python tools/probe_endpoint.py` checks one; `QS_PREFILL=0` runs without prefill ([docs/SERVICE.md](docs/SERVICE.md)).

## How it works
- **Closed choices only.** Chapter, subtopic, ad-hoc yes/no and evidence sentence are each a choice among listed codes, read
  from Apertus's next-token probabilities; a label outside the scheme is never stored (asked to name a topic freely,
  Apertus answered outside the scheme in 36 of 40 affairs; with the list shown, in 0 of 40).
- **Two readings.** Federal affairs are read with and without retrieved APS examples; others in a second code order when the
  first is below p 0.9; bilingual parliaments in German and French. Both feed the confidence and are shown as the explanation.
- **Lane.** `please_check` when the recalibrated p is below 0.7 or the German and French readings disagree; otherwise `pass`.
- **Read back from the subtopic.** One request over the subtopics of the top chapters; the chapter is read back from the
  chosen subtopic; the top three subtopics ship ranked.
- **Evidence.** One numbered sentence chosen by Apertus, checked by code as an exact substring, stored with its offsets.
- **Schemes are files** (`src/querschnitt/schemes/`): `aps.yaml` (24 chapters × 190 subtopics), `be-directorates.yaml`,
  `bs-themen.yaml`, `adhoc/*.yaml`.
- **Builds are never mixed.** Every row names the served model, build, prompt id and input hash; a run stops on any other build.

![Why this label: German and French readings disagree, so a person checks](docs/img/entscheid.png)

## Integration with OpenParlData
- **Output:** one topic row per affair, scheme and rank, with evidence, provenance and build ([docs/CONTRACT.md](docs/CONTRACT.md); OPD migration
  [upstream/opd/migrations/0001_topics.up.sql](upstream/opd/migrations/0001_topics.up.sql)). A correction adds a row, never overwrites.
- **API:** `GET /affairs/{id}/topics`, `GET /topics/{scheme}/{code}/affairs`, `POST …/confirm|reject|undo`,
  `GET /changes?after=<seq>`, `POST /adhoc`.
- **Upstream pack** ([docs/UPSTREAM.md](docs/UPSTREAM.md)): migrations in OPD's naming, an Apache Hop pipeline that loads the
  topics file, the Prüfstand as an evaluation task for any Apertus build.
- **Operations:** `docker compose --profile lite` (nightly steps into an existing Postgres) or `--profile full`; the nightly
  delta reads OPD's published exports ([docs/SERVICE.md](docs/SERVICE.md)).

## Runtime and cost
- About 61.5 minutes per 1,000 affairs at the corpus run's average 0.969 requests/s on a shared key; a dedicated endpoint
  shortens it in proportion to its rate.
- All 326,123 OPD affairs, chapter and subtopic steps: 843,173 requests, USD 102.24, about 241.8 h — a projection
  ([eval/cost/results.json](eval/cost/results.json)).

## Model roles
Apertus makes every topic decision, through Public AI's route `swiss-ai/apertus-v1.5-8b` (served build `…dd237840` on every
call reported here); figures hold for the model behind that route and build ([upstream/APERTUS-NOTES.md](upstream/APERTUS-NOTES.md)).
Example retrieval is BM25 in code. In the evaluation only, blind Claude runs and the open-weights Qwen-SEA-LION serve as
annotators where no human labels exist; every figure measured against them is labelled as agreement with that judge. The code
was written with Claude Code.

## Licences
Code Apache-2.0 ([LICENSE](LICENSE)); documentation CC BY 4.0; the topics file CDLA-Permissive-2.0. Source data:
OpenParlData bulk exports (files.openparldata.ch); Basel-Stadt topics OGD 100086 (CC BY 4.0, Kantons- und
Stadtentwicklung Basel-Stadt); boundaries BFS GEOSTAT / swisstopo via swiss-maps 4.7.0. APS chapter codes and subtopic
identifiers as published by Année Politique Suisse.
