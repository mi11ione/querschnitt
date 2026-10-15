#!/bin/sh
# Unattended nightly delta (ops/nightly-loop.sh, 09:15 CEST, after OPD's ~08:10 CEST export): fresh export → new/changed affairs → batch →
# store → one metrics line. On even days of the month the endpoint is cut for the first pass (`--no-model`): new rows wait
# as pending; the second pass with the endpoint drains them, and the log records pending count and minutes to drain.
# Steps: the delta's full-profile default, `ch sub yn bi ev` (cli.NIGHTLY_STEPS; QS_STEPS overrides).
# Paths: QS_DATA_DIR (default ../data, relative to the repo) holds inputs.jsonl.gz and the OPD export opd-new/; PY the
# interpreter (default .venv/bin/python); caffeinate (macOS: no sleep during the run) only where it exists.
cd "$(dirname "$0")/.." || exit 1
D="${QS_DATA_DIR:-../data}"; case "$D" in /*) ;; *) D="$PWD/$D" ;; esac
export QS_DB="$PWD/data/querschnitt.sqlite" QS_RUN_DIR="$PWD/runs/nightly" QS_INPUTS="$D/inputs.jsonl.gz" QS_EXPORT_DIR="$D/opd-new"
L="runs/nightly/$(date +%F).log"; PY="${PY:-.venv/bin/python}"
CAF=""; command -v caffeinate > /dev/null 2>&1 && CAF="caffeinate -i"
mkdir -p runs/nightly
day=$(date +%d); cut=${QS_NIGHTLY_CUT:-$(( ${day#0} % 2 == 0 ))}
case "$cut" in 1|true|yes) cut=1 ;; *) cut=0 ;; esac
# the new export is fetched by the first pass: the cut pass on even days, else the model pass itself
FETCH="--no-fetch"; [ "$cut" = 1 ] || FETCH=""
{
  echo "== $(date '+%F %T') nightly start (endpoint cut for first pass: $cut)"
  t0=$(date +%s)
  # the store mirrors the corpus run first (latest export of its rows; reloading identical rows adds nothing)
  # (--topics-file: topics.jsonl.gz must come from the same export as affairs.json, or the store and the app disagree)
  $PY -m querschnitt export --out app/data --topics-file > /dev/null && $PY -m querschnitt load --auto
  if [ "$cut" = 1 ]; then
    $CAF $PY -m querschnitt delta --since yesterday --no-model --max-rate 1.0 --last runs/nightly/last.json
    echo "-- $(date '+%F %T') after cut pass:"; $PY -m querschnitt metrics
    t1=$(date +%s)
  fi
  # the model pass scores the queue (everything pass 1 or an earlier night left unscored), whatever --since says;
  # on a day without a cut pass it also fetches the new export
  $CAF $PY -m querschnitt delta --since yesterday $FETCH --max-rate 1.0 --last runs/nightly/last.json
  t2=$(date +%s)
  echo "-- $(date '+%F %T') after model pass:"; $PY -m querschnitt metrics
  echo "== $(date '+%F %T') nightly end, wall $(( (t2 - t0) / 60 )) min"
  # last.json: the delta passes wrote date, opd_export_generated, new_affairs, new_rows, scored, pending_after_cut,
  # pending_after_drain, drain_minutes, usd, pending, unscored_in_scope; the script adds its own two fields
  $PY - <<PYEOF
import json
p = 'runs/nightly/last.json'
L = json.load(open(p))
L.update(endpoint_cut_first_pass=bool($cut), wall_min=round(($t2 - $t0) / 60, 1))
json.dump(L, open(p, 'w'), indent=1)
PYEOF
} >> "$L" 2>&1
