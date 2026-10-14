#!/bin/zsh
# re-render interim results every 10 min while the runner is alive
cd /Users/mi11ion/Desktop/hackapertus/bern/ideation2/spikes/s9-aps
while pgrep -f "scripts/run.py" >/dev/null; do
  python3 -I scripts/analyze.py >/dev/null 2>>raw/analyze_err.log && python3 -I scripts/render_md.py interim >/dev/null 2>>raw/analyze_err.log
  sleep 600
done
