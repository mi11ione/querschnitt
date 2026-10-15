"""Append one entry to eval/PREREG-BUILD.md and log its sha256 + UTC time in eval/PREREG-BUILD.sha256, under a lock (several
jobs may pre-register at once). The entry's header time is taken from the clock now, never typed by hand.
Usage: python tools/prereg_append.py "S28 short title (what is fixed before which call)" entry.md"""
import datetime as dt, hashlib, os, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
LOG, SHA, LOCK = ROOT / "eval/PREREG-BUILD.md", ROOT / "eval/PREREG-BUILD.sha256", ROOT / "eval/.prereg.lock"


def main(title: str, body_file: str):
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
            f.write(f"{h}  eval/PREREG-BUILD.md\n{dt.datetime.now(dt.timezone.utc):%a %b %d %H:%M:%S UTC %Y}\n")
        print(f"pre-registered at {now:%H:%M:%S} · sha256 {h[:12]}…")
    finally:
        os.rmdir(LOCK)


if __name__ == "__main__":
    main(*sys.argv[1:3])
