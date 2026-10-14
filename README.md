# Querschnitt

**One topic field for every Swiss parliament.** Querschnitt gives each OpenParlData affair — federal, cantonal and communal,
German, French and Italian — an Année Politique Suisse (APS) chapter with ranked subtopics, a lane that says when a person
should check, and a quoted sentence from the affair that supports it. A new topic is a file: written once, applied to every
parliament, no training. Every topic decision is made by [Apertus](https://www.swiss-ai.org/apertus), Switzerland's open model.

Built for Hack Apertus Liebefeld (18–19 Oct 2026), challenge «Topic classification for OpenParlData».
Live (static, read-only): https://querschnitt.mi11ion.io

![Überblick: one small Switzerland per topic, every canton shaded by the topic's share of its affairs](docs/img/ueberblick.png)

## Measured
Human labels first. Full table with intervals, baselines and source files: [docs/PRUEFSTAND.md](docs/PRUEFSTAND.md).

| Test | n | Querschnitt | Baseline on the same items |
|---|---|---|---|
| APS chapter vs APS editors, held-out federal affairs, pre-registered | 1,357 | **0.740** [0.716, 0.764] as shipped (five APS-labelled examples, two code orders, chapter read back from the subtopic); where the two readings agree (64% of affairs) 0.826 [0.800, 0.851] | plain list prompting 0.655 · keywords 0.191 |
| "Digitalisierung": the 30 affairs DVS curated by hand on its public page (the question and its 0.5 cut-off were written with these items in view) | 30 | 27 recognised | keywords 21 |
| Bern's lead directorate (scheme swap, 8 directorates) vs the Grand Council's own field, 2025–26, DE / FR titles, pre-registered | 531 | 0.651 [0.610, 0.691] / 0.650; no measurable DE–FR gap (+0.001 [−0.031, +0.034]) | keywords 0.525 / 0.512 · majority 0.214 |
| Basel-Stadt's own 46 topics vs the canton's hand-assigned «Thema 1», all Grand Council affairs 2019–24, scheme handed over as a file (names only), pre-registered | 2,437 | 0.498 [0.478, 0.518]; Thema 1 or 2: 0.605; top 3: 0.665 | keywords 0.181 · majority 0.053 |
| — the same, with five of Basel's own labelled affairs as examples (other half of the data; no training), pre-registered | 2,437 | 0.526 [0.506, 0.547], +0.028 [+0.014, +0.043] paired; top 3: 0.711; where the two readings agree (54.9%): 0.651 | names only: 0.498 |
| Evidence: the quoted sentence supports the topic (blind AI judge) | 120 | 0.850 | — |

## Quick start
```sh
make data                   # the scored data (GitHub release `data-latest`): app export, inputs, topic rows
make run                    # API + app at http://127.0.0.1:8000 (SQLite; no model calls)
make test
make eval GOLD=my.csv       # score any labelled CSV (affair_id,label) against the stored topic rows
```
Model calls need an OpenAI-compatible endpoint serving Apertus (`QS_BASE_URL`, `QS_MODEL`, `QS_API_KEY`); Public AI's
`swiss-ai/apertus-v1.5-8b` route is the default. `python tools/probe_endpoint.py` checks any endpoint (log-probabilities,
prefill, served build, throughput) before a run.

## How it works
- **Closed choices only.** Every classification step — chapter, subtopic, yes/no for an ad-hoc topic, evidence sentence — is
  a choice among listed codes, read from Apertus's next-token probabilities. A label outside the scheme is never stored.
  Asked to name a topic freely, Apertus answered outside the scheme in 36 of 40 affairs; with the list shown, in 0 of 40.
- **Chapter, then subtopic, read back.** Two readings of the chapter question in two code orders; one request over the
  subtopics of the top two or three chapters; the shipped chapter is the one read back from the chosen subtopic. Federal
  affairs see the five most similar APS-labelled affairs as examples (both readings always). Elsewhere the second reading
  runs when the first is below p 0.9 (a single reading at p ≥ 0.9 counts as agreeing).
- **Lanes.** The two readings agree → `readings_agree`; they disagree → `please_check`. For federal affairs the two readings
  are the chapter question with five APS-labelled examples and without them, in two code orders; elsewhere two code orders;
  in bilingual parliaments (Bern, Fribourg, Valais; from OPD's body languages) the German and the French version.
- **Evidence.** One numbered sentence of the affair, chosen by Apertus, checked by code as an exact substring and stored with
  its character offsets.
- **Schemes are files.** `src/querschnitt/schemes/`: `aps.yaml` (24 chapters × 190 subtopics, APS identifiers),
  `be-directorates.yaml` (Bern's 8 directorates), `adhoc/digitalisierung.yaml` (question with scope note in de/fr/it).
  A new scheme or topic is a new file; nothing is trained.
- **Builds are never mixed.** Every row names the served model, its `system_fingerprint`, the prompt id and the input hash;
  a run locks the first build it sees and stops on any other. Prompts are pinned byte-identical to the measured ones by tests.

## Runtime and cost (measured on the corpus run, Public AI list price — [`eval/cost/results.json`](eval/cost/results.json))
- USD 0.333 per 1,000 affairs for chapter, subtopic and one ad-hoc topic (USD 0.314 chapter step alone).
- About 61.5 minutes per 1,000 affairs at this job's own 0.969 requests/s on a key shared with other jobs.
- All 326,123 OPD affairs, chapter step: 843,173 requests, USD 102.24, about 241.8 h at that rate — a projection, not run; a dedicated endpoint shortens it in proportion to its rate.

![Why this label: the chapter read twice, the two readings side by side, the quoted sentence](docs/img/entscheid.png)

## Output
A `topics` row per affair, scheme and rank ([docs/CONTRACT.md](docs/CONTRACT.md); Postgres DDL in [sql/topics.sql](sql/topics.sql)):
`affair_id, scheme, level, code, rank, p, lane, status (suggested|confirmed|rejected), provenance (inferred|confirmed),
evidence {source, char_start, char_end, quote}, model, build, prompt_id, input_hash, valid_from, valid_to`.
Generated and confirmed content stay distinguishable; a correction adds a row and never overwrites one.

## Model roles
Apertus makes every topic decision, through Public AI's route `swiss-ai/apertus-v1.5-8b` (served build `…dd237840`; its
16-way parallel build tag and an MMLU spot check in our notes point to the 70B weights behind this route name, see
[upstream/APERTUS-NOTES.md](upstream/APERTUS-NOTES.md)). Retrieval of examples is BM25 in code. In the
evaluation only, blind Claude runs and the open-weights Qwen-SEA-LION serve as annotators where no human labels exist; every
figure measured against them is labelled as agreement with that judge. The code was written with Claude Code.

## Licences
Code Apache-2.0 ([LICENSE](LICENSE)); documentation CC BY 4.0; the topics file CDLA-Permissive-2.0. Source data: OpenParlData
bulk exports (files.openparldata.ch). APS chapter codes and subtopic identifiers as published by Année Politique Suisse.
