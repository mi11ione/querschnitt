#!/bin/sh
# two lanes x 4 workers = 8 concurrent requests max
cd "$(dirname "$0")"
lane1() { while pgrep -f "run.py e2d" >/dev/null; do sleep 5; done
  for p in e1m e5a e5b e5t e6f; do python3 -I run.py $p 4; done; echo LANE1_DONE; }
lane2() { while pgrep -f "run.py e3a" >/dev/null; do sleep 5; done
  for p in e3m e3b e6a e6b; do python3 -I run.py $p 4; done; echo LANE2_DONE; }
lane1 > raw/lane1.log 2>&1 &
lane2 > raw/lane2.log 2>&1 &
wait
