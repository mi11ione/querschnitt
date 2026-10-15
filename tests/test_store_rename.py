"""The store's table is `qs_topics`. A store made before the prefix (rows in `topics`) is renamed when opened; a `topics`
that is not the store's own (OpenParlData's, upstream/opd/migrations/0001_topics.up.sql) is never touched. SQLite always;
Postgres when QS_TEST_PG_DSN is set (CI), each case in its own schema."""
import gzip
import json
import os
import sqlite3

import pytest

from querschnitt.store import SQL, Store, read_rows
from conftest import FIX

ROOT = SQL.parent
OLD_COLS = ("affair_id, body_key, scheme, level, code, rank, p, p_raw, lane, status, provenance, evidence, model, build, "
            "cutoffs_id, prompt_id, input_hash, valid_from, valid_to, confirmed_by, confirmed_at, version")


def old_ddl(pg: bool, with_seq: bool = True) -> str:
    """The DDL as it was before the qs_ prefix: same table, `topics`, `topics_*` indexes, `topics_current` view."""
    ddl = (SQL / ("qs_topics.sql" if pg else "qs_topics.sqlite.sql")).read_text().replace("qs_topics", "topics")
    if not with_seq:                                   # the oldest stores: no seq / closed_by (init adds them)
        ddl = "\n".join(l for l in ddl.splitlines() if not l.lstrip().startswith(("seq ", "closed_by ")))
    return ddl


def sample_store(tmp_path) -> Store:
    s = Store(path=str(tmp_path / "sample.sqlite"), dsn="")
    s.load_affairs(FIX / "inputs_sample.jsonl")
    s.load_topics(FIX / "topics_sample.jsonl")
    return s


def sqlite_names(db) -> dict[str, str]:
    with sqlite3.connect(db) as c:
        return {n: t for t, n in c.execute("SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")}


@pytest.mark.parametrize("with_seq", [True, False])
def test_sqlite_legacy_store_is_renamed(tmp_path, with_seq):
    ref = sample_store(tmp_path)
    dec = ref.decide(341382, "aps", ref.topics_for(341382, "aps")[0]["code"], "confirm", "editor")
    n = ref.one("SELECT COUNT(*) AS n FROM qs_topics")["n"]
    ref.close()
    db = tmp_path / "old.sqlite"
    with sqlite3.connect(db) as c:
        c.executescript(old_ddl(pg=False, with_seq=with_seq))
        c.execute(f"ATTACH '{tmp_path / 'sample.sqlite'}' AS s")
        cols = OLD_COLS + (", seq, closed_by" if with_seq else "")
        c.execute(f"INSERT INTO topics (row_id, {cols}) SELECT row_id, {cols} FROM s.qs_topics ORDER BY row_id")
        c.execute("INSERT INTO qs_affairs SELECT * FROM s.qs_affairs")
    names = sqlite_names(db)
    assert names["topics"] == "table" and names["topics_current"] == "view" and "qs_topics" not in names
    max_id = sqlite3.connect(db).execute("SELECT MAX(row_id) FROM topics").fetchone()[0]

    s = Store(path=str(db), dsn="")
    names = sqlite_names(db)
    assert "topics" not in names and not [k for k in names if k.startswith("topics")]          # nothing left under the old name
    assert names["qs_topics"] == "table" and names["qs_topics_current"] == "view"
    assert {"qs_topics_current_affair", "qs_topics_current_code", "qs_topics_key", "qs_topics_valid_from",
            "qs_topics_valid_to", "qs_topics_seq"} <= {k for k, t in names.items() if t == "index"}
    assert s.one("SELECT COUNT(*) AS n FROM qs_topics")["n"] == n
    assert s.one("SELECT COUNT(*) AS n FROM qs_topics_current")["n"] == s.one(
        "SELECT COUNT(*) AS n FROM qs_topics WHERE valid_to IS NULL")["n"]
    assert s.one("SELECT COUNT(*) AS n FROM qs_topics WHERE seq IS NULL")["n"] == 0
    assert s.load_topics(FIX / "topics_sample.jsonl")["inserted"] == 0                  # the rows are the same rows
    cur = [r for r in s.topics_for(341382, "aps") if r["provenance"] == "confirmed"]
    assert cur and cur[0]["code"] == dec["code"] and cur[0]["confirmed_by"] == "editor"       # decisions kept
    new = s.decide(341382, "aps", dec["code"], "reject", "editor")                      # writes go on, ids continue
    assert new["row_id"] > max_id
    s.close()
    Store(path=str(db), dsn="").close()                                                 # opening again changes nothing
    assert sqlite_names(db) == names


def test_sqlite_other_topics_table_is_never_touched(tmp_path):
    """A `topics` with OPD's columns (scheme_key, scheme_id, id) stays exactly as it is; the store uses qs_topics."""
    db = tmp_path / "shared.sqlite"
    opd = ("CREATE TABLE topics (id INTEGER PRIMARY KEY, affair_id INTEGER NOT NULL, scheme_id INTEGER NOT NULL, "
           "scheme_key TEXT NOT NULL, level INTEGER, code TEXT, rank INTEGER, valid_from TEXT NOT NULL, valid_to TEXT)")
    with sqlite3.connect(db) as c:
        c.execute(opd)
        c.execute("CREATE VIEW topics_current AS SELECT * FROM topics WHERE valid_to IS NULL")
        c.execute("INSERT INTO topics VALUES (7, 341382, 1, 'aps', 1, 'aps:1.7.2.', 1, '2026-10-15 00:00:00', NULL)")
    before = sqlite3.connect(db).execute("SELECT type, name, sql FROM sqlite_master WHERE name LIKE 'topics%' ORDER BY name").fetchall()
    s = Store(path=str(db), dsn="")
    s.load_affairs(FIX / "inputs_sample.jsonl")
    assert s.load_topics(FIX / "topics_sample.jsonl")["inserted"] == 504
    s.close()
    c = sqlite3.connect(db)
    assert c.execute("SELECT type, name, sql FROM sqlite_master WHERE name LIKE 'topics%' ORDER BY name").fetchall() == before
    assert c.execute("SELECT * FROM topics").fetchall() == [(7, 341382, 1, "aps", 1, "aps:1.7.2.", 1, "2026-10-15 00:00:00", None)]
    assert c.execute("SELECT COUNT(*) FROM qs_topics").fetchone()[0] == 504


def test_topics_file_is_the_loaders_shape(store, tmp_path):
    """write_topics_file: every current machine row, in the shape upstream/hop/load_topics.hpl reads."""
    out = tmp_path / "out" / "topics.jsonl.gz"
    n = store.write_topics_file(out, chunk=50)                        # several pages
    rows = list(read_rows(out))
    want = store.one("SELECT COUNT(*) AS n FROM qs_topics WHERE provenance = 'inferred' AND valid_to IS NULL")["n"]
    assert n == len(rows) == want and len({(r["affair_id"], r["scheme"], r["level"], r["rank"]) for r in rows}) == n
    for r in rows:
        assert r["provenance"] == "inferred" and r["valid_to"] is None
        assert len(r["valid_from"]) == 20 and r["valid_from"].endswith("Z")                 # yyyy-MM-dd'T'HH:mm:ss'Z'
        if r["evidence"]:
            ev = r["evidence"]
            assert ev["start"] == ev["char_start"] and ev["end"] == ev["char_end"] and ev["quote"]
    assert any(r["evidence"] for r in rows)
    assert not list(out.parent.glob("*.tmp"))
    # a decision closes its machine row: that row leaves the file
    aid = rows[0]["affair_id"]
    r1 = next(r for r in store.topics_for(aid, "aps") if r["level"] == 1 and r["rank"] == 1)
    store.decide(aid, "aps", r1["code"], "reject", "editor")
    assert store.write_topics_file(out) == n - 1


# ---------------------------------------------------------------------------------------------------------- Postgres
def pg_schema(name: str):
    """A fresh schema on the CI Postgres and a DSN whose search_path is that schema (the store and the SQL land there)."""
    dsn = os.environ.get("QS_TEST_PG_DSN")
    if not dsn:
        pytest.skip("no QS_TEST_PG_DSN")
    import psycopg
    from psycopg.conninfo import make_conninfo
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute(f"DROP SCHEMA IF EXISTS {name} CASCADE")
        c.execute(f"CREATE SCHEMA {name}")
    sdsn = make_conninfo(dsn, options=f"-csearch_path={name}")
    return psycopg.connect(sdsn, autocommit=True), sdsn


def test_postgres_legacy_store_is_renamed():
    c, dsn = pg_schema("qs_test_legacy")
    c.execute(old_ddl(pg=True, with_seq=False))
    for i, code in enumerate(["aps:1.7.2.", "aps:1.1.1.", "aps:2.1.1."], 1):
        c.execute("INSERT INTO topics (affair_id, scheme, level, code, rank, lane, valid_from) VALUES (%s, 'aps', 1, %s, %s, %s, now())",
                  (341382, code, i, "pass" if i == 1 else None))
    old = {r[0] for r in c.execute("SELECT conname FROM pg_constraint WHERE conrelid = 'topics'::regclass")}
    assert "topics_pkey" in old and "topics_lane_check" in old
    s = Store(dsn=dsn)
    q = lambda sql: [r[0] for r in c.execute(sql)]
    assert q("SELECT to_regclass('topics') IS NULL")[0] and q("SELECT to_regclass('topics_current') IS NULL")[0]
    assert q("SELECT to_regclass('qs_topics_current') IS NOT NULL")[0]
    idx = q("SELECT c.relname FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid WHERE i.indrelid = 'qs_topics'::regclass")
    con = q("SELECT conname FROM pg_constraint WHERE conrelid = 'qs_topics'::regclass")
    assert idx and all(n.startswith("qs_topics") for n in idx) and "qs_topics_pkey" in idx and "qs_topics_seq" in idx
    assert con and all(n.startswith("qs_topics") for n in con) and len(con) == len(old)
    assert q("SELECT pg_get_serial_sequence('qs_topics', 'row_id')")[0].endswith("qs_topics_row_id_seq")
    assert q("SELECT relname FROM pg_class WHERE relnamespace = 'qs_test_legacy'::regnamespace AND relname LIKE 'topics%'") == []
    assert s.one("SELECT COUNT(*) AS n FROM qs_topics WHERE seq IS NOT NULL")["n"] == 3        # columns added after the rename
    s.load_affairs(FIX / "inputs_sample.jsonl")
    assert s.load_topics(FIX / "topics_sample.jsonl")["inserted"] > 0
    assert s.one("SELECT MIN(row_id) AS m FROM qs_topics WHERE row_id > 3")["m"] == 4             # the sequence continues
    s.close()
    Store(dsn=dsn).close()                                                                       # opening again: no-op
    c.close()


def test_postgres_opd_topics_is_never_touched(tmp_path):
    """OPD's migration 0001 (over the stand-in affairs/bodies of the hop CI job), then the store in the same schema."""
    c, dsn = pg_schema("qs_test_opd")
    c.execute((ROOT / "upstream/hop/ci/opd_stand_in.sql").read_text())
    c.execute((ROOT / "upstream/opd/migrations/0001_topics.up.sql").read_text())
    c.execute("INSERT INTO topic_schemes (id, scheme_key, version, type, levels, source_name) VALUES (1, 'aps', 'x', 'standard', 2, 'APS')")
    aid = c.execute("SELECT id FROM affairs LIMIT 1").fetchone()[0]
    c.execute("INSERT INTO topics (affair_id, scheme_id, scheme_key, level, code, valid_from) VALUES (%s, 1, 'aps', 1, 'aps:1.7.2.', now())", (aid,))
    snap = lambda: (c.execute("SELECT md5(string_agg(t::text, '|' ORDER BY id)) FROM topics t").fetchone()[0],
                    c.execute("SELECT pg_get_viewdef('topics_current')").fetchone()[0],
                    sorted(r[0] for r in c.execute("SELECT relname FROM pg_class WHERE relnamespace = 'qs_test_opd'::regnamespace "
                                                   "AND relname LIKE 'topic%'")))
    before = snap()
    s = Store(dsn=dsn)
    s.load_affairs(FIX / "inputs_sample.jsonl")
    assert s.load_topics(FIX / "topics_sample.jsonl")["inserted"] == 504
    assert s.write_topics_file(tmp_path / "topics.jsonl.gz") == 504
    s.close()
    Store(dsn=dsn).close()
    assert snap() == before
    assert c.execute("SELECT count(*) FROM qs_topics").fetchone()[0] == 504
    c.close()
