-- Stand-in for the two OPD tables that migrations 0001-0003 reference, for the `hop` CI job (.github/workflows/ci.yml).
-- Not part of the merge request: OPD has these tables. Only the columns the migrations and the Hop pipeline use:
--   bodies.id, bodies.body_key   foreign keys topics.body_id, topics.confirmed_by_body_id, topic_schemes.body_id,
--                                topic_feed_bodies.body_id; the seed (0002) looks up BE and BS; the pipeline looks up
--                                body_id by body_key
--   affairs.id                   foreign key topics.affair_id
-- Rows: the bodies and affairs of ci/topics.ci.jsonl, ids as in the 6 Oct OPD bulk export (bodies.ndjson.gz).
BEGIN;

CREATE TABLE bodies (
  id        integer PRIMARY KEY,
  body_key  text    NOT NULL UNIQUE
);

CREATE TABLE affairs (
  id        integer PRIMARY KEY,
  body_id   integer REFERENCES bodies (id),
  body_key  text
);

INSERT INTO bodies (id, body_key) VALUES
  (42, 'CHE'), (250, 'AG'), (253, 'BE'), (255, 'BS'), (276, '1024'), (278, '1058');

INSERT INTO affairs (id, body_key, body_id)
SELECT a.id, a.body_key, b.id
FROM (VALUES (46562, 'BS'), (252495, '1058'), (312843, '1024'), (326823, '1024'), (338125, '1058'), (339101, '1024'),
             (339102, '1024'), (339103, '1024'), (339104, '1024'), (340791, 'AG'), (340903, '1024'), (341408, 'CHE'),
             (341432, '1024'), (341467, '1024')) AS a (id, body_key)
JOIN bodies b ON b.body_key = a.body_key;

COMMIT;
