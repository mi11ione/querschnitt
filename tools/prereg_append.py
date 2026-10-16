"""Append one entry to eval/PREREG-BUILD.md and log its sha256 + UTC time in eval/PREREG-BUILD.sha256, under a lock (several
jobs may pre-register at once). The entry's header time is taken from the clock now, never typed by hand. Then the two
files alone are committed and pushed, so the entry has a public timestamp before any call it governs (--no-push skips).
Usage: python tools/prereg_append.py "S28 short title (what is fixed before which call)" entry.md [--no-push]"""
import datetime as dt, hashlib, os, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
LOG, SHA, LOCK = ROOT / "eval/PREREG-BUILD.md", ROOT / "eval/PREREG-BUILD.sha256", ROOT / "eval/.prereg.lock"
if os.environ.get("QS_PREREG_LOG"):   # another log (make scheme-eval --prereg local: a tooling check's run dir); never pushed
    LOG = Path(os.environ["QS_PREREG_LOG"]).resolve()
    SHA, LOCK = LOG.with_suffix(".sha256"), LOG.parent / ".prereg.lock"


def main(title: str, body_file: str, push: bool = True):
    body = Path(body_file).read_text().strip()
    for _ in range(600):                                   # mkdir is atomic: a portable lock (macOS has no flock(1))
        try:
            os.mkdir(LOCK); break
        except FileExistsError:
            time.sleep(0.1)
    else:
        sys.exit("prereg lock busy for 60 s: remove eval/.prereg.lock if no other job is writing")
    try:
        now = dt.datetime.now().astimezone()
        with open(LOG, "a") as f:
            f.write(f"\n## {now:%Y-%m-%d %H:%M} CEST — {title}\n{body}\n")
        h = hashlib.sha256(LOG.read_bytes()).hexdigest()
        with open(SHA, "a") as f:
            f.write(f"{h}  {LOG.relative_to(ROOT) if LOG.is_relative_to(ROOT) else LOG}\n{dt.datetime.now(dt.timezone.utc):%a %b %d %H:%M:%S UTC %Y}\n")
        print(f"pre-registered at {now:%H:%M:%S} · sha256 {h[:12]}…")
        if push and not os.environ.get("QS_PREREG_LOG"):
            files = ["eval/PREREG-BUILD.md", "eval/PREREG-BUILD.sha256"]
            c = subprocess.run(["git", "commit", "-q", "-m", f"Pre-registration: {title}", "--", *files], cwd=ROOT)
            p = subprocess.run(["git", "push", "-q"], cwd=ROOT) if c.returncode == 0 else c
            print("committed and pushed" if p.returncode == 0 else "NOT pushed: commit and push eval/PREREG-BUILD.* before any call")
    finally:
        os.rmdir(LOCK)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--no-push"]
    main(args[0], args[1], push="--no-push" not in sys.argv)
