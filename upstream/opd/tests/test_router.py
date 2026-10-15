"""Tests of ../api/router.py against PostgreSQL with migrations 0001-0003 applied and topic rows loaded (CI job `hop`,
after the Hop loads: .github/workflows/ci.yml). Every test runs in one transaction that is rolled back, so the loaded
rows are as before; feed switches, decisions and affair fields are set inside it. Expected values come from SQL on the
same tables (the view `topics_public` of migration 0003 for the current public rows).

    OPD_TEST_DSN=postgresql://opd:opd@localhost:5432/openparldata python -m pytest -q upstream/opd/tests/test_router.py

Skipped without OPD_TEST_DSN."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

DSN = os.environ.get("OPD_TEST_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="OPD_TEST_DSN not set (PostgreSQL with migrations 0001-0003 and loaded rows)")

psycopg = pytest.importorskip("psycopg")
pytest.importorskip("fastapi")
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from psycopg import sql  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
import models  # noqa: E402
import router  # noqa: E402

DEFAULT_STATUS = ("suggested", "confirmed")
SWITCH_ALL = """INSERT INTO topic_feed_bodies (body_id, body_key, scheme_id, scheme_key)
SELECT DISTINCT t.body_id, t.body_key, s.id, s.scheme_key FROM topics t JOIN topic_schemes s ON s.scheme_key = t.scheme_key AND s.active
WHERE t.body_id IS NOT NULL ON CONFLICT (body_id, scheme_key) DO NOTHING"""   # the statement in the header of 0003


@pytest.fixture
def db():
    conn = psycopg.connect(DSN)
    try:
        conn.execute("DELETE FROM topic_feed_bodies")   # start with every body switched off, as after 0003 up
        yield conn
    finally:
        conn.rollback()
        conn.close()


@pytest.fixture
def client(db):
    app = FastAPI()
    app.include_router(router.router)
    app.dependency_overrides[router.get_conn] = lambda: db
    with TestClient(app) as c:
        yield c


def one(db, q, *params):
    return db.execute(q, params).fetchone()[0]


def col(db, q, *params):
    return [r[0] for r in db.execute(q, params).fetchall()]


def get(client, url, model=models.TopicList, status=200):
    r = client.get(url)
    assert r.status_code == status, (url, r.status_code, r.text[:500])
    body = r.json()
    if status == 200 and model is not None:
        model.model_validate(body)   # the response shape of models.py
    return body


def walk(client, url, model=models.TopicList):
    """Every page of a list, following meta.next_page; -> (rows, metas)."""
    rows, metas = [], []
    while url:
        b = get(client, url, model)
        rows += b["data"]
        metas.append(b["meta"])
        nxt = b["meta"]["next_page"]
        url = (urlsplit(nxt).path + "?" + urlsplit(nxt).query) if nxt else None
    return rows, metas


def switch_all(db):
    db.execute(SWITCH_ALL)


def an_affair(db, cond="TRUE"):
    a = one(db, f"SELECT affair_id FROM topics t WHERE valid_to IS NULL AND {cond} ORDER BY affair_id LIMIT 1")
    assert a is not None, f"no loaded affair with {cond}"
    return a


# ------------------------------------------------------------------------------------------------------------ feed switch

def test_feed_empty_until_a_body_is_switched_on(db, client):
    assert one(db, "SELECT count(*) FROM topics") > 0, "no loaded rows"
    a = an_affair(db)
    assert get(client, "/v1/topics/?limit=5")["meta"]["total_records"] == 0
    assert get(client, f"/v1/affairs/{a}/topics?rank=1,2,3")["meta"]["total_records"] == 0
    assert get(client, "/v1/topics/group_by/body_key", models.TopicBodyCountList)["meta"]["total_records"] == 0
    t = one(db, "SELECT id FROM topics WHERE valid_to IS NULL AND NOT (scheme_key = 'aps' AND level = 2) LIMIT 1")
    get(client, f"/v1/topics/{t}", status=404)


def test_feed_switch_per_body_and_scheme(db, client):
    body, scheme = db.execute("""SELECT body_key, scheme_key FROM topics WHERE valid_to IS NULL AND rank = 1 AND level = 1
                                 GROUP BY 1, 2 ORDER BY count(*) DESC, 1, 2 LIMIT 1""").fetchone()
    db.execute("""INSERT INTO topic_feed_bodies (body_id, body_key, scheme_id, scheme_key)
                  SELECT b.id, b.body_key, s.id, s.scheme_key FROM bodies b, topic_schemes s
                  WHERE b.body_key = %s AND s.scheme_key = %s AND s.active""", (body, scheme))
    want = one(db, "SELECT count(*) FROM topics_public WHERE rank = 1 AND status = ANY(%s)", list(DEFAULT_STATUS))
    b = get(client, "/v1/topics/?limit=1000")
    assert b["meta"]["total_records"] == want > 0
    assert {(r["body_key"], r["scheme_key"]) for r in b["data"]} == {(body, scheme)}
    g = get(client, "/v1/topics/group_by/body_key", models.TopicBodyCountList)["data"]
    assert [(x["body_key"], x["count"]) for x in g] == [(body, want)]

    other = one(db, "SELECT affair_id FROM topics WHERE valid_to IS NULL AND (body_key, scheme_key) <> (%s, %s) LIMIT 1", body, scheme)
    if other is not None:
        n = one(db, "SELECT count(*) FROM topics WHERE affair_id = %s AND body_key = %s AND scheme_key = %s AND valid_to IS NULL "
                    "AND rank = 1 AND status = ANY(%s) AND NOT (scheme_key = 'aps' AND level = 2)",
                other, body, scheme, list(DEFAULT_STATUS))
        assert get(client, f"/v1/affairs/{other}/topics")["meta"]["total_records"] == n

    # machine rows off for that body: nothing left (no decisions loaded)
    db.execute("UPDATE topic_feed_bodies SET inferred_public = false")
    assert get(client, "/v1/topics/")["meta"]["total_records"] == 0


def test_without_migration_0003_every_body_is_shown(db, client):
    db.execute("DROP VIEW topics_public")
    db.execute("DROP TABLE topic_feed_bodies")
    want = one(db, "SELECT count(*) FROM topics WHERE valid_to IS NULL AND NOT (scheme_key = 'aps' AND level = 2)")
    b = get(client, "/v1/topics/?rank=1,2,3&level=1,2&status=suggested,confirmed,rejected&limit=1")
    assert b["meta"]["total_records"] == want
    bodies = one(db, "SELECT count(DISTINCT body_key) FROM topics WHERE valid_to IS NULL AND rank = 1 AND status = ANY(%s) "
                     "AND NOT (scheme_key = 'aps' AND level = 2)", list(DEFAULT_STATUS))
    assert get(client, "/v1/topics/group_by/body_key?limit=1000", models.TopicBodyCountList)["meta"]["total_records"] == bodies


def test_public_rows_equal_the_view(db, client):
    switch_all(db)
    want = one(db, "SELECT count(*) FROM topics_public")
    b = get(client, "/v1/topics/?rank=1,2,3&level=1,2&status=suggested,confirmed,rejected&limit=1")
    assert b["meta"]["total_records"] == want > 0


# -------------------------------------------------------------------------------------------------- APS subtopics held back

def test_aps_subtopics_held_back(db, client, monkeypatch):
    switch_all(db)
    a = an_affair(db, "scheme_key = 'aps' AND level = 2")
    sub = one(db, "SELECT id FROM topics WHERE affair_id = %s AND scheme_key = 'aps' AND level = 2 AND valid_to IS NULL LIMIT 1", a)
    chapter = one(db, "SELECT parent_code FROM topics WHERE id = %s", sub)

    rows = get(client, f"/v1/affairs/{a}/topics?level=1,2&rank=1,2,3&limit=1000")["data"]
    assert rows and all(not (r["scheme_key"] == "aps" and r["level"] == 2) for r in rows)
    assert len(rows) == one(db, "SELECT count(*) FROM topics WHERE affair_id = %s AND valid_to IS NULL AND status = ANY(%s) "
                                "AND NOT (scheme_key = 'aps' AND level = 2)", a, list(DEFAULT_STATUS))
    assert get(client, f"/v1/affairs/{a}/topics?scheme=aps&level=2&rank=1,2,3")["meta"]["total_records"] == 0
    assert get(client, "/v1/topics/?scheme=aps&level=2&rank=1,2,3")["meta"]["total_records"] == 0
    assert get(client, f"/v1/topics/?scheme=aps&code={chapter}&level=2")["meta"]["total_records"] == 0
    get(client, f"/v1/topics/{sub}", status=404)
    codes = get(client, "/v1/topics/group_by/code?scheme=aps&level=1,2&rank=1,2,3&limit=1000", models.TopicCodeCountList)["data"]
    assert codes and all(c["level"] == 1 for c in codes)

    aps = one(db, "SELECT id FROM topic_schemes WHERE scheme_key = 'aps' AND active")
    c = get(client, f"/v1/topic_schemes/{aps}/codes?limit=1000", models.TopicCodeList)
    assert c["meta"]["total_records"] == one(db, "SELECT count(*) FROM topic_codes WHERE scheme_id = %s AND level = 1", aps) > 0
    assert all(x["level"] == 1 for x in c["data"])
    assert get(client, f"/v1/topic_schemes/{aps}/codes?level=2", models.TopicCodeList)["meta"]["total_records"] == 0

    # the one switch for when APS agrees
    monkeypatch.setattr(router, "APS_SUBTOPICS_PUBLIC", True)
    n2 = one(db, "SELECT count(*) FROM topics WHERE affair_id = %s AND scheme_key = 'aps' AND level = 2 AND valid_to IS NULL", a)
    assert get(client, f"/v1/affairs/{a}/topics?scheme=aps&level=2&rank=1,2,3")["meta"]["total_records"] == n2 > 0
    under = get(client, f"/v1/topics/?scheme=aps&code={chapter}&level=2&rank=1,2,3&limit=1000")["data"]
    assert under and all(r["parent_code"] == chapter and r["level"] == 2 for r in under)
    assert get(client, f"/v1/topics/{sub}", models.Topic)["level"] == 2
    assert get(client, f"/v1/topic_schemes/{aps}/codes?limit=1", models.TopicCodeList)["meta"]["total_records"] == \
        one(db, "SELECT count(*) FROM topic_codes WHERE scheme_id = %s", aps)


# ------------------------------------------------------------------------------------------------- provenance and status

DECIDE = """INSERT INTO topics (affair_id, body_id, body_key, scheme_id, scheme_key, level, code, parent_code, rank,
                    label_de, label_fr, label_it, label_rm, status, provenance, valid_from,
                    confirmed_by, confirmed_by_body_id, confirmed_at)
SELECT affair_id, body_id, body_key, scheme_id, scheme_key, level, code, parent_code, rank,
       label_de, label_fr, label_it, label_rm, %(status)s, 'confirmed', valid_from + interval '1 hour',
       'router test', body_id, valid_from + interval '1 hour'
FROM topics WHERE id = %(id)s RETURNING id"""
CLOSE = "UPDATE topics SET valid_to = valid_from + interval '1 hour', updated_at = now() AT TIME ZONE 'utc' WHERE id = %(id)s"


# the only row of its key, no older versions: the history of the affair's chapter is then exactly what the test adds
ALONE = """NOT EXISTS (SELECT 1 FROM topics o WHERE (o.affair_id, o.scheme_key, o.level, o.rank) = (t.affair_id, t.scheme_key, t.level, t.rank)
           AND o.id <> t.id)"""


def _decide(db, machine_id, status):
    """MERGE_REQUEST.md, "Who owns a row" 2: add the decision row, close the machine row it decides."""
    d = db.execute(DECIDE, {"status": status, "id": machine_id}).fetchone()[0]
    db.execute(CLOSE, {"id": machine_id})
    return d


def test_rejection_is_its_own_row_and_hides_the_suggestion(db, client):
    switch_all(db)
    m, a, code = db.execute(f"""SELECT id, affair_id, code FROM topics t WHERE scheme_key = 'aps' AND level = 1 AND rank = 1
                                AND valid_to IS NULL AND provenance = 'inferred' AND model IS NOT NULL AND {ALONE}
                                ORDER BY id LIMIT 1""").fetchone()
    d = _decide(db, m, "rejected")
    base = f"/v1/affairs/{a}/topics?scheme=aps&level=1"

    assert get(client, base)["data"] == []           # default status: suggested, confirmed; the machine row is closed
    rej = get(client, base + "&status=rejected")["data"]
    assert [r["id"] for r in rej] == [d]
    r = rej[0]
    assert (r["provenance"], r["status"], r["code"], r["confirmed_by"], r["valid_to"]) == ("confirmed", "rejected", code, "router test", None)
    assert r["confirmed_at"] is not None and r["generated_by"] is None and r["p"] is None

    hist = {r["id"]: r for r in get(client, base + "&history=true&status=suggested,confirmed,rejected")["data"]}
    assert set(hist) == {m, d}
    mr = hist[m]
    assert (mr["provenance"], mr["status"], mr["confirmed_by"], mr["confirmed_at"]) == ("inferred", "suggested", None, None)
    assert mr["valid_to"] is not None and mr["generated_by"]["model"] and mr["generated_by"]["model_build"]
    only = get(client, base + "&history=true&status=suggested,confirmed,rejected&provenance=inferred")["data"]
    assert [x["id"] for x in only] == [m]
    assert get(client, f"/v1/topics/{m}", models.Topic)["valid_to"] is not None   # closed rows stay readable by id
    assert get(client, f"/v1/topics/?affair_id={a}&scheme=aps&current=false&status=rejected")["meta"]["total_records"] == 1

    # the switches act on each provenance separately
    db.execute("UPDATE topic_feed_bodies SET decisions_public = false")
    assert get(client, base + "&status=rejected")["data"] == []
    get(client, f"/v1/topics/{d}", status=404)
    db.execute("UPDATE topic_feed_bodies SET decisions_public = true, inferred_public = false")
    assert [x["id"] for x in get(client, base + "&history=true&status=suggested,confirmed,rejected")["data"]] == [d]


def test_confirmation_replaces_the_suggestion(db, client):
    switch_all(db)
    m, a = db.execute(f"""SELECT id, affair_id FROM topics t WHERE scheme_key = 'aps' AND level = 1 AND rank = 1 AND valid_to IS NULL
                          AND provenance = 'inferred' AND {ALONE} ORDER BY id DESC LIMIT 1""").fetchone()
    d = _decide(db, m, "confirmed")
    rows = get(client, f"/v1/affairs/{a}/topics?scheme=aps&level=1")["data"]
    assert [(r["id"], r["provenance"], r["status"]) for r in rows] == [(d, "confirmed", "confirmed")]
    assert get(client, f"/v1/affairs/{a}/topics?scheme=aps&level=1&provenance=inferred")["data"] == []


def test_rows_never_mix_provenance(db, client):
    switch_all(db)
    m = one(db, "SELECT id FROM topics WHERE rank = 1 AND valid_to IS NULL AND provenance = 'inferred' ORDER BY id LIMIT 1")
    _decide(db, m, "rejected")
    rows = get(client, "/v1/topics/?current=false&status=suggested,confirmed,rejected&sort_by=-updated_at&limit=1000")["data"]
    assert any(r["provenance"] == "confirmed" for r in rows) and any(r["provenance"] == "inferred" for r in rows)
    for r in rows:
        if r["provenance"] == "inferred":
            assert r["status"] == "suggested" and r["confirmed_by"] is None and r["confirmed_at"] is None, r
        else:
            assert r["status"] in ("confirmed", "rejected") and r["confirmed_by"] and r["confirmed_at"], r


# ------------------------------------------------------------------------------------------------------------- pagination

def test_pagination_walks_every_row_once(db, client):
    switch_all(db)
    body = one(db, """SELECT body_key FROM topics WHERE valid_to IS NULL AND rank = 1 AND NOT (scheme_key = 'aps' AND level = 2)
                      GROUP BY 1 HAVING count(*) BETWEEN 15 AND 400 ORDER BY count(*) DESC, 1 LIMIT 1""")
    assert body, "no body with 15-400 current rank-1 rows"
    want = col(db, """SELECT id FROM topics_public WHERE body_key = %s AND rank = 1 AND status = ANY(%s)
                      ORDER BY valid_from DESC, id""", body, list(DEFAULT_STATUS))
    rows, metas = walk(client, f"/v1/topics/?body={body}&limit=7")
    ids = [r["id"] for r in rows]
    assert ids == want                                   # every row once, in the default order (-valid_from, then id)
    n, pages = len(want), -(-len(want) // 7)
    assert len(metas) == pages and all(m["total_records"] == n and m["total_pages"] == pages for m in metas)
    assert [m["current_page"] for m in metas] == list(range(1, pages + 1))
    assert [m["offset"] for m in metas] == [7 * i for i in range(pages)]
    assert metas[0]["prev_page"] is None and metas[0]["has_more"]
    assert parse_qs(urlsplit(metas[1]["prev_page"]).query)["offset"] == ["0"]
    assert not metas[-1]["has_more"] and metas[-1]["next_page"] is None and metas[-1]["last_page"] == metas[-1]["self"]
    assert parse_qs(urlsplit(metas[0]["next_page"]).query) == {"body": [body], "offset": ["7"], "limit": ["7"]}

    past = get(client, f"/v1/topics/?body={body}&offset={n + 10}&limit=7")
    assert past["data"] == [] and not past["meta"]["has_more"] and past["meta"]["total_records"] == n
    for bad in ("limit=0", f"limit={router.LIMIT_MAX + 1}", "offset=-1", "sort_by=nope", "status=maybe", "level=x", "lang=en"):
        get(client, f"/v1/topics/?{bad}", status=422)

    ps = [r["p"] for r in get(client, f"/v1/topics/?body={body}&sort_by=-p&limit=1000")["data"]]
    nn = [p for p in ps if p is not None]
    assert nn == sorted(nn, reverse=True) and ps[:len(nn)] == nn   # nulls last


def test_group_by_code_counts_add_up(db, client):
    switch_all(db)
    body = one(db, "SELECT body_key FROM topics WHERE valid_to IS NULL AND scheme_key = 'aps' AND rank = 1 GROUP BY 1 "
                   "ORDER BY count(*) DESC LIMIT 1")
    q = f"scheme=aps&body_key={body}"
    total = get(client, f"/v1/topics/?{q}&limit=1")["meta"]["total_records"]
    groups, _ = walk(client, f"/v1/topics/group_by/code?{q}&limit=5", models.TopicCodeCountList)
    assert sum(g["count"] for g in groups) == total > 0
    assert [g["count"] for g in groups] == sorted((g["count"] for g in groups), reverse=True)
    for g in groups[:3]:
        assert get(client, f"/v1/topics/?{q}&code={g['code']}&limit=1")["meta"]["total_records"] == g["count"]
        assert g["affair_count"] <= g["count"] and isinstance(g["label"], dict) and g["label"]["de"]


# ------------------------------------------------------------------------------------------------------ shapes and filters

def test_shapes_labels_and_values(db, client):
    switch_all(db)
    t = one(db, "SELECT id FROM topics_public WHERE p IS NOT NULL AND label_fr IS NOT NULL AND evidence_field IS NOT NULL "
                "AND rank = 1 ORDER BY id LIMIT 1")
    row = db.execute("SELECT p::text, p_raw::text, label_de, label_fr, evidence_quote, evidence_field, evidence_char_start, model "
                     "FROM topics WHERE id = %s", (t,)).fetchone()
    nested = get(client, f"/v1/topics/{t}", models.Topic)
    assert nested["label"] == {"de": row[2], "fr": row[3], "it": nested["label"]["it"], "rm": None}
    assert nested["p"] == float(row[0]) and nested["p_raw"] == float(row[1])
    assert nested["evidence"]["quote"] == row[4] and nested["evidence"]["field"] == row[5]
    assert nested["evidence"]["char_start"] == row[6] and nested["generated_by"]["model"] == row[7]
    assert get(client, f"/v1/topics/{t}?lang=fr&lang_format=flat", models.Topic)["label"] == row[3]
    assert get(client, f"/v1/topics/{t}?lang=rm&lang_format=flat&lang_fallback=fr,de", models.Topic)["label"] == row[3]

    doc = one(db, "SELECT id FROM topics_public WHERE evidence_field = 'doc' LIMIT 1")
    if doc:
        ev = get(client, f"/v1/topics/{doc}", models.Topic)["evidence"]
        assert ev["doc_id"] == one(db, "SELECT evidence_doc_id FROM topics WHERE id = %s", doc) and ev["text_id"] is None

    for u in ("/v1/topics/?limit=200&rank=1,2,3", "/v1/topics/?limit=50&lang=it&lang_format=flat"):
        get(client, u)
    get(client, "/v1/topics/999999999", status=404)
    get(client, f"/v1/affairs/{one(db, 'SELECT min(id) - 1 FROM affairs')}/topics", status=404)

    s = get(client, "/v1/topic_schemes/?limit=100", models.TopicSchemeList)
    assert s["meta"]["total_records"] == one(db, "SELECT count(*) FROM topic_schemes") == len(s["data"])
    dig = next(x for x in s["data"] if x["scheme_key"] == "adhoc/digitalisierung")
    assert dig["question"]["de"] and dig["type"] == "adhoc" and dig["licence"] == "CC-BY-4.0"
    assert get(client, f"/v1/topic_schemes/{dig['id']}?lang=fr&lang_format=flat", models.TopicScheme)["name"] == \
        one(db, "SELECT name_fr FROM topic_schemes WHERE id = %s", dig["id"])
    assert [x["scheme_key"] for x in get(client, "/v1/topic_schemes/?type=body", models.TopicSchemeList)["data"]] == \
        col(db, "SELECT scheme_key FROM topic_schemes WHERE type = 'body' ORDER BY id")
    get(client, "/v1/topic_schemes/999999", status=404)
    get(client, "/v1/topic_schemes/999999/codes", status=404)


def test_filters(db, client):
    switch_all(db)

    def total(q):
        return get(client, f"/v1/topics/?{q}&limit=1")["meta"]["total_records"]

    def want(cond, *params):
        return one(db, f"SELECT count(*) FROM topics_public t WHERE rank = 1 AND status = ANY(%s) AND {cond}",
                   list(DEFAULT_STATUS), *params)

    code = one(db, "SELECT code FROM topics_public WHERE scheme_key = 'aps' AND rank = 1 GROUP BY 1 ORDER BY count(*) DESC LIMIT 1")
    short = code.split(":", 1)[1]
    assert total(f"scheme=aps&code={short}") == total(f"code={code}") == want("code = %s", code) > 0
    body = one(db, "SELECT body_key FROM topics_public GROUP BY 1 ORDER BY count(*) DESC LIMIT 1")
    assert total(f"body={body}") == total(f"body_key={body}") == want("body_key = %s", body) > 0
    assert total("p_min=0.8") == want("p >= %s", 0.8)
    assert all(r["p"] >= 0.8 for r in get(client, "/v1/topics/?p_min=0.8&limit=500")["data"])
    assert total("lane=please_check") == want("lane = 'please_check'")
    assert total("provenance=inferred") == want("provenance = 'inferred'")
    assert total("rank=2") == one(db, "SELECT count(*) FROM topics_public WHERE rank = 2 AND status = ANY(%s)", list(DEFAULT_STATUS))
    a, b = col(db, "SELECT DISTINCT affair_id FROM topics_public WHERE rank = 1 ORDER BY 1 LIMIT 2")
    assert {r["affair_id"] for r in get(client, f"/v1/topics/?affair_id={a},{b}&limit=100")["data"]} == {a, b}

    t = one(db, "SELECT id FROM topics_public WHERE rank = 1 ORDER BY id LIMIT 1")
    db.execute("UPDATE topics SET updated_at = '2030-01-01' WHERE id = %s", (t,))
    for since in ("2029-12-31T00:00:00", "2029-12-31T01:00:00%2B01:00"):
        assert [r["id"] for r in get(client, f"/v1/topics/?since={since}")["data"]] == [t]

    aff = one(db, "SELECT affair_id FROM topics_public WHERE rank = 1 ORDER BY affair_id DESC LIMIT 1")
    db.execute("UPDATE affairs SET language = 'fr', begin_date = '2026-03-04 10:00' WHERE id = %s", (aff,))
    n = want("affair_id = %s", aff)
    assert total("affair_lang=fr") == n and total("affair_lang=fr,it") == n
    assert total("date_from=2026-03-04&date_to=2026-03-04") == n
    assert total("date_from=2026-03-05") == 0 and total("date_to=2026-03-03") == 0

    m, ma = db.execute("SELECT id, affair_id FROM topics_public WHERE rank = 1 AND provenance = 'inferred' ORDER BY id LIMIT 1").fetchone()
    db.execute("UPDATE topics SET valid_to = valid_from + interval '1 minute' WHERE id = %s", (m,))
    assert m not in [r["id"] for r in get(client, f"/v1/topics/?affair_id={ma}")["data"]]
    assert m in [r["id"] for r in get(client, f"/v1/topics/?current=false&affair_id={ma}")["data"]]


# ---------------------------------------------------------------------------------------- helpers for OPD's affairs list

def test_expand_topics_and_topic_filter(db):
    switch_all(db)
    ids = col(db, """SELECT affair_id FROM topics_public WHERE rank = 1 GROUP BY 1 ORDER BY count(DISTINCT scheme_key) DESC,
                     affair_id LIMIT 3""")
    empty = one(db, "SELECT max(id) + 1 FROM affairs")
    db.execute("INSERT INTO affairs (id, body_id, body_key) SELECT %s, id, body_key FROM bodies ORDER BY id LIMIT 1", (empty,))
    got = router.topics_for_affairs(db, ids + [empty])
    assert set(got) == set(ids + [empty]) and got[empty] == []
    for a in ids:
        n = one(db, "SELECT count(*) FROM topics_public WHERE affair_id = %s AND rank = 1 AND status = ANY(%s)", a, list(DEFAULT_STATUS))
        assert len(got[a]) == n > 0
        for r in got[a]:
            models.Topic.model_validate(r)
            assert r["rank"] == 1 and r["affair_id"] == a
    first = router.topics_for_affairs(db, ids, topics_limit=1)
    second = router.topics_for_affairs(db, ids, topics_limit=1, topics_offset=1)
    assert all(len(first[a]) == 1 and first[a][0] == got[a][0] for a in ids)
    assert all(second[a] == got[a][1:2] for a in ids)
    flat = router.topics_for_affairs(db, ids[:1], lang="fr", lang_format="flat")
    assert all(isinstance(r["label"], (str, type(None))) for r in flat[ids[0]])

    code = one(db, "SELECT code FROM topics_public WHERE rank = 1 AND scheme_key = 'aps' GROUP BY 1 ORDER BY count(*) DESC LIMIT 1")
    cond, params = router.affairs_topic_filter(db, code, affairs_alias="a")
    got_ids = [r[0] for r in db.execute(sql.SQL("SELECT a.id FROM affairs a WHERE {} ORDER BY a.id").format(cond), params)]
    assert got_ids == col(db, "SELECT DISTINCT affair_id FROM topics_public WHERE rank = 1 AND code = %s AND status = ANY(%s) "
                              "ORDER BY 1", code, list(DEFAULT_STATUS)) and got_ids
