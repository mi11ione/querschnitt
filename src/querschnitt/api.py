"""HTTP API (docs/CONTRACT.md §2) over the topics store, the Neues-Thema backend, and the static app from app/ at `/`.

    querschnitt serve [--host 127.0.0.1 --port 8000]      (QS_DB / QS_PG_DSN pick the store)

Every response is JSON in the shapes of the static export; rows carry `label` {de, fr, it} from the scheme files."""
from __future__ import annotations

import asyncio
import contextlib
import json
import os
import re
import time
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import scheme as S
from .adhoc import Adhoc
from .compose import VERSION
from .scheme import APS
from .store import ROOT, Store, metrics_line

STATIC_SCHEMES = ("aps", "curia28", "be-directorates")


def label(scheme: str, code: str) -> dict | None:
    """{de, fr, it} name of a code (APS chapter / subtopic, ad-hoc yes/no, flat schemes where their file has one)."""
    if scheme == "aps":
        if code in APS.codes:
            i = APS.codes.index(code)
            return {l: APS.short(i, l) for l in ("de", "fr", "it")}
        if code in APS.sub_name:
            return {"de": APS.sub_name[code]}
        return None
    if scheme.startswith("adhoc/"):
        try:
            t = S.adhoc(scheme.split("/", 1)[1])
        except (FileNotFoundError, OSError):
            return None
        return t.get("names")
    for c in flat_codes(scheme):
        if c.get("code") == code:
            return c.get("name")
    return None


def flat_codes(scheme: str) -> list[dict]:
    try:
        doc = S.flat(scheme)
    except (FileNotFoundError, OSError):
        return []
    return [c for c in (doc.get("options") or []) + ([doc["none"]] if doc.get("none") else []) if isinstance(c, dict)]


def full_code(scheme: str, code: str) -> str:
    """Short forms: `1.7.2.` / `kw:1374918` (aps), `yes` (adhoc/<slug>), `BKD` (flat scheme option)."""
    if scheme == "aps":
        return code if code.startswith("aps:") else f"aps:{code}"
    if scheme.startswith("adhoc/"):
        return code if code.startswith(scheme + ":") else f"{scheme}:{code}"
    if ":" in code:
        return code
    m = [c["code"] for c in flat_codes(scheme) if c["code"].split(":", 1)[-1] == code]
    return m[0] if m else f"{scheme}:{code}"


def scheme_of(code: str) -> str | None:
    if code.startswith("aps:"):
        return "aps"
    if code.startswith("adhoc/"):
        return code.rsplit(":", 1)[0]
    for s in STATIC_SCHEMES:
        if any(c["code"] == code for c in flat_codes(s)):
            return s
    return None


def with_label(r: dict) -> dict:
    r["label"] = label(r["scheme"], r["code"])
    return r


def known_schemes(store: Store) -> list[str]:
    s = set(STATIC_SCHEMES) | {f"adhoc/{x}" for x in S.adhoc_topics()} | set(store.schemes())
    return sorted(s, key=len, reverse=True)


def split_scheme_code(rest: str, store: Store) -> tuple[str, str]:
    """`adhoc/digitalisierung/yes`, `aps/1.7.2.`, `aps/aps:kw:1374918` → (scheme, full code)."""
    for s in known_schemes(store):
        if rest.startswith(s + "/"):
            code = rest[len(s) + 1:]
            if not code:
                break
            return s, full_code(s, code)
    raise HTTPException(404, f"unknown scheme in {rest!r}; known: {', '.join(sorted(known_schemes(store)))}")


def create_app(store: Store | None = None, adhoc: Adhoc | None = None, app_dir: str | Path | None = None) -> FastAPI:
    st = store or Store()
    ah = adhoc or Adhoc(st)
    @contextlib.asynccontextmanager
    async def lifespan(_app):
        yield
        ah.shutdown()                      # running Neues-Thema jobs stop with the server

    app = FastAPI(title="Querschnitt", version=VERSION, description="Topic rows for OpenParlData affairs, decided by Apertus.",
                  lifespan=lifespan)
    app.state.store, app.state.adhoc, app.state.t0 = st, ah, time.time()
    app.add_middleware(CORSMiddleware, allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?",
                       allow_methods=["GET", "POST", "PUT", "OPTIONS"], allow_headers=["*"])

    # ---------------------------------------------------------------- affairs and topics
    @app.get("/affairs/{aid}/topics")
    def affair_topics(aid: int, scheme: str | None = None, history: bool = False):
        rows = [with_label(r) for r in st.topics_for(aid, scheme, history)]
        aff = st.affair(aid)
        if aff is None and not rows:
            raise HTTPException(404, f"affair {aid} not loaded")
        return {"affair": aff or {"id": aid}, "topics": rows}

    @app.get("/topics/{rest:path}")
    def topic_affairs(rest: str, date_from: str | None = Query(None, alias="from"), date_to: str | None = Query(None, alias="to"),
                      body: str | None = None, level: str | None = None, lang: str | None = None, lane: str | None = None,
                      status: str | None = None, rank: int | None = 1, limit: int = Query(100, ge=1, le=5000),
                      offset: int = Query(0, ge=0)):
        if not rest.endswith("/affairs"):
            raise HTTPException(404, "use /topics/{scheme}/{code}/affairs")
        scheme, code = split_scheme_code(rest[: -len("/affairs")], st)
        total, rows = st.by_code(scheme, code, date_from, date_to, body, level, lang, lane, status, rank, limit, offset)
        return {"scheme": scheme, "code": code, "label": label(scheme, code), "total": total, "limit": limit, "offset": offset,
                "rows": [with_label(r) for r in rows]}

    @app.post("/affairs/{aid}/topics/{rest:path}")
    def decide(aid: int, rest: str, payload: dict = Body(default={})):
        m = re.fullmatch(r"(.+)/(confirm|reject)", rest)
        if not m:
            raise HTTPException(404, "use /affairs/{id}/topics/{code}/confirm|reject")
        code, action = m.group(1), m.group(2)
        scheme = payload.get("scheme") or scheme_of(code)
        if not scheme:
            raise HTTPException(422, f"cannot tell the scheme of {code!r}; send {{\"scheme\": …}}")
        code = full_code(scheme, code)
        if scheme == "aps" and code not in APS.codes and code not in APS.sub_name:
            raise HTTPException(422, f"{code} is not an APS code")
        if scheme.startswith("adhoc/") and code not in (f"{scheme}:yes", f"{scheme}:no"):
            raise HTTPException(422, f"{code} is not a code of {scheme} (:yes / :no)")
        try:
            row = st.decide(aid, scheme, code, action, payload.get("by", ""))
        except ValueError as e:
            raise HTTPException(422, str(e))
        return with_label(row)

    @app.get("/changes")
    def changes(since: str, scheme: str | None = None, limit: int = Query(1000, ge=1, le=20000), offset: int = Query(0, ge=0)):
        try:
            rows = st.changes(since, scheme, limit, offset)
        except ValueError as e:
            raise HTTPException(422, f"since: {e}")
        return {"since": since, "n": len(rows), "rows": rows}

    @app.get("/coverage")
    def coverage(scheme: str = "aps"):
        return {"scheme": scheme, "bodies": st.coverage(scheme)}

    @app.get("/schemes")
    def schemes():
        return {"schemes": sorted(known_schemes(st)),
                "aps": {"chapters": [{"code": c, "name": {l: APS.short(i, l) for l in ("de", "fr", "it")},
                                      "subtopics": [{"code": s, "name": {"de": APS.sub_name[s]}} for s in APS.sub_codes.get(i, [])]}
                                     for i, c in enumerate(APS.codes)]},
                "adhoc": [{"id": f"adhoc/{x}", "names": S.adhoc(x).get("names")} for x in S.adhoc_topics()]}

    # ---------------------------------------------------------------- Neues Thema
    @app.post("/adhoc")
    def adhoc_start(payload: dict = Body(...)):
        try:
            job = ah.start(payload.get("sentence", ""), payload.get("lang", "de"), payload.get("examples"),
                           payload.get("period"), payload.get("from"), payload.get("to"), payload.get("terms"),
                           payload.get("limit"), payload.get("generate", True))
        except ValueError as e:
            raise HTTPException(422, str(e))
        return {"slug": job.slug, "topic": job.topic, "terms": job.terms, "terms_pending": job.terms_thread.is_alive(),
                "period": job.period, "stream": f"/adhoc/{job.slug}/stream"}

    def _job(slug: str):
        job = ah.jobs.get(slug)
        if job is None:
            raise HTTPException(404, f"no ad-hoc run {slug!r} in this process")
        return job

    @app.get("/adhoc/{slug}")
    def adhoc_state(slug: str):
        job = _job(slug)
        return {"slug": slug, "topic": job.topic, "terms": job.terms, "period": job.period, "done": job.done,
                "error": job.error, "summary": job.summary(),
                "decisions": sorted(job.decisions.values(), key=lambda d: (d["date"], d["id"]), reverse=True)}

    @app.get("/adhoc/{slug}/stream")
    async def adhoc_stream(slug: str, request: Request, start: int = Query(0, alias="from", ge=0)):
        job = _job(slug)
        last = request.headers.get("last-event-id")
        i = int(last) + 1 if last and last.isdigit() else start

        async def gen():
            nonlocal i
            idle = 0.0
            while True:
                if await request.is_disconnected():
                    return
                sent = False
                while i < len(job.events):
                    e = job.events[i]
                    yield f"id: {i}\nevent: {e['event']}\ndata: {json.dumps(e['data'], ensure_ascii=False)}\n\n"
                    i += 1; sent = True
                if job.done and i >= len(job.events):
                    return
                if sent:
                    idle = 0.0
                else:
                    idle += 0.2
                    if idle >= 15:
                        yield ": keep-alive\n\n"; idle = 0.0
                await asyncio.sleep(0.2)

        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.post("/adhoc/{slug}/stop")
    def adhoc_stop(slug: str):
        job = _job(slug)
        job.stop.set()
        return {"slug": slug, "stopping": True}

    @app.put("/adhoc/{slug}/terms")
    def adhoc_terms(slug: str, payload: dict = Body(...)):
        job = _job(slug)
        job.terms = ah.verify_terms(payload.get("terms") or {})
        return {"slug": slug, "terms": job.terms}

    @app.post("/adhoc/{slug}/save")
    def adhoc_save(slug: str, payload: dict = Body(default={})):
        _job(slug)
        return ah.save(slug, payload.get("examples"), payload.get("by"), payload.get("load_rows", True))

    # ---------------------------------------------------------------- operations
    @app.get("/health")
    def health():
        try:
            n = st.one("SELECT COUNT(*) AS n FROM topics")["n"]
            return {"ok": True, "store": st.kind, "rows": n, "version": VERSION, "uptime_s": round(time.time() - app.state.t0)}
        except Exception as e:  # noqa: BLE001
            return JSONResponse({"ok": False, "store": st.kind, "error": repr(e)[:300]}, status_code=503)

    @app.get("/metrics")
    def metrics(format: str = "json"):
        m = st.metrics()
        m["line"] = metrics_line(m)
        m["adhoc_calls"] = ah.calls
        if format == "line":
            return PlainTextResponse(m["line"] + "\n")
        return m

    # ---------------------------------------------------------------- the app
    d = Path(app_dir or os.environ.get("QS_APP_DIR") or ROOT / "app")
    if (d / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(d), html=True), name="app")
    else:
        @app.get("/")
        def root():
            return {"name": "Querschnitt", "version": VERSION, "endpoints": ["/affairs/{id}/topics", "/topics/{scheme}/{code}/affairs",
                    "/changes?since=", "/coverage", "/schemes", "POST /adhoc", "/health", "/metrics", "/docs"]}
    return app


def serve(host: str = "127.0.0.1", port: int = 8000):
    import uvicorn
    uvicorn.run(create_app(), host=host, port=port, log_level=os.environ.get("QS_LOG_LEVEL", "info"))
