"""Unattended sequence of corpus phases, one after the other on the shared key (resumable; a finished phase leaves
runs/pipeline/<phase>.done). Waits for any batch already running in runs/main. A STOP.md in a run dir halts the pipeline.

    nohup .venv/bin/python ops/pipeline.py >> runs/pipeline/pipeline.log 2>&1 &"""
import json, os, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PIPE = ROOT / "runs/pipeline"; PIPE.mkdir(parents=True, exist_ok=True)
INP = "../data/inputs.jsonl.gz"
PHASES = [
    ("p1-slice", "runs/main", ["--since", "2025-01-01", "--steps", "ch", "sub", "yn"]),
    ("p2-evidence-2026", "runs/main", ["--since", "2026-01-01", "--steps", "ev"]),
    ("p3-evidence-2025", "runs/main", ["--since", "2025-01-01", "--until", "2025-12-31", "--steps", "ev"]),
    ("p4-since-2015-chapters", "runs/main", ["--since", "2015-01-01", "--until", "2024-12-31", "--steps", "ch"]),
]


def alive(run):
    p = ROOT / run / "PID"
    try:
        os.kill(int(p.read_text()), 0); return True
    except Exception:
        return False


def log(*a):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), *a, flush=True)


for name, run, args in PHASES:
    if (PIPE / f"{name}.done").exists():
        continue
    while alive(run):
        time.sleep(30)
    if (ROOT / run / "STOP.md").exists():
        log("STOP.md in", run, "- pipeline halted"); sys.exit(1)
    log("start", name, args)
    cmd = [str(ROOT / ".venv/bin/python"), "-m", "querschnitt.batch", "run", "--out", run, "--inputs", INP,
           "--conc", "6", "--max-rate", "1.7", "--cap", "60"] + args
    with open(ROOT / run / "run.log", "a") as f:
        rc = subprocess.call(["caffeinate", "-i"] + cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
    prog = (ROOT / run / "PROGRESS.md").read_text() if (ROOT / run / "PROGRESS.md").exists() else ""
    if rc == 0 and "**finished**" in prog:
        (PIPE / f"{name}.done").write_text(time.strftime("%Y-%m-%dT%H:%M:%S%z") + "\n" + prog)
        log("done", name)
    else:
        log("phase ended without finishing", name, "rc", rc); sys.exit(1)
log("pipeline complete")
