#!/bin/sh
# Every 5 min: a run dir paused for disk ("Disk low" STOP.md) resumes with its recorded ARGS once > 3 GB are free.
# The pipeline-managed runs/main resumes through ops/pipeline.py; this covers side runs started with ops/run-start.sh.
cd "$(dirname "$0")/.." || exit 1
echo $$ > runs/watchdog.pid
while true; do
  free=$(df -k . | awk 'NR==2{print $4}')
  for d in runs/*/; do
    d=${d%/}; [ "$d" = runs/main ] && continue
    if [ -f "$d/STOP.md" ] && grep -q "Disk low" "$d/STOP.md" && [ -f "$d/ARGS" ] && [ "$free" -gt 3000000 ]; then
      mv "$d/STOP.md" "$d/STOP-$(date +%Y%m%d-%H%M%S).md"
      echo "$(date '+%F %T') resume $d" >> runs/watchdog.log
      # shellcheck disable=SC2046
      ops/run-start.sh "$d" $(tr '\n' ' ' < "$d/ARGS") >> runs/watchdog.log 2>&1
    fi
  done
  sleep 300
done
