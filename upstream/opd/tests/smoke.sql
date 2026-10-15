-- Smoke test for migrations 0001 + 0002 (run after applying them; 0003 optional). Leaves nothing behind: everything
-- happens in one transaction that is rolled back. Needs at least one row in affairs and the bodies table.
--   psql -v ON_ERROR_STOP=1 -f upstream/opd/tests/smoke.sql "$OPD_DSN"      → ends with NOTICE "topics smoke: ok"
BEGIN;

DO $$
DECLARE
  a integer := (SELECT min(id) FROM affairs);
  s integer := (SELECT id FROM topic_schemes WHERE scheme_key = 'aps' AND active);
  n integer;
BEGIN
  -- seed: every scheme active once, code_count = its codes
  ASSERT (SELECT count(*) FROM topic_schemes WHERE active) = (SELECT count(DISTINCT scheme_key) FROM topic_schemes),
    'one active version per scheme';
  ASSERT NOT EXISTS (SELECT 1 FROM topic_schemes s2 WHERE code_count <> (SELECT count(*) FROM topic_codes c WHERE c.scheme_id = s2.id)),
    'code_count matches topic_codes';
  ASSERT (SELECT count(*) FROM topic_codes WHERE scheme_id = s AND level = 1) = 25, 'APS: 24 chapters + no policy topic';

  -- a machine row with each lane value
  INSERT INTO topics (affair_id, scheme_id, scheme_key, level, code, rank, lane, valid_from)
  VALUES (a, s, 'aps', 1, 'aps:1.2.', 1, 'pass', '2026-01-01'),
         (a, s, 'aps', 1, 'aps:1.3.', 2, 'please_check', '2026-01-01'),
         (a, s, 'aps', 1, 'aps:1.5.', 3, 'readings_agree', '2026-01-01');

  -- constraints that must refuse a row
  BEGIN
    INSERT INTO topics (affair_id, scheme_id, scheme_key, level, code, lane, valid_from) VALUES (a, s, 'aps', 1, 'aps:1.2.', 'maybe', '2026-01-02');
    RAISE EXCEPTION 'lane outside the three values was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO topics (affair_id, scheme_id, scheme_key, level, code, status, valid_from) VALUES (a, s, 'aps', 1, 'aps:1.2.', 'confirmed', '2026-01-02');
    RAISE EXCEPTION 'a machine row with status confirmed was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO topics (affair_id, scheme_id, scheme_key, level, code, status, provenance, valid_from)
    VALUES (a, s, 'aps', 1, 'aps:1.2.', 'rejected', 'confirmed', '2026-01-02');
    RAISE EXCEPTION 'a decision without confirmed_by / confirmed_at was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO topics (affair_id, scheme_id, scheme_key, level, code, rank, valid_from) VALUES (a, s, 'aps', 1, 'aps:1.4.1.', 1, '2026-01-01');
    RAISE EXCEPTION 'a second row with the same version key was accepted';
  EXCEPTION WHEN unique_violation THEN NULL;
  END;

  -- a published rejection: decision row added, machine row closed; the current view shows the decision only
  INSERT INTO topics (affair_id, scheme_id, scheme_key, level, code, rank, status, provenance, valid_from, confirmed_by, confirmed_at)
  VALUES (a, s, 'aps', 1, 'aps:1.2.', 1, 'rejected', 'confirmed', '2026-01-03', 'smoke test', '2026-01-03');
  UPDATE topics SET valid_to = '2026-01-03' WHERE affair_id = a AND code = 'aps:1.2.' AND provenance = 'inferred' AND valid_to IS NULL;
  SELECT count(*) INTO n FROM topics_current WHERE affair_id = a AND scheme_key = 'aps' AND rank = 1;
  ASSERT n = 1, 'one current rank-1 row after the rejection';
  ASSERT (SELECT provenance FROM topics_current WHERE affair_id = a AND scheme_key = 'aps' AND rank = 1) = 'confirmed',
    'the current rank-1 row is the decision';

  RAISE NOTICE 'topics smoke: ok';
END $$;

ROLLBACK;
