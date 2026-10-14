-- 0001_topics (down): removes the topic tables. Data in them is lost; export topics.ndjson.gz first if it should be kept.
BEGIN;
DROP VIEW IF EXISTS topics_current;
DROP TABLE IF EXISTS topics;
DROP TABLE IF EXISTS topic_codes;
DROP TABLE IF EXISTS topic_schemes;
COMMIT;
