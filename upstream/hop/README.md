# Apache Hop: load Querschnitt topics into OpenParlData

An Apache Hop 2.x project that loads Querschnitt's `topics.jsonl.gz` (rows of `docs/CONTRACT.md` §1) into OPD's `topics`
table (`../opd/migrations/0001_topics.up.sql`). CI runs it on every push with Hop 2.19.0 against PostgreSQL 16 (job `hop`,
details under "Tested").

| File | |
|---|---|
| `load_topics.hwf` | workflow: run the pipeline, then close superseded machine rows (one SQL action); abort without closing anything if the pipeline fails |
| `load_topics.hpl` | pipeline: read → parse → keep machine rows → evidence source → rename to OPD columns → content hash → compare with the latest machine row → look up `body_id`, `scheme_id`, labels → load time → insert / update |
| `metadata/rdbms/opd.json` | the `opd` PostgreSQL connection, from variables only (no values in the repo) |
| `metadata/*-run-configuration/local.json` | local run configurations |
| `project-config.json` | Hop project file |
| `env/opd-example.json` | environment file to copy and fill (`OPD_DB_HOST`, `OPD_DB_PORT`, `OPD_DB_NAME`, `OPD_DB_USER`, `OPD_DB_PASSWORD`) |
| `ci/` | what the CI job `hop` loads and checks: stand-in `affairs` / `bodies`, a fixture from the shipped file, assertions |

## Pipeline

```
read topics.jsonl.gz ─ parse JSON row ─ machine rows only ─ evidence source ─ evidence field ─ to OPD columns ─ content hash ─┐
   (text file, gzip)     (JSON input)    provenance=inferred   text:<id>, doc:<id>  doc:<id> → doc   rename + dates   SHA-256 │
                                         else → skip           → text / doc id      else as given                             │
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
└ latest machine row ─ unchanged? ─ body_id ─ scheme_id ─ labels ─ load time ─ topics (insert / update)
  DB lookup on topics  equal → skip  (bodies)  (topic_     (topic_   updated_at   key: affair_id, scheme_key, level, rank,
                                               schemes)    codes)                 valid_from
```

- **Input:** one JSON object per line, gzip-compressed. `valid_from` / `valid_to` as `2026-10-13T23:57:18Z` (what
  `querschnitt export --topics-file` writes); evidence as `{source, field, start, end, quote}`.
- **Renames:** `scheme` → `scheme_key`, `build` → `model_build`, `version` → `engine_version`, `evidence.*` →
  `evidence_field`, `evidence_char_start`, `evidence_char_end`, `evidence_quote`.
- **Evidence source** (as `../opd/export/to_opd.py`): `evidence.source` `text:<id>` → `evidence_text_id`; `doc:<id>` →
  `evidence_doc_id` and `evidence_field = 'doc'` (the quote is from a document, whatever `evidence.field` says);
  `title`, `title_long` and no evidence leave both ids null.
- **`updated_at`** is the start time of the load on every inserted or updated row, so `?since=` sees both; `created_at` is
  the database default.
- **Unchanged rows are skipped:** the content hash (SHA-256 over code, probabilities, lane, evidence with its text or
  document id, model, build, prompt ids, input hash, version) is compared with the latest machine row of the same
  affair, scheme, level and rank, closed or not. A reload of the same file writes nothing, and a machine row closed by a published decision is not
  brought back by an identical reload.
- **Lookups:** `bodies.body_key` → `body_id`; the active `topic_schemes` version → `scheme_id`; `topic_codes` →
  `label_de/fr/it/rm`, `parent_code`. A scheme missing from `topic_schemes` stops the load (`scheme_id` is NOT NULL);
  apply `0002_topic_schemes_seed.up.sql` first. It seeds every scheme file in `src/querschnitt/schemes/`; an ad-hoc
  topic saved later (Neues Thema writes `schemes/adhoc/<slug>.yaml`, and the nightly scores it) needs its own
  `topic_schemes` row before the next load, or that load stops (rows committed before the failing batch stay; a re-run
  after seeding skips them as unchanged).
- **Only machine rows are loaded.** Decisions (`provenance = 'confirmed'`) come from the parliament or editor, not from
  this file (`../MERGE_REQUEST.md`, "Who owns a row").

The workflow's SQL action then sets `valid_to` on every current machine row that a newer machine row of the same key
supersedes (`valid_to` = the newer row's `valid_from`). Decision rows are never touched.

## Parameters

| Parameter | Default | |
|---|---|---|
| `QS_TOPICS_FILE` | `${PROJECT_HOME}/../../app/data/topics.jsonl.gz` | the topics file (the repo's shipped file by default) |
| `QS_COMMIT_SIZE` | `1000` | rows per commit in the insert / update transform |

Connection variables (`OPD_DB_*`) come from a Hop environment, so credentials never sit in the project.

## Run

Prerequisites: Java 17 or newer, Apache Hop 2.x (client zip from `https://downloads.apache.org/hop/`), and the
migrations `0001`, `0002` (and optionally `0003`) applied to the OPD database.

```sh
cp env/opd-example.json ~/opd-hop-env.json            # fill in the values; keep this file outside the repo
cd <hop-install>
./hop-conf.sh -pc -p querschnitt-opd -ph <repo>/upstream/hop
./hop-conf.sh -ec -e opd -ep querschnitt-opd -eu production -eg ~/opd-hop-env.json
export HOP_OPTIONS="-Xmx2g -Duser.timezone=UTC"         # timestamps are UTC end to end
./hop-run.sh -j querschnitt-opd -e opd -r local -f '${PROJECT_HOME}/load_topics.hwf' \
  -p QS_TOPICS_FILE=/path/to/topics.jsonl.gz
```

Exit code 0 means the load and the closing step both succeeded. For a nightly run, call the same command after
`querschnitt delta` has written a new topics file: the `lite` compose profile writes it at the end of every night
(`/app/out/topics.jsonl.gz`, volume `topics_out`; `docs/SERVICE.md`, "Lite in OpenParlData's Postgres"), and
`querschnitt topics-file --out FILE` writes it from Querschnitt's store at any time. That store's own tables are named
`qs_*`, so it can live in OPD's database without touching `topics`. `-Duser.timezone=UTC` matters: the columns are `timestamp` without
time zone holding UTC, and the JDBC driver writes dates in the JVM's zone. The connection also sends
`SET TIME ZONE 'UTC'` on connect.

## Tested

In CI on every push and pull request: job `hop` in `.github/workflows/ci.yml`, about four minutes. Apache Hop 2.19.0
client (official zip from downloads.apache.org, archive.apache.org once 2.19.0 leaves the mirror; SHA-512 checked against
the `.sha512` file at the same location; cached), Temurin JDK 21, the `postgres:16` service image, migrations 0001–0003 up
over stand-in `affairs` / `bodies` tables (`ci/opd_stand_in.sql`: id and `body_key`, and empty `language` / `begin_date` on affairs for the API router's filters; ids from OPD's export), then
`../opd/tests/smoke.sql`. Every load is the command under "Run" (`hop-run.sh … load_topics.hwf`), and the expected rows
come from `../opd/export/to_opd.py --with-subtopics` on the same file: each loaded row must equal its converted row in
every column except `id`, `created_at`, `updated_at` and `content_hash`.

| Step | Input | Checked |
|---|---|---|
| 1 | `ci/topics.ci.jsonl`: 19 rows of the shipped file (the 12 of `../opd/export/sample/`, three more of one affair incl. a subtopic, two text quotes, a `bs-themen` row) plus one decision row | the 18 machine rows inserted, the decision row skipped; equal to `to_opd.py`; text quote `text:226062` → `evidence_text_id`, document quote `doc:927452` → `evidence_doc_id` with `evidence_field = 'doc'`, title quote without ids; `body_id`, `scheme_id`, labels, subtopic parent; `updated_at` and `created_at` both UTC |
| 2 | the same file again | nothing written: every column of every row as after step 1 |
| 3 | the same file with two rows changed by the job | `p` changed at the same `valid_from`: updated in place, `updated_at` later, `created_at` kept; code changed with a later `valid_from`: inserted, the old row closed at the new `valid_from`; the other 16 rows untouched |
| 4 | one row per code of every scheme file in `src/querschnitt/schemes/` (`ci/every_code.py`, read from the YAML files, not through `gen_seed.py`), each on its own stand-in affair | first `ci/assert_seeded.sql`: every code is in the active seed version of its scheme, else the job fails naming the scheme (a scheme file added without an id in `gen_seed.SCHEME_IDS` fails CI on that push, before any topics file carries its rows); then loaded like step 5 |
| 4b | `ci/topics.app-slice.jsonl.gz`: every row of 2,097 affairs of the app's export of 15 Oct (`ci/make_slice.py`: each code on at least 3 affairs, each code of a parliament's own scheme on 25, each body on 4; 7,398 rows, 89 bodies, all 8 schemes incl. `ti-dipartimenti`), for rows a release does not carry yet | as step 5 |
| 5 | the released topics file (`make data`, release `data-latest`), into an empty table, stand-in rows added for its affairs and bodies (`ci/load_full.sh`) | row count = machine rows of the file; every row equal to `to_opd.py`; `body_id` and `scheme_id` set on every row |
| – | the rows of step 5 | `../opd/tests/test_router.py`: the API router (`../opd/api/router.py`) against these rows, each test in a transaction that is rolled back (`../opd/api/topics.md`, "Implementation") |
| 5b | Querschnitt's own store in the same database (`QS_PG_DSN`): `ci/topics.app-slice.jsonl.gz` loaded with `querschnitt load`, then the store's topics file written with `querschnitt topics-file` (what the `lite` nightly writes) | the store's tables are `qs_*` and OPD's `topics` is unchanged by the store (rows and their checksum); the store's file loaded like step 5, every row equal to `to_opd.py` |
| 6 | migrations down 0003 → 0002 → 0001 with the rows of step 5b in place | 0002 down leaves no topic rows or schemes; 0001 down leaves no `topic*` relation |

The [run of 15 Oct](https://github.com/mi11ione/querschnitt/actions/runs/38744888546) (PostgreSQL 16.15), before step 4
existed: the release step loaded the release of that day, 159,834 rows in 142 s (12,763 document quotes, 7,008 text quotes); the job took
3 min 39 s.

Before CI, on 14 Oct, by hand (Hop 2.19.0, OpenJDK 21, PostgreSQL 16.2, stub tables from the 6 Oct OPD export, the
migrations and topics file of that day, before the evidence mapping): 15,386 rows inserted in 4.1 s; the same file again
skipped all; a new export with one changed code after a published rejection of another affair's chapter inserted 1 row,
closed 1, and left the rejection current and its machine row closed. CI does not repeat that last case (a decision row
already in the table).

Known gap of the loader:
- **Vanished keys.** A key that disappears from a re-scored affair (e.g. an affair that loses its third subtopic) keeps
  its last machine row current; Querschnitt's own store closes such keys, and the same rule can be added to the SQL
  action if OPD wants it.
