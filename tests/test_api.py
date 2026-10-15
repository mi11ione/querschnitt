"""API endpoints (docs/CONTRACT.md §2) on the sample store."""
AID = 341382


def test_health_metrics(api):
    h = api.get("/health").json()
    assert h["ok"] and h["store"] in ("sqlite", "postgres") and h["rows"] == 504
    m = api.get("/metrics").json()
    for k in ("affairs", "rows", "pending", "last_run", "line"):
        assert k in m
    assert "pending" in api.get("/metrics?format=line").text


def test_affair_topics(api):
    r = api.get(f"/affairs/{AID}/topics").json()
    assert r["affair"]["id"] == AID and r["affair"]["title"]
    t = r["topics"]
    assert {x["scheme"] for x in t} == {"aps", "adhoc/digitalisierung"}
    ch = next(x for x in t if x["scheme"] == "aps" and x["level"] == 1 and x["rank"] == 1)
    assert ch["label"]["de"] and ch["label"]["fr"] and isinstance(ch["evidence"], dict)
    assert api.get("/affairs/1/topics").status_code == 404


def test_topic_affairs_and_filters(api):
    r = api.get("/topics/adhoc/digitalisierung/yes/affairs").json()
    assert r["code"] == "adhoc/digitalisierung:yes" and r["total"] == len(r["rows"]) > 0
    assert all(x["affair"]["title"] for x in r["rows"])
    dates = [x["affair"]["date"] for x in r["rows"]]
    assert dates == sorted(dates, reverse=True)
    full = api.get("/topics/adhoc/digitalisierung/adhoc/digitalisierung:yes/affairs").json()
    assert full["total"] == r["total"]
    fr = api.get("/topics/adhoc/digitalisierung/yes/affairs?lang=fr").json()
    assert all(x["affair"]["lang"] == "fr" for x in fr["rows"])
    one = api.get("/topics/adhoc/digitalisierung/no/affairs?limit=1&offset=1").json()
    assert len(one["rows"]) == 1 and one["total"] > 1
    code = next(t["code"] for t in api.get(f"/affairs/{AID}/topics").json()["topics"] if t["scheme"] == "aps")
    short = code.split(":", 1)[1]
    a = api.get(f"/topics/aps/{short}/affairs?level=federal").json()
    assert a["code"] == code and all(x["affair"]["level"] == "federal" for x in a["rows"])
    assert api.get("/topics/nosuch/x/affairs").status_code == 404
    assert api.get("/topics/aps/1.1.1./affairs?from=2026-10-01&to=2026-10-31").status_code == 200


def test_confirm_reject(api):
    r = api.post(f"/affairs/{AID}/topics/adhoc/digitalisierung:yes/confirm", json={"by": "dvs", "scheme": "adhoc/digitalisierung"})
    assert r.status_code == 200 and r.json()["status"] == "confirmed" and r.json()["confirmed_by"] == "dvs"
    r = api.post(f"/affairs/{AID}/topics/aps:1.7.2./reject", json={"by": "dvs"})
    assert r.status_code == 200 and r.json()["status"] == "rejected" and r.json()["scheme"] == "aps"
    assert api.post(f"/affairs/{AID}/topics/aps:9.9.9./confirm", json={"by": "x"}).status_code == 422
    assert api.post(f"/affairs/{AID}/topics/aps:1.7.2./confirm", json={}).status_code == 422
    t = api.get(f"/affairs/{AID}/topics?history=true").json()["topics"]
    assert any(x["provenance"] == "confirmed" for x in t) and any(x["valid_to"] for x in t)
    ch = api.get("/changes?since=2000-01-01").json()
    assert ch["n"] >= 2
    assert api.get("/changes?since=not-a-date").status_code == 422


def test_coverage_schemes_root(api):
    c = api.get("/coverage").json()
    assert c["bodies"] and {"body_key", "affairs", "scored", "scored_share", "title_only_share", "covered_from"} <= set(c["bodies"][0])
    s = api.get("/schemes").json()
    assert len(s["aps"]["chapters"]) == 25 and "adhoc/digitalisierung" in s["schemes"]
    from querschnitt.scheme import HERE
    assert {f.stem for f in HERE.glob("*.yaml")} <= set(s["schemes"]) and "curia28" not in s["schemes"]   # the scheme files
    assert api.get("/").json()["name"] == "Querschnitt"


def test_cors_localhost(api):
    r = api.options("/health", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
    r = api.options("/health", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in r.headers


def test_static_app(store, tmp_path):
    from fastapi.testclient import TestClient
    from querschnitt.api import create_app
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "index.html").write_text("<!doctype html><title>Querschnitt</title>")
    with TestClient(create_app(store, app_dir=tmp_path / "app")) as c:
        assert "Querschnitt" in c.get("/").text
        assert c.get("/health").json()["ok"]


def test_write_token(api, store, tmp_path, monkeypatch):
    """With QS_WRITE_TOKEN set, every endpoint that writes or spends model calls needs the bearer token (401 otherwise);
    reads stay open. Without it (every other test here), writes are open as before."""
    import re
    import time
    from fastapi.routing import APIRoute
    from fastapi.testclient import TestClient
    from querschnitt.api import create_app
    monkeypatch.setenv("QS_WRITE_TOKEN", "s3cret")
    app = create_app(store, api.ah, app_dir=tmp_path / "noapp")
    fill = {"aid": str(AID), "rest:path": "aps:1.7.2./confirm", "slug": "x"}
    writes = [(m, re.sub(r"\{([^}]+)\}", lambda g: fill[g.group(1)], r.path)) for r in app.routes if isinstance(r, APIRoute)
              for m in r.methods - {"GET", "HEAD"}]
    assert {p for _, p in writes} >= {f"/affairs/{AID}/topics/aps:1.7.2./confirm", "/adhoc", "/adhoc/x/stop", "/adhoc/x/continue",
                                      "/adhoc/x/terms", "/adhoc/x/save"}
    ok = {"Authorization": "Bearer s3cret"}
    with TestClient(app) as c:
        for m, p in writes:
            for h in ({}, {"Authorization": "Bearer wrong"}, {"Authorization": "s3cret"}, {"Authorization": "Basic s3cret"}):
                r = c.request(m, p, json={}, headers=h)
                assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer", (m, p, h)
        for p in ("/health", f"/affairs/{AID}/topics", "/changes", "/coverage", "/schemes", "/metrics"):
            assert c.get(p).status_code == 200
        r = c.post(f"/affairs/{AID}/topics/aps:1.7.2./reject", json={"by": "dvs"}, headers=ok)
        assert r.status_code == 200 and r.json()["status"] == "rejected"
        assert c.post(f"/affairs/{AID}/topics/aps:1.7.2./undo", json={"by": "dvs"}, headers=ok).status_code == 200
        r = c.post("/adhoc", json={"sentence": "Wolf", "lang": "de", "limit": 1}, headers=ok)
        assert r.status_code == 200
        t = time.time()
        while not c.get(f"/adhoc/{r.json()['slug']}").json()["done"] and time.time() - t < 20:
            time.sleep(0.05)


def test_adhoc_daily_cap(api):
    """QS_ADHOC_DAILY_USD: today's list-price spend in the ad-hoc ledger caps new runs and `continue` (429) and stops a
    running one (`stop: daily_cap`); earlier days do not count; 0 turns it off."""
    import json
    import pathlib
    import time

    def wait(slug):
        t = time.time()
        while time.time() - t < 20:
            st = api.get(f"/adhoc/{slug}").json()
            if st["done"]:
                return st
            time.sleep(0.05)
        raise AssertionError("ad-hoc run did not finish")

    ah = api.ah
    led = pathlib.Path(ah.client.ledger)
    led.write_text(json.dumps(dict(ts=time.time() - 2 * 86400, tag="adhoc", usd=5.0)) + "\n")      # two days ago
    ah.daily_usd = 1.0
    assert ah.spent_today() == 0
    r = api.post("/adhoc", json={"sentence": "Wolf", "lang": "de", "limit": 1})
    assert r.status_code == 200 and wait(r.json()["slug"])["stop"] == "done"
    today = ah.spent_today()
    assert today > 0                                     # the fake endpoint reports usage; the ledger prices it
    ah.daily_usd = today + 1e-9                          # room for nothing beyond the topic's own generation request
    r = api.post("/adhoc", json={"sentence": "Digitale Verwaltung", "lang": "de", "period": "2026-09-01..2026-10-31"})
    assert r.status_code == 200
    st = wait(r.json()["slug"])
    assert st["stop"] == "daily_cap" and st["summary"]["read"] == 0 and st["summary"]["unread"] > 0 and st["error"] is None
    c = api.post(f"/adhoc/{r.json()['slug']}/continue")
    assert c.status_code == 429 and "QS_ADHOC_DAILY_USD" in c.json()["detail"]
    n = len(ah.jobs)
    r = api.post("/adhoc", json={"sentence": "Wolf", "lang": "de", "limit": 1})
    assert r.status_code == 429 and "QS_ADHOC_DAILY_USD" in r.json()["detail"] and len(ah.jobs) == n    # refused before any call
    ah.daily_usd = None                                  # QS_ADHOC_DAILY_USD=0
    r = api.post("/adhoc", json={"sentence": "Wolf", "lang": "de", "limit": 1})
    assert r.status_code == 200
    wait(r.json()["slug"])


def test_confirmations_become_examples(api, store, tmp_path, monkeypatch):
    """The nightly's `querschnitt examples --all`: a Pult decision on an ad-hoc topic lands in that topic's file as an
    example (the S26 loop), and a topic without decisions is left alone."""
    import shutil, yaml
    from querschnitt import cli
    from querschnitt.store import ROOT
    d = tmp_path / "adhoc_yaml"; d.mkdir(exist_ok=True)
    shutil.copy(ROOT / "src/querschnitt/schemes/adhoc/digitalisierung.yaml", d / "digitalisierung.yaml")
    import os
    monkeypatch.setenv("QS_DB", store.path)
    if os.environ.get("QS_TEST_ALL_PG") and os.environ.get("QS_TEST_PG_DSN"):
        monkeypatch.setenv("QS_PG_DSN", os.environ["QS_TEST_PG_DSN"])
    assert api.post(f"/affairs/{AID}/topics/adhoc/digitalisierung:yes/confirm",
                    json={"by": "dvs", "scheme": "adhoc/digitalisierung"}).status_code == 200
    cli.examples_cmd(["--all"])
    ex = yaml.safe_load((d / "digitalisierung.yaml").read_text())["examples"]
    assert [e["affair_id"] for e in ex if e["affair_id"] == AID] == [AID] and next(e for e in ex if e["affair_id"] == AID)["match"] is True
