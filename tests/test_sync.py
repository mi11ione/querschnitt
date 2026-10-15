"""The sync contract an OPD job or POLITmonitor relies on: `/changes` as a feed with a stable cursor (every change exactly
once, closures included, under any page size), idempotent decisions, a server-side undo with who/when in the history,
and rows in the docs/CONTRACT.md §1 shape."""
import pytest

from conftest import FIX
from querschnitt.store import read_rows

AID = 341382
CONTRACT = ["affair_id", "body_key", "scheme", "level", "code", "rank", "p", "p_raw", "lane", "status", "provenance", "evidence",
            "model", "build", "cutoffs_id", "prompt_id", "input_hash", "valid_from", "valid_to", "confirmed_by", "confirmed_at", "version"]


def drain(api, url):
    """Follow `next` links to the end; returns (rows, last page)."""
    out, page = [], None
    while url:
        page = api.get(url).json()
        out += page["rows"]
        url = page["next"]
    return out, page


def test_feed_pages_every_row_once(api):
    rows, last = drain(api, "/changes?limit=37")
    assert len(rows) == 504 and len({r["row_id"] for r in rows}) == 504
    first = api.get("/changes?limit=37").json()
    assert first["total"] == 504 and first["next"].startswith("/changes?") and "after=" in first["next"]
    seqs = [r["seq"] for r in rows]
    assert seqs == sorted(seqs) and len(set(seqs)) == 504
    # all 504 rows share one valid_from: paging by `since` alone would lose them, the cursor does not
    assert len({r["valid_from"] for r in rows}) == 1
    assert last["next"] is None and last["cursor"] == seqs[-1]


def test_feed_sees_decisions_and_closures(api):
    _, last = drain(api, "/changes?limit=500")
    cur = last["cursor"]
    api.post(f"/affairs/{AID}/topics/adhoc/digitalisierung:no/confirm", json={"by": "dvs", "scheme": "adhoc/digitalisierung"})
    new, _ = drain(api, f"/changes?after={cur}")
    kinds = {(r["provenance"], r["valid_to"] is None) for r in new}
    assert ("confirmed", True) in kinds            # the decision
    assert ("inferred", False) in kinds            # the machine row it closed, re-sent with its valid_to
    assert all(r["seq"] > cur for r in new)
    # nothing new: an empty page with the same cursor
    p = api.get(f"/changes?after={max(r['seq'] for r in new)}").json()
    assert p["rows"] == [] and p["total"] == 0 and p["next"] is None


def test_feed_filters(api):
    api.post(f"/affairs/{AID}/topics/adhoc/digitalisierung:no/confirm", json={"by": "dvs", "scheme": "adhoc/digitalisierung"})
    be, _ = drain(api, "/changes?body=BE&limit=50")
    assert be and all(r["body_key"] == "BE" for r in be)
    dec = api.get("/changes?kind=decisions").json()
    assert dec["total"] == 1 and dec["rows"][0]["provenance"] == "confirmed"
    assert api.get("/decisions").json()["total"] == 1
    m = api.get("/changes?kind=machine&scheme=adhoc/digitalisierung&limit=1000").json()
    assert all(r["provenance"] == "inferred" and r["scheme"] == "adhoc/digitalisierung" for r in m["rows"])
    assert api.get("/changes?limit=5001").status_code == 422
    assert api.get("/changes?kind=nonsense").status_code == 422
    assert api.get("/changes?since=2999-01-01").json()["total"] == 0
    s = api.get("/changes?since=2000-01-01&limit=10").json()
    assert s["total"] == 505 and "since=2000-01-01" in s["next"]


def test_decisions_are_idempotent(api, store):
    url = f"/affairs/{AID}/topics/adhoc/digitalisierung:yes/confirm"
    body = {"by": "S. Meier (polsan)", "scheme": "adhoc/digitalisierung"}
    first = api.post(url, json=body).json()
    for _ in range(9):
        again = api.post(url, json=body).json()
        assert again["row_id"] == first["row_id"] and again["unchanged"] is True
    n = store.one("SELECT COUNT(*) AS n FROM qs_topics WHERE provenance = 'confirmed'")["n"]
    assert n == 1
    other = api.post(url, json={"by": "DVS Redaktion", "scheme": "adhoc/digitalisierung"}).json()
    assert other["row_id"] != first["row_id"] and not other.get("unchanged")
    rj = api.post(f"/affairs/{AID}/topics/adhoc/digitalisierung:yes/reject", json=body).json()
    assert rj["status"] == "rejected" and not rj.get("unchanged")


def test_undo_restores_the_machine_rows(api):
    before = {(r["scheme"], r["level"], r["rank"]): r for r in api.get(f"/affairs/{AID}/topics").json()["topics"]}
    ch = before[("aps", 1, 2)]["code"]
    api.post(f"/affairs/{AID}/topics/{ch}/confirm", json={"by": "editor", "scheme": "aps"})
    mid = api.get(f"/affairs/{AID}/topics?scheme=aps").json()["topics"]
    assert [r["provenance"] for r in mid if r["level"] == 1] == ["confirmed"]
    r = api.post(f"/affairs/{AID}/topics/{ch}/undo", json={"by": "editor 2", "scheme": "aps"})
    assert r.status_code == 200
    u = r.json()
    assert u["undone"]["code"] == ch and u["undone"]["closed_by"] == "editor 2" and u["undone"]["valid_to"]
    after = {(x["scheme"], x["level"], x["rank"]): x for x in api.get(f"/affairs/{AID}/topics").json()["topics"]}
    assert set(after) == set(before)
    for k, x in after.items():
        assert x["provenance"] == "inferred" and x["code"] == before[k]["code"] and x["p_raw"] == before[k]["p_raw"]
    hist = api.get(f"/affairs/{AID}/topics?scheme=aps&history=true").json()["topics"]
    dec = [x for x in hist if x["provenance"] == "confirmed"]
    assert len(dec) == 1 and dec[0]["valid_to"] and dec[0]["closed_by"] == "editor 2"
    assert api.post(f"/affairs/{AID}/topics/{ch}/undo", json={"by": "editor 2", "scheme": "aps"}).status_code == 409
    assert api.post(f"/affairs/{AID}/topics/{ch}/undo", json={"scheme": "aps"}).status_code == 422
    # an identical nightly reload neither duplicates the restored rows nor closes them
    from querschnitt.store import read_rows as rr
    st = api.app.state.store.load_topics([x for x in rr(FIX / "topics_sample.jsonl") if x["affair_id"] == AID])
    assert st["inserted"] == 0 and st["closed"] == 0


def test_undo_of_a_reject(api):
    t = {x["scheme"]: x for x in api.get(f"/affairs/{AID}/topics").json()["topics"]}
    code = t["adhoc/digitalisierung"]["code"]
    api.post(f"/affairs/{AID}/topics/{code}/reject", json={"by": "x", "scheme": "adhoc/digitalisierung"})
    u = api.post(f"/affairs/{AID}/topics/{code}/undo", json={"by": "x", "scheme": "adhoc/digitalisierung"}).json()
    assert [r["code"] for r in u["restored"]] == [code]
    cur = [x for x in api.get(f"/affairs/{AID}/topics?scheme=adhoc/digitalisierung").json()["topics"]]
    assert [(x["provenance"], x["code"]) for x in cur] == [("inferred", code)]


def test_row_shape_is_the_contract(api, store):
    rows = [dict(r, evidence=dict(field="title", start=0, end=12, quote="Postulat Nan")) for r in read_rows(FIX / "topics_sample.jsonl")
            if r["affair_id"] == AID and r["scheme"] == "aps" and r["level"] == 1 and r["rank"] == 1]
    store.load_topics(rows)
    t = api.get(f"/affairs/{AID}/topics?scheme=aps").json()["topics"]
    r = next(x for x in t if x["level"] == 1 and x["rank"] == 1)
    assert r["evidence"] == {"source": "title", "field": "title", "char_start": 0, "char_end": 12, "quote": "Postulat Nan"}
    for k in CONTRACT:
        assert k in r, k
    extra = set(r) - set(CONTRACT)
    assert extra <= {"row_id", "seq", "closed_by", "label"}, extra
    spec = api.get("/openapi.json").json()
    ok = spec["paths"]["/changes"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert ok.get("$ref", "").endswith("/ChangesPage")
    assert set(CONTRACT) <= set(spec["components"]["schemas"]["TopicRow"]["properties"])


@pytest.mark.parametrize("field,src", [("text", "text:7100"), ("title_long", "title_long")])
def test_evidence_source_from_field(store, field, src):
    store.ex("UPDATE qs_affairs SET text_src = 'text:7100' WHERE id = ?", (AID,)); store.commit()
    r = next(x for x in read_rows(FIX / "topics_sample.jsonl") if x["affair_id"] == AID and x["scheme"] == "aps" and x["rank"] == 1)
    store.load_topics([dict(r, evidence=dict(field=field, start=3, end=9, quote="abcdef"))])
    ev = next(x for x in store.topics_for(AID, "aps") if x["level"] == 1 and x["rank"] == 1)["evidence"]
    assert ev == {"source": src, "field": field, "char_start": 3, "char_end": 9, "quote": "abcdef"}
