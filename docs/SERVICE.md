# Service layer: store, API, Neues Thema, nightly delta, eval

Everything around the engine: the versioned `topics` store (SQLite or Postgres), the HTTP API of docs/CONTRACT.md §2
with the app at `/`, the Neues-Thema backend (a topic in one sentence, streamed decisions), the nightly export delta,
`make eval GOLD=…`, packaging (Makefile, Dockerfile, compose profiles, CI) and the tests. Model calls in tests go to a
fake OpenAI-compatible endpoint only.

## Run

```sh
make install                         # uv venv .venv (Python 3.12) + editable install with dev and Postgres extras
make run                             # API + app on SQLite with the shipped data -> http://127.0.0.1:8000
make test                            # 50 tests (+1 Postgres test when QS_TEST_PG_DSN is set), fake endpoint, ~16 s
make eval GOLD=data/eval/gold_dvs30.csv          # recall + misses by level for a positives list
make eval GOLD=data/eval/gold_aps_s9.csv         # APS editors' chapters (multi-class)
make delta                           # nightly: fresh OPD export -> new/changed affairs -> batch -> rows (SINCE=yesterday)
make delta-plan                      # robots.txt + export index only: what would be downloaded
make smoke                           # load, start, /health + /metrics, stop (CI)
docker compose --profile full up -d  # Postgres + API + app + nightly
QS_PG_DSN=postgresql://… docker compose --profile lite up -d   # nightly chapter-only delta into an existing Postgres
```

`make run` loads, once (`--if-empty`), the first of: `data/inputs.jsonl.gz` + `data/topics.jsonl.gz`; the app's static
export `app/data/` (affair summaries from `affairs.json`/`bodies.json`/`detail/`, rows from `topics.jsonl.gz`, written by
`querschnitt export --topics-file`); else the test sample (80 OPD affairs, 504 synthetic rows marked `model: fixture`).
The API serves `app/` at `/` when `app/index.html` exists.

| Variable | Default | |
|---|---|---|
| `QS_DB` / `QS_PG_DSN` | `data/querschnitt.sqlite` / – | store; Postgres when the DSN is set |
| `QS_BASE_URL`, `QS_MODEL`, `QS_API_KEY` (or `QS_KEY_FILE`) | Public AI, `swiss-ai/apertus-v1.5-8b` | endpoint (client.Endpoint.from_env) |
| `QS_MAX_RATE` | 1.6 (nightly 1.0) | requests/s ceiling of this process |
| `QS_ADHOC_CONC`, `QS_ADHOC_CAP`, `QS_ADHOC_MAX_CALLS`, `QS_ADHOC_LEDGER` | 3, USD 2, –, `runs/adhoc/ledger.jsonl` | Neues Thema limits |
| `QS_SCORED_SINCE` | 2025-01-01 | Neues Thema reads every affair from here on; before it, the candidate step |
| `QS_SCOPE_SINCE` | 2025-01-01 | `pending` and the nightly's scope for new affairs |
| `QS_EXPORT_DIR`, `QS_INPUTS`, `QS_RUN_DIR` | `data/opd`, `data/inputs.jsonl.gz`, `runs/main` | nightly paths |
| `QS_PROFILE`, `QS_STEPS` | full, the batch's default | `lite` = chapter step only |
| `QS_NIGHTLY_AT` | 02:30 | `querschnitt nightly` |

## What exists

| File | |
|---|---|
| `sql/topics.sql` | Postgres DDL, ready to propose upstream: `topics` (CONTRACT §1, checks on lane/status/provenance, partial indexes on current rows, `topics_current` view) + `qs_affairs`, `qs_runs` (prefixed so they never collide with OPD tables in a shared database) |
| `sql/topics.sqlite.sql` | the SQLite equivalent (ISO-8601 UTC text timestamps, JSON text evidence) |
| `src/querschnitt/store.py` | `Store` (one class, both dialects), `load_topics` (jsonl, jsonl.gz, parquet), `load_affairs` (inputs), `load_affairs_export` (static export), reads, `decide`, `changes`, `coverage`, `pending`, `metrics`, run log |
| `src/querschnitt/api.py` | FastAPI: every CONTRACT §2 endpoint + `/schemes`, `/adhoc/{slug}` (state), `/adhoc/{slug}/stop`, `PUT /adhoc/{slug}/terms`, `POST /adhoc/{slug}/save`; CORS for localhost; app at `/` |
| `src/querschnitt/adhoc.py` | Neues Thema |
| `src/querschnitt/evaluate.py` | `querschnitt eval` / `make eval` |
| `src/querschnitt/cli.py` | `querschnitt build-inputs · run · load · serve · delta · nightly · eval · metrics · export` (`run` = `batch`, `export` = the lead's `export.main`) |
| `src/querschnitt/net.py` | downloads: published export files only, RFC 9309 robots check (ported from gegenprobe), fail closed |
| `src/querschnitt/fake_endpoint.py` | fake OpenAI-compatible endpoint (A/B top_logprobs by yes words, peaked codes for chapter/subtopic/evidence, topic JSON for generation; refuses a system message) |
| `tools/gold_csv.py` | `data/eval/gold_aps_s9.csv` (1,357 APS editors' chapters, S9) and `data/eval/gold_dvs30.csv` (the 30 public DVS items, S15) |
| `tools/adhoc_live_check.py` | Neues Thema end to end against a running API (POST + SSE), timeline per topic |
| `Makefile`, `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `.github/workflows/ci.yml` | packaging |
| `tests/test_{store,api,eval,adhoc,net,delta}.py`, `tests/conftest.py`, `tests/fixtures/{inputs,topics}_sample.jsonl` | tests |

## API

| | |
|---|---|
| `GET /affairs/{id}/topics[?scheme=&history=true]` | `{affair, topics}`; current rows, or every version with `history` |
| `GET /topics/{scheme}/{code}/affairs?from=&to=&body=&level=&lang=&lane=&status=&rank=1&limit=&offset=` | `{scheme, code, label, total, rows}`, newest affair first, each row with its affair summary. Codes in short form work: `/topics/aps/1.7.2./affairs`, `/topics/adhoc/digitalisierung/yes/affairs`, `/topics/be-directorates/BKD/affairs`. `level` = parliament level (federal, cantonal, communal) |
| `POST /affairs/{id}/topics/{code}/confirm` · `/reject` | body `{"by": "…", "scheme": "…"}` (scheme inferred from the code when absent; `by` required; codes checked against the scheme) → the new row |
| `GET /changes?since=ISO\|yesterday[&scheme=]` | rows whose `valid_from` or `valid_to` is after `since` |
| `GET /coverage[?scheme=aps]` | per body: affairs, scored, scored share, title-only share (scored affairs without text), covered_from (first year from which every later year has scored share ≥ 0.9); cached on the store state |
| `POST /adhoc` | `{sentence, lang, period?, from?, to?, examples?, terms?, limit?}` → `{slug, topic, terms, terms_pending, period, stream}` |
| `GET /adhoc/{slug}/stream` | SSE: `topic`, `terms`, then per affair `decision {id, p, flag, t, lane, sample, title, body, parl, level, lang, date, p_a, p_b, build, prompt_id}` and `progress {read, flagged, seconds, total, line: "read 50 / flagged 4 / 12.6 s"}`, last `done` (summary, outside-sample estimate). `Last-Event-ID` / `?from=` resume |
| `GET /health`, `GET /metrics[?format=line]` | `/metrics`: affairs, scored, rows, pending, builds, last run (wall s, list-price USD, pending) and the one-line form |

Every row carries `label` {de, fr, it} from the scheme files.

## Store and versioning (decisions)
- A row is never changed except to close it (`valid_to`). Loading compares each (affair, scheme, level, rank) with the
  latest machine row for that key: identical content is skipped (reloads are idempotent), changed content (code, p,
  lane, evidence, build, prompt, input hash, …) closes the current row and adds a new one, and keys that vanish from a
  re-scored affair are closed. `valid_from` is the load time, so `/changes?since=` sees exactly what a sync missed.
- `confirm` adds a `provenance = confirmed`, `status = confirmed` row (who, when; p, evidence, build and prompt copied
  from the machine row it decides) and closes the current rows of that scheme at that level; `reject` adds a
  `rejected` row and closes the rows with that code. The machine rows stay in the history, and a later identical reload
  does not bring them back. If the affair's input changes, the nightly adds a new machine row beside the decision.
- `pending` = affairs in scope whose current input hash has no current machine row (new or changed, waiting for the
  batch). Affairs loaded from the static export carry no input hash and never count as pending.
- One `Store` class serves both dialects (`?` → `%s`, `CAST(? AS jsonb)`, `RETURNING`); the whole test suite also runs
  on Postgres (`QS_TEST_ALL_PG=1 QS_TEST_PG_DSN=…`). Verified locally on PostgreSQL from the `pgserver` wheel: 31 store,
  API, eval and Neues-Thema tests and both delta tests pass; CI runs the same suite against a Postgres 16 service.

## Neues Thema (decisions and the live check)
- Topic: one plain generation request (user message only, no system message, no prefill) for the name in de/fr/it and
  a literal translation of the sentence; the scope note in the sentence's own language is the sentence itself. A
  translation longer than 1.6 × the sentence + 30 characters is treated as a paraphrase and dropped (name only).
  Unparseable output falls back to the sentence verbatim in all three frames. The question uses the frame of
  `digitalisierung.yaml`, so `prompts.yesno_prompt` is unchanged and the decisions are the engine's `yn` calls.
- Terms: a second request, in parallel and off the critical path; a term is kept only if it occurs in corpus titles
  (count shown), and marked `broad` (not used for candidates) when it occurs in more than 0.5% of its language's titles.
- Period: default the 7 days ending at the newest begin date with ≥ 20 affairs (the last days of an export are sparse:
  on the 11 Oct export that is 30 Sep – 6 Oct, 626 affairs, S13's week). Inside the scored slice every affair is read;
  before it, candidates = title hits of the kept terms ∪ affairs whose stored APS subtopic (rank ≤ 3) Apertus names as
  able to hold the topic, plus a random outside sample (40; a third of `limit` in a capped run) whose flag rate and
  Wilson interval estimate the misses.
- Decisions: order a, order b when 0.1 < p < 0.9; p, flag and lane by `compose.yn_decision` (the nightly rows' rule);
  3 worker threads, newest first. The first served build is locked for the process; a different build stops the run.
- Save: `schemes/adhoc/<slug>.yaml` (id, names, question, answer_yes, cutoff 0.5, examples as `{title, match}`, terms,
  subtopics, sentence; no bare `yes:` key) and the run's decisions as `adhoc/<slug>` rows; `delta` picks up every file
  in `schemes/adhoc/` (`scheme.adhoc_topics()`).
- Live check, 14 Oct, Public AI, build `…dd237840` (every call), `Endpoint(max_rate=0.5, conc=2)`, store with all
  326,123 affairs: 110 requests in total (USD 0.0027 at list price; `runs/service-dev/ledger.jsonl`), results in
  `runs/service-dev/adhoc_live/run{1..4}.json`.

| Sentence (lang) | Period | Topic ready | 1st decision | 10th | Read / flagged | All |
|---|---|---|---|---|---|---|
| "Wölfe, Grossraubtiere und Herdenschutz" (de), limit 40 | 30 Sep – 6 Oct | 8.2 s | 9.9 s | 28.0 s | 40 / 1 | 111 s |
| "Protection de la population contre la chaleur et les canicules" (fr), limit 25 | 30 Sep – 6 Oct | 6.1 s | 7.8 s | 35.0 s | 25 / 0 | 78 s |
| "Wölfe, Grossraubtiere und Herdenschutz" (de), limit 18 | 2019 (candidates) | 5.8 s | 14.7 s | 47.4 s | 18 / 4 | 80 s |

  At 0.5 requests/s the decision rate is the cap, not the model (S13 measured 1.14–1.26 decisions/s at 3 workers).
  2019 run: 15,541 affairs in the period, 30 candidates from the terms, 4 flagged among the 12 candidates read (an
  association for a habitat without large predators in Solothurn, livestock guard dogs in the Federal Assembly, «Les Loups vont-ils s'installer
  dans la bergerie ?» in Vaud, a Zurich nature-protection item at p 0.81); outside sample 0 of 6 flagged [0, 0.39].
  Of the five subtopics Apertus named for wolves, two hold the topic (Jagd; Tierhaltung, -versuche und -schutz) and
  three do not (Grundrechte, Öffentliche Ordnung, Innere Sicherheit); the outside sample is what measures that step.
  Fixed during the check: the scope note first carried the prompt's framing in French and Italian (now a literal
  translation), the terms answer was cut at 160 tokens (now 320 and a parser that keeps complete items), the first
  decision came after 21 s (name/scope and terms now run in parallel), and the default week ended on sparse days.

## Eval (`make eval GOLD=…`)
Formats: `affair_id` (positives list), `affair_id,label` (0/1, ja/nein, … or a code), `affair_id,scheme,code`; `,` `;`
or tab. Prediction = the latest machine row at rank 1 (editor rows are never scored as predictions). Proportions with
Wilson 95% intervals, F1 with a 1,000-resample bootstrap; per level, language and body; misses listed; unscored gold
affairs counted and listed. On the store composed from `runs/main` (14 Oct, 12,417 rows): the 30 public DVS items →
recall 0.900 [0.744, 0.965] (27/30), cantonal 23/25, federal 4/5; misses BL 297879, BE 337826, CHE 161610. The 1,357
APS editors' chapters are not yet in a run (pipeline phase `p1b-aps-gold`); the multi-class path is covered by tests.

## Nightly delta (`querschnitt delta --since yesterday`)
1. `fetch_exports`: robots.txt, then `index.json`; downloads `affairs`, `bodies`, `contributors` and the `texts` split
   files whose size or `created` changed (first fetch: 22 files, 371 MB).
2. Affairs new to the store or begun since `--since` → their `docs_<body>` files are streamed, and only those affairs'
   slim rows appended to `docs_slim.jsonl.gz`. OPD refreshed `updated_at` on 82,995 affairs between 10 and 11 Oct, so
   updated-only affairs are rebuilt from titles, texts and the documents already on disk, never re-downloaded.
3. Inputs are rebuilt for touched affairs only (data.build over a filtered view of the export) and merged into the
   previous file; the first night (`--full-rebuild` or no inputs file) builds everything.
4. New or changed input hash, begun ≥ `QS_SCOPE_SINCE` or already scored → `batch run --ids` on the shared run dir
   (cached prompts are never re-sent; refused while a batch with a live PID runs there); `lite` = `--steps ch`.
5. Rows: `compose.decide` + `compose.topic_rows` with `eval/calibration.json` (the export's rule) → `load_topics`.
6. One `qs_runs` line and the printed `/metrics` line: `affairs N · wall S s · list-price USD X · pending P · rows R`.

Measured on the 11 Oct export (no fetch, no model): touched-only rebuild of 83,000 affairs in 132 s, peak RSS 1.56 GB,
all 326,123 input hashes identical to the full build (0 to re-score); the full rebuild takes 86 s at 4.8 GB peak.

## Footprints
| | measured |
|---|---|
| Python deps (site-packages) | 213 MB, of which pyarrow 123 MB and psycopg-binary 17 MB; image = python:3.12-slim + deps + repo (app 40 MB) |
| Export files for the delta | 371 MB (affairs 52, contributors 61, texts 258 MB) + `docs_slim.jsonl.gz` 335 MB; inputs 174 MB |
| Store, 326,123 affairs | SQLite 176 MB file, load 15 s, 35 MB RSS; Postgres `qs_affairs` 158 MB, load 13.5 s, 48 MB RSS |
| Topic rows | Postgres ≈ 450 B per row (5.6 MB for 12,417); 2025–26 slice ≈ 33k affairs × ~7 rows ≈ 0.1 GB |
| Nightly RAM | 1.56 GB peak (touched-only rebuild); first night 4.8 GB |
| Queries (326k affairs) | `/topics/…/affairs` 5–12 ms; `pending` 30–50 ms; coverage 0.6 s Postgres / 3–4 s SQLite, then cached |

`lite` on OPD's ~20 GB VPS: about 0.95 GB of files (exports 371 MB, docs 335 MB, inputs 174 MB, chapter step rows
≈ 1.4 KB per call ≈ 60 MB for 2025–26) plus the `topics` table (chapter rows only, ≈ 45 MB for 2025–26); `full` adds
the API, the app and a Postgres volume.
Docker is not available on the build Mac: CI builds the image, checks it runs as uid 10001, starts it, calls `/health`,
`/metrics` and `/coverage`, and validates both compose profiles.

## Requests to the lead
1. `batch`: pass a topic file's `examples` to `engine.yn` (Neues-Thema files carry editor decisions; the batch ignores
   them now). It changes those topics' prompt ids, so it is your call.
2. `compose.topic_rows`: ad-hoc rows have `prompt_id = None`; Neues-Thema rows carry `pid_a[,pid_b]` — the nightly rows
   could do the same.
3. The calibration rule is duplicated (export.run and cli.compose_rows: `aps-fed` when the decision used examples). A
   `compose.calibrated(calib)` helper both call would keep them in step.
4. `data.parl_name(…, "fr")`: for FR and VD the OPD field gives "Grand Council" (English) as the French name.
5. `.gitignore`: add `data/*.sqlite-wal`, `data/*.sqlite-shm`.
6. Runtime deps include pyarrow and duckdb (≈ 125 MB of the image); the service reads Parquet only when given a
   `.parquet` file. Moving them to an extra would shrink the image; your call.
7. Ship (or let the nightly download) a seed `inputs.jsonl.gz` + `topics.jsonl.gz` so a fresh `full`/`lite` deploy does
   not start with a 4.8 GB full rebuild and a 33k-affair batch.

## Footprint, measured 14 Oct 07:45 (colima, `docker stats`, idle after start)
| profile | containers | memory | image |
|---|---|---|---|
| full | db (postgres:16-alpine) 46.5 MiB · api 42.9 MiB (34,085 topic rows loaded) · nightly 12.7 MiB | ≈ 102 MiB | querschnitt 307 MB |
| lite | nightly-lite 12.6 MiB, into an existing Postgres | ≈ 13 MiB | same image |
Peaks: the nightly input rebuild for changed affairs stays under 1.6 GB (measured by the service build, see "Delta").
Verified: `docker compose --profile full up -d` → `/health` ok, app at `/`, `/coverage`; `--profile lite` with `QS_PG_DSN`.
