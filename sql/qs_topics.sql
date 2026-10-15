-- Querschnitt's own store in Postgres (QS_PG_DSN; docs/CONTRACT.md §1 rows): `qs_topics` plus the service tables below.
-- This is the service's working store, not the table proposed to OpenParlData: that is `topics` in
-- upstream/opd/migrations/0001_topics.up.sql (OPD's naming), loaded from the topics file by upstream/hop. Every object
-- here is prefixed `qs_`, so the store can live in the same database as OPD's tables, including its `topics`.
-- One row per affair × scheme × level × rank × version. Rows are never updated except to close them (`valid_to`):
-- a re-score or an editor's decision adds a row; `valid_to IS NULL` = current. Machine rows have provenance 'inferred',
-- editor decisions provenance 'confirmed' (status 'confirmed' or 'rejected') with who and when.
-- `seq` orders every change (an insert, and a close, which re-stamps the row): a sync client reads `seq > cursor` and
-- upserts by row_id, so no change is lost, whatever the page size and however many rows share one valid_from.
-- A store made by an earlier version has this table as `topics`: Store.init renames it (and its indexes, constraints, sequence
-- and view) to the qs_ names, and only when that `topics` has this table's columns (row_id, scheme), never OPD's.
CREATE TABLE IF NOT EXISTS qs_topics (
  row_id        bigserial PRIMARY KEY,
  affair_id     bigint      NOT NULL,             -- OPD affairs.id
  body_key      text,                             -- OPD body key: CHE, BE, 351, ...
  scheme        text        NOT NULL,             -- aps, be-directorates, bs-themen, adhoc/<slug>
  level         smallint    NOT NULL,             -- 1 = chapter / yes-no, 2 = subtopic
  code          text        NOT NULL,             -- aps:1.7.2., aps:kw:1374918, aps:none, adhoc/<slug>:yes
  rank          smallint    NOT NULL DEFAULT 1,   -- 1 = shipped label; 2-3 = ranked suggestions
  p             real,                             -- recalibrated probability
  p_raw         real,                             -- engine probability before recalibration
  lane          text CHECK (lane IN ('pass', 'please_check', 'readings_agree')),
  status        text        NOT NULL DEFAULT 'suggested' CHECK (status IN ('suggested', 'confirmed', 'rejected')),
  provenance    text        NOT NULL DEFAULT 'inferred' CHECK (provenance IN ('inferred', 'confirmed')),
  evidence      jsonb,                            -- {source, field, char_start, char_end, quote}
  model         text,                             -- served model
  build         text,                             -- system_fingerprint
  cutoffs_id    text,                             -- aps@dd237840
  prompt_id     text,                             -- sha256[:12] of the exact prompt(s)
  input_hash    text,                             -- sha256[:16] of lang + title + long title + text
  valid_from    timestamptz NOT NULL DEFAULT now(),
  valid_to      timestamptz,
  confirmed_by  text,
  confirmed_at  timestamptz,
  version       text,                             -- engine version
  seq           bigint,                           -- change sequence: set on insert and again on close
  closed_by     text,                             -- who closed the row, when a person did (a decision or an undo)
  CHECK (provenance = 'inferred' OR (confirmed_by IS NOT NULL AND confirmed_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS qs_topics_current_affair ON qs_topics (affair_id) WHERE valid_to IS NULL;
CREATE INDEX IF NOT EXISTS qs_topics_current_code ON qs_topics (scheme, code) WHERE valid_to IS NULL;
CREATE INDEX IF NOT EXISTS qs_topics_key ON qs_topics (affair_id, scheme, level, rank, provenance);
CREATE INDEX IF NOT EXISTS qs_topics_valid_from ON qs_topics (valid_from);
CREATE INDEX IF NOT EXISTS qs_topics_valid_to ON qs_topics (valid_to);
-- (qs_topics_seq on qs_topics (seq) is created by the store after the column migration of older databases)
CREATE OR REPLACE VIEW qs_topics_current AS SELECT * FROM qs_topics WHERE valid_to IS NULL;

-- Service tables (Querschnitt's own, prefixed like qs_topics).
-- qs_affairs: the affair summary the API returns beside topic rows (one row per affair, from inputs.jsonl.gz).
CREATE TABLE IF NOT EXISTS qs_affairs (
  id bigint PRIMARY KEY, body_key text, level text, canton text, parl text, parl_fr text, lang text, date text,
  number text, title text, title_long text, type text, type_h text, state text, url text, submitter text, party text,
  submitter_type text, has_text boolean, text_src text, input_hash text, updated text
);
CREATE INDEX IF NOT EXISTS qs_affairs_body_date ON qs_affairs (body_key, date);
CREATE INDEX IF NOT EXISTS qs_affairs_date ON qs_affairs (date);
-- qs_bodies: parliament names and the year OPD's data for it starts (the export's bodies.json, or the inputs).
CREATE TABLE IF NOT EXISTS qs_bodies (
  key text PRIMARY KEY, name_de text, name_fr text, level text, canton text, lang text, covered_from integer
);
-- qs_queue: the nightly's queue: affairs new or changed since the previous nightly and not yet scored (input hash as
-- queued). A pass without the endpoint fills it; the next model pass scores exactly these, whatever its --since says.
CREATE TABLE IF NOT EXISTS qs_queue (
  affair_id bigint PRIMARY KEY, input_hash text, reason text, queued_at timestamptz NOT NULL DEFAULT now()
);
-- qs_runs: one line per load / nightly delta (the /metrics source).
CREATE TABLE IF NOT EXISTS qs_runs (
  id bigserial PRIMARY KEY, ts timestamptz NOT NULL DEFAULT now(), kind text NOT NULL, affairs integer, rows integer,
  wall_s real, usd real, pending integer, build text, note text
);
