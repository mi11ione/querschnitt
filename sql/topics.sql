-- Querschnitt `topics` table for OpenParlData's Postgres (docs/CONTRACT.md §1). Proposed upstream as is.
-- One row per affair × scheme × level × rank × version. Rows are never updated except to close them (`valid_to`):
-- a re-score or an editor's decision adds a row; `valid_to IS NULL` = current. Machine rows have provenance 'inferred',
-- editor decisions provenance 'confirmed' (status 'confirmed' or 'rejected') with who and when.
CREATE TABLE IF NOT EXISTS topics (
  row_id        bigserial PRIMARY KEY,
  affair_id     bigint      NOT NULL,             -- OPD affairs.id
  body_key      text,                             -- OPD body key: CHE, BE, 351, ...
  scheme        text        NOT NULL,             -- aps, curia28, be-directorates, adhoc/<slug>
  level         smallint    NOT NULL,             -- 1 = chapter / yes-no, 2 = subtopic
  code          text        NOT NULL,             -- aps:1.7.2., aps:kw:1374918, aps:none, adhoc/<slug>:yes
  rank          smallint    NOT NULL DEFAULT 1,   -- 1 = shipped label; 2-3 = ranked suggestions
  p             real,                             -- recalibrated probability
  p_raw         real,                             -- engine probability before recalibration
  lane          text CHECK (lane IN ('readings_agree', 'please_check')),
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
  CHECK (provenance = 'inferred' OR (confirmed_by IS NOT NULL AND confirmed_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS topics_current_affair ON topics (affair_id) WHERE valid_to IS NULL;
CREATE INDEX IF NOT EXISTS topics_current_code ON topics (scheme, code) WHERE valid_to IS NULL;
CREATE INDEX IF NOT EXISTS topics_key ON topics (affair_id, scheme, level, rank, provenance);
CREATE INDEX IF NOT EXISTS topics_valid_from ON topics (valid_from);
CREATE INDEX IF NOT EXISTS topics_valid_to ON topics (valid_to);
CREATE OR REPLACE VIEW topics_current AS SELECT * FROM topics WHERE valid_to IS NULL;

-- Service tables (Querschnitt's own; prefixed so they never collide with OPD's tables in a shared database).
-- qs_affairs: the affair summary the API returns beside topic rows (one row per affair, from inputs.jsonl.gz).
CREATE TABLE IF NOT EXISTS qs_affairs (
  id bigint PRIMARY KEY, body_key text, level text, canton text, parl text, parl_fr text, lang text, date text,
  number text, title text, title_long text, type text, type_h text, state text, url text, submitter text, party text,
  submitter_type text, has_text boolean, text_src text, input_hash text, updated text
);
CREATE INDEX IF NOT EXISTS qs_affairs_body_date ON qs_affairs (body_key, date);
CREATE INDEX IF NOT EXISTS qs_affairs_date ON qs_affairs (date);
-- qs_runs: one line per load / nightly delta (the /metrics source).
CREATE TABLE IF NOT EXISTS qs_runs (
  id bigserial PRIMARY KEY, ts timestamptz NOT NULL DEFAULT now(), kind text NOT NULL, affairs integer, rows integer,
  wall_s real, usd real, pending integer, build text, note text
);
