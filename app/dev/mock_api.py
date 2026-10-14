"""DEV ONLY: a stand-in for the live API (CONTRACT §2) so the app's live paths (Pult POSTs, Neues Thema streaming) can be
exercised without the engine. It serves app/ as static files on the same origin. Decisions it streams are NOT model
output: p is 0.97 when a word of the sentence (or of the terms) occurs in the title, else 0.02. Never deploy.

Usage: python3 app/dev/mock_api.py [port]   → http://127.0.0.1:8766/"""
from __future__ import annotations

import datetime as dt
import http.server
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
DATA = APP / "data" if (APP / "data" / "affairs.json").exists() else APP / "data-fixture"
A = json.loads((DATA / "affairs.json").read_text())
C = A.get("cols", A)
TOPICS: dict[str, dict] = {}
ROWS: list[dict] = []


def norm(s):
    return unicodedata.normalize("NFD", (s or "").lower()).encode("ascii", "ignore").decode()


def last_week_ids():
    gen = json.loads((DATA / "meta.json").read_text()).get("generated_at", "")[:10] or max(C["date"])
    d1 = dt.date.fromisoformat(gen); d0 = d1 - dt.timedelta(days=7)
    return [(i, C["id"][i]) for i in range(len(C["id"])) if d0.isoformat() <= (C["date"][i] or "") <= d1.isoformat()]


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(APP), **k)

    def log_message(self, *a):
        pass

    def js(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("content-type", "application/json"); self.send_header("access-control-allow-origin", "*")
        self.send_header("content-length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_OPTIONS(self):
        self.send_response(204); self.send_header("access-control-allow-origin", "*")
        self.send_header("access-control-allow-headers", "content-type"); self.send_header("access-control-allow-methods", "GET,POST"); self.end_headers()

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/health":
            return self.js({"ok": True, "mock": True})
        if p == "/metrics":
            return self.js({"affairs": len(C["id"]), "rows": len(C["id"]), "pending": 0, "rows_last_night": None, "mock": True})
        if p == "/changes":
            return self.js({"rows": ROWS, "next": None, "total": len(ROWS)})
        m = re.fullmatch(r"/adhoc/([\w-]+)/stream", p)
        if m:
            return self.stream(m.group(1))
        return super().do_GET()

    def do_POST(self):
        n = int(self.headers.get("content-length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        p = self.path.split("?")[0]
        if p == "/adhoc":
            s = body.get("sentence", "")
            words = [w for w in re.findall(r"[a-zA-ZÀ-ÿ]{5,}", s)][:6]
            if body.get("terms"):
                words = [w.strip() for w in re.split(r"[,·:]", body["terms"]) if len(w.strip()) >= 4 and w.strip() not in ("de", "fr", "it")]
            slug = re.sub(r"[^a-z0-9]+", "-", norm(s))[:40].strip("-") or "thema"
            TOPICS[slug] = {"words": [norm(w)[:7] for w in words]}
            ids = last_week_ids()
            per = [C["date"][ids[-1][0]], C["date"][ids[0][0]]] if ids else None
            TOPICS[slug]["period"] = per
            return self.js({"slug": slug, "period": per, "topic": {"names": {"de": s, "fr": s, "it": s}, "terms": {"de": words}, "mock": True}})
        m = re.fullmatch(r"/affairs/(\d+)/topics/(.+)/undo", p)
        if m:
            now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            for r in reversed(ROWS):
                if r["affair_id"] == int(m.group(1)) and r["valid_to"] is None and r["scheme"] == body.get("scheme"):
                    r["valid_to"] = now; return self.js(r)
            return self.js({"error": "nothing to undo"}, 404)
        m = re.fullmatch(r"/affairs/(\d+)/topics/(.+)/(confirm|reject)", p)
        if m:
            row = {"affair_id": int(m.group(1)), "code": m.group(2), "scheme": body.get("scheme"), "status": "confirmed" if m.group(3) == "confirm" else "rejected",
                   "provenance": "confirmed", "confirmed_by": body.get("by"), "confirmed_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                   "valid_from": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "valid_to": None}
            for r in ROWS:
                if r["affair_id"] == row["affair_id"] and r["scheme"] == row["scheme"] and r["valid_to"] is None and (r["code"] == row["code"] or row["scheme"] != "aps"):
                    r["valid_to"] = row["valid_from"]
            ROWS.append(row)
            return self.js(row)
        self.js({"error": "not found"}, 404)

    def stream(self, slug):
        words = TOPICS.get(slug, {}).get("words", [])
        self.send_response(200); self.send_header("content-type", "text/event-stream"); self.send_header("cache-control", "no-cache")
        self.send_header("access-control-allow-origin", "*"); self.end_headers()
        ids = last_week_ids(); t0 = time.time()
        cap = int(__import__("os").environ.get("MOCK_CAP", "0")) or None
        per = TOPICS.get(slug, {}).get("period") or [C["date"][ids[-1][0]] if ids else "", C["date"][ids[0][0]] if ids else ""]
        try:
            self.wfile.write(f"event: topic\ndata: {json.dumps({'slug': slug, 'period': per})}\n\n".encode())
            self.wfile.write(f"event: progress\ndata: {json.dumps({'total': len(ids), 'read': 0})}\n\n".encode()); self.wfile.flush()
            for k, (i, aid) in enumerate(ids):
                if cap and k >= cap:
                    self.wfile.write(f"event: done\ndata: {json.dumps({'read': k, 'error': f'RuntimeError(QS_ADHOC_MAX_CALLS {cap} reached)'})}\n\n".encode()); self.wfile.flush()
                    return
                hit = any(w and w in norm(C["title"][i]) for w in words)
                d = {"id": aid, "p": 0.97 if hit else 0.02, "flag": hit, "t": round(time.time() - t0, 2)}
                self.wfile.write(f"event: decision\ndata: {json.dumps(d)}\n\n".encode())
                self.wfile.write(f"event: progress\ndata: {json.dumps({'total': len(ids), 'read': k + 1})}\n\n".encode()); self.wfile.flush()
                time.sleep(0.02)
            self.wfile.write(b"event: done\ndata: {\"done\": true}\n\n"); self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8766
    http.server.ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
