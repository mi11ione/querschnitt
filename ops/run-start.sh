#!/bin/sh
# Start or resume a corpus run in the background (nohup + caffeinate). Usage: ops/run-start.sh <run dir> [batch args…]
# Example: ops/run-start.sh ../runs/main --inputs ../data/inputs.jsonl.gz --since 2025-01-01
set -e
cd "$(dirname "$0")/.."
OUT="$1"; shift
mkdir -p "$OUT"
if [ -f "$OUT/PID" ] && kill -0 "$(cat "$OUT/PID")" 2>/dev/null; then echo "running: PID $(cat "$OUT/PID")"; exit 1; fi
[ -f "$OUT/STOP.md" ] && { echo "$OUT/STOP.md exists:"; cat "$OUT/STOP.md"; exit 1; }
printf '%s\n' "$@" > "$OUT/ARGS"   # for ops/watchdog.sh (resume after a disk pause)
nohup caffeinate -i .venv/bin/python -m querschnitt.batch run --out "$OUT" "$@" >> "$OUT/run.log" 2>&1 &
sleep 3; tail -2 "$OUT/run.log"
