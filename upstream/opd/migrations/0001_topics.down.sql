-- 0001_topics (down): removes the topic tables. Data in them is lost; export topics.ndjson.gz first if it should be kept.
-- Order: 0003 down first (its view topics_public depends on topics; DROP TABLE topics fails while it exists). 0002 down
-- is not needed before this one: dropping topic_schemes removes the seed with it.
BEGIN;
DROP VIEW IF EXISTS topics_current;
DROP TABLE IF EXISTS topics;
DROP TABLE IF EXISTS topic_codes;
DROP TABLE IF EXISTS topic_schemes;
COMMIT;
