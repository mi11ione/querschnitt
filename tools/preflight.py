"""Morning preflight for the demo (docs/ONSITE.md): one table, green / red, and what to do for each red.

    .venv/bin/python -I tools/preflight.py                 every check (about 30 s; the API check expects make demo running)
    .venv/bin/python -I tools/preflight.py --no-tests      without the quick test subset
    .venv/bin/python -I tools/preflight.py --endpoint-only one line: does the model endpoint answer (make demo prints it)

Checks: venv, the scored data in app/data, the demo affair, the Neues-Thema recording, the demo store, app assets local
(no CDN), disk space, a quick test subset, the local API (make demo), the deployed site, the model endpoint (QS_BASE_URL /
QS_MODEL / QS_API_KEY as Neues Thema uses them; one /models request and one 1-token request, short timeouts).
Exit code 1 when a check is red. Standard library only; no model call beyond the one 1-token request."""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

DEMO_ID = 334708
SITE = "https://querschnitt.mi11ion.io"
PY = ROOT / ".venv/bin/python"
QUICK = ["tests/test_api.py", "tests/test_store.py", "tests/test_compose.py", "tests/test_prompts.py",
         "tests/test_adhoc.py::test_new_topic_streams", "tests/test_adhoc.py::test_dead_endpoint_refuses_in_seconds"]
OK, WARN, BAD = "ok", "warn", "RED"
rows: list[tuple[str, str, str, str]] = []          # (check, status, detail, what to do)


def add(name: str, status: str, detail: str, todo: str = ""):
    rows.append((name, status, detail, todo if status != OK else ""))


def get(url: str, timeout: float, headers: dict | None = None, data: bytes | None = None) -> tuple[int, bytes, float]:
    t0 = time.time()
    req = urllib.request.Request(url, data=data, headers=dict(headers or {}, **{"User-Agent": "querschnitt-preflight"}))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:400], time.time() - t0


# ---------------------------------------------------------------- checks
def venv():
    if not PY.exists():
        return add("venv", BAD, "no .venv/bin/python", "make install (needs internet once)")
    r = subprocess.run([str(PY), "-c", "import sys, fastapi, uvicorn, yaml; import querschnitt.api; print(sys.version.split()[0])"],
                       capture_output=True, text=True, env=dict(os.environ, PYTHONPATH=str(ROOT / "src")), timeout=60)
    if r.returncode:
        return add("venv", BAD, (r.stderr.strip().splitlines() or ["import failed"])[-1][:90], "make install")
    add("venv", OK, f"Python {r.stdout.strip()}, fastapi, uvicorn, querschnitt import")


def data():
    d = ROOT / "app/data"
    need = ["affairs.json", "topics.jsonl.gz", "meta.json", "bodies.json", "scheme_aps.json", "geo.json", "pruefstand.json",
            "integration.json", "neu_replay.json"]
    miss = [f for f in need if not (d / f).exists()]
    if miss:
        return add("data", BAD, f"missing in app/data: {', '.join(miss)}", "make data (while online), then make demo FRESH=1")
    m = json.loads((d / "meta.json").read_text())
    add("data", OK, f"app/data complete; export until {m.get('until', '?')}, build {m.get('build_short') or m.get('build', '?')}")


def affair():
    d = ROOT / "app/data"
    try:
        a = json.loads((d / "affairs.json").read_text())
        ids = set((a.get("cols") or a)["id"])
    except Exception as e:  # noqa: BLE001
        return add("demo affair", BAD, f"affairs.json unreadable: {e!r}"[:90], "make data")
    det = d / "detail" / f"{DEMO_ID // 1000}.json"
    in_det = det.exists() and str(DEMO_ID) in json.loads(det.read_text())
    rows_ = 0
    with gzip.open(d / "topics.jsonl.gz", "rt") as f:
        for line in f:
            if f'"affair_id": {DEMO_ID},' in line or f'"affair_id":{DEMO_ID},' in line:
                rows_ += 1
    if DEMO_ID in ids and in_det and rows_:
        return add("demo affair", OK, f"{DEMO_ID} in affairs.json, detail/{DEMO_ID // 1000}.json, {rows_} topic rows")
    add("demo affair", BAD, f"{DEMO_ID}: affairs {DEMO_ID in ids}, detail {in_det}, topic rows {rows_}",
        "the data changed: pick another DE/FR-disagreement affair for Gate 1 and update docs/DEMO.md")


def replay():
    p = ROOT / "app/data/neu_replay.json"
    try:
        r = json.loads(p.read_text())
        ev = r["events"]
        n = sum(1 for e in ev if e.get("event") == "decision")
        assert r.get("sentence") and r.get("post", {}).get("slug") and n
    except Exception as e:  # noqa: BLE001
        return add("recording", BAD, f"neu_replay.json: {e!r}"[:90], "make data (it ships in the release), or python app/dev/make_replay.py")
    add("recording", OK, f"neu_replay.json: {n} decisions, recorded {r.get('recorded', '?')[:10]}, {r.get('model', '?')}")


def store():
    p = Path(os.environ.get("DEMO_DB") or ROOT / "runs/demo/querschnitt.sqlite")
    if not p.exists():
        return add("demo store", WARN, f"{p.relative_to(ROOT) if p.is_relative_to(ROOT) else p} not loaded yet",
                   "make demo loads it on first start (about a minute)")
    try:
        c = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=5)
        # read-only: a store not yet opened by this version still has its rows in `topics` (the store renames it on open)
        t = "qs_topics" if c.execute("SELECT 1 FROM sqlite_master WHERE name = 'qs_topics'").fetchone() else "topics"
        n = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        a = c.execute("SELECT COUNT(*) FROM qs_affairs WHERE id = ?", (DEMO_ID,)).fetchone()[0]
        dec = c.execute(f"SELECT COUNT(*) FROM {t} WHERE affair_id = ? AND valid_to IS NULL AND status IN ('confirmed', 'rejected')",
                        (DEMO_ID,)).fetchone()[0]
        c.close()
    except Exception as e:  # noqa: BLE001
        return add("demo store", BAD, f"{e!r}"[:90], "make demo FRESH=1")
    if not n or not a:
        return add("demo store", BAD, f"{n} rows, demo affair {'present' if a else 'missing'}", "make demo FRESH=1")
    if dec:
        return add("demo store", WARN, f"{n:,} rows; {DEMO_ID} already has {dec} decision(s) from a rehearsal",
                   "make demo FRESH=1 (the Decide beat should start undecided)")
    add("demo store", OK, f"{n:,} rows, {DEMO_ID} present and undecided")


ASSET = re.compile(r"""(?:src|href)\s*=\s*["']https?://|url\(\s*["']?https?://|@import\s+["']?(?:url\()?https?://|"""
                   r"""fetch\(\s*[`'"]https?://|import\s*\(?\s*[`'"]https?://|from\s+[`'"]https?://""")


def assets():
    hits = []
    for f in [ROOT / "app/index.html", *sorted((ROOT / "app/css").glob("*.css")), *sorted((ROOT / "app/js").glob("*.js"))]:
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if ASSET.search(line):
                hits.append(f"{f.relative_to(ROOT)}:{i}")
    fonts = sorted(x.name for x in (ROOT / "app/fonts").glob("*.woff2"))
    if hits:
        return add("assets local", BAD, f"remote loads: {', '.join(hits[:3])}", "vendor the file into app/ (no CDN on stage)")
    add("assets local", OK, f"no remote script/style/font/fetch in app/; {len(fonts)} fonts in app/fonts")


def disk():
    free = shutil.disk_usage(ROOT).free / 1e9
    add("disk", OK if free >= 5 else WARN if free >= 1 else BAD, f"{free:.1f} GB free", "free space (runs/, ~/Library/Caches)")


def tests():
    if not PY.exists():
        return add("tests (quick)", BAD, "no venv", "make install")
    t0 = time.time()
    r = subprocess.run([str(PY), "-m", "pytest", "-q", "-x", *QUICK], cwd=ROOT, capture_output=True, text=True, timeout=300,
                       env=dict(os.environ, PYTHONPATH=str(ROOT / "src")))
    last = (r.stdout.strip().splitlines() or ["no output"])[-1]
    add("tests (quick)", OK if r.returncode == 0 else BAD, f"{last[:70]} ({time.time() - t0:.0f} s)",
        "make test; read the first failure before the demo")


def api(base: str):
    try:
        st, body, dt = get(f"{base}/health", 2)
        h = json.loads(body)
        assert st == 200 and h.get("ok") and h.get("rows")
    except Exception as e:  # noqa: BLE001
        return add("local API", BAD, f"{base}/health: {type(e).__name__}", "make demo (in its own terminal), then rerun")
    try:
        st, body, _ = get(f"{base}/affairs/{DEMO_ID}/topics", 3)
        n = len(json.loads(body)["topics"]) if st == 200 else 0
        st2, page, _ = get(f"{base}/", 3)
        assert st2 == 200 and b"js/main.js" in page
    except Exception as e:  # noqa: BLE001
        return add("local API", BAD, f"health ok, app or affair failed: {e!r}"[:90], "make demo FRESH=1")
    add("local API", OK if n else BAD, f"{base}: {h['rows']:,} rows, {h['store']}, affair {DEMO_ID}: {n} rows",
        "make demo FRESH=1")


def site():
    try:
        st, page, dt = get(SITE + "/", 6)
        st2, meta, _ = get(SITE + "/data/meta.json", 6)
        assert st == 200 and st2 == 200
        m, mine = json.loads(meta), json.loads((ROOT / "app/data/meta.json").read_text())
    except Exception as e:  # noqa: BLE001
        return add("deployed site", BAD, f"{SITE}: {type(e).__name__}", "no internet or site down: the laptop (make demo) is the demo")
    same = m.get("build") == mine.get("build") and m.get("until") == mine.get("until")
    add("deployed site", OK if same else WARN, f"answers in {dt:.1f} s; data until {m.get('until')}"
        + ("" if same else f" (local {mine.get('until')})"), "the site and the laptop show different data: deploy, or say which one is shown")


def endpoint(timeout: float = 5):
    from querschnitt.client import Endpoint
    ep = Endpoint.from_env()
    base, hdr = ep.base_url.rstrip("/"), {"Authorization": f"Bearer {ep.key()}", "Content-Type": "application/json"}
    todo = ("Neues Thema: Enter answers in seconds with «Der Modell-Endpunkt antwortet nicht» and offers the recording "
            f"(or open #neu?rec=1); check QS_BASE_URL / key ({ep.name})")
    try:
        st, body, dt = get(base + "/models", timeout, hdr)
    except Exception as e:  # noqa: BLE001
        return add("model endpoint", BAD, f"{base}: {type(e).__name__} {str(e)[:40]}", todo)
    if st != 200:
        return add("model endpoint", BAD, f"{base}/models: HTTP {st}", todo)
    listed = ep.model in body.decode("utf-8", "replace")
    req = json.dumps(dict(model=ep.model, max_tokens=1, temperature=0,
                          messages=[{"role": "user", "content": "Antworte mit Ja oder Nein: Ist Bern eine Stadt?"}])).encode()
    try:
        st, body, dt2 = get(base + "/chat/completions", 2 * timeout, hdr, req)
        assert st == 200, f"HTTP {st}"
        ans = (json.loads(body)["choices"][0].get("message") or {}).get("content", "")
    except Exception as e:  # noqa: BLE001
        return add("model endpoint", BAD, f"/models ok, 1-token request: {str(e)[:50]}", todo)
    add("model endpoint", OK if listed else WARN, f"{ep.name} {ep.model}: /models {dt:.1f} s, 1 token {dt2:.1f} s ({ans!r})",
        f"{ep.model} not listed in /models: check QS_MODEL")


# ---------------------------------------------------------------- table
def table() -> int:
    tty = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
    col = {OK: "\033[32m", WARN: "\033[33m", BAD: "\033[31m"}
    w = max(len(r[0]) for r in rows)
    for name, st, detail, _ in rows:
        mark = f"{col[st]}{st:>4}\033[0m" if tty else f"{st:>4}"
        print(f"{mark}  {name:<{w}}  {detail}")
    todo = [(n, t) for n, s, _, t in rows if s != OK and t]
    if todo:
        print("\nwhat to do:")
        for n, t in todo:
            print(f"  {n}: {t}")
    red = sum(r[1] == BAD for r in rows)
    print(f"\n{len(rows) - red} of {len(rows)} not red" + ("" if red else "; the demo runs from this laptop"))
    return 1 if red else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--api", default=os.environ.get("QS_DEMO_URL", "http://127.0.0.1:8000"), help="the make demo server")
    ap.add_argument("--no-tests", action="store_true")
    ap.add_argument("--endpoint-only", action="store_true")
    a = ap.parse_args()
    if a.endpoint_only:
        endpoint(timeout=3)
        name, st, detail, _ = rows[0]
        print(f"model endpoint: {detail}" + ("" if st == OK else
              " → Neues Thema offers the recording (labelled) after a few seconds; #neu?rec=1 opens it directly"))
        return 0
    for f in (venv, data, affair, replay, store, assets, disk):
        f()
    if not a.no_tests:
        tests()
    api(a.api.rstrip("/"))
    site()
    endpoint()
    return table()


if __name__ == "__main__":
    sys.exit(main())
