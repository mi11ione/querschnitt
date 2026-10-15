# Apache Hop: load Querschnitt topics into OpenParlData

An Apache Hop 2.x project that loads Querschnitt's `topics.jsonl.gz` (rows of `docs/CONTRACT.md` §1) into OPD's `topics`
table (`../opd/migrations/0001_topics.up.sql`). Run with Hop 2.19.0 against PostgreSQL 16.2; details under "Tested".

| File | |
|---|---|
| `load_topics.hwf` | workflow: run the pipeline, then close superseded machine rows (one SQL action); abort without closing anything if the pipeline fails |
| `load_topics.hpl` | pipeline: read → parse → keep machine rows → rename to OPD columns → content hash → compare with the latest machine row → look up `body_id`, `scheme_id`, labels → insert / update |
| `metadata/rdbms/opd.json` | the `opd` PostgreSQL connection, from variables only (no values in the repo) |
| `metadata/*-run-configuration/local.json` | local run configurations |
| `project-config.json` | Hop project file |
| `env/opd-example.json` | environment file to copy and fill (`OPD_DB_HOST`, `OPD_DB_PORT`, `OPD_DB_NAME`, `OPD_DB_USER`, `OPD_DB_PASSWORD`) |

## Pipeline

```
read topics.jsonl.gz ─ parse JSON row ─ machine rows only ─ to OPD columns ─ content hash ─ latest machine row ─ unchanged?
   (text file, gzip)     (JSON input)    provenance=inferred   rename + dates    SHA-256       DB lookup on topics   equal → skip
                                         else → skip                                                                 │ new or changed
                         topics (insert / update) ─ labels (topic_codes) ─ scheme_id (topic_schemes) ─ body_id (bodies)
                         key: affair_id, scheme_key, level, rank, valid_from
```

- **Input:** one JSON object per line, gzip-compressed. `valid_from` / `valid_to` as `2026-10-13T23:57:18Z` (what
  `querschnitt export --topics-file` writes); evidence as `{field, start, end, quote}`.
- **Renames:** `scheme` → `scheme_key`, `build` → `model_build`, `version` → `engine_version`, `evidence.*` →
  `evidence_field`, `evidence_char_start`, `evidence_char_end`, `evidence_quote`.
- **Unchanged rows are skipped:** the content hash (SHA-256 over code, probabilities, lane, evidence, model, build,
  prompt ids, input hash, version) is compared with the latest machine row of the same affair, scheme, level and rank,
  closed or not. A reload of the same file writes nothing, and a machine row closed by a published decision is not
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
`querschnitt delta` has written a new topics file. `-Duser.timezone=UTC` matters: the columns are `timestamp` without
time zone holding UTC, and the JDBC driver writes dates in the JVM's zone. The connection also sends
`SET TIME ZONE 'UTC'` on connect.

## Tested

On 14 Oct 2026, with the Apache Hop 2.19.0 client (official zip from downloads.apache.org, SHA-512 checked) on OpenJDK 21,
against PostgreSQL 16.2 with migrations 0001–0003 applied over stub `affairs` and `bodies` tables filled from the 6 Oct OPD
bulk export (326,124 affairs, 2,411 bodies):

| Run | Input | Result |
|---|---|---|
| 1 | `app/data/topics.jsonl.gz`, 15,386 rows | 15,386 inserted in 4.1 s; every row with `body_id`, `scheme_id` and labels; `valid_from` kept as `2026-10-13 23:57:18` |
| 2 | the same file again | 15,386 skipped as unchanged, 0 written |
| 3 | a new export (`valid_from` two days later, one row with a changed code) after a published rejection of another affair's chapter | 1 inserted, 1 closed at the new `valid_from`; the 15,385 equal rows skipped; the rejection stayed current and its machine row stayed closed |

Both files are well-formed XML (`xmllint --noout`). That test predates three changes, so it has to be repeated before
the merge: the shipped topics file now carries seven schemes, four of which the old seed lacked (a load of it stopped at
the first such row), and evidence quotes from documents; migration 0002 became `0002_topic_schemes_seed.up.sql` with a
`.down.sql` and seeds all seven; 0001 lost the redundant `topics_machine_key` index (the lookup uses
`topics_version_key`). The migrations themselves were re-checked on 15 Oct on PostgreSQL 16.2 without Hop (up, re-run,
reverse rollback 0003 → 0002 → 0001 with data, re-up; the shipped file converted by `../opd/export/to_opd.py
--with-subtopics` loads with every constraint and foreign key satisfied).

Known gaps of the loader (not fixed, because they need a Hop run to verify):
- **Evidence source.** The pipeline reads `evidence.field/start/end/quote` but not `evidence.source` (`text:<id>`,
  `doc:<id>`), so `evidence_text_id` / `evidence_doc_id` stay null and a quote taken from a document is stored with
  `evidence_field = 'text'`. `../opd/export/to_opd.py` maps it correctly (`doc` + `evidence_doc_id`); the pipeline needs
  the same: one more JSON field (`$.evidence.source`) and a split on `:`.
- **`updated_at` on update.** When the insert / update transform updates an existing key (same `valid_from`, changed
  content), `updated_at` is not set, so `?since=` misses that change. Querschnitt never re-sends a changed row with the
  same `valid_from`, so this does not happen with its files; add `updated_at` to the update fields if OPD writes rows
  another way.
- **Vanished keys.** A key that disappears from a re-scored affair (e.g. an affair that loses its third subtopic) keeps
  its last machine row current; Querschnitt's own store closes such keys, and the same rule can be added to the SQL
  action if OPD wants it.
