"""Read endpoints of topics.md as a drop-in FastAPI router: plain SQL with psycopg 3 against the tables of migrations
0001-0003. No ORM, no other dependency than FastAPI, Pydantic v2 (models.py) and psycopg 3.

    from router import router, get_conn          # or `from .router import ...` inside a package
    app.include_router(router)                    # paths under /v1, as in topics.md
    app.dependency_overrides[get_conn] = opd_db   # OPD's own connection or pool; default: OPD_DSN, one connection a request

Rules every endpoint applies (topics.md, MERGE_REQUEST.md "Who owns a row"):
- Feed switch (migration 0003): when `topic_feed_bodies` exists, a row is shown only if its body and scheme are switched on,
  machine rows (`inferred`) by `inferred_public`, published decisions (`confirmed`) by `decisions_public`; the same
  condition as the view `topics_public`, applied to closed rows too (history). Without 0003 every body is shown. The check
  is made on each request, so applying or rolling back 0003 needs no restart.
- APS subtopics (`scheme_key = 'aps' AND level = 2`) are left out of rows, counts and codes while
  APS_SUBTOPICS_PUBLIC is False (until APS agrees).
- Defaults: current rows (`valid_to IS NULL`), `rank=1`, `status=suggested,confirmed`.

`GET /v1/affairs/?expand=topics` and `GET /v1/affairs/?topic=` belong to OPD's affairs endpoint; topics_for_affairs()
and affairs_topic_filter() below are what that endpoint calls. `fields`, `hide_null`, `exclude_null` and
`output_format` are left to OPD's shared response layer, as for its other resources."""
from __future__ import annotations

import datetime as dt
import inspect
import os
from typing import Any, Iterator, Literal, Optional
from urllib.parse import urlencode

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from psycopg import sql
from psycopg.rows import dict_row

try:
    from .models import (Meta, Topic, TopicBodyCountList, TopicCodeCountList, TopicCodeList, TopicList, TopicScheme,
                         TopicSchemeList)
except ImportError:  # imported as a top-level module (tests, or copied next to OPD's app)
    from models import (Meta, Topic, TopicBodyCountList, TopicCodeCountList, TopicCodeList, TopicList, TopicScheme,
                        TopicSchemeList)

APS_SUBTOPICS_PUBLIC = False     # True once APS agrees to publish subtopic rows and labels (MERGE_REQUEST.md, questions)
LIMIT_DEFAULT, LIMIT_MAX = 100, 1000
AFFAIRS_LANG, AFFAIRS_BEGIN = "language", "begin_date"   # OPD's affairs columns behind affair_lang and date_from/date_to
LANGS = ("de", "fr", "it", "rm")

Lang = Literal["de", "fr", "it", "rm"]
LangFormat = Literal["nested", "flat"]

# the columns of `topics` the API exposes (content_hash is the loader's); sort_by accepts any of them
TOPIC_COLUMNS = ("id", "affair_id", "body_id", "body_key", "scheme_id", "scheme_key", "level", "code", "parent_code", "rank",
                 "label_de", "label_fr", "label_it", "label_rm", "p", "p_raw", "lane", "status", "provenance",
                 "evidence_field", "evidence_text_id", "evidence_doc_id", "evidence_char_start", "evidence_char_end",
                 "evidence_quote", "model", "model_build", "cutoffs_id", "prompt_id", "input_hash", "engine_version",
                 "valid_from", "valid_to", "confirmed_by", "confirmed_by_body_id", "confirmed_at", "created_at", "updated_at")
SCHEME_COLUMNS = ("id", "scheme_key", "version", "type", "levels", "name_de", "name_fr", "name_it", "name_rm", "name_en",
                  "question_de", "question_fr", "question_it", "body_id", "body_key", "licence", "source_name", "source_url",
                  "notes", "code_count", "active", "created_at", "updated_at")
CODE_COLUMNS = ("id", "scheme_id", "scheme_key", "code", "level", "parent_code", "position", "external_id",
                "label_de", "label_fr", "label_it", "label_rm")
GENERATED_BY = ("model", "model_build", "cutoffs_id", "prompt_id", "input_hash", "engine_version")

router = APIRouter(prefix="/v1", tags=["topics"])


def get_conn() -> Iterator[psycopg.Connection]:
    """One read connection per request from OPD_DSN. OPD replaces this with its own pool via app.dependency_overrides."""
    dsn = os.environ.get("OPD_DSN")
    if not dsn:
        raise RuntimeError("set OPD_DSN, or override router.get_conn with OPD's connection dependency")
    with psycopg.connect(dsn, autocommit=True) as conn:
        yield conn


# ---------------------------------------------------------------------------------------------------------------- rules

def public_rows(conn: psycopg.Connection, *, current: bool) -> tuple[sql.Composable, list[sql.Composable]]:
    """FROM clause and WHERE conditions of the public feed over `topics t`: the feed switch of 0003 when applied, the APS
    subtopic hold-back, and current rows unless `current` is False (history)."""
    switch = conn.execute("SELECT to_regclass('topic_feed_bodies') IS NOT NULL").fetchone()[0]
    src = sql.SQL("topics t")
    if switch:
        src = sql.SQL("topics t JOIN topic_feed_bodies f ON f.body_id = t.body_id AND f.scheme_key = t.scheme_key AND "
                      "((t.provenance = 'inferred' AND f.inferred_public) OR (t.provenance = 'confirmed' AND f.decisions_public))")
    where = []
    if not APS_SUBTOPICS_PUBLIC:
        where.append(sql.SQL("NOT (t.scheme_key = 'aps' AND t.level = 2)"))
    if current:
        where.append(sql.SQL("t.valid_to IS NULL"))
    return src, where


def _codes_hidden() -> sql.Composable:
    return sql.SQL("TRUE") if APS_SUBTOPICS_PUBLIC else sql.SQL("NOT (c.scheme_key = 'aps' AND c.level = 2)")


# -------------------------------------------------------------------------------------------------------------- helpers

def _split(v: Optional[str]) -> list[str]:
    return [x.strip() for x in (v or "").split(",") if x.strip()]


def _ints(name: str, v: Optional[str]) -> list[int]:
    try:
        return [int(x) for x in _split(v)]
    except ValueError:
        raise HTTPException(422, f"{name}: comma-separated integers expected, got {v!r}")


def _enum(name: str, v: Optional[str], allowed: tuple[str, ...]) -> list[str]:
    out = _split(v)
    bad = [x for x in out if x not in allowed]
    if bad:
        raise HTTPException(422, f"{name}: {', '.join(bad)} not in {', '.join(allowed)}")
    return out


def _utc(t: dt.datetime) -> dt.datetime:
    """Timestamps in the tables are UTC without zone; an aware parameter is converted."""
    return t.astimezone(dt.timezone.utc).replace(tzinfo=None) if t.tzinfo else t


def _order(sort_by: Optional[str], allowed: tuple[str, ...], default: str, prefix: str = "t.") -> sql.Composable:
    """sort_by as on OPD's other resources: comma-separated columns, '-' = descending; id last for a stable page order."""
    parts, cols = [], []
    for s in _split(sort_by or default):
        col, desc = (s[1:], True) if s.startswith("-") else (s, False)
        if col not in allowed:
            raise HTTPException(422, f"sort_by: unknown column {col!r}")
        cols.append(col)
        ident = sql.Identifier(col) if not prefix else sql.SQL(prefix) + sql.Identifier(col)
        parts.append(ident + sql.SQL(" DESC NULLS LAST" if desc else " ASC NULLS LAST"))
    if "id" in allowed and "id" not in cols:
        parts.append((sql.SQL(prefix) if prefix else sql.SQL("")) + sql.SQL("id ASC"))
    return sql.SQL(", ").join(parts)


def _labels(row: dict, stem: str, lang: Optional[str], fmt: str, fallback: list[str]):
    """nested: {de, fr, it, rm}; flat: the `lang` label (default de), else the first of `lang_fallback` that is set."""
    vals = {k: row.get(f"{stem}_{k}") for k in LANGS}
    if fmt == "nested":
        return vals
    for k in [lang or "de", *fallback]:
        if vals.get(k) is not None:
            return vals[k]
    return None


def _meta(request: Request, offset: int, limit: int, total: int) -> Meta:
    """OPD's pagination block; links keep the request's other parameters."""
    pages = -(-total // limit)
    last = max(pages - 1, 0) * limit
    keep = [(k, v) for k, v in request.query_params.multi_items() if k not in ("offset", "limit")]

    def url(off: int) -> str:
        return str(request.url.replace(query=urlencode(keep + [("offset", off), ("limit", limit)], safe=",:/")))

    has_more = offset + limit < total
    return Meta(offset=offset, limit=limit, total_records=total, total_pages=pages, current_page=offset // limit + 1,
                has_more=has_more, next_page=url(offset + limit) if has_more else None,
                prev_page=url(max(offset - limit, 0)) if offset > 0 else None,
                first_page=url(0), last_page=url(last), self=url(offset))


class Paging:
    def __init__(self, offset: int = Query(0, ge=0), limit: int = Query(LIMIT_DEFAULT, ge=1, le=LIMIT_MAX)):
        self.offset, self.limit = offset, limit


class Language:
    def __init__(self, lang: Optional[Lang] = Query(None, description="language of the label with lang_format=flat"),
                 lang_format: LangFormat = Query("nested"),
                 lang_fallback: Optional[str] = Query(None, description="flat: languages tried in order when `lang` is empty")):
        self.lang, self.fmt = lang, lang_format
        self.fallback = _enum("lang_fallback", lang_fallback, LANGS)

    def __call__(self, row: dict, stem: str = "label"):
        return _labels(row, stem, self.lang, self.fmt, self.fallback)


def _topic(row: dict, lg: Language) -> dict:
    ev = None
    if row["evidence_field"] is not None:
        ev = dict(field=row["evidence_field"], text_id=row["evidence_text_id"], doc_id=row["evidence_doc_id"],
                  char_start=row["evidence_char_start"], char_end=row["evidence_char_end"], quote=row["evidence_quote"])
    gen = {k: row[k] for k in GENERATED_BY}
    out = {k: row[k] for k in TOPIC_COLUMNS if not k.startswith(("label_", "evidence_")) and k not in GENERATED_BY}
    out.update(label=lg(row), evidence=ev, generated_by=gen if any(v is not None for v in gen.values()) else None)
    for k in ("p", "p_raw"):   # real -> the stored decimal (0.3776, not 0.37759998...)
        out[k] = float(row[k]) if row[k] is not None else None
    return out


_SELECT_TOPIC = sql.SQL(", ").join(
    sql.SQL("t.{c}::text AS {c}").format(c=sql.Identifier(c)) if c in ("p", "p_raw") else sql.SQL("t.") + sql.Identifier(c)
    for c in TOPIC_COLUMNS)


# -------------------------------------------------------------------------------------------------------------- filters

class TopicFilters:
    """The filters of topics.md, "Filters on /v1/topics/". Shared by the list, the group_by endpoints and the relation."""

    def __init__(self,
                 scheme: Optional[str] = Query(None, description="scheme_key; comma-separated"),
                 code: Optional[str] = Query(None, description="code, or the short form without the scheme prefix when "
                                                               "scheme is set; with level=2 and a chapter: its subtopics"),
                 level: Optional[str] = Query(None, description="1 = chapter or yes/no, 2 = subtopic"),
                 rank: str = Query("1", description="default 1 (the label); 1,2,3 adds the ranked suggestions"),
                 body: Optional[str] = Query(None, description="body_key; comma-separated (same as body_key)"),
                 body_key: Optional[str] = Query(None),
                 affair_ids: Optional[str] = Query(None, alias="affair_id", description="comma-separated"),
                 status: str = Query("suggested,confirmed"),
                 provenance: Optional[str] = Query(None, description="inferred = machine suggestion, confirmed = decision"),
                 lane: Optional[str] = Query(None),
                 p_min: Optional[float] = Query(None, ge=0, le=1),
                 since: Optional[dt.datetime] = Query(None, description="rows opened or closed after this time (UTC)"),
                 current: bool = Query(True, description="false includes closed versions (history)"),
                 affair_lang: Optional[str] = Query(None, description="language of the affair; comma-separated"),
                 date_from: Optional[dt.date] = Query(None, description="affair begin_date at least"),
                 date_to: Optional[dt.date] = Query(None, description="affair begin_date at most")):
        self.scheme = _split(scheme)
        self.code = _split(code)
        self.level = _ints("level", level)
        self.rank = _ints("rank", rank)
        self.body = _split(body) + _split(body_key)
        self.affair_id = _ints("affair_id", affair_ids)
        self.status = _enum("status", status, ("suggested", "confirmed", "rejected"))
        self.provenance = _enum("provenance", provenance, ("inferred", "confirmed"))
        self.lane = _enum("lane", lane, ("pass", "please_check", "readings_agree"))
        self.p_min, self.since, self.current = p_min, since, current
        self.affair_lang = _split(affair_lang)
        self.date_from, self.date_to = date_from, date_to

    def where(self, conn: psycopg.Connection) -> tuple[sql.Composable, sql.Composable, dict[str, Any]]:
        """-> (FROM, WHERE, params) over `topics t` for the public rows these filters select."""
        src, conds = public_rows(conn, current=self.current)
        params: dict[str, Any] = {}

        def add(cond: str, **kw):
            conds.append(sql.SQL(cond))
            params.update(kw)

        if self.scheme:
            add("t.scheme_key = ANY(%(scheme)s)", scheme=self.scheme)
        if self.code:
            codes = list(self.code)
            if self.scheme:   # short form: the part after the scheme's prefix (aps:1.7.2. <- 1.7.2.; bs:… <- …)
                codes += [r[0] for r in conn.execute(
                    "SELECT DISTINCT code FROM topic_codes WHERE scheme_key = ANY(%s) "
                    "AND substr(code, strpos(code, ':') + 1) = ANY(%s)", (self.scheme, self.code))]
            if self.level == [2]:
                add("(t.code = ANY(%(code)s) OR t.parent_code = ANY(%(code)s))", code=codes)
            else:
                add("t.code = ANY(%(code)s)", code=codes)
        if self.level:
            add("t.level = ANY(%(level)s)", level=self.level)
        if self.rank:
            add("t.rank = ANY(%(rank)s)", rank=self.rank)
        if self.body:
            add("t.body_key = ANY(%(body)s)", body=self.body)
        if self.affair_id:
            add("t.affair_id = ANY(%(affair_id)s)", affair_id=self.affair_id)
        if self.status:
            add("t.status = ANY(%(status)s)", status=self.status)
        if self.provenance:
            add("t.provenance = ANY(%(provenance)s)", provenance=self.provenance)
        if self.lane:
            add("t.lane = ANY(%(lane)s)", lane=self.lane)
        if self.p_min is not None:
            add("t.p >= %(p_min)s", p_min=self.p_min)
        if self.since is not None:
            add("t.updated_at > %(since)s", since=_utc(self.since))
        if self.affair_lang or self.date_from or self.date_to:
            src = src + sql.SQL(" JOIN affairs a ON a.id = t.affair_id")
            if self.affair_lang:
                conds.append(sql.SQL("a.{} = ANY(%(affair_lang)s)").format(sql.Identifier(AFFAIRS_LANG)))
                params["affair_lang"] = self.affair_lang
            if self.date_from:
                conds.append(sql.SQL("a.{} >= %(date_from)s").format(sql.Identifier(AFFAIRS_BEGIN)))
                params["date_from"] = self.date_from
            if self.date_to:   # the whole day
                conds.append(sql.SQL("a.{} < %(date_to)s").format(sql.Identifier(AFFAIRS_BEGIN)))
                params["date_to"] = self.date_to + dt.timedelta(days=1)
        return src, sql.SQL(" AND ").join(conds or [sql.SQL("TRUE")]), params


class AffairTopicFilters(TopicFilters):
    """The same filters on the relation endpoint, without `affair_id` (the path) and `current` (`history` instead)."""


def _relation_init(self, **kw):
    TopicFilters.__init__(self, affair_ids=None, current=True, **kw)


_sig = inspect.signature(TopicFilters.__init__, eval_str=True)
_relation_init.__signature__ = _sig.replace(parameters=[p for p in _sig.parameters.values() if p.name not in ("affair_ids", "current")])
AffairTopicFilters.__init__ = _relation_init


def _topic_page(conn, request: Request, f: TopicFilters, pg: Paging, lg: Language, sort_by: Optional[str]) -> dict:
    src, where, params = f.where(conn)
    with conn.cursor(row_factory=dict_row) as cur:
        total = cur.execute(sql.SQL("SELECT count(*) AS n FROM {} WHERE {}").format(src, where), params).fetchone()["n"]
        rows = cur.execute(sql.SQL("SELECT {} FROM {} WHERE {} ORDER BY {} LIMIT %(_limit)s OFFSET %(_offset)s").format(
            _SELECT_TOPIC, src, where, _order(sort_by, TOPIC_COLUMNS, "-valid_from")),
            {**params, "_limit": pg.limit, "_offset": pg.offset}).fetchall()
    return dict(data=[_topic(r, lg) for r in rows], meta=_meta(request, pg.offset, pg.limit, total))


# ------------------------------------------------------------------------------------------------------------ endpoints

@router.get("/topics/", response_model=TopicList)
def list_topics(request: Request, f: TopicFilters = Depends(), pg: Paging = Depends(), lg: Language = Depends(),
                sort_by: Optional[str] = Query(None, description="any column, '-' = descending; default -valid_from"),
                conn: psycopg.Connection = Depends(get_conn)):
    return _topic_page(conn, request, f, pg, lg, sort_by)


def _group_by(conn, request: Request, f: TopicFilters, pg: Paging, sort_by: Optional[str], keys: list[str],
              extra: list[str], default_sort: str) -> tuple[list[dict], Meta]:
    src, where, params = f.where(conn)
    cols = keys + ["count", "affair_count"]
    grouped = sql.SQL("SELECT {k}, {x} count(*) AS count, count(DISTINCT t.affair_id) AS affair_count FROM {src} "
                      "WHERE {w} GROUP BY {k}").format(
        k=sql.SQL(", ").join(sql.SQL("t.") + sql.Identifier(k) for k in keys),
        x=sql.SQL("").join(sql.SQL(e + ", ") for e in extra), src=src, w=where)
    with conn.cursor(row_factory=dict_row) as cur:
        total = cur.execute(sql.SQL("SELECT count(*) AS n FROM ({}) g").format(grouped), params).fetchone()["n"]
        rows = cur.execute(sql.SQL("SELECT * FROM ({}) g ORDER BY {} LIMIT %(_limit)s OFFSET %(_offset)s").format(
            grouped, _order(sort_by, tuple(cols), default_sort, prefix="")), {**params, "_limit": pg.limit, "_offset": pg.offset}).fetchall()
    return rows, _meta(request, pg.offset, pg.limit, total)


@router.get("/topics/group_by/code", response_model=TopicCodeCountList)
def topics_by_code(request: Request, f: TopicFilters = Depends(), pg: Paging = Depends(), lg: Language = Depends(),
                   sort_by: Optional[str] = Query(None, description="scheme_key, code, level, count, affair_count; default -count"),
                   conn: psycopg.Connection = Depends(get_conn)):
    """Counts per code for the filters given; `count` = rows, `affair_count` = distinct affairs."""
    rows, meta = _group_by(conn, request, f, pg, sort_by, ["scheme_key", "code", "level"],
                           [f"min(t.label_{k}) AS label_{k}" for k in LANGS], "-count,scheme_key,code")
    return dict(data=[dict(scheme_key=r["scheme_key"], code=r["code"], level=r["level"], label=lg(r),
                           count=r["count"], affair_count=r["affair_count"]) for r in rows], meta=meta)


@router.get("/topics/group_by/body_key", response_model=TopicBodyCountList)
def topics_by_body(request: Request, f: TopicFilters = Depends(), pg: Paging = Depends(),
                   sort_by: Optional[str] = Query(None, description="body_key, body_id, count, affair_count; default -count"),
                   conn: psycopg.Connection = Depends(get_conn)):
    """Counts per parliament for the filters given; `count` = rows, `affair_count` = distinct affairs."""
    rows, meta = _group_by(conn, request, f, pg, sort_by, ["body_key", "body_id"], [], "-count,body_key")
    return dict(data=[dict(body_key=r["body_key"], body_id=r["body_id"], count=r["count"], affair_count=r["affair_count"])
                      for r in rows], meta=meta)


@router.get("/topics/{topic_id}", response_model=Topic)
def get_topic(topic_id: int, lg: Language = Depends(), conn: psycopg.Connection = Depends(get_conn)):
    """One row by id, current or closed, if the public feed shows its body, scheme and provenance."""
    src, conds = public_rows(conn, current=False)
    with conn.cursor(row_factory=dict_row) as cur:
        row = cur.execute(sql.SQL("SELECT {} FROM {} WHERE {} AND t.id = %s").format(
            _SELECT_TOPIC, src, sql.SQL(" AND ").join(conds or [sql.SQL("TRUE")])), (topic_id,)).fetchone()
    if row is None:
        raise HTTPException(404, f"topic {topic_id} not found")
    return _topic(row, lg)


@router.get("/affairs/{affair_id}/topics", response_model=TopicList)
def affair_topics(affair_id: int, request: Request, f: AffairTopicFilters = Depends(), pg: Paging = Depends(),
                  lg: Language = Depends(), history: bool = Query(False, description="true adds closed rows"),
                  sort_by: Optional[str] = Query(None, description="default scheme_key,level,rank"),
                  conn: psycopg.Connection = Depends(get_conn)):
    """The current rows of one affair (relation endpoint); 404 when the affair does not exist."""
    if conn.execute("SELECT 1 FROM affairs WHERE id = %s", (affair_id,)).fetchone() is None:
        raise HTTPException(404, f"affair {affair_id} not found")
    f.affair_id, f.current = [affair_id], not history
    return _topic_page(conn, request, f, pg, lg, sort_by or "scheme_key,level,rank,-valid_from")


def _scheme(row: dict, lg: Language) -> dict:
    out = {k: row[k] for k in SCHEME_COLUMNS if not k.startswith(("name_", "question_"))}
    out.update(name=lg(row, "name"), question=lg(row, "question"))
    return out


@router.get("/topic_schemes/", response_model=TopicSchemeList)
def list_schemes(request: Request, pg: Paging = Depends(), lg: Language = Depends(),
                 scheme_key: Optional[str] = Query(None, description="comma-separated"),
                 type: Optional[str] = Query(None, description="standard, body, adhoc"),
                 active: Optional[bool] = Query(None, description="true: the versions new rows are written with"),
                 sort_by: Optional[str] = Query(None, description="any column; default id"),
                 conn: psycopg.Connection = Depends(get_conn)):
    """Schemes and their versions, with licence and source."""
    conds, params = [sql.SQL("TRUE")], {}
    if scheme_key:
        conds.append(sql.SQL("s.scheme_key = ANY(%(scheme_key)s)")); params["scheme_key"] = _split(scheme_key)
    if type:
        conds.append(sql.SQL("s.type = ANY(%(type)s)")); params["type"] = _enum("type", type, ("standard", "body", "adhoc"))
    if active is not None:
        conds.append(sql.SQL("s.active = %(active)s")); params["active"] = active
    where = sql.SQL(" AND ").join(conds)
    with conn.cursor(row_factory=dict_row) as cur:
        total = cur.execute(sql.SQL("SELECT count(*) AS n FROM topic_schemes s WHERE {}").format(where), params).fetchone()["n"]
        rows = cur.execute(sql.SQL("SELECT * FROM topic_schemes s WHERE {} ORDER BY {} LIMIT %(_limit)s OFFSET %(_offset)s").format(
            where, _order(sort_by, SCHEME_COLUMNS, "id", prefix="s.")), {**params, "_limit": pg.limit, "_offset": pg.offset}).fetchall()
    return dict(data=[_scheme(r, lg) for r in rows], meta=_meta(request, pg.offset, pg.limit, total))


@router.get("/topic_schemes/{scheme_id}", response_model=TopicScheme)
def get_scheme(scheme_id: int, lg: Language = Depends(), conn: psycopg.Connection = Depends(get_conn)):
    with conn.cursor(row_factory=dict_row) as cur:
        row = cur.execute("SELECT * FROM topic_schemes WHERE id = %s", (scheme_id,)).fetchone()
    if row is None:
        raise HTTPException(404, f"topic scheme {scheme_id} not found")
    return _scheme(row, lg)


@router.get("/topic_schemes/{scheme_id}/codes", response_model=TopicCodeList)
def scheme_codes(scheme_id: int, request: Request, pg: Paging = Depends(), lg: Language = Depends(),
                 level: Optional[str] = Query(None), parent_code: Optional[str] = Query(None, description="comma-separated"),
                 sort_by: Optional[str] = Query(None, description="any column; default position"),
                 conn: psycopg.Connection = Depends(get_conn)):
    """The codes of one scheme version with labels and parent; APS subtopic codes held back (module docstring)."""
    if conn.execute("SELECT 1 FROM topic_schemes WHERE id = %s", (scheme_id,)).fetchone() is None:
        raise HTTPException(404, f"topic scheme {scheme_id} not found")
    conds, params = [sql.SQL("c.scheme_id = %(scheme_id)s"), _codes_hidden()], {"scheme_id": scheme_id}
    if level:
        conds.append(sql.SQL("c.level = ANY(%(level)s)")); params["level"] = _ints("level", level)
    if parent_code:
        conds.append(sql.SQL("c.parent_code = ANY(%(parent_code)s)")); params["parent_code"] = _split(parent_code)
    where = sql.SQL(" AND ").join(conds)
    with conn.cursor(row_factory=dict_row) as cur:
        total = cur.execute(sql.SQL("SELECT count(*) AS n FROM topic_codes c WHERE {}").format(where), params).fetchone()["n"]
        rows = cur.execute(sql.SQL("SELECT * FROM topic_codes c WHERE {} ORDER BY {} LIMIT %(_limit)s OFFSET %(_offset)s").format(
            where, _order(sort_by, CODE_COLUMNS, "position", prefix="c.")), {**params, "_limit": pg.limit, "_offset": pg.offset}).fetchall()
    data = [{**{k: r[k] for k in CODE_COLUMNS if not k.startswith("label_")}, "label": lg(r)} for r in rows]
    return dict(data=data, meta=_meta(request, pg.offset, pg.limit, total))


# ---------------------------------------------------------------------------------- for OPD's affairs list endpoint

def topics_for_affairs(conn: psycopg.Connection, affair_ids: list[int], *, topics_limit: int = LIMIT_DEFAULT,
                       topics_offset: int = 0, lang: Optional[str] = None, lang_format: str = "nested",
                       lang_fallback: Optional[str] = None) -> dict[int, list[dict]]:
    """`GET /v1/affairs/?expand=topics`: the public current rank-1 rows (status suggested, confirmed) of each affair on the
    page, `topics_limit` / `topics_offset` per affair, ordered by scheme_key, level, rank. Affairs without rows map to []."""
    src, conds = public_rows(conn, current=True)
    conds += [sql.SQL("t.affair_id = ANY(%(ids)s)"), sql.SQL("t.rank = 1"), sql.SQL("t.status IN ('suggested', 'confirmed')")]
    q = sql.SQL("SELECT * FROM (SELECT {cols}, row_number() OVER (PARTITION BY t.affair_id ORDER BY t.scheme_key, t.level, "
                "t.rank, t.id) AS _n FROM {src} WHERE {w}) x WHERE _n > %(off)s AND _n <= %(off)s + %(lim)s "
                "ORDER BY affair_id, _n").format(cols=_SELECT_TOPIC, src=src, w=sql.SQL(" AND ").join(conds))
    lg = Language(lang=lang, lang_format=lang_format, lang_fallback=lang_fallback)
    out: dict[int, list[dict]] = {i: [] for i in affair_ids}
    with conn.cursor(row_factory=dict_row) as cur:
        for r in cur.execute(q, {"ids": list(affair_ids), "off": topics_offset, "lim": topics_limit}):
            out[r["affair_id"]].append(_topic(r, lg))
    return out


def affairs_topic_filter(conn: psycopg.Connection, topic: str, affairs_alias: str = "affairs") -> tuple[sql.Composable, dict]:
    """`GET /v1/affairs/?topic=aps:1.7.2.`: an EXISTS condition for OPD's affairs query (named parameter `topic_codes`):
    affairs whose current public rank-1 row (status suggested or confirmed) has one of these codes (comma-separated)."""
    src, conds = public_rows(conn, current=True)
    conds += [sql.SQL("t.affair_id = {}.id").format(sql.Identifier(affairs_alias)), sql.SQL("t.rank = 1"),
              sql.SQL("t.status IN ('suggested', 'confirmed')"), sql.SQL("t.code = ANY(%(topic_codes)s)")]
    return (sql.SQL("EXISTS (SELECT 1 FROM {} WHERE {})").format(src, sql.SQL(" AND ").join(conds)),
            {"topic_codes": _split(topic)})
