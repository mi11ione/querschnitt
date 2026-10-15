# Service layer: store, API, Neues Thema, nightly delta, eval

Everything around the engine: the versioned `topics` store (SQLite or Postgres), the HTTP API of docs/CONTRACT.md §2
with the app at `/`, the Neues-Thema backend (a topic in one sentence, streamed decisions), the nightly export delta,
`make eval GOLD=…`, packaging (Makefile, Dockerfile, compose profiles, CI) and the tests. Model calls in tests go to a
fake OpenAI-compatible endpoint only.

## Run

```sh
make install                         # uv venv .venv (Python 3.12) + editable install with dev and Postgres extras
make run                             # API + app on SQLite with the shipped data -> http://127.0.0.1:8000
make test                            # unit, API, delta and export tests (+1 Postgres test when QS_TEST_PG_DSN is set), fake endpoint
make eval GOLD=data/eval/gold_dvs30.csv          # recall + misses by level for a positives list
make eval GOLD=data/eval/gold_aps_s9.csv         # APS editors' chapters (multi-class)
make delta                           # nightly: fresh OPD export -> new/changed affairs -> batch -> rows (SINCE=yesterday)
make delta-plan                      # robots.txt + export index only: what would be downloaded
make data-release                    # dist/querschnitt-data.tar.gz from the current export (checks it; does not publish)
make smoke                           # load, start, /health + /metrics, stop (CI)
docker compose --profile full up -d  # Postgres + API + app + nightly
QS_PG_DSN=postgresql://… docker compose --profile lite up -d   # nightly chapter + subtopic delta into an existing Postgres
```

`make run` loads, once (`--if-empty`), the first of: `data/inputs.jsonl.gz` + `data/topics.jsonl.gz`; the app's static
export `app/data/` (affair summaries from `affairs.json`/`bodies.json`/`detail/`, rows from `topics.jsonl.gz`, written by
`querschnitt export --topics-file`); else the test sample (80 OPD affairs, 504 synthetic rows marked `model: fixture`).
The API serves `app/` at `/` when `app/index.html` exists.

Writes: with `QS_WRITE_TOKEN` set, confirm / reject / undo, `POST /adhoc` and the run's stop / continue / terms / save need
`Authorization: Bearer <token>` (constant-time compare; `401` otherwise); reads stay open. Unset, writes are open and
`serve` logs one warning at startup: keep such an API on localhost (`make run` binds 127.0.0.1) or behind a reverse proxy
that authenticates. The app sends the token when one is stored in the browser (`localStorage.setItem('qs.token', '…')`
in the console); without it the review desk and Neues Thema expect a token-less local API.

| Variable | Default | |
|---|---|---|
| `QS_DB` / `QS_PG_DSN` | `data/querschnitt.sqlite` / – | store; Postgres when the DSN is set |
| `QS_BASE_URL`, `QS_MODEL`, `QS_API_KEY` (or `QS_KEY_FILE`) | Public AI, `swiss-ai/apertus-v1.5-8b` | endpoint (client.Endpoint.from_env) |
| `QS_MAX_RATE` | 1.6 (nightly 1.0) | requests/s ceiling of this process |
| `QS_WRITE_TOKEN` | – | bearer token for every write (above); unset = open, warned at startup |
| `QS_ADHOC_CONC`, `QS_ADHOC_CAP`, `QS_ADHOC_MAX_CALLS`, `QS_ADHOC_LEDGER` | 3, USD 50, –, `runs/adhoc/ledger.jsonl` | Neues Thema limits (`QS_ADHOC_CAP`: the ledger's lifetime total, a safety net; the working cap is `QS_ADHOC_DAILY_USD`) |
| `QS_ADHOC_DAILY_USD` | USD 2 | Neues Thema list-price spend per local day, summed from the ledger; 0 = off |
| `QS_SCORED_SINCE` | 2025-01-01 | Neues Thema reads every affair from here on; before it, the candidate step |
| `QS_SCOPE_SINCE` | 2025-01-01 | `pending` and the nightly's scope for new affairs |
| `QS_EXPORT_DIR`, `QS_INPUTS`, `QS_RUN_DIR` | `data/opd`, `data/inputs.jsonl.gz`, `runs/main` | nightly paths |
| `QS_PROFILE`, `QS_STEPS` | full, `ch sub yn bi ev` | `lite` = `ch sub`; `QS_STEPS` overrides the full profile's steps |
| `QS_DATA_DIR`, `PY` | `../data`, `.venv/bin/python` | `ops/nightly.sh` only: inputs and OPD export (`opd-new/`), interpreter |
| `QS_NIGHTLY_AT` | 02:30 | `querschnitt nightly` |

### From a fresh clone
`make data` → `make run` → `make test` → `make eval GOLD=data/eval/gold_aps_s9.csv` → `make claims`; no model calls, no key.
The first target that runs Python creates `.venv` (`make install`: uv, else any `python >= 3.11` with venv + pip);
`PY=…` picks another interpreter, which must import fastapi, uvicorn and yaml. The S9 gold is mostly older than the app's
slice, so `make eval` scores it on its production rows: `eval/prod_gold/{inputs,topics}.jsonl.gz` (from
`eval/prod_gold/rows.py`) in their own store `runs/eval-prodgold.sqlite`, which reproduces
`eval/results/eval-gold_aps_s9.json` byte for byte (CI checks it; `EVAL_DB=` scores the app's store instead, into
`…-appstore.json`). Any other `GOLD` is scored on the app's store, loaded first when empty. `make data` never replaces an
existing `data/querschnitt.sqlite`: `make clean-db` first to load a newer release.

## What exists

| File | |
|---|---|
| `sql/topics.sql` | Postgres DDL, ready to propose upstream: `topics` (CONTRACT §1, checks on lane/status/provenance, partial indexes on current rows, `topics_current` view) + `qs_affairs`, `qs_runs` (prefixed so they never collide with OPD tables in a shared database) |
| `sql/topics.sqlite.sql` | the SQLite equivalent (ISO-8601 UTC text timestamps, JSON text evidence) |
| `src/querschnitt/store.py` | `Store` (one class, both dialects), `load_topics` (jsonl, jsonl.gz, parquet), `load_affairs` (inputs), `load_affairs_export` (static export), reads, `decide`, `changes`, `coverage`, `pending`, `metrics`, run log |
| `src/querschnitt/api.py` | FastAPI: every CONTRACT §2 endpoint + `/schemes`, `/adhoc/{slug}` (state), `/adhoc/{slug}/stop`, `PUT /adhoc/{slug}/terms`, `POST /adhoc/{slug}/save`; bearer token on writes (`QS_WRITE_TOKEN`); CORS for localhost; app at `/` |
| `src/querschnitt/adhoc.py` | Neues Thema |
| `src/querschnitt/evaluate.py` | `querschnitt eval` / `make eval` |
| `src/querschnitt/cli.py` | `querschnitt build-inputs · run · load · serve · delta · nightly · eval · metrics · export` (`run` = `batch`, `export` = the lead's `export.main`) |
| `src/querschnitt/net.py` | downloads: published export files only, RFC 9309 robots check (ported from gegenprobe), fail closed |
| `src/querschnitt/fake_endpoint.py` | fake OpenAI-compatible endpoint (A/B top_logprobs by yes words, peaked codes for chapter/subtopic/evidence, topic JSON for generation; refuses a system message) |
| `tools/gold_csv.py` | `data/eval/gold_aps_s9.csv` (1,357 APS editors' chapters, S9) and `data/eval/gold_dvs30.csv` (the 30 public DVS items, S15) |
| `tools/adhoc_live_check.py` | Neues Thema end to end against a running API (POST + SSE), timeline per topic |
| `Makefile`, `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `.github/workflows/ci.yml` | packaging |
| `tests/test_*.py` (store, API, sync, eval, Neues Thema, net, delta, compose, prompts, export end to end, doc links), `tests/conftest.py`, `tests/fixtures/{inputs,topics}_sample.jsonl` | tests |

## API

| | |
|---|---|
| `GET /affairs/{id}/topics[?scheme=&history=true]` | `{affair, topics}`; current rows, or every version with `history` |
| `GET /topics/{scheme}/{code}/affairs?from=&to=&body=&level=&lang=&lane=&status=&rank=1&limit=&offset=` | `{scheme, code, label, total, rows}`, newest affair first, each row with its affair summary. Codes in short form work: `/topics/aps/1.7.2./affairs`, `/topics/adhoc/digitalisierung/yes/affairs`, `/topics/be-directorates/BKD/affairs`. `level` = parliament level (federal, cantonal, communal) |
| `POST /affairs/{id}/topics/{code}/confirm` · `/reject` | body `{"by": "…", "scheme": "…"}` (scheme inferred from the code when absent; `by` required; codes checked against the scheme) → the new row; the same decision by the same person while it is current returns that row with `unchanged: true` and adds nothing |
| `POST /affairs/{id}/topics/{code}/undo` | body `{"by", "scheme"}` → `{undone, restored}`: the current decision closed (`closed_by` = who undid it), the rows it had closed back as current rows; 409 when there is no decision to undo |
| `GET /changes?after=<seq>&since=&scheme=&body=&kind=all\|decisions\|machine&limit=≤5000` | the sync feed: every insert and every close, in `seq` order, exactly once; `{total, n, cursor, next, rows}`; upsert by `row_id` and follow `next`. `GET /decisions` = `kind=decisions` |
| `GET /coverage[?scheme=aps&since=]` | per body over the affairs begun since `since` (default `QS_SCOPE_SINCE` = the export's slice, so the totals equal `meta.json`): affairs, scored, scored share, title-only share, `by_year` [affairs, scored], covered_from (first year of OPD's data for that parliament, from bodies.json); cached on the store state |
| `POST /adhoc` | `{sentence, lang, period?: last_week\|last_month\|scored\|YYYY\|a..b, from?, to?, examples?, terms?, limit?}` → `{slug, topic, terms, terms_pending, period, period_name, estimate {affairs, mode, seconds, budget}, stream}` |
| `POST /adhoc/{slug}/continue` | after `cap` or `stopped`: reads the affairs not yet decided with a fresh call budget, on the same stream; `429` (like `POST /adhoc`) once the day's spend reached `QS_ADHOC_DAILY_USD` |
| `GET /adhoc/{slug}/stream` | SSE: `topic`, `terms`, then per affair `decision {id, p, flag, t, lane, sample, title, body, parl, level, lang, date, p_a, p_b, build, prompt_id}` and `progress {read, flagged, unread, seconds, total, period, stop, line: "read 50 / flagged 4 / 12.6 s"}`, last `done` with `stop` = `done` \| `cap` \| `daily_cap` \| `stopped` \| `error: …` and the period read (also in `GET /adhoc/{slug}`). `Last-Event-ID` / `?from=` resume |
| `GET /health`, `GET /metrics[?format=line]` | `/metrics`: affairs in scope (= the export's `meta.affairs`), APS-scored in scope, affairs loaded, rows, seq, pending, builds, last run (wall s, list-price USD, pending) and the one-line form |

Every row carries `label` {de, fr, it} from the scheme files.

## Store and versioning (decisions)
- Sync (dogfood round 1): `seq` is stamped on every insert and again on every close, under one serialized writer
  (SQLite `BEGIN IMMEDIATE`, Postgres `pg_advisory_xact_lock`), so `seq` order is commit order and `after=<cursor>`
  never skips a change, however many rows share one `valid_from` (58,392 did after one load). Older databases get
  the columns on open (`seq = row_id`). Every response has a schema in `/openapi.json` (`TopicRow`, `ChangesPage`, …).
- Evidence is stored and served as `{source, field, char_start, char_end, quote}`; `start`/`end` are accepted on load,
  and a missing source is the field for titles, else the affair's `text_src`.
- One `p`: `compose.topic_rows` picks the map (`aps-fed` when the chapter step showed examples, else `aps`) and the
  export copies `ch_p` and the detail's `p`/`p_raw` from those rows (the detail panel showed the chapter step's mean
  P, 0.502 for 341104, where the row's calibrated `p` is 0.283). Tested end to end: run → export → load → API.
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
  on Postgres (`QS_TEST_ALL_PG=1 QS_TEST_PG_DSN=…`), verified locally on PostgreSQL from the `pgserver` wheel; CI runs
  the store, API, eval and Neues-Thema tests again against a Postgres 16 service.

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
- Budget and stop (dogfood round 1): `QS_ADHOC_MAX_CALLS` is a per-run budget (per start and per `continue`); the run
  ends with `stop: cap` and `unread`, never as if complete. `QS_ADHOC_DAILY_USD` caps the list-price spend per local day:
  today's rows in the ad-hoc ledger are summed before every start and `continue` (`429` when reached), and a running
  run counts its own calls on top and stops with `stop: daily_cap`. The term request failed with `FileNotFoundError` because
  the ledger's directory did not exist yet at the first call (both the name and the terms then fell back silently);
  the directory is created up front and a terms failure is reported in the `terms` event.
- Verify (S27 rule, as batch/compose for `verify: true` files): every flag (p ≥ 0.5) gets the stricter second question
  (`engine.verify`, order a; b when 0.1 < p < 0.9); an unverified flag stays a flag and goes to `please_check`. Decisions
  stream `{id, p, flag, verified, p_verify, lane, …}`; the summary and the running line report flagged / verified /
  please check; saved files carry `verify: true` (`"verify": false` in the request turns it off).
- Save: `schemes/adhoc/<slug>.yaml` (id, names, question, answer_yes, cutoff 0.5, examples as `{title, match}`, terms,
  subtopics, sentence; no bare `yes:` key) and the run's decisions as `adhoc/<slug>` rows; `delta` picks up every file
  in `schemes/adhoc/` (`scheme.adhoc_topics()`).
- Live check, 14 Oct, Public AI, build `…dd237840` (every call), `Endpoint(max_rate=0.5, conc=2)`, store with all
  326,123 affairs: 110 requests in total (USD 0.0026 at list price; `runs/service-dev/ledger.jsonl`), results in
  `runs/service-dev/adhoc_live/run{1..4}.json`.

| Sentence (lang) | Period | Topic ready | 1st decision | 10th | Read / flagged | All |
|---|---|---|---|---|---|---|
| "Wölfe, Grossraubtiere und Herdenschutz" (de), limit 40 | 30 Sep – 6 Oct | 8.2 s | 9.8 s | 28.0 s | 40 / 1 | 111 s |
| "Protection de la population contre la chaleur et les canicules" (fr), limit 25 | 30 Sep – 6 Oct | 6.1 s | 7.7 s | 35.0 s | 25 / 0 | 77 s |
| "Wölfe, Grossraubtiere und Herdenschutz" (de), limit 18 | 2019 (candidates) | 5.7 s | 14.6 s | 47.3 s | 18 / 4 | 79 s |

  At 0.5 requests/s the decision rate is the cap, not the model (S13 measured 1.139–1.263 decisions/s at 3 workers).
  2019 run: 15,541 affairs in the period, 30 candidates from the terms, 4 flagged among the 12 candidates read (an
  association for a habitat without large predators in Solothurn, livestock guard dogs in the Federal Assembly, «Les Loups vont-ils s'installer
  dans la bergerie ?» in Vaud, a Zurich nature-protection item at p 0.81); outside sample 0 of 6 flagged [0, 0.391].
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
recall 0.900 [0.743, 0.966] (27/30), cantonal 23/25, federal 4/5; misses BL 297879, BE 337826, CHE 161610. The 1,357
APS editors' chapters (`data/eval/gold_aps_s9.csv`, multi-class) on their production rows, composed from `runs/main` and
`runs/side` by `eval/prod_gold/rows.py` with the export's rule: accuracy 0.718 [0.693, 0.743] on the 1,340 scored (17
not scored), top 3 0.860 ([`eval/results/eval-gold_aps_s9.json`](../eval/results/eval-gold_aps_s9.json)).

## Nightly delta (`querschnitt delta --since yesterday`)
1. `fetch_exports`: robots.txt, then `index.json`; downloads `affairs`, `bodies`, `contributors` and the `texts` split
   files whose size or `created` changed (first fetch: 22 files, 370 MB).
2. Affairs new to the store or begun since `--since` → their `docs_<body>` files are streamed, and only those affairs'
   slim rows appended to `docs_slim.jsonl.gz`. the 11 Oct export carries an `updated_at` of 10 or 11 Oct on 82,999 affairs, so
   updated-only affairs are rebuilt from titles, texts and the documents already on disk, never re-downloaded.
3. Inputs are rebuilt for touched affairs only (data.build over a filtered view of the export) and merged into the
   previous file; the first night (`--full-rebuild` or no inputs file) builds everything.
4. New affairs (begun ≥ `QS_SCOPE_SINCE`) and changed ones (input hash differs from the stored one, or from the input
   their rows were scored on) enter `qs_queue`. A pass with `--no-model` stops there (endpoint cut); every model pass
   scores the whole queue (`batch run --ids`, cached prompts never re-sent, refused while a batch with a live PID runs
   in that dir), whatever its `--since`, and an affair leaves the queue only when it has a current row for its queued
   input — a failed drain keeps it for the next pass. Steps (`cli.NIGHTLY_STEPS`, `QS_STEPS` overrides): full
   `ch sub yn bi ev` — chapter, subtopic (the chapter is read back from it), the ad-hoc topics, the German and French
   readings of bilingual parliaments (their lane) and the evidence quote, so nightly rows carry what the export's rows
   carry; lite `ch sub` — the chapter as measured, without ad-hoc topics, bilingual lane or quote.
5. Rows: `compose.decide` + `compose.topic_rows` with `eval/calibration.json` (the export's rule) → `load_topics`.
6. One `qs_runs` line and the printed line: `affairs N · wall S s · list-price USD X · pending P · unscored in scope U ·
   rows R · queue before → after · drain M min`. `pending` = the queue (new/changed since the previous nightly, not yet
   scored); `unscored_in_scope` = every affair in scope without rows (the corpus run's backlog). `--last FILE` writes
   the night's record (`runs/nightly/last.json`): date, opd_export_generated, new_affairs, new_rows, scored,
   pending_after_cut, pending_after_drain, drain_minutes, usd, pending, unscored_in_scope (a cut pass starts it, the
   model pass after it completes it). Real smoke, 14 Oct: 2 affairs scored, 1 new affair queued by a cut pass and
   drained by the next pass with `--since 2030-01-01` (19 Public AI calls, build `…dd237840`).
- **Decisions become examples.** Before scoring, the nightly runs `querschnitt examples --all`: every ad-hoc topic with
  confirmed or rejected rows in the Pult gets them written into its file as examples; its next yes/no prompts show the
  four most similar decided affairs (the S26 loop; new prompt ids, so rows are re-scored, never mixed).
- **First real night, 15 Oct, with an endpoint outage** ([`eval/nightly/2026-10-15.json`](../eval/nightly/2026-10-15.json),
  [log](../eval/nightly/2026-10-15.log)): Public AI answered HTTP `400`/`404` from about 08:35. The cut pass fetched OPD's
  export of 15 Oct and queued 33 new affairs, 49 in all with the changed ones, without a model call; once the endpoint
  answered with the locked build, the drain scored all 49 in 9.6 min for USD 0.0215 at list price, and 0 were left in
  the queue. The 09:15 run itself fetched nothing: on days without a cut pass the model pass did not fetch (fixed in
  `ops/nightly.sh`).

Measured on the 11 Oct export (no fetch, no model): touched-only rebuild in 131 s, peak RSS 1.55 GB,
all 326,123 input hashes identical to the full build (0 to re-score); the full rebuild takes 86 s at 4.7 GB peak.

## Footprints
| | measured |
|---|---|
| Python deps (site-packages) | 215 MB (`du`), of which pyarrow 123 MB and psycopg-binary 17 MB; image = python:3.12-slim + deps + repo |
| Export files for the delta | 370 MB (affairs 51, contributors 60, texts 258 MB) + `docs_slim.jsonl.gz` 335 MB; inputs 174 MB |
| Store, 326,123 affairs | SQLite 176 MB file, load 15 s, 35 MB RSS; Postgres: not logged on disk |
| Topic rows | 12,417 rows in the store composed from `runs/main`; size per row in Postgres not logged on disk |
| Nightly RAM | 1.55 GB peak (touched-only rebuild); first night 4.7 GB |
| Queries (326k affairs) | `/topics/…/affairs` 5–12 ms; `pending` 30–50 ms; coverage 0.6 s Postgres / 3–4 s SQLite, then cached |

`lite` on OPD's ~20 GB VPS: about 0.95 GB of files (exports 370 MB, docs 335 MB, inputs 174 MB, chapter step rows
≈ 1.3 KB per call ≈ 60 MB for 2025–26) plus the `topics` table (≈ 45 MB for 2025–26 with chapter rows); these estimates
are for the chapter step alone, and the subtopic step lite now runs adds step rows and subtopic rows not measured here.
`full` adds the API, the app and a Postgres volume.

What is measured: lite's `ch sub` is the shipped chapter design (chapter read back from the subtopic, recalibrated with
`eval/calibration.json`), the design the held-out S25 score and the lane figures in PRUEFSTAND.md were measured on. A
chapter-only run (`QS_STEPS=ch`) is not measured: its `p` would go through a map fitted on read-back confidences. Full's
`bi` and `ev` add the bilingual lane and the quote.

Outside this Mac: `ops/nightly.sh` takes `QS_DATA_DIR` and `PY` and uses `caffeinate` only where it exists, but
`ops/nightly-loop.sh` (BSD `date -j`) and `ops/watchdog.sh` (BSD `stat -f`) are macOS scripts for the author's machine,
and `ops/refresh-site.sh` deploys the author's site. A server runs `querschnitt nightly` (the compose `nightly` service)
or cron with `querschnitt delta --since yesterday`.
CI (GitHub Actions) builds the image, checks it runs as uid 10001, starts it, calls `/health`, `/metrics` and `/coverage`,
and brings up both compose profiles (footprint below).

## Requests to the lead
All resolved (14 Oct): parliament names, `.gitignore`, slimmer image (Parquet support is the `parquet` extra), seed data as the
`data-latest` release (`make data`), ad-hoc prompt ids, export flags.

## Footprint (GitHub Actions `compose` job; `docker stats`, idle after start) — source: [`eval/ci_footprint.txt`](../eval/ci_footprint.txt)
| profile | containers | memory | image |
|---|---|---|---|
| full | db 33.82 MiB · api 43.68 MiB · nightly 12.72 MiB | 90.22 MiB | querschnitt 173 MB |
| lite | nightly-lite 12.7 MiB, into an existing Postgres | 12.7 MiB | same image |
Every push re-measures it in the job summary.
