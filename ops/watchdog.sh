#!/bin/sh
# Every 5 min: a run dir paused for disk ("Disk low" STOP.md) resumes with its recorded ARGS once > 3 GB are free.
# The pipeline-managed runs/main resumes through ops/pipeline.py; this covers side runs started with ops/run-start.sh.
cd "$(dirname "$0")/.." || exit 1
echo $$ > runs/watchdog.pid
while true; do
  free=$(df -k . | awk 'NR==2{print $4}')
  for d in runs/*/; do
    d=${d%/}; [ "$d" = runs/main ] && continue; [ -f "$d/ARGS" ] || continue
    if [ -f "$d/STOP.md" ] && grep -q "Disk low" "$d/STOP.md" && [ -f "$d/ARGS" ] && [ "$free" -gt 3000000 ]; then
      mv "$d/STOP.md" "$d/STOP-$(date +%Y%m%d-%H%M%S).md"
      echo "$(date '+%F %T') resume $d" >> runs/watchdog.log
      # shellcheck disable=SC2046
      ops/run-start.sh "$d" $(tr '\n' ' ' < "$d/ARGS") >> runs/watchdog.log 2>&1
    fi
  done
    # alive but stalled (e.g. after a network outage): no ledger line for 20 min → graceful restart from cache
    if [ -f "$d/PID" ] && kill -0 "$(cat "$d/PID")" 2>/dev/null && [ -f "$d/ledger.jsonl" ] && [ -f "$d/ARGS" ]; then
      age=$(( $(date +%s) - $(stat -f %m "$d/ledger.jsonl") ))
      if [ "$age" -gt 1200 ]; then
        echo "$(date '+%F %T') stalled $d (${age}s) → restart" >> runs/watchdog.log
        ops/run-stop.sh "$d" >> runs/watchdog.log 2>&1; sleep 30; kill -9 "$(cat "$d/PID")" 2>/dev/null; rm -f "$d/PID"
        # shellcheck disable=SC2046
        ops/run-start.sh "$d" $(tr '\n' ' ' < "$d/ARGS") >> runs/watchdog.log 2>&1
      fi
    fi
  done
  sleep 300
done
