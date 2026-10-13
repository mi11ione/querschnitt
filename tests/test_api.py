"""API endpoints (docs/CONTRACT.md §2) on the sample store."""
AID = 341382


def test_health_metrics(api):
    h = api.get("/health").json()
    assert h["ok"] and h["store"] == "sqlite" and h["rows"] == 504
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
