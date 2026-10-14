#!/bin/sh
# Unattended nightly delta (ops/nightly-loop.sh, 07:05 CEST, after OPD's ~06:35 export): fresh export → new/changed affairs → batch →
# store → one metrics line. On even days of the month the endpoint is cut for the first pass (`--no-model`): new rows wait
# as pending; the second pass with the endpoint drains them, and the log records pending count and minutes to drain.
cd "$(dirname "$0")/.." || exit 1
export QS_DB="$PWD/data/querschnitt.sqlite" QS_RUN_DIR="$PWD/runs/nightly" QS_INPUTS="$PWD/../data/inputs.jsonl.gz" QS_EXPORT_DIR="$PWD/../data/opd-new"
L="runs/nightly/$(date +%F).log"; PY=.venv/bin/python
day=$(date +%d); cut=$(( ${day#0} % 2 == 0 ))
{
  echo "== $(date '+%F %T') nightly start (endpoint cut for first pass: $cut)"
  t0=$(date +%s)
  # the store mirrors the corpus run first (latest export of its rows; reloading identical rows adds nothing)
  $PY -m querschnitt export --out app/data --topics-file > /dev/null && $PY -m querschnitt load --auto
  if [ "$cut" = 1 ]; then
    caffeinate -i $PY -m querschnitt delta --since yesterday --no-model --max-rate 1.0
    echo "-- $(date '+%F %T') after cut pass:"; $PY -m querschnitt metrics
    t1=$(date +%s)
  fi
  caffeinate -i $PY -m querschnitt delta --since yesterday --no-fetch --max-rate 1.0
  t2=$(date +%s)
  echo "-- $(date '+%F %T') after model pass:"; $PY -m querschnitt metrics
  [ "$cut" = 1 ] && echo "drain_minutes=$(( (t2 - t1) / 60 ))"
  echo "== $(date '+%F %T') nightly end, wall $(( (t2 - t0) / 60 )) min"
  $PY - <<PYEOF
import json, time
from querschnitt.store import Store
m = Store().metrics() if hasattr(Store, "metrics") else {}
json.dump(dict(date=time.strftime('%F'), endpoint_cut_first_pass=bool($cut), wall_min=round(($t2-$t0)/60, 1),
               new_rows=(m.get("last_run") or {}).get("affairs"), pending=m.get("pending")), open('runs/nightly/last.json', 'w'))
PYEOF
} >> "$L" 2>&1
