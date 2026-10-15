-- `hop` CI job, after the second load of the same file: nothing written, nothing closed (every column, updated_at too).
DO $$
DECLARE
  diff integer := (SELECT count(*) FROM (
                     (SELECT * FROM topics EXCEPT ALL SELECT * FROM ci.after_first)
                     UNION ALL
                     (SELECT * FROM ci.after_first EXCEPT ALL SELECT * FROM topics)) d);
BEGIN
  ASSERT diff = 0, format('the second load of the same file changed %s rows', diff);
  RAISE NOTICE 'reload: ok (% rows, none changed)', (SELECT count(*) FROM topics);
END $$;
