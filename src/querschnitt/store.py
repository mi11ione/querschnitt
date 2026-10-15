"""The `topics` store: SQLite by default (`QS_DB`, default data/querschnitt.sqlite), Postgres when `QS_PG_DSN` is set
(psycopg 3). DDL: sql/topics.sql (Postgres, proposed upstream) and sql/topics.sqlite.sql.

Versioning (docs/CONTRACT.md §1): a row is never changed except to close it (`valid_to`). Loading topic rows compares
each (affair, scheme, level, rank) with the latest machine row for that key; identical content is skipped, changed
content closes the current row and adds a new one, and keys that disappear from a re-scored affair are closed. An
editor's confirm or reject adds a `provenance = confirmed` row with who and when and closes the machine row it decides;
the machine row stays in the history, and a later identical reload does not bring it back. Repeating the current
decision adds nothing; `undo` closes the decision (closed_by, valid_to) and restores, as new current rows, the rows it
had closed.

Every change gets the next `seq` (an insert, and a close, which re-stamps the row): `/changes?after=<seq>` is a feed in
which no change is lost. Writers are serialized (SQLite BEGIN IMMEDIATE, Postgres advisory lock), so `seq` order is
commit order across processes."""
from __future__ import annotations

import contextlib
import datetime as dt
import gzip
import json
import os
import re
import sqlite3
import threading
from pathlib import Path
from typing import Iterable, Iterator

ROOT = Path(__file__).resolve().parents[2]
SQL = ROOT / "sql"
COLS = ["affair_id", "body_key", "scheme", "level", "code", "rank", "p", "p_raw", "lane", "status", "provenance",
        "evidence", "model", "build", "cutoffs_id", "prompt_id", "input_hash", "valid_from", "valid_to", "confirmed_by",
        "confirmed_at", "version", "seq", "closed_by"]
CONTENT = ["body_key", "code", "p", "p_raw", "lane", "evidence", "model", "build", "cutoffs_id", "prompt_id",
           "input_hash", "version"]                      # a change in any of these is a new version
AFF_COLS = ["id", "body_key", "level", "canton", "parl", "parl_fr", "lang", "date", "number", "title", "title_long",
            "type", "type_h", "state", "url", "submitter", "party", "submitter_type", "has_text", "text_src",
            "input_hash", "updated"]
TS_COLS = ("valid_from", "valid_to", "confirmed_at", "ts")
EVIDENCE_KEYS = ("source", "field", "char_start", "char_end", "quote")
KINDS = {"all": None, "decisions": "confirmed", "machine": "inferred"}
LANES = ("pass", "please_check", "readings_agree")       # the lane check of sql/topics*.sql


def norm_evidence(ev, text_src: str | None = None):
    """Evidence in the CONTRACT §1 shape {source, field, char_start, char_end, quote}; `start`/`end` are accepted, and a
    missing source is the field for titles, else the affair's text source (text:<id> / doc:<id>)."""
    if isinstance(ev, str):
        try:
            ev = json.loads(ev)
        except ValueError:
            return ev
    if not isinstance(ev, dict):
        return ev
    f = ev.get("field")
    src = ev.get("source") or (f if f in ("title", "title_long") else (text_src or f))
    return dict(source=src, field=f, char_start=ev.get("char_start", ev.get("start")), char_end=ev.get("char_end", ev.get("end")),
                quote=ev.get("quote"))


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def parse_ts(s: str | dt.datetime | None) -> dt.datetime | None:
    """ISO 8601 (date or datetime; naive = UTC), 'yesterday' (00:00 UTC) or 'today'."""
    if s is None or isinstance(s, dt.datetime):
        return s if (s is None or s.tzinfo) else s.replace(tzinfo=dt.timezone.utc)
    s = s.strip()
    if s in ("today", "yesterday"):
        d = now().replace(hour=0, minute=0, second=0, microsecond=0)
        return d - dt.timedelta(days=1) if s == "yesterday" else d
    t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def iso(t: dt.datetime | str | None) -> str | None:
    if t is None or isinstance(t, str):
        return t
    return t.astimezone(dt.timezone.utc).isoformat(timespec="microseconds")


def _canon(v):
    if isinstance(v, float):
        return round(v, 4)
    if isinstance(v, (dict, list)):
        return json.dumps(v, sort_keys=True, ensure_ascii=False)
    if isinstance(v, str) and v[:1] in "{[":
        try:
            return json.dumps(json.loads(v), sort_keys=True, ensure_ascii=False)
        except ValueError:
            return v
    return v if v != "" else None


def sig(r: dict) -> tuple:
    return tuple(_canon(r.get(c)) for c in CONTENT)


def read_rows(path: str | Path) -> Iterator[dict]:
    """Topic rows from .jsonl, .jsonl.gz or .parquet."""
    p = Path(path)
    if p.suffix == ".parquet":
        import pyarrow.parquet as pq
        for batch in pq.ParquetFile(p).iter_batches(batch_size=20000):
            yield from batch.to_pylist()
        return
    op = gzip.open if p.suffix == ".gz" else open
    with op(p, "rt") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


class Store:
    def __init__(self, path: str | None = None, dsn: str | None = None):
        self.dsn = dsn if dsn is not None else os.environ.get("QS_PG_DSN") or None
        self.path = path or os.environ.get("QS_DB") or str(ROOT / "data" / "querschnitt.sqlite")
        self.lock = threading.RLock()
        self._tx_depth = 0
        if self.dsn:
            import psycopg
            self.pg = True
            self.conn = psycopg.connect(self.dsn, autocommit=False)
            self.ph = "%s"
        else:
            self.pg = False
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(self.path, check_same_thread=False, timeout=60)
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
            self.ph = "?"
        self.init()

    @property
    def kind(self) -> str:
        return "postgres" if self.pg else "sqlite"

    # ------------------------------------------------------------------ low level
    def _q(self, sql: str) -> str:
        return sql.replace("?", "%s") if self.pg else sql

    def ex(self, sql: str, params=(), many: bool = False):
        with self.lock:
            cur = self.conn.cursor()
            if many:
                cur.executemany(self._q(sql), params)
            else:
                cur.execute(self._q(sql), params)
            return cur

    def all(self, sql: str, params=()) -> list[dict]:
        with self.lock:
            cur = self.ex(sql, params)
            names = [d[0] for d in cur.description]
            out = [dict(zip(names, r)) for r in cur.fetchall()]
            if self.pg and not self._tx_depth:
                self.conn.commit()          # end the read transaction (no idle-in-transaction connections)
            return out

    def one(self, sql: str, params=()) -> dict | None:
        r = self.all(sql, params)
        return r[0] if r else None

    def commit(self):
        with self.lock:
            if not self._tx_depth:
                self.conn.commit()

    @contextlib.contextmanager
    def tx(self):
        """One serialized write transaction (SQLite BEGIN IMMEDIATE / Postgres advisory lock) with a seq allocator."""
        with self.lock:
            if self._tx_depth:
                self._tx_depth += 1
                try:
                    yield
                finally:
                    self._tx_depth -= 1
                return
            self.conn.commit()
            if self.pg:
                self.conn.execute("SELECT pg_advisory_xact_lock(714001)")
            else:
                self.conn.execute("BEGIN IMMEDIATE")
            self._tx_depth = 1
            try:
                self._seq = int(self.one("SELECT COALESCE(MAX(seq), 0) AS m FROM topics")["m"])
                yield
                self._tx_depth = 0
                self.conn.commit()
            except BaseException:
                self._tx_depth = 0
                self.conn.rollback()
                raise

    def next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def init(self):
        ddl = (SQL / ("topics.sql" if self.pg else "topics.sqlite.sql")).read_text()
        with self.lock:
            if self.pg:
                self.conn.execute(ddl)
                self._check_lanes()
                for c, ty in (("seq", "bigint"), ("closed_by", "text")):
                    self.conn.execute(f"ALTER TABLE topics ADD COLUMN IF NOT EXISTS {c} {ty}")
            else:
                self.conn.executescript(ddl)
                self._check_lanes()
                have = {r[1] for r in self.conn.execute("PRAGMA table_info(topics)")}
                for c, ty in (("seq", "INTEGER"), ("closed_by", "TEXT")):
                    if c not in have:
                        self.conn.execute(f"ALTER TABLE topics ADD COLUMN {c} {ty}")
            self.conn.execute("UPDATE topics SET seq = row_id WHERE seq IS NULL")       # databases from before seq
            self.conn.execute("CREATE INDEX IF NOT EXISTS topics_seq ON topics (seq)")
            self.conn.commit()

    def _check_lanes(self):
        """CREATE TABLE IF NOT EXISTS keeps an older table as it is: one whose lane check predates `pass` (14 Oct) would
        refuse today's chapter rows at the first load, so the store stops at open with what to do instead."""
        if self.pg:
            bad = [r[0] for r in self.conn.execute(
                "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'topics'::regclass AND contype = 'c'")
                if "lane" in r[1] and "please_check" in r[1] and "'pass'" not in r[1]]
            if bad:
                self.conn.rollback()
                raise RuntimeError(
                    f"topics: the lane check {bad[0]} predates the 'pass' lane, so today's rows would be refused. Migrate: "
                    f"ALTER TABLE topics DROP CONSTRAINT {bad[0]}, ADD CONSTRAINT topics_lane_check CHECK (lane IN "
                    f"({', '.join(repr(l) for l in LANES)}));")
            return
        ddl = (self.conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'topics'").fetchone() or [""])[0]
        m = re.search(r"lane\s+IN\s*\(([^)]*)\)", ddl, re.I)
        if m and "'pass'" not in m.group(1):
            raise RuntimeError(f"{self.path}: the topics table's lane check predates the 'pass' lane, so today's rows would be "
                               f"refused. Run `make clean-db` (or delete this file when QS_DB points elsewhere) and load again.")

    def close(self):
        with self.lock:
            self.conn.close()

    def _ts(self, t: dt.datetime | None):
        return t if (self.pg or t is None) else iso(t)

    def _out(self, r: dict) -> dict:
        """DB row -> API row: ISO timestamps, evidence as an object."""
        for c in TS_COLS:
            if c in r and isinstance(r[c], dt.datetime):
                r[c] = iso(r[c])
        if r.get("evidence") is not None:
            r["evidence"] = norm_evidence(r["evidence"])
        if "has_text" in r and r["has_text"] is not None:
            r["has_text"] = bool(r["has_text"])
        return r

    def _ins_row(self, r: dict, t: dt.datetime):
        r = dict(r)
        r["valid_from"] = self._ts(parse_ts(r.get("valid_from")) or t)
        r["valid_to"] = self._ts(parse_ts(r.get("valid_to")))
        r["confirmed_at"] = self._ts(parse_ts(r.get("confirmed_at")))
        ev = r.get("evidence")
        r["evidence"] = json.dumps(ev, ensure_ascii=False) if isinstance(ev, (dict, list)) else (ev or None)
        r.setdefault("status", "suggested"); r.setdefault("provenance", "inferred"); r.setdefault("rank", 1)
        r["seq"] = self.next_seq()
        r["closed_by"] = None
        return tuple(r.get(c) for c in COLS)

    def _close(self, row_ids: list[int], t: dt.datetime, by: str | None = None):
        """Close current rows (valid_to, a new seq, and who when a person closes them)."""
        if row_ids:
            self.ex("UPDATE topics SET valid_to = ?, seq = ?, closed_by = ? WHERE row_id = ? AND valid_to IS NULL",
                    [(self._ts(t), self.next_seq(), by, rid) for rid in row_ids], many=True)

    def _insert_sql(self) -> str:
        vals = ", ".join("CAST(? AS jsonb)" if (self.pg and c == "evidence") else "?" for c in COLS)
        return f"INSERT INTO topics ({', '.join(COLS)}) VALUES ({vals})"

    # ------------------------------------------------------------------ loading
    def load_topics(self, rows: str | Path | Iterable[dict], chunk: int = 2000) -> dict:
        """Load topic rows (CONTRACT §1) with versioning. Rows of one affair should be contiguous (compose writes them
        so); an affair seen again later in the same file is loaded without closing its vanished keys."""
        src = read_rows(rows) if isinstance(rows, (str, Path)) else rows
        t = now()
        st = dict(read=0, inserted=0, unchanged=0, closed=0, affairs=0, noncontiguous=0)
        seen: set[int] = set()
        groups: dict[int, list[dict]] = {}
        order: list[int] = []
        last = None
        for r in src:
            st["read"] += 1
            a = int(r["affair_id"]); r["affair_id"] = a
            if a != last and a in seen and a not in groups:
                st["noncontiguous"] += 1
            if a not in groups:
                groups[a] = []; order.append(a)
            groups[a].append(r)
            last = a
            if len(groups) >= chunk:
                self._load_chunk(groups, order, seen, t, st)
                seen.update(order); groups, order = {}, []
        if groups:
            self._load_chunk(groups, order, seen, t, st)
        self.commit()
        return st

    def _load_chunk(self, groups: dict[int, list[dict]], order: list[int], seen: set[int], t, st: dict):
        with self.tx():
            self._load_chunk_tx(groups, order, seen, t, st)

    def _load_chunk_tx(self, groups: dict[int, list[dict]], order: list[int], seen: set[int], t, st: dict):
        ids = list(groups)
        latest: dict[tuple, dict] = {}
        current: dict[tuple, list[int]] = {}
        tsrc: dict[int, str] = {}
        for i in range(0, len(ids), 900):
            part = ids[i:i + 900]
            q = ("SELECT row_id, affair_id, scheme, level, rank, valid_to, " + ", ".join(CONTENT) +
                 f" FROM topics WHERE provenance = 'inferred' AND affair_id IN ({', '.join('?' * len(part))})")
            for r in self.all(q, part):
                k = (r["affair_id"], r["scheme"], r["level"], r["rank"])
                if k not in latest or r["row_id"] > latest[k]["row_id"]:
                    latest[k] = r
                if r["valid_to"] is None:
                    current.setdefault(k, []).append(r["row_id"])
            if any(r.get("evidence") for a in part for r in groups[a]):
                tsrc.update({r["id"]: r["text_src"] for r in self.all(
                    f"SELECT id, text_src FROM qs_affairs WHERE id IN ({', '.join('?' * len(part))})", part)})
        for k, r in latest.items():
            if r.get("evidence") is not None:
                r["evidence"] = norm_evidence(r["evidence"])
        close, ins = [], []
        for a in order:
            keys = set()
            for r in groups[a]:
                r.setdefault("rank", 1)
                if r.get("evidence"):
                    r["evidence"] = norm_evidence(r["evidence"], tsrc.get(a))
                k = (a, r["scheme"], int(r["level"]), int(r["rank"]))
                keys.add(k)
                old = latest.get(k)
                if old is not None and sig(old) == sig(r):
                    st["unchanged"] += 1
                    continue
                close += current.get(k, [])
                ins.append(dict(r, provenance="inferred", valid_from=None, valid_to=None))
            if a not in seen:                                   # keys of re-scored schemes that vanished
                schemes = {k[1] for k in keys}
                for k, rids in current.items():
                    if k[0] == a and k[1] in schemes and k not in keys:
                        close += rids
            st["affairs"] += 1
        if close:
            self._close(close, t)
            st["closed"] += len(close)
        if ins:
            self.ex(self._insert_sql(), [self._ins_row(r, t) for r in ins], many=True)
            st["inserted"] += len(ins)

    def load_affairs(self, inputs: str | Path) -> int:
        """Affair summaries from inputs.jsonl.gz (one row per affair; upsert)."""
        sql = (f"INSERT INTO qs_affairs ({', '.join(AFF_COLS)}) VALUES ({', '.join('?' * len(AFF_COLS))}) "
               "ON CONFLICT (id) DO UPDATE SET " + ", ".join(f"{c} = excluded.{c}" for c in AFF_COLS[1:]))
        n, buf = 0, []
        op = gzip.open if str(inputs).endswith(".gz") else open
        with op(inputs, "rt") as f:
            for line in f:
                if not line.strip():
                    continue
                x = json.loads(line)
                x = dict(x, body_key=x.get("body"), title_long=(x.get("title_long") or "")[:400],
                         has_text=bool(x.get("text")), number=None if x.get("number") is None else str(x["number"]),
                         updated=None if x.get("updated") is None else str(x["updated"]))
                buf.append(tuple(x.get(c) for c in AFF_COLS)); n += 1
                if len(buf) >= 5000:
                    self.ex(sql, buf, many=True); buf = []
        if buf:
            self.ex(sql, buf, many=True)
        self.commit()
        rows = self.all("SELECT body_key AS key, MIN(parl) AS name_de, MIN(parl_fr) AS name_fr, MIN(level) AS level, "
                        "MIN(canton) AS canton, MIN(SUBSTR(date, 1, 4)) AS y FROM qs_affairs "
                        "WHERE date >= '1800' GROUP BY body_key")
        self.load_bodies([dict(r, covered_from=int(r["y"]) if (r["y"] or "").isdigit() else None) for r in rows], keep_names=True)
        return n

    def load_bodies(self, bodies: list[dict], keep_names: bool = False) -> int:
        """Parliaments (key, names, level, canton, lang, covered_from). covered_from keeps the earliest year seen, so a
        slim inputs file (the slice only) never moves it later than the export's bodies.json says."""
        old = {r["key"]: r for r in self.all("SELECT * FROM qs_bodies")}
        cols = ["key", "name_de", "name_fr", "level", "canton", "lang", "covered_from"]
        out = []
        for b in bodies:
            o = old.get(b["key"]) or {}
            cf = [int(x) for x in (b.get("covered_from"), o.get("covered_from")) if x not in (None, "") and str(x)[:4].isdigit()]
            r = {c: (o.get(c) if (keep_names and o.get(c)) else (b.get(c) or o.get(c))) for c in cols[1:6]}
            out.append((b["key"], *[r[c] for c in cols[1:6]], min(cf) if cf else None))
        sql = (f"INSERT INTO qs_bodies ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))}) "
               "ON CONFLICT (key) DO UPDATE SET " + ", ".join(f"{c} = excluded.{c}" for c in cols[1:]))
        if out:
            self.ex(sql, out, many=True)
        self.commit()
        return len(out)

    def load_affairs_export(self, d: str | Path) -> int:
        """Affair summaries from the static export (app/data: affairs.json columns, bodies.json, detail/*.json), for a
        clean checkout that ships the export but not inputs.jsonl.gz. No input hash there: such affairs never count
        as pending."""
        d = Path(d)
        cols = json.loads((d / "affairs.json").read_text())["cols"]
        B = {b["key"]: b for b in json.loads((d / "bodies.json").read_text())} if (d / "bodies.json").exists() else {}
        det: dict = {}
        for p in sorted((d / "detail").glob("*.json")) if (d / "detail").exists() else []:
            det.update({int(k): v for k, v in json.loads(p.read_text()).items()})
        keep = ("input_hash", "updated", "text_src")                 # the export has none of these: never erase them
        sql = (f"INSERT INTO qs_affairs ({', '.join(AFF_COLS)}) VALUES ({', '.join('?' * len(AFF_COLS))}) "
               "ON CONFLICT (id) DO UPDATE SET " + ", ".join(f"{c} = COALESCE(excluded.{c}, qs_affairs.{c})" if c in keep
                                                            else f"{c} = excluded.{c}" for c in AFF_COLS[1:]))
        buf = []
        for i, aid in enumerate(cols["id"]):
            g = lambda k: (cols.get(k) or [None] * (i + 1))[i]
            b, x = B.get(g("body")) or {}, det.get(aid) or {}
            r = dict(id=aid, body_key=g("body"), level=b.get("level"), canton=b.get("canton"), parl=b.get("name_de"),
                     parl_fr=b.get("name_fr"), lang=g("lang"), date=g("date"), number=x.get("number"), title=g("title"),
                     title_long=(x.get("title_long") or "")[:400], type=g("type_h"), type_h=g("type_h"), state=g("state"),
                     url=x.get("url"), submitter=g("submitter"), party=g("party"), submitter_type=g("stype"),
                     has_text=bool(x.get("text")), text_src=x.get("text_src"), input_hash=None, updated=None)
            r["number"] = None if r["number"] is None else str(r["number"])
            buf.append(tuple(r.get(c) for c in AFF_COLS))
        for i in range(0, len(buf), 5000):
            self.ex(sql, buf[i:i + 5000], many=True)
        self.commit()
        if B:
            self.load_bodies_json(d / "bodies.json")
        return len(buf)

    def load_bodies_json(self, path: str | Path) -> int:
        """Parliament names and covered_from from the export's bodies.json."""
        B = json.loads(Path(path).read_text())
        return self.load_bodies([dict(key=b["key"], name_de=b.get("name_de"), name_fr=b.get("name_fr"), level=b.get("level"),
                                      canton=b.get("canton"), lang=b.get("lang"), covered_from=b.get("covered_from")) for b in B])

    # ------------------------------------------------------------------ reads
    def affair(self, aid: int) -> dict | None:
        r = self.one("SELECT * FROM qs_affairs WHERE id = ?", (aid,))
        return self._out(r) if r else None

    def affairs(self, ids: list[int]) -> dict[int, dict]:
        out = {}
        for i in range(0, len(ids), 900):
            part = ids[i:i + 900]
            for r in self.all(f"SELECT * FROM qs_affairs WHERE id IN ({', '.join('?' * len(part))})", part):
                out[r["id"]] = self._out(r)
        return out

    def topics_for(self, aid: int, scheme: str | None = None, history: bool = False) -> list[dict]:
        q, a = "SELECT * FROM topics WHERE affair_id = ?", [aid]
        if scheme:
            q += " AND scheme = ?"; a.append(scheme)
        if not history:
            q += " AND valid_to IS NULL"
        q += " ORDER BY scheme, level, rank, row_id"
        return [self._out(r) for r in self.all(q, a)]

    def by_code(self, scheme: str, code: str, date_from: str | None = None, date_to: str | None = None,
                body: str | None = None, plevel: str | None = None, lang: str | None = None, lane: str | None = None,
                status: str | None = None, rank: int | None = 1, limit: int = 100, offset: int = 0) -> tuple[int, list[dict]]:
        """Current rows with this code, newest affair first, each with its affair summary."""
        w, a = ["t.valid_to IS NULL", "t.scheme = ?", "t.code = ?"], [scheme, code]
        for cond, v in (("a.date >= ?", date_from), ("a.date <= ?", date_to), ("t.body_key = ?", body), ("a.level = ?", plevel),
                        ("a.lang = ?", lang), ("t.lane = ?", lane), ("t.status = ?", status), ("t.rank = ?", rank)):
            if v not in (None, ""):
                w.append(cond); a.append(v)
        base = f"FROM topics t LEFT JOIN qs_affairs a ON a.id = t.affair_id WHERE {' AND '.join(w)}"
        total = self.one(f"SELECT COUNT(*) AS n {base}", a)["n"]
        acols = ", ".join(f"a.{c} AS a_{c}" for c in AFF_COLS)
        rows = self.all(f"SELECT t.*, {acols} {base} ORDER BY a.date DESC, t.affair_id DESC, t.row_id DESC LIMIT ? OFFSET ?",
                        a + [int(limit), int(offset)])
        out = []
        for r in rows:
            aff = {c: r.pop(f"a_{c}") for c in AFF_COLS}
            r = self._out(r)
            r["affair"] = self._out(aff) if aff["id"] is not None else {"id": r["affair_id"]}
            out.append(r)
        return total, out

    def changes(self, after: int = 0, since: str | None = None, scheme: str | None = None, body: str | None = None,
                kind: str = "all", limit: int = 1000) -> tuple[int, list[dict]]:
        """The sync feed: rows whose last change (insert or close) has seq > `after`, in seq order, optionally only those
        changed after `since` (valid_from or valid_to), of one scheme / body, decisions or machine rows. Returns (rows
        matching after the cursor, page). A client upserts by row_id and continues from the page's last seq."""
        if kind not in KINDS:
            raise ValueError(f"kind must be one of {', '.join(KINDS)}")
        w, a = ["seq > ?"], [int(after)]
        if since:
            t = self._ts(parse_ts(since))
            w.append("(valid_from > ? OR valid_to > ?)"); a += [t, t]
        for cond, v in (("scheme = ?", scheme), ("body_key = ?", body), ("provenance = ?", KINDS[kind])):
            if v:
                w.append(cond); a.append(v)
        where = " AND ".join(w)
        total = int(self.one(f"SELECT COUNT(*) AS n FROM topics WHERE {where}", a)["n"])
        rows = self.all(f"SELECT * FROM topics WHERE {where} ORDER BY seq LIMIT ?", a + [int(limit)])
        return total, [self._out(r) for r in rows]

    def schemes(self) -> list[str]:
        return [r["scheme"] for r in self.all("SELECT DISTINCT scheme FROM topics WHERE valid_to IS NULL ORDER BY scheme")]

    # ------------------------------------------------------------------ editor decisions
    def decide(self, aid: int, scheme: str, code: str, action: str, by: str, level: int | None = None) -> dict:
        """confirm | reject one code for one affair. Adds a `provenance = confirmed` row (status confirmed / rejected,
        confirmed_by, confirmed_at; p, evidence, build and prompt copied from the machine row it decides) and closes
        what it decides: a confirm closes every current row of that scheme at that level (the ranked machine suggestions
        and any earlier decision); a reject closes the current rows with that code. The same decision by the same person
        while it is current returns that row (`unchanged: true`) and adds nothing."""
        assert action in ("confirm", "reject")
        by = (by or "").strip()[:200]
        if not by:
            raise ValueError("`by` is required")
        status = "confirmed" if action == "confirm" else "rejected"
        with self.tx():
            cur = self.topics_for(aid, scheme)
            dup = [r for r in cur if r["provenance"] == "confirmed" and r["code"] == code and r["status"] == status
                   and r["confirmed_by"] == by]
            if dup:
                return dict(dup[-1], unchanged=True)
            same = [r for r in cur if r["code"] == code]
            if level is None:
                level = same[0]["level"] if same else (2 if ":kw:" in code else 1)
            src = min(same, key=lambda r: (r["provenance"] != "inferred", r["rank"]), default=None) or {}
            close = [r for r in cur if r["level"] == level] if action == "confirm" else same
            t = now()
            body = src.get("body_key") or (self.affair(aid) or {}).get("body_key")
            row = dict(affair_id=aid, body_key=body, scheme=scheme, level=level, code=code, rank=1, p=src.get("p"),
                       p_raw=src.get("p_raw"), lane=src.get("lane"), status=status, provenance="confirmed",
                       evidence=src.get("evidence"), model=src.get("model"), build=src.get("build"),
                       cutoffs_id=src.get("cutoffs_id"), prompt_id=src.get("prompt_id"), input_hash=src.get("input_hash"),
                       valid_from=t, valid_to=None, confirmed_by=by, confirmed_at=t, version=src.get("version"))
            self._close([r["row_id"] for r in close], t, by)
            rid = self._insert(row, t)
        return self._out(self.one("SELECT * FROM topics WHERE row_id = ?", (rid,)))

    def _insert(self, row: dict, t) -> int:
        c = self.ex(self._insert_sql() + (" RETURNING row_id" if self.pg else ""), self._ins_row(row, t))
        return c.fetchone()[0] if self.pg else c.lastrowid

    def undo(self, aid: int, scheme: str, code: str, by: str) -> dict:
        """Revert the current decision on (affair, scheme, code): close it (valid_to, closed_by = who undid it) and put back,
        as new current rows, the rows that decision had closed. Raises LookupError when there is no current decision."""
        by = (by or "").strip()[:200]
        if not by:
            raise ValueError("`by` is required")
        with self.tx():
            dec = [r for r in self.topics_for(aid, scheme) if r["provenance"] == "confirmed" and r["code"] == code]
            if not dec:
                raise LookupError(f"no current decision on {code} for affair {aid}")
            d = max(dec, key=lambda r: r["row_id"])
            prev = self.all("SELECT * FROM topics WHERE affair_id = ? AND scheme = ? AND valid_to = ? AND row_id < ? "
                            "AND (closed_by = ? OR closed_by IS NULL)", (aid, scheme, self._ts(parse_ts(d["valid_from"])), d["row_id"], d["confirmed_by"]))
            t = now()
            self._close([d["row_id"]], t, by)
            new = []
            for r in sorted(prev, key=lambda r: r["row_id"]):
                r = self._out(dict(r))
                for k in ("row_id", "seq", "closed_by", "valid_to"):
                    r.pop(k, None)
                new.append(self._insert(dict(r, valid_from=t), t))
        rows = {r["row_id"]: r for r in self.topics_for(aid, scheme, history=True)}
        return dict(undone=rows[d["row_id"]], restored=[rows[i] for i in new])

    # ------------------------------------------------------------------ coverage, metrics, runs
    def state_key(self) -> tuple:
        """Changes whenever rows or affairs change (cache key for whole-table aggregates)."""
        r = self.one("SELECT MAX(seq) AS m, COUNT(*) AS n FROM topics")
        a = self.one("SELECT COUNT(*) AS n FROM qs_affairs")
        b = self.one("SELECT COUNT(*) AS n, MIN(covered_from) AS c FROM qs_bodies")
        return r["m"], r["n"], a["n"], b["n"], b["c"]

    def scope(self, since: str | None = None) -> str:
        return since or os.environ.get("QS_SCOPE_SINCE", "2025-01-01")

    def coverage(self, scheme: str = "aps", since: str | None = None) -> list[dict]:
        key = (scheme, self.scope(since), self.state_key())
        c = getattr(self, "_cov", {})
        if key not in c:
            self._cov = {key: self._coverage(scheme, self.scope(since))}
        return self._cov[key]

    def _coverage(self, scheme: str, since: str) -> list[dict]:
        """Per body, over the affairs begun since `since` (QS_SCOPE_SINCE, default 2025-01-01: the export's slice):
        affairs, scored (a current row in `scheme`), scored share, title-only share (scored affairs without text beyond
        the title), by year [affairs, scored], and covered_from = the first year of OPD's data for that parliament."""
        rows = self.all(
            "SELECT a.body_key, MIN(a.parl) AS parl, MIN(a.parl_fr) AS parl_fr, MIN(a.level) AS level, "
            "SUBSTR(a.date, 1, 4) AS year, COUNT(*) AS n, COUNT(s.affair_id) AS scored, "
            "SUM(CASE WHEN s.affair_id IS NOT NULL AND NOT " + ("a.has_text" if self.pg else "(a.has_text = 1)") +
            " THEN 1 ELSE 0 END) AS title_only "
            "FROM qs_affairs a LEFT JOIN (SELECT DISTINCT affair_id FROM topics WHERE valid_to IS NULL AND scheme = ?) s "
            "ON s.affair_id = a.id WHERE a.date >= ? GROUP BY a.body_key, SUBSTR(a.date, 1, 4)", (scheme, since))
        B = {b["key"]: b for b in self.all("SELECT * FROM qs_bodies")}
        by: dict[str, dict] = {}
        for r in rows:
            b0 = B.get(r["body_key"]) or {}
            b = by.setdefault(r["body_key"], dict(body_key=r["body_key"], parl=b0.get("name_de") or r["parl"],
                                                  parl_fr=b0.get("name_fr") or r["parl_fr"], level=b0.get("level") or r["level"],
                                                  affairs=0, scored=0, title_only=0, by_year={}, covered_from=b0.get("covered_from")))
            b["affairs"] += r["n"]; b["scored"] += r["scored"]; b["title_only"] += r["title_only"] or 0
            if r["year"]:
                b["by_year"][r["year"]] = [r["n"], r["scored"]]
        out = []
        for b in by.values():
            out.append(dict(body_key=b["body_key"], parl=b["parl"], parl_fr=b["parl_fr"], level=b["level"],
                            affairs=b["affairs"], scored=b["scored"],
                            scored_share=round(b["scored"] / b["affairs"], 4) if b["affairs"] else None,
                            title_only_share=round(b["title_only"] / b["scored"], 4) if b["scored"] else None,
                            covered_from=b["covered_from"], by_year=dict(sorted(b["by_year"].items()))))
        return sorted(out, key=lambda x: (-x["affairs"], x["body_key"] or ""))

    def unscored(self, since: str | None = None, scheme: str = "aps") -> int:
        """Affairs in scope (begin date ≥ QS_SCOPE_SINCE) whose current input has no current machine row in `scheme`:
        the whole backlog, including what the corpus run has not reached yet. Affairs without an input hash (loaded from
        the static export) are not counted."""
        since = self.scope(since)
        r = self.one("SELECT COUNT(*) AS n FROM qs_affairs a WHERE a.date >= ? AND a.input_hash IS NOT NULL AND NOT EXISTS (SELECT 1 FROM topics t "
                     "WHERE t.affair_id = a.id AND t.scheme = ? AND t.valid_to IS NULL AND t.provenance = 'inferred' "
                     "AND (t.input_hash = a.input_hash OR t.input_hash IS NULL))", (since, scheme))
        return int(r["n"])

    # ------------------------------------------------------------------ the nightly's queue
    def pending(self) -> int:
        """The nightly's queue: affairs new or changed since the previous nightly and not yet scored."""
        return int(self.one("SELECT COUNT(*) AS n FROM qs_queue")["n"])

    def queue_add(self, items: list[tuple[int, str, str]]) -> int:
        """(affair id, input hash, reason) → queue (upsert: a changed affair keeps one entry with its newest hash)."""
        t = self._ts(now())
        sql = ("INSERT INTO qs_queue (affair_id, input_hash, reason, queued_at) VALUES (?, ?, ?, ?) "
               "ON CONFLICT (affair_id) DO UPDATE SET input_hash = excluded.input_hash, reason = excluded.reason")
        if items:
            self.ex(sql, [(a, h, r, t) for a, h, r in items], many=True)
        self.commit()
        return len(items)

    def queue(self) -> dict[int, str]:
        return {r["affair_id"]: r["input_hash"] for r in self.all("SELECT affair_id, input_hash FROM qs_queue")}

    def queue_drain(self, scheme: str = "aps") -> int:
        """Remove the queued affairs that now carry a current machine row for their queued input; returns how many."""
        done = [r["affair_id"] for r in self.all(
            "SELECT q.affair_id FROM qs_queue q WHERE EXISTS (SELECT 1 FROM topics t WHERE t.affair_id = q.affair_id "
            "AND t.scheme = ? AND t.valid_to IS NULL AND t.provenance = 'inferred' AND t.input_hash = q.input_hash)", (scheme,))]
        if done:
            self.ex("DELETE FROM qs_queue WHERE affair_id = ?", [(a,) for a in done], many=True)
        self.commit()
        return len(done)

    def log_run(self, kind: str, affairs: int | None = None, rows: int | None = None, wall_s: float | None = None,
                usd: float | None = None, pending: int | None = None, build: str | None = None, note: str | None = None):
        self.ex("INSERT INTO qs_runs (ts, kind, affairs, rows, wall_s, usd, pending, build, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (self._ts(now()), kind, affairs, rows, wall_s, usd, pending, build, note))
        self.commit()

    def runs(self, kind: str | None = None, limit: int = 20) -> list[dict]:
        q, a = "SELECT * FROM qs_runs", []
        if kind:
            q += " WHERE kind = ?"; a.append(kind)
        return [self._out(r) for r in self.all(q + " ORDER BY id DESC LIMIT ?", a + [limit])]

    def metrics(self) -> dict:
        c = self.one("SELECT COUNT(*) AS rows, COUNT(DISTINCT affair_id) AS affairs_with_rows, "
                     "SUM(CASE WHEN provenance = 'confirmed' THEN 1 ELSE 0 END) AS decisions FROM topics WHERE valid_to IS NULL")
        n_all = self.one("SELECT COUNT(*) AS n FROM qs_affairs")["n"]
        n_aff = self.one("SELECT COUNT(*) AS n FROM qs_affairs WHERE date >= ?", (self.scope(),))["n"]
        n_sc = self.one("SELECT COUNT(DISTINCT t.affair_id) AS n FROM topics t JOIN qs_affairs a ON a.id = t.affair_id "
                        "WHERE t.valid_to IS NULL AND t.scheme = 'aps' AND a.date >= ?", (self.scope(),))["n"]
        tot = self.one("SELECT COUNT(*) AS n FROM topics")["n"]
        last = self.runs("delta", 1) or self.runs(None, 1)
        builds = [r["build"] for r in self.all("SELECT DISTINCT build FROM topics WHERE valid_to IS NULL AND build IS NOT NULL")]
        lr = last[0] if last else {}
        seq = self.one("SELECT COALESCE(MAX(seq), 0) AS m FROM topics")["m"]
        return dict(affairs=n_aff, scope_since=self.scope(), affairs_aps_scored=n_sc, affairs_loaded=n_all,
                    affairs_with_rows=c["affairs_with_rows"] or 0, rows=c["rows"] or 0, rows_all_versions=tot, seq=seq,
                    decisions=c["decisions"] or 0, pending=self.pending(), unscored_in_scope=self.unscored(), builds=builds,
                    store=self.kind,
                    last_run=dict(kind=lr.get("kind"), ts=lr.get("ts"), affairs=lr.get("affairs"), wall_s=lr.get("wall_s"),
                                  usd=lr.get("usd"), pending=lr.get("pending"), note=lr.get("note")) if lr else None)


def metrics_line(m: dict) -> str:
    """The one-line /metrics summary printed by the nightly job."""
    lr = m.get("last_run") or {}
    usd = lr.get("usd")
    return (f"affairs {lr.get('affairs') if lr.get('affairs') is not None else '-'} · wall "
            f"{(str(round(lr['wall_s'])) + ' s') if lr.get('wall_s') is not None else '-'} · list-price USD "
            f"{f'{usd:.4f}' if usd is not None else '-'} · pending {m['pending']} · unscored in scope {m.get('unscored_in_scope', '-')} "
            f"· rows {m['rows']} · store {m['store']}")


_STORE: Store | None = None


def get_store() -> Store:
    global _STORE
    if _STORE is None:
        _STORE = Store()
    return _STORE
