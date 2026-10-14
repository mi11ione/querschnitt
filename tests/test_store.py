"""Store versioning: reloads are idempotent, a changed row is a new version, vanished keys close, editor decisions add
rows and never bring back or overwrite machine rows."""
import json
import time

from querschnitt.store import Store, read_rows
from conftest import FIX

AID = 341382


def rows_of(aid):
    return [r for r in read_rows(FIX / "topics_sample.jsonl") if r["affair_id"] == aid]


def test_reload_is_idempotent(store):
    n = store.one("SELECT COUNT(*) AS n FROM topics")["n"]
    st = store.load_topics(FIX / "topics_sample.jsonl")
    assert st["inserted"] == 0 and st["unchanged"] == st["read"]
    assert store.one("SELECT COUNT(*) AS n FROM topics")["n"] == n


def test_changed_row_is_new_version(store):
    rs = rows_of(AID)
    r1 = next(r for r in rs if r["scheme"] == "aps" and r["level"] == 1 and r["rank"] == 1)
    new = [dict(r, p=0.77, input_hash="feedfacefeedface") if r is r1 else r for r in rs]
    st = store.load_topics(new)
    assert st["inserted"] == 1 and st["closed"] == 1
    hist = [r for r in store.topics_for(AID, "aps", history=True) if r["level"] == 1 and r["rank"] == 1]
    assert len(hist) == 2
    old, cur = sorted(hist, key=lambda r: r["row_id"])
    assert old["valid_to"] is not None and cur["valid_to"] is None and cur["p"] == 0.77
    assert cur["valid_from"] == old["valid_to"]


def test_vanished_key_is_closed(store):
    rs = [r for r in rows_of(AID) if not (r["scheme"] == "aps" and r["level"] == 2 and r["rank"] == 3)]
    st = store.load_topics(rs)
    assert st["closed"] == 1 and st["inserted"] == 0
    assert not [r for r in store.topics_for(AID, "aps") if r["level"] == 2 and r["rank"] == 3]


def test_confirm_and_reject(store):
    cur = store.topics_for(AID, "aps")
    top = next(r for r in cur if r["level"] == 1 and r["rank"] == 1)
    other = next(r for r in cur if r["level"] == 1 and r["rank"] == 2)
    row = store.decide(AID, "aps", other["code"], "confirm", "editor@dvs")
    assert row["status"] == "confirmed" and row["provenance"] == "confirmed" and row["confirmed_by"] == "editor@dvs"
    assert row["confirmed_at"] and row["p_raw"] == other["p_raw"]
    now = store.topics_for(AID, "aps")
    lvl1 = [r for r in now if r["level"] == 1]
    assert [r["code"] for r in lvl1] == [other["code"]] and lvl1[0]["provenance"] == "confirmed"
    # the machine rows are kept, closed
    hist = store.topics_for(AID, "aps", history=True)
    assert any(r["row_id"] == top["row_id"] and r["valid_to"] for r in hist)
    # an identical nightly reload does not bring the machine rows back
    st = store.load_topics(rows_of(AID))
    assert st["inserted"] == 0
    # reject the digitalisation flag
    dg = next(r for r in store.topics_for(AID) if r["scheme"] == "adhoc/digitalisierung")
    rj = store.decide(AID, "adhoc/digitalisierung", dg["code"], "reject", "editor@dvs")
    assert rj["status"] == "rejected"
    cur = [r for r in store.topics_for(AID) if r["scheme"] == "adhoc/digitalisierung"]
    assert [r["status"] for r in cur] == ["rejected"]


def test_decide_requires_by(store):
    import pytest
    with pytest.raises(ValueError):
        store.decide(AID, "aps", "aps:1.1.1.", "confirm", " ")


def test_changes_since(store):
    t = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() - 1))
    time.sleep(0.01)
    store.decide(AID, "adhoc/digitalisierung", "adhoc/digitalisierung:yes", "confirm", "x")
    ch = store.changes(since=t)[1]
    assert any(r["provenance"] == "confirmed" for r in ch)          # the new decision
    assert any(r["valid_to"] for r in ch)                           # the machine row it closed
    assert store.changes(since="2999-01-01") == (0, [])


def test_unscored_counts_changed_inputs(store):
    assert store.unscored() == 0
    store.ex("UPDATE qs_affairs SET input_hash = 'changed' WHERE id = ?", (AID,)); store.commit()
    assert store.unscored() == 1


def test_coverage_and_metrics(store):
    cov = {c["body_key"]: c for c in store.coverage()}
    assert cov["CHE"]["affairs"] >= cov["CHE"]["scored"] > 0
    assert 0 <= cov["CHE"]["scored_share"] <= 1
    m = store.metrics()
    assert m["rows"] > 0 and m["affairs_loaded"] == 80 and m["store"] == store.kind
    assert m["affairs"] == 60 == sum(c["affairs"] for c in store.coverage())     # the 2025- scope; 20 affairs are from 2019


def test_postgres_if_available():
    """Runs in CI against a Postgres service (QS_TEST_PG_DSN); skipped elsewhere."""
    import os
    import pytest
    dsn = os.environ.get("QS_TEST_PG_DSN")
    if not dsn:
        pytest.skip("no QS_TEST_PG_DSN")
    s = Store(dsn=dsn)
    s.ex("DELETE FROM topics"); s.ex("DELETE FROM qs_affairs"); s.commit()
    s.load_affairs(FIX / "inputs_sample.jsonl")
    st = s.load_topics(FIX / "topics_sample.jsonl")
    assert st["inserted"] == 504
    assert s.load_topics(FIX / "topics_sample.jsonl")["inserted"] == 0
    r = s.decide(AID, "adhoc/digitalisierung", "adhoc/digitalisierung:yes", "confirm", "ci")
    assert r["provenance"] == "confirmed" and isinstance(r["valid_from"], str)
    assert isinstance(s.topics_for(AID, "aps")[0]["evidence"], dict)
    assert s.coverage() and s.metrics()["store"] == "postgres"
    s.close()


def test_load_affairs_from_static_export(tmp_path):
    """make run on a clean checkout: affair summaries from app/data (columnar affairs.json, bodies.json, detail/)."""
    d = tmp_path / "data"; (d / "detail").mkdir(parents=True)
    (d / "affairs.json").write_text(json.dumps(dict(n=2, cols=dict(id=[5001, 5002], body=["CHE", "351"], date=["2026-10-01", "2026-09-30"],
        type_h=["Motion", "Interpellation"], state=["eingereicht", ""], lang=["de", "de"], title=["A", "B"], party=["FDP", ""],
        submitter=["X", ""], stype=["member", "member"]))))
    (d / "bodies.json").write_text(json.dumps([dict(key="CHE", name_de="Bundesversammlung", name_fr="Assemblée fédérale", level="federal"),
                                               dict(key="351", name_de="Stadtrat Bern", name_fr="Conseil de ville de Berne", level="communal")]))
    (d / "detail" / "5.json").write_text(json.dumps({"5001": dict(title_long="Langtitel A", text="x" * 50, url="https://x", number=26.4)}))
    s = Store(path=str(tmp_path / "e.sqlite"), dsn="")
    assert s.load_affairs_export(d) == 2
    a = s.affair(5001)
    assert a["level"] == "federal" and a["parl"] == "Bundesversammlung" and a["title_long"] == "Langtitel A" and a["has_text"]
    assert s.affair(5002)["level"] == "communal" and s.affair(5002)["has_text"] is False
    assert s.unscored("2000-01-01") == 0                   # no input hash: never counted as unscored
    s.close()
