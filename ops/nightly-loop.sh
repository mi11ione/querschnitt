#!/bin/sh
# Runs ops/nightly.sh every day at 09:15 local time. Started once with nohup from a session that can read ~/Desktop
# (cron cannot: macOS privacy rules block it). PID in runs/nightly/loop.pid.
cd "$(dirname "$0")/.." || exit 1
echo $$ > runs/nightly/loop.pid
while true; do
  now=$(date +%s); next=$(date -j -f "%Y-%m-%d %H:%M:%S" "$(date +%F) 09:15:00" +%s)
  [ "$next" -le "$now" ] && next=$(( next + 86400 ))
  sleep $(( next - now ))
  ops/nightly.sh
done
