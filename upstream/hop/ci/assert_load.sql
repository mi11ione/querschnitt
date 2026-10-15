-- `hop` CI job, after a first load into an empty topics table.
--   psql -v ON_ERROR_STOP=1 -v n=<machine rows in the file> -v fixture=1|0 -f assert_load.sql
-- ci.expected holds the same file converted by ../../opd/export/to_opd.py --with-subtopics (one jsonb per row): the
-- reference mapping. Every machine row must be in topics exactly as to_opd.py maps it (all columns except id,
-- created_at, updated_at and the loader's content_hash), and nothing else. fixture=1 (ci/topics.ci.jsonl) adds checks
-- of named rows and keeps a copy of the table for the reload checks.

CREATE TEMP VIEW load_diff AS
SELECT coalesce(e.affair_id, t.affair_id) AS affair_id, coalesce(e.scheme_key, t.scheme_key) AS scheme_key,
       coalesce(e.level, t.level) AS level, coalesce(e.rank, t.rank) AS rank,
       CASE WHEN t.id IS NULL THEN 'missing in topics' WHEN e.affair_id IS NULL THEN 'not in the file' ELSE 'differs' END AS what,
       t.evidence_field, e.evidence_field AS want_field, t.evidence_text_id, e.evidence_text_id AS want_text_id,
       t.evidence_doc_id, e.evidence_doc_id AS want_doc_id
FROM (SELECT r.* FROM ci.expected x, jsonb_populate_record(NULL::topics, x.doc) r WHERE r.provenance = 'inferred') e
FULL JOIN topics t ON (t.affair_id, t.scheme_key, t.level, t.rank, t.valid_from) = (e.affair_id, e.scheme_key, e.level, e.rank, e.valid_from)
WHERE t.id IS NULL OR e.affair_id IS NULL
   OR (t.body_id, t.body_key, t.scheme_id, t.code, t.parent_code, t.label_de, t.label_fr, t.label_it, t.label_rm, t.p, t.p_raw,
       t.lane, t.status, t.provenance, t.evidence_field, t.evidence_text_id, t.evidence_doc_id, t.evidence_char_start,
       t.evidence_char_end, t.evidence_quote, t.model, t.model_build, t.cutoffs_id, t.prompt_id, t.input_hash,
       t.engine_version, t.valid_to, t.confirmed_by, t.confirmed_by_body_id, t.confirmed_at)
      IS DISTINCT FROM
      (e.body_id, e.body_key, e.scheme_id, e.code, e.parent_code, e.label_de, e.label_fr, e.label_it, e.label_rm, e.p, e.p_raw,
       e.lane, e.status, e.provenance, e.evidence_field, e.evidence_text_id, e.evidence_doc_id, e.evidence_char_start,
       e.evidence_char_end, e.evidence_quote, e.model, e.model_build, e.cutoffs_id, e.prompt_id, e.input_hash,
       e.engine_version, e.valid_to, e.confirmed_by, e.confirmed_by_body_id, e.confirmed_at);

\echo 'rows that differ from to_opd.py (expect none):'
SELECT * FROM load_diff LIMIT 50;

\echo 'evidence as loaded:'
SELECT evidence_field, count(*) AS n_rows, count(evidence_text_id) AS with_text_id, count(evidence_doc_id) AS with_doc_id
FROM topics GROUP BY 1 ORDER BY 1;

SELECT set_config('ci.n', :'n', false) \gset
DO $$
DECLARE
  n integer := current_setting('ci.n')::integer;
  bad integer;
BEGIN
  ASSERT (SELECT count(*) FROM topics) = n, format('topics has %s rows, the file %s machine rows', (SELECT count(*) FROM topics), n);
  ASSERT (SELECT count(*) FROM ci.expected WHERE doc->>'provenance' = 'inferred') = n, 'to_opd.py and the file agree on machine rows';
  ASSERT NOT EXISTS (SELECT 1 FROM topics WHERE provenance <> 'inferred'), 'machine rows only';

  SELECT count(*) INTO bad FROM load_diff;
  ASSERT bad = 0, format('%s rows differ from to_opd.py (listed above)', bad);

  -- lookups and timestamps
  ASSERT NOT EXISTS (SELECT 1 FROM topics WHERE body_id IS NULL OR scheme_id IS NULL), 'every row with body_id and scheme_id';
  ASSERT NOT EXISTS (SELECT 1 FROM topics WHERE content_hash IS NULL OR updated_at IS NULL), 'content_hash and updated_at set';
  ASSERT NOT EXISTS (SELECT 1 FROM topics WHERE abs(extract(epoch FROM updated_at - created_at)) > 600),
    'updated_at (written by Hop) and created_at (database default) both UTC';
  RAISE NOTICE 'load: ok (% rows)', n;
END $$;

\if :fixture
\echo 'evidence of the fixture rows:'
SELECT affair_id, scheme_key, rank, evidence_field, evidence_text_id, evidence_doc_id, evidence_char_start, evidence_char_end
FROM topics WHERE evidence_field IS NOT NULL ORDER BY evidence_field, affair_id;

DO $$
BEGIN
  -- evidence.source, spelled out (docs/CONTRACT.md §1): text:<id> -> texts.id, doc:<id> -> docs.id and field 'doc'
  ASSERT (SELECT (evidence_field, evidence_text_id, evidence_doc_id) IS NOT DISTINCT FROM ('text'::text, 226062, NULL::integer)
          FROM topics WHERE affair_id = 341408 AND scheme_key = 'aps' AND level = 1 AND rank = 1), 'text quote: text:226062';
  ASSERT (SELECT (evidence_field, evidence_text_id, evidence_doc_id) IS NOT DISTINCT FROM ('doc'::text, NULL::integer, 927452)
          FROM topics WHERE affair_id = 340903 AND scheme_key = 'aps' AND level = 1 AND rank = 1), 'document quote: doc:927452, field doc';
  ASSERT (SELECT (evidence_field, evidence_text_id, evidence_doc_id) IS NOT DISTINCT FROM ('title'::text, NULL::integer, NULL::integer)
          FROM topics WHERE affair_id = 339102 AND scheme_key = 'aps' AND level = 1 AND rank = 1), 'title quote: no ids';
  ASSERT (SELECT count(*) FROM topics WHERE evidence_field = 'doc') = 5
     AND (SELECT count(*) FROM topics WHERE evidence_doc_id IS NOT NULL) = 5, 'five document quotes';
  ASSERT (SELECT count(*) FROM topics WHERE evidence_field = 'text') = 2
     AND (SELECT count(*) FROM topics WHERE evidence_text_id IS NOT NULL) = 2, 'two text quotes';

  ASSERT NOT EXISTS (SELECT 1 FROM topics WHERE label_de IS NULL), 'every row with labels';
  ASSERT (SELECT parent_code FROM topics WHERE affair_id = 341467 AND scheme_key = 'aps' AND level = 2 AND rank = 1) = 'aps:1.6.3.',
    'subtopic with its chapter';
  ASSERT (SELECT count(*) FROM topics_current) = (SELECT count(*) FROM topics), 'all rows current';
  RAISE NOTICE 'fixture rows: ok';
END $$;

CREATE TABLE ci.after_first AS SELECT * FROM topics;
\endif
