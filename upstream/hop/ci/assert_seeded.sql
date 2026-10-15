-- `hop` CI job, after migrations 0001-0003 up: every code of every scheme file (ci.every_code, written by every_code.py)
-- is in the seed, in the active version of its scheme. A scheme file without a seed id fails here, before any load.
--   psql -v ON_ERROR_STOP=1 -f assert_seeded.sql
\echo 'scheme-file codes the seed does not carry (expect none):'
SELECT e.scheme_key, count(*) AS missing_codes, min(e.code) AS e_g
FROM ci.every_code e
LEFT JOIN topic_schemes s ON s.scheme_key = e.scheme_key AND s.active
LEFT JOIN topic_codes c ON c.scheme_id = s.id AND c.code = e.code
WHERE c.code IS NULL GROUP BY 1 ORDER BY 1;

DO $$
DECLARE
  bad text := (SELECT string_agg(DISTINCT e.scheme_key, ', ') FROM ci.every_code e
               LEFT JOIN topic_schemes s ON s.scheme_key = e.scheme_key AND s.active
               LEFT JOIN topic_codes c ON c.scheme_id = s.id AND c.code = e.code
               WHERE c.code IS NULL);
BEGIN
  ASSERT bad IS NULL, format('scheme files not (fully) in the seed: %s. Add the scheme to SCHEME_IDS (and BODY_SCHEMES) in '
                             'upstream/opd/tools/gen_seed.py and regenerate 0002, or once 0002 is applied in OPD write a '
                             'later migration with gen_seed.py --scheme', bad);
  RAISE NOTICE 'seed: every code of % scheme files', (SELECT count(DISTINCT scheme_key) FROM ci.every_code);
END $$;
