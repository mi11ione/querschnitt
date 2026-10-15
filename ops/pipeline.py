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
    ("p1b-aps-gold", "runs/main", ["--ids", "runs/pipeline/ids_s9_gold.txt", "--steps", "ch", "sub"]),
    ("p1c-trim-inputs", None, ["QS_TRIM_DOCS=1", "build-inputs"]),          # documents start at the title (letterheads cut)
    ("p1d-rescore-changed", "runs/main", ["--since", "2025-01-01", "--steps", "ch", "sub", "yn"]),   # cache: only changed
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


STRIKES, LEDGER_AT = {}, {}   # Errors resumes per run without a successful call between them


def log(*a):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), *a, flush=True)


for name, run, args in PHASES:
    if (PIPE / f"{name}.done").exists():
        continue
    if run is None:   # a command phase: rebuild inputs with the given environment
        env = dict(os.environ, **dict(a.split("=", 1) for a in args if "=" in a))
        log("start", name)
        rc = subprocess.call([str(ROOT / ".venv/bin/python"), "-m", "querschnitt.data", str(ROOT.parent / "data/opd-new"),
                              str(ROOT.parent / "data/inputs.jsonl.gz")], cwd=ROOT, env=env)
        if rc == 0:
            (PIPE / f"{name}.done").write_text(time.strftime("%Y-%m-%dT%H:%M:%S%z")); log("done", name); continue
        log("command phase failed", name, rc); sys.exit(1)
    while alive(run):
        time.sleep(30)
    while (ROOT / run / "STOP.md").exists() and "Disk low" in (ROOT / run / "STOP.md").read_text():
        import shutil
        if shutil.disk_usage(ROOT).free > 3e9:   # space came back: resume by itself
            (ROOT / run / "STOP.md").rename(ROOT / run / f"STOP-{time.strftime('%Y%m%d-%H%M%S')}.md"); break
        time.sleep(300)
    errors_stop = lambda: (ROOT / run / "STOP.md").exists() and (ROOT / run / "STOP.md").read_text().startswith("# Errors")
    if errors_stop():
        # once per stop: a run that made no successful call since its last resume is a strike (errors that are not an
        # outage, e.g. a bug); three strikes leave it stopped for a person instead of resuming it again
        led = ROOT / run / "ledger.jsonl"; n = sum(1 for _ in open(led)) if led.exists() else 0
        STRIKES[run] = STRIKES.get(run, 0) + 1 if n == LEDGER_AT.get(run) else 0; LEDGER_AT[run] = n
        if STRIKES[run] >= 3:
            log("three resumes without a successful call in", run, "- left stopped for a person")
    while errors_stop() and STRIKES.get(run, 0) < 3:
        # an endpoint outage: resume once the endpoint answers with the build this run locked
        if subprocess.call([str(ROOT / ".venv/bin/python"), str(ROOT / "ops/endpoint_ok.py"), run], cwd=ROOT) == 0:
            (ROOT / run / "STOP.md").rename(ROOT / run / f"STOP-{time.strftime('%Y%m%d-%H%M%S')}.md"); log("endpoint back", run); break
        time.sleep(300)
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
    elif (ROOT / run / "STOP.md").exists() and ("Disk low" in (ROOT / run / "STOP.md").read_text()
                                                 or (ROOT / run / "STOP.md").read_text().startswith("# Errors")):
        log("paused (disk or endpoint)", name); PHASES.insert(PHASES.index((name, run, args)) + 1, (name, run, args))
    else:
        log("phase ended without finishing", name, "rc", rc); sys.exit(1)
log("pipeline complete")
