# Data contract (engine → store → API → app)

## 1. `topics` row (one per affair × scheme × level × version; Postgres table `topics`, Parquet/CSV bulk file)
| column | type | meaning |
|---|---|---|
| affair_id | int | OPD affair id |
| body_key | text | OPD body key (`CHE`, `BE`, `351`, …) |
| scheme | text | `aps`, `curia28`, `be-directorates`, `adhoc/digitalisierung`, `adhoc/<slug>` |
| level | int | 1 = chapter / yes-no, 2 = subtopic |
| code | text | `aps:1.7.2.`, `aps:kw:1374918`, `aps:none`, `adhoc/digitalisierung:yes` |
| rank | int | 1 = shipped label; 2–3 = ranked suggestions |
| p | real | recalibrated probability (raw `p_raw` kept beside it) |
| p_raw | real | engine probability before recalibration |
| lane | text | `readings_agree` · `please_check` |
| status | text | `suggested` · `confirmed` · `rejected` |
| provenance | text | `inferred` · `confirmed` |
| evidence | jsonb | `{"source": "text:7100" \| "doc:4711" \| "title", "field": "title\|title_long\|text", "char_start": 212, "char_end": 318, "quote": "…"}` |
| model, build | text | served model, `system_fingerprint` |
| cutoffs_id | text | `aps@dd237840` |
| prompt_id | text | sha256[:12] of the exact prompt |
| input_hash | text | sha256[:16] of lang + title + long title + text |
| valid_from, valid_to | timestamptz | versioning; `valid_to` null = current |
| confirmed_by, confirmed_at | text, timestamptz | set by `POST …/confirm|reject` |
| version | text | engine version (`0.6.0`) |
| seq | bigint | change sequence: set on insert and again when the row is closed (the `/changes` cursor) |
| closed_by | text | who closed the row, when a person did (a decision or an undo) |

Generated and confirmed content are always distinguishable (`provenance`). A rejection keeps the inferred row (with `valid_to`) and adds a `rejected` row.

## 2. API (FastAPI; same JSON shapes in the static export)
- `GET /affairs/{id}/topics` → `{affair, topics: [row…]}`
- `GET /topics/{scheme}/{code}/affairs?from=&to=&body=&level=&lang=&lane=&status=&limit=&offset=` → rows + affair summary
- `POST /affairs/{id}/topics/{code}/confirm|reject` body `{"by": "name", "scheme": "aps"}` → new row
- `POST /affairs/{id}/topics/{code}/undo` body `{"by": "name", "scheme": "aps"}` → closes the current decision (closed_by) and restores the rows it had closed; repeating a current confirm/reject by the same person returns it (`unchanged: true`), no new row
- `GET /changes?after=<seq>&since=&scheme=&body=&kind=all|decisions|machine&limit=≤5000` → `{total, n, cursor, next, rows}` in `seq` order; every insert and every close exactly once (upsert by `row_id`, follow `next`); `GET /decisions` = `kind=decisions`
- `GET /coverage` → per body: affairs, scored, scored share, title-only share, covered from year
- `POST /adhoc` body `{"sentence": "...", "lang": "de", "period": "last_week"}` → `{slug, topic}`; `GET /adhoc/{slug}/stream` (SSE: one event per decision `{id, p, flag, t}` + progress)
- `GET /health`, `GET /metrics` (affairs, rows, pending, last run wall time, list-price USD)

## 3. Static export for the app (`app/data/`, built by `querschnitt export`)
- `meta.json` — build, model, generated_at, counts, scored share, version, nightly log line
- `bodies.json` — `[{key, name_de, name_fr, level, canton, lang, lat, lon, n_affairs, n_scored, title_only_share, covered_from}]`
- `affairs.json` — columnar arrays over the scored slice: `id, body, date, type_h, state, lang, title, party, submitter, ch (chapter index 0–24), ch_p, lane, subs ([3 subtopic indices]), dig_p, dig_flag, dig_lane, kw (keyword hit)`
- `detail/<id // 1000>.json` — `{id: {title_long, text_excerpt, text_src, url, evidence {field, start, end, quote}, ch_rank [3], subs [[code, p]×3], dig {p_a, p_b}, build, prompt_ids}}`
- `scheme_aps.json` — chapters (codes, de/fr/it names), subtopics (codes, de names)
- `pruefstand.json` — measured rows (test, n, design, result, interval, baseline, split, file)

## 4. Levels and languages
`level` of a parliament: `federal` (CHE), `cantonal` (two-letter key), `communal` (numeric key = BFS commune number), `other` (LIE).
Every affair is shown in its own language (`lang`); the UI language (DE/FR) switches labels only.
