-- `hop` CI job, after a third load of the file with two rows changed by the job (synthetic changes):
--   affair 341432 aps level 1 rank 1: p and p_raw changed, same valid_from  -> updated in place, updated_at moves
--   affair 341467 aps level 1 rank 2: code changed, valid_from a day later -> new row; the workflow closes the old one
-- Every other row stays exactly as after the first load.
DO $$
DECLARE
  n integer := (SELECT count(*) FROM ci.after_first);
BEGIN
  ASSERT (SELECT count(*) FROM topics) = n + 1, 'one row added';

  ASSERT (SELECT t.p = 0.5 AND t.p_raw = 0.5 AND t.id = f.id AND t.created_at = f.created_at AND t.updated_at > f.updated_at
          FROM topics t JOIN ci.after_first f USING (affair_id, scheme_key, level, rank, valid_from)
          WHERE t.affair_id = 341432 AND t.scheme_key = 'aps' AND t.level = 1 AND t.rank = 1),
    'changed row updated in place with a new updated_at';

  ASSERT (SELECT t.valid_to = '2026-10-16 13:05:09' AND t.updated_at > f.updated_at
          FROM topics t JOIN ci.after_first f USING (id)
          WHERE t.affair_id = 341467 AND t.scheme_key = 'aps' AND t.level = 1 AND t.rank = 2),
    'superseded row closed at the new valid_from';
  ASSERT (SELECT code = 'aps:1.7.1.' AND label_de = 'Bevölkerung und Arbeit' AND valid_to IS NULL
          FROM topics WHERE affair_id = 341467 AND scheme_key = 'aps' AND level = 1 AND rank = 2 AND valid_from = '2026-10-16 13:05:09'),
    'new row current, with its label';

  ASSERT NOT EXISTS (
    (SELECT * FROM ci.after_first WHERE (affair_id, rank) NOT IN ((341432, 1), (341467, 2)) OR scheme_key <> 'aps' OR level <> 1
     EXCEPT ALL
     SELECT * FROM topics WHERE (affair_id, rank) NOT IN ((341432, 1), (341467, 2)) OR scheme_key <> 'aps' OR level <> 1)),
    'every other row unchanged';
  RAISE NOTICE 'change: ok (1 updated in place, 1 inserted, 1 closed)';
END $$;
