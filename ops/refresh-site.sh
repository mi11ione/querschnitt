#!/bin/sh
# Every 3 h: static export of the current run state → app/data, then deploy to querschnitt.mi11ion.io. Log: runs/refresh.log
cd "$(dirname "$0")/.."
while true; do
  echo "$(date '+%F %T') export" >> runs/refresh.log
  .venv/bin/python -m querschnitt.export --out app/data --topics-file >> runs/refresh.log 2>&1 && \
    (cd ../../querschnitt-site && ./deploy.sh 2>&1 | grep -E "Deployed|Version ID|files:" >> ../bern/querschnitt/runs/refresh.log)
  sleep 10800
done
