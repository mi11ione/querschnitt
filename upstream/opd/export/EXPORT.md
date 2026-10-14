# Bulk export: topics

Follows OpenParlData's bulk export conventions at `files.openparldata.ch/exports/`: one gzipped NDJSON file per table, one
JSON object per row, the table's own column names, timestamps as naive ISO 8601 in UTC (`2026-10-13T23:57:18`), and an
entry in `index.json` (`entity`, `type`, `format`, `filename`, `url`, `size`, `size_human`, `row_count`, `created`).
Large affair-attached tables (`docs`, `texts`, `speeches`, `news`) are split per body as `<entity>/<entity>_<body_key>.ndjson.gz`
with a `type: split` index entry.

## Files

| File | Entity | Rows | Index type |
|---|---|---|---|
| `topics.ndjson.gz` | `topics` | every row, current and closed (`valid_to`), so a client can rebuild any past state | `single` |
| `topics/topics_<body_key>.ndjson.gz` | `topics` | the same rows, one file per parliament (`topics_CHE`, `topics_BE`, `topics_351`, …) | `split` |
| `topic_schemes.ndjson.gz` | `topic_schemes` | one row per scheme version, with licence and source | `single` |
| `topic_codes.ndjson.gz` | `topic_codes` | codes, labels de/fr/it/rm, parent | `single` |

OPD picks single or split for `topics` the way it does for its other tables: `affairs` (52 MB) is one file, `texts`
(258 MB) is split. On the 2025–26 slice the single file is 313 KB for 12,719 rows (chapters and ad-hoc rows; subtopics held
back, see below); `to_opd.py --split` writes the per-body form. Both shapes of the index entry are in `sample/`.

## Columns

The columns of the `topics` table (`../migrations/0001_topics.up.sql`) in table order, without `content_hash` (internal to
the loader). Machine suggestions and published decisions are told apart by `provenance` (`inferred` / `confirmed`);
`status` is `suggested` on every machine row and `confirmed` or `rejected` on decision rows; decision rows also carry
`confirmed_by`, `confirmed_at` and, when the parliament itself published the decision, `confirmed_by_body_id`.

What a consumer should read:
- the current label of an affair: rows with `valid_to = null`, `rank = 1`, `status != 'rejected'`; a `confirmed` row
  takes precedence over an `inferred` row of the same scheme and level;
- machine rows only: `provenance = 'inferred'`; decisions only: `provenance = 'confirmed'`;
- changes since the last export: `updated_at` after the previous `created` of the index entry.

## Licence and attribution

Querschnitt releases its topic rows under CDLA-Permissive-2.0, a permissive data licence that allows redistribution next to
OPD's CC BY 4.0 data; which licence the OPD export states for the table is OPD's decision. Labels follow the licence of their scheme
(`topic_schemes.licence`). APS chapter codes and keyword identifiers are used as published by Année Politique Suisse;
whether OPD publishes APS subtopic labels and level-2 rows is to be agreed with APS, so the export leaves them out by
default (`to_opd.py --with-subtopics` includes them).

## Producing the files now

Until OPD exports the table itself, `to_opd.py` writes the same files from Querschnitt's `topics.jsonl.gz`:

```sh
python3 upstream/opd/export/to_opd.py --topics app/data/topics.jsonl.gz \
  --bodies ../data/opd-new/bodies.ndjson.gz --out /tmp/opd-export          # add --split, --with-subtopics, --sample 12
```

`sample/topics.sample.ndjson` (12 rows) and `sample/index.fragment*.json` were written this way from the shipped file.
