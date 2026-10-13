"""The `topics` store: SQLite by default (`QS_DB`, default data/querschnitt.sqlite), Postgres when `QS_PG_DSN` is set
(psycopg 3). DDL: sql/topics.sql (Postgres, proposed upstream) and sql/topics.sqlite.sql.

Versioning (docs/CONTRACT.md §1): a row is never changed except to close it (`valid_to`). Loading topic rows compares
each (affair, scheme, level, rank) with the latest machine row for that key; identical content is skipped, changed
content closes the current row and adds a new one, and keys that disappear from a re-scored affair are closed. An
editor's confirm or reject adds a `provenance = confirmed` row with who and when and closes the machine row it decides;
the machine row stays in the history, and a later identical reload does not bring it back."""
from __future__ import annotations

import datetime as dt
import gzip
import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Iterable, Iterator

ROOT = Path(__file__).resolve().parents[2]
SQL = ROOT / "sql"
COLS = ["affair_id", "body_key", "scheme", "level", "code", "rank", "p", "p_raw", "lane", "status", "provenance",
        "evidence", "model", "build", "cutoffs_id", "prompt_id", "input_hash", "valid_from", "valid_to", "confirmed_by",
        "confirmed_at", "version"]
CONTENT = ["body_key", "code", "p", "p_raw", "lane", "evidence", "model", "build", "cutoffs_id", "prompt_id",
           "input_hash", "version"]                      # a change in any of these is a new version
AFF_COLS = ["id", "body_key", "level", "canton", "parl", "parl_fr", "lang", "date", "number", "title", "title_long",
            "type", "type_h", "state", "url", "submitter", "party", "submitter_type", "has_text", "text_src",
            "input_hash", "updated"]
TS_COLS = ("valid_from", "valid_to", "confirmed_at", "ts")


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
            if self.pg:
                self.conn.commit()          # end the read transaction (no idle-in-transaction connections)
            return out

    def one(self, sql: str, params=()) -> dict | None:
        r = self.all(sql, params)
        return r[0] if r else None

    def commit(self):
        with self.lock:
            self.conn.commit()

    def init(self):
        ddl = (SQL / ("topics.sql" if self.pg else "topics.sqlite.sql")).read_text()
        with self.lock:
            if self.pg:
                self.conn.execute(ddl)
            else:
                self.conn.executescript(ddl)
            self.conn.commit()

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
        if isinstance(r.get("evidence"), str):
            try:
                r["evidence"] = json.loads(r["evidence"])
            except ValueError:
                pass
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
        return tuple(r.get(c) for c in COLS)

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
        ids = list(groups)
        latest: dict[tuple, dict] = {}
        current: dict[tuple, list[int]] = {}
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
        close, ins = [], []
        for a in order:
            keys = set()
            for r in groups[a]:
                r.setdefault("rank", 1)
                k = (a, r["scheme"], int(r["level"]), int(r["rank"]))
                keys.add(k)
                old = latest.get(k)
                if old is not None and sig(old) == sig(r):
                    st["unchanged"] += 1
                    continue
                close += current.get(k, [])
                r = dict(r, provenance="inferred", valid_from=None, valid_to=None)
                ins.append(self._ins_row(r, t))
            if a not in seen:                                   # keys of re-scored schemes that vanished
                schemes = {k[1] for k in keys}
                for k, rids in current.items():
                    if k[0] == a and k[1] in schemes and k not in keys:
                        close += rids
            st["affairs"] += 1
        if close:
            self.ex("UPDATE topics SET valid_to = ? WHERE row_id = ? AND valid_to IS NULL",
                    [(self._ts(t), rid) for rid in close], many=True)
            st["closed"] += len(close)
        if ins:
            self.ex(self._insert_sql(), ins, many=True)
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
        return n

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
        sql = (f"INSERT INTO qs_affairs ({', '.join(AFF_COLS)}) VALUES ({', '.join('?' * len(AFF_COLS))}) "
               "ON CONFLICT (id) DO UPDATE SET " + ", ".join(f"{c} = excluded.{c}" for c in AFF_COLS[1:]))
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
        return len(buf)

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

    def changes(self, since: str, scheme: str | None = None, limit: int = 1000, offset: int = 0) -> list[dict]:
        t = self._ts(parse_ts(since))
        q, a = "SELECT * FROM topics WHERE (valid_from > ? OR valid_to > ?)", [t, t]
        if scheme:
            q += " AND scheme = ?"; a.append(scheme)
        q += " ORDER BY row_id LIMIT ? OFFSET ?"
        return [self._out(r) for r in self.all(q, a + [int(limit), int(offset)])]

    def schemes(self) -> list[str]:
        return [r["scheme"] for r in self.all("SELECT DISTINCT scheme FROM topics WHERE valid_to IS NULL ORDER BY scheme")]

    # ------------------------------------------------------------------ editor decisions
    def decide(self, aid: int, scheme: str, code: str, action: str, by: str, level: int | None = None) -> dict:
        """confirm | reject one code for one affair. Adds a `provenance = confirmed` row (status confirmed / rejected,
        confirmed_by, confirmed_at; p, evidence, build and prompt copied from the machine row it decides) and closes
        what it decides: a confirm closes every current row of that scheme at that level (the ranked machine suggestions
        and any earlier decision); a reject closes the current rows with that code. Returns the new row."""
        assert action in ("confirm", "reject")
        by = (by or "").strip()
        if not by:
            raise ValueError("`by` is required")
        cur = self.topics_for(aid, scheme)
        same = [r for r in cur if r["code"] == code]
        if level is None:
            level = same[0]["level"] if same else (2 if ":kw:" in code else 1)
        src = min(same, key=lambda r: (r["provenance"] != "inferred", r["rank"]), default=None)
        close = [r for r in cur if r["level"] == level] if action == "confirm" else same
        t = now()
        body = (src or {}).get("body_key") or (self.affair(aid) or {}).get("body_key")
        row = dict(affair_id=aid, body_key=body, scheme=scheme, level=level, code=code, rank=1,
                   p=(src or {}).get("p"), p_raw=(src or {}).get("p_raw"), lane=(src or {}).get("lane"),
                   status="confirmed" if action == "confirm" else "rejected", provenance="confirmed",
                   evidence=(src or {}).get("evidence"), model=(src or {}).get("model"), build=(src or {}).get("build"),
                   cutoffs_id=(src or {}).get("cutoffs_id"), prompt_id=(src or {}).get("prompt_id"),
                   input_hash=(src or {}).get("input_hash"), valid_from=t, valid_to=None, confirmed_by=by[:200],
                   confirmed_at=t, version=(src or {}).get("version"))
        with self.lock:
            if close:
                self.ex("UPDATE topics SET valid_to = ? WHERE row_id = ? AND valid_to IS NULL",
                        [(self._ts(t), r["row_id"]) for r in close], many=True)
            cur_ = self.ex(self._insert_sql() + (" RETURNING row_id" if self.pg else ""), self._ins_row(row, t))
            rid = cur_.fetchone()[0] if self.pg else cur_.lastrowid
            self.commit()
        return self._out(self.one("SELECT * FROM topics WHERE row_id = ?", (rid,)))

    # ------------------------------------------------------------------ coverage, metrics, runs
    def coverage(self, scheme: str = "aps", full_share: float = 0.9) -> list[dict]:
        """Per body: affairs, scored (a current row in `scheme`), scored share, title-only share (scored affairs without
        text beyond the title), covered_from = the first year from which every later year has scored share ≥ 0.9."""
        rows = self.all(
            "SELECT a.body_key, MIN(a.parl) AS parl, MIN(a.parl_fr) AS parl_fr, MIN(a.level) AS level, "
            "SUBSTR(a.date, 1, 4) AS year, COUNT(*) AS n, COUNT(s.affair_id) AS scored, "
            "SUM(CASE WHEN s.affair_id IS NOT NULL AND NOT " + ("a.has_text" if self.pg else "(a.has_text = 1)") +
            " THEN 1 ELSE 0 END) AS title_only "
            "FROM qs_affairs a LEFT JOIN (SELECT DISTINCT affair_id FROM topics WHERE valid_to IS NULL AND scheme = ?) s "
            "ON s.affair_id = a.id GROUP BY a.body_key, SUBSTR(a.date, 1, 4)", (scheme,))
        by: dict[str, dict] = {}
        for r in rows:
            b = by.setdefault(r["body_key"], dict(body_key=r["body_key"], parl=r["parl"], parl_fr=r["parl_fr"],
                                                  level=r["level"], affairs=0, scored=0, title_only=0, years={}))
            b["affairs"] += r["n"]; b["scored"] += r["scored"]; b["title_only"] += r["title_only"] or 0
            if r["year"]:
                b["years"][r["year"]] = (r["n"], r["scored"])
        out = []
        for b in by.values():
            cf = None
            for y in sorted(b["years"], reverse=True):
                n, s = b["years"][y]
                if n and s / n >= full_share:
                    cf = int(y)
                else:
                    break
            out.append(dict(body_key=b["body_key"], parl=b["parl"], parl_fr=b["parl_fr"], level=b["level"],
                            affairs=b["affairs"], scored=b["scored"],
                            scored_share=round(b["scored"] / b["affairs"], 4) if b["affairs"] else None,
                            title_only_share=round(b["title_only"] / b["scored"], 4) if b["scored"] else None,
                            covered_from=cf))
        return sorted(out, key=lambda x: (-x["affairs"], x["body_key"] or ""))

    def pending(self, since: str | None = None, scheme: str = "aps") -> int:
        """Affairs in scope (begin date ≥ QS_SCOPE_SINCE, default 2025-01-01) whose current input has no current
        machine row in `scheme`: new or changed affairs waiting for the batch."""
        since = since or os.environ.get("QS_SCOPE_SINCE", "2025-01-01")
        r = self.one("SELECT COUNT(*) AS n FROM qs_affairs a WHERE a.date >= ? AND a.input_hash IS NOT NULL AND NOT EXISTS (SELECT 1 FROM topics t "
                     "WHERE t.affair_id = a.id AND t.scheme = ? AND t.valid_to IS NULL AND t.provenance = 'inferred' "
                     "AND (t.input_hash = a.input_hash OR t.input_hash IS NULL))", (since, scheme))
        return int(r["n"])

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
        n_aff = self.one("SELECT COUNT(*) AS n FROM qs_affairs")["n"]
        tot = self.one("SELECT COUNT(*) AS n FROM topics")["n"]
        last = self.runs("delta", 1) or self.runs(None, 1)
        builds = [r["build"] for r in self.all("SELECT DISTINCT build FROM topics WHERE valid_to IS NULL AND build IS NOT NULL")]
        lr = last[0] if last else {}
        return dict(affairs=n_aff, affairs_scored=c["affairs_with_rows"] or 0, rows=c["rows"] or 0, rows_all_versions=tot,
                    decisions=c["decisions"] or 0, pending=self.pending(), builds=builds, store=self.kind,
                    last_run=dict(kind=lr.get("kind"), ts=lr.get("ts"), affairs=lr.get("affairs"), wall_s=lr.get("wall_s"),
                                  usd=lr.get("usd"), pending=lr.get("pending"), note=lr.get("note")) if lr else None)


def metrics_line(m: dict) -> str:
    """The one-line /metrics summary printed by the nightly job."""
    lr = m.get("last_run") or {}
    usd = lr.get("usd")
    return (f"affairs {lr.get('affairs') if lr.get('affairs') is not None else '-'} · wall "
            f"{(str(round(lr['wall_s'])) + ' s') if lr.get('wall_s') is not None else '-'} · list-price USD "
            f"{f'{usd:.4f}' if usd is not None else '-'} · pending {m['pending']} · rows {m['rows']} · store {m['store']}")


_STORE: Store | None = None


def get_store() -> Store:
    global _STORE
    if _STORE is None:
        _STORE = Store()
    return _STORE
