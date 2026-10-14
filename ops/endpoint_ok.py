"""Exit 0 when the endpoint answers one plain request with the build a run locked, else 1. Used by ops/watchdog.sh and
ops/pipeline.py to resume runs that stopped on errors (an outage) once the endpoint is back.
Usage: .venv/bin/python ops/endpoint_ok.py runs/<dir>     (reads the lock from <dir>/state.json)"""
import json, sys, time, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt.client import Endpoint  # noqa: E402


def ok(run: Path) -> bool:
    lock = json.loads((run / "state.json").read_text())["lock"]
    ep = Endpoint.from_env()
    body = json.dumps(dict(model=lock["model"], messages=[{"role": "user", "content": "Antworte mit A."}], max_tokens=1,
                           temperature=0)).encode()
    req = urllib.request.Request(ep.base_url.rstrip("/") + "/chat/completions", body, method="POST",
                                 headers={"Authorization": f"Bearer {ep.key()}", "Content-Type": "application/json",
                                          "User-Agent": "querschnitt/0.6"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read())
    except Exception as e:
        print(time.strftime("%F %T"), "endpoint not ok:", type(e).__name__, str(e)[:120]); return False
    if d.get("system_fingerprint") != lock["fp"]:
        print(time.strftime("%F %T"), "endpoint answers another build:", d.get("system_fingerprint")); return False
    return True


if __name__ == "__main__":
    sys.exit(0 if ok(ROOT / sys.argv[1]) else 1)
