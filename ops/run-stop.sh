#!/bin/sh
# Graceful stop (in-flight requests finish; everything done is on disk). Usage: ops/run-stop.sh <run dir>
OUT="$1"; [ -f "$OUT/PID" ] && kill -TERM "$(cat "$OUT/PID")" && echo "SIGTERM sent to $(cat "$OUT/PID")" || echo "not running"
