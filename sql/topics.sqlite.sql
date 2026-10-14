-- SQLite equivalent of sql/topics.sql (the default local store, QS_DB). Timestamps are ISO 8601 UTC text
-- (YYYY-MM-DDTHH:MM:SS.ffffff+00:00, so text order = time order); evidence is JSON text.
CREATE TABLE IF NOT EXISTS topics (
  row_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  affair_id     INTEGER NOT NULL,
  body_key      TEXT,
  scheme        TEXT    NOT NULL,
  level         INTEGER NOT NULL,
  code          TEXT    NOT NULL,
  rank          INTEGER NOT NULL DEFAULT 1,
  p             REAL,
  p_raw         REAL,
  lane          TEXT CHECK (lane IN ('readings_agree', 'please_check')),
  status        TEXT    NOT NULL DEFAULT 'suggested' CHECK (status IN ('suggested', 'confirmed', 'rejected')),
  provenance    TEXT    NOT NULL DEFAULT 'inferred' CHECK (provenance IN ('inferred', 'confirmed')),
  evidence      TEXT,
  model         TEXT,
  build         TEXT,
  cutoffs_id    TEXT,
  prompt_id     TEXT,
  input_hash    TEXT,
  valid_from    TEXT    NOT NULL,
  valid_to      TEXT,
  confirmed_by  TEXT,
  confirmed_at  TEXT,
  version       TEXT,
  CHECK (provenance = 'inferred' OR (confirmed_by IS NOT NULL AND confirmed_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS topics_current_affair ON topics (affair_id) WHERE valid_to IS NULL;
CREATE INDEX IF NOT EXISTS topics_current_code ON topics (scheme, code) WHERE valid_to IS NULL;
CREATE INDEX IF NOT EXISTS topics_key ON topics (affair_id, scheme, level, rank, provenance);
CREATE INDEX IF NOT EXISTS topics_valid_from ON topics (valid_from);
CREATE INDEX IF NOT EXISTS topics_valid_to ON topics (valid_to);
CREATE VIEW IF NOT EXISTS topics_current AS SELECT * FROM topics WHERE valid_to IS NULL;

CREATE TABLE IF NOT EXISTS qs_affairs (
  id INTEGER PRIMARY KEY, body_key TEXT, level TEXT, canton TEXT, parl TEXT, parl_fr TEXT, lang TEXT, date TEXT,
  number TEXT, title TEXT, title_long TEXT, type TEXT, type_h TEXT, state TEXT, url TEXT, submitter TEXT, party TEXT,
  submitter_type TEXT, has_text INTEGER, text_src TEXT, input_hash TEXT, updated TEXT
);
CREATE INDEX IF NOT EXISTS qs_affairs_body_date ON qs_affairs (body_key, date);
CREATE INDEX IF NOT EXISTS qs_affairs_date ON qs_affairs (date);
CREATE TABLE IF NOT EXISTS qs_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, kind TEXT NOT NULL, affairs INTEGER, rows INTEGER,
  wall_s REAL, usd REAL, pending INTEGER, build TEXT, note TEXT
);
