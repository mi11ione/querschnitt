# Upstream pack

Files in `upstream/` that hand Querschnitt's results to the people who maintain the data and the model. Opening the merge
request and publishing anything are Roman's decisions; nothing here has been sent anywhere.

| Folder / file | What it is | For |
|---|---|---|
| `upstream/MERGE_REQUEST.md` | the merge-request description: what it adds, data model, measured quality, versioning, build changes, who owns a row, licensing, day-1 steps for the OPD admin, rollback, known gaps, open questions, a proposed CHANGELOG entry and issue text | OpenParlData (Christian Gutknecht) |
| `upstream/opd/` | the merge request's files: `migrations/` (`NNNN_name.up.sql` / `.down.sql`: tables `topic_schemes`, `topic_codes`, `topics`, indexes; seed of every scheme the topics file carries; an optional per-body feed switch), `tools/gen_seed.py` (the seed, and later per-scheme migrations), `tests/smoke.sql`, `api/` (resource description for `/v1/topics/` and `/v1/affairs/{id}/topics`, Pydantic models), `export/` (`topics.ndjson.gz` spec, converter, samples) | OpenParlData |
| `upstream/hop/` | Apache Hop 2.x project: `load_topics.hwf` + `load_topics.hpl` load `topics.jsonl.gz` into `topics`, skip unchanged rows, close superseded ones | OpenParlData's ETL |
| `upstream/eval-task/` | the Prüfstand as a re-runnable task for any Apertus build: task card `TASK.md`, spec `task.yaml`, runner `run.py`, frozen items (1,357 APS-labelled federal affairs; the 30 DVS affairs), rendered prompts | the swiss-ai evaluation work |
| `upstream/APERTUS-NOTES.md` | measured Apertus behaviour in a closed-choice classifier, each with n and source file | the swiss-ai team |

## State

- Migrations 0001–0003 (as they are now) on PostgreSQL 16.2, 15 Oct, over stub `affairs` / `bodies` from OPD's export of
  that day: up, up again (no-op), reverse rollback with data, up again; the shipped topics file converted by
  `to_opd.py --with-subtopics` loads with every constraint and foreign key satisfied; `upstream/opd/tests/smoke.sql` passes.
- The Hop workflow ran on 14 Oct with Hop 2.19.0 against the migrations and topics file of that day: first load,
  identical reload (all skipped), a changed row (one new version, one closed), a published rejection left in place
  (`upstream/hop/README.md`, "Tested"). Since then the file carries four more schemes and the migrations changed, so
  that run has to be repeated; the pipeline also still drops `evidence.source` (`upstream/hop/README.md`, known gaps).
- `eval-task/run.py --score-only` on the stored S9/S16/S8 rows reproduces the published results; a smoke run against the
  repo's fake endpoint checked the call path and resume. No model was called while building the pack.
- `python3 tools/claims_check.py upstream/APERTUS-NOTES.md` passes; its sources are rows in `eval/claims.tsv`.

## Opening the merge request (Roman)

1. Ask Christian at the deep dive which repository and paths the data model lives in (OPD's issue tracker:
   `gitlab.com/opendata.ch/openparldatach/data-infrastructure`), and the open questions in `upstream/MERGE_REQUEST.md`
   (APS subtopic labels, `consultation_topics` vocabulary, which ad-hoc topics, single or split export, the feed switch,
   licence statement, who runs the nightly).
2. Fork, branch, copy `upstream/opd/` and `upstream/hop/` to the agreed paths, and use `upstream/MERGE_REQUEST.md` as the
   description (its known gaps first: the Hop evidence mapping and a Hop re-run).
3. Before pushing: `python3 upstream/opd/tools/gen_seed.py` (regenerates the seed; it stops on a scheme file without a
   fixed id) and the checks under "State".

## Publishing the rest (Roman)

- Topics file for the scored slice: `python3 upstream/opd/export/to_opd.py --topics app/data/topics.jsonl.gz --bodies
  <opd export>/bodies.ndjson.gz --out <dir>` writes the OPD-shaped files (chapters and ad-hoc rows; subtopics only with
  `--with-subtopics` once APS agrees).
- Eval task and notes: hand `upstream/eval-task/` and `APERTUS-NOTES.md` to the swiss-ai evaluation team in the form they
  ask for. The frozen items carry Curia Vista, OpenParlData and APS content; publishing them follows those sources' terms.
