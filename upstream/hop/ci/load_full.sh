#!/usr/bin/env bash
# `hop` CI job: one topics file loaded in full into an emptied topics table and checked row by row against to_opd.py.
#   upstream/hop/ci/load_full.sh <topics.jsonl.gz> <label>      (env: HOP_DIR, RUNNER_TEMP, PG*; after the inputs step)
# Stand-in rows for the file's affairs and bodies (bodies not in opd_stand_in.sql get ids from 100001).
set -euo pipefail
full=$1; label=$2
psql -v ON_ERROR_STOP=1 -q -c "DELETE FROM topics" -c "DROP TABLE IF EXISTS ci.file_affairs" \
  -c "CREATE TABLE ci.file_affairs (affair_id integer, body_key text)"
gzip -dc "$full" | jq -r '[.affair_id, .body_key] | @tsv' | sort -u | psql -v ON_ERROR_STOP=1 -c "COPY ci.file_affairs FROM STDIN"
psql -v ON_ERROR_STOP=1 -q \
  -c "INSERT INTO bodies (id, body_key) SELECT (SELECT greatest(max(id), 100000) FROM bodies) + row_number() OVER (ORDER BY body_key), body_key
      FROM (SELECT DISTINCT body_key FROM ci.file_affairs WHERE body_key NOT IN (SELECT body_key FROM bodies)) b" \
  -c "INSERT INTO affairs (id, body_key, body_id) SELECT DISTINCT ON (f.affair_id) f.affair_id, f.body_key, b.id
      FROM ci.file_affairs f JOIN bodies b USING (body_key) ON CONFLICT (id) DO NOTHING"
psql -At -c "SELECT row_to_json(b) FROM bodies b" | gzip -n > "$RUNNER_TEMP/bodies.ndjson.gz"
python upstream/opd/export/to_opd.py --topics "$full" --bodies "$RUNNER_TEMP/bodies.ndjson.gz" \
  --out "$RUNNER_TEMP/expected-$label" --with-subtopics
psql -v ON_ERROR_STOP=1 -q -c "TRUNCATE ci.expected"
gzip -dc "$RUNNER_TEMP/expected-$label/topics.ndjson.gz" \
  | psql -v ON_ERROR_STOP=1 -c "COPY ci.expected (doc) FROM STDIN WITH (FORMAT csv, QUOTE E'\x01', DELIMITER E'\x02')"
"$HOP_DIR/hop-run.sh" -j querschnitt-opd -e opd -r local -f '${PROJECT_HOME}/load_topics.hwf' \
  -p QS_TOPICS_FILE="$full" 2>&1 | tee "$RUNNER_TEMP/load-$label.log"
if grep -n "ERROR" "$RUNNER_TEMP/load-$label.log"; then exit 1; fi
psql -v ON_ERROR_STOP=1 -v n="$(gzip -dc "$full" | jq -c 'select(.provenance == "inferred")' | wc -l)" -v fixture=0 \
  -f upstream/hop/ci/assert_load.sql
echo "### $label: $(psql -At -c "SELECT count(*) || ' rows, ' || count(DISTINCT scheme_key) || ' schemes: ' || string_agg(DISTINCT scheme_key, ', ') FROM topics")" \
  | tee -a "${GITHUB_STEP_SUMMARY:-/dev/null}"
