#!/bin/sh
# Usage: ops/run-status.sh <run dir>
OUT="$1"
if [ -f "$OUT/PID" ] && kill -0 "$(cat "$OUT/PID")" 2>/dev/null; then echo "process: running (PID $(cat "$OUT/PID"))"; else echo "process: not running"; fi
cat "$OUT/PROGRESS.md" 2>/dev/null; [ -f "$OUT/STOP.md" ] && { echo; cat "$OUT/STOP.md"; }
for f in "$OUT"/*/*.jsonl; do [ -f "$f" ] && printf '%8d %s\n' "$(wc -l < "$f")" "$f"; done
tail -3 "$OUT/errors.jsonl" 2>/dev/null
