"""Neues Thema: a topic in one sentence → a yes/no topic file → one Apertus decision per affair, streamed.

1. Topic. One plain generation request (user message only, no system message, no prefill) asks Apertus for the topic's
   name in de/fr/it and a literal translation of the sentence, as JSON; the scope note in the sentence's own language
   is the sentence itself. Unparseable or missing fields fall back to the sentence verbatim in every frame. The
   question is built in the frame of the shipped "Digitalisierung" file (S3 E6 / S8), so `prompts.yesno_prompt` is
   unchanged.
2. Terms. A second request, sent in parallel and off the critical path, proposes up to six search terms per language;
   a term is kept only if it occurs in the corpus titles (count shown), and nothing else is stored.
3. Period. Default: the newest 7 days in the loaded affairs. Inside the scored slice (begin date ≥ QS_SCORED_SINCE,
   default 2025-01-01) every affair is read. Before it, candidates = title hits of the kept, non-broad terms ∪ affairs whose stored
   APS subtopic (rank ≤ 3) is one Apertus names as able to hold the topic (a closed choice over the 190 subtopics,
   checked against the list); a random outside sample (QS_OUTSIDE_N, default 40) is read as well and its flag rate,
   with a Wilson interval, estimates what the candidate step misses (VISION §4.1).
4. Decisions. `engine.Engine.yn`, order a; order b when 0.1 < p < 0.9 (as in the batch); p, flag and lane by
   `compose.yn_decision` (the nightly rows' rule). 3 worker threads, newest affair first, each decision an SSE event.
   Every flag gets two checks (same two-order rule): the S27 question «is the topic central?» and the S30 scope check
   (`prompts.scope_check_prompt`) with the topic's generated include / exclude lists; a flag both confirm is `verified`,
   any other flag goes to `please_check` (the flag stays). The lists come from one more plain generation request
   (SCOPE_PROMPT, user message only, sent in parallel with step 1 under the same deadline); without them (generation
   off, no answer in time, unparseable) flags get the S27 check only, as before S30.
5. Save. `schemes/adhoc/<slug>.yaml` (id, names, question, answer_yes, cutoff 0.5, verify, include, exclude, examples,
   terms, subtopics) and the run's decisions as `adhoc/<slug>` topic rows; the nightly job picks up every file in
   schemes/adhoc/.

An endpoint that does not accept a connection within QS_ADHOC_PROBE_S (3 s) refuses the start (`Unreachable`, HTTP 503)
instead of waiting out the client's retries; the topic request has QS_ADHOC_GEN_S (20 s) before the fallback frame."""
from __future__ import annotations

import datetime as dt
import json
import os
import random
import re
import socket
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from . import scheme as S
from .client import BuildChanged, Client, Endpoint
from .compose import VERSION, run_build, yn_decision
from .engine import Engine, need_yn_b
from .prompts import has_scope_check
from .evaluate import wilson
from .examples import topic_examples
from .scheme import APS
from .store import ROOT, Store

LANGS = ("de", "fr", "it")
FRAME = {  # question and yes answer, the frame of schemes/adhoc/digitalisierung.yaml
    "de": ("Betrifft das folgende parlamentarische Geschäft das Thema «{name}»{scope}?", "Ja, das Geschäft betrifft {name}"),
    "fr": ("L'objet parlementaire suivant concerne-t-il le thème « {name} »{scope} ?", "Oui, l'objet concerne le thème « {name} »"),
    "it": ("Il seguente oggetto parlamentare riguarda il tema «{name}»{scope}?", "Sì, l'oggetto riguarda il tema «{name}»"),
}
TOPIC_PROMPT = (
    "Thema, in einem Satz: «{sentence}»\n\n"
    "1. Gib dem Thema einen kurzen Namen (höchstens vier Wörter) auf Deutsch, Französisch und Italienisch.\n"
    "2. Übersetze nur den Satz zwischen « und » auf Deutsch, Französisch und Italienisch, Wort für Wort, ohne Einleitung "
    "und ohne Zusätze.\n\n"
    "Antworte nur mit JSON in einer Zeile:\n"
    '{{"name": {{"de": "…", "fr": "…", "it": "…"}}, "scope": {{"de": "…", "fr": "…", "it": "…"}}}}')
TERMS_PROMPT = (
    "Schlage Suchbegriffe für das Thema «{sentence}» vor, wie sie in Titeln von parlamentarischen Geschäften der Schweiz "
    "vorkommen: pro Sprache bis zu sechs einzelne Wörter oder Wortstämme.\n\n"
    "Antworte nur mit JSON in einer Zeile:\n"
    '{{"terms": {{"de": ["…"], "fr": ["…"], "it": ["…"]}}}}')
SCOPE_PROMPT = (  # S30 (eval/s30/common.py, measured): include / exclude keywords per language for the scope check
    "Thema, in einem Satz: «{sentence}»\n\n"
    "Ein Redaktionsteam prüft Titel von parlamentarischen Geschäften der Schweiz auf dieses Thema. Schreibe für jede Sprache "
    "(Deutsch, Französisch, Italienisch):\n"
    "1. include: was dazu gehört, als kurze Liste (höchstens acht Stichworte, durch Kommas getrennt);\n"
    "2. exclude: verwandte, aber andere Themen, die nicht dazu gehören (höchstens sechs Stichworte, durch Kommas getrennt).\n\n"
    "Antworte nur mit JSON in einer Zeile:\n"
    '{{"include": {{"de": "…", "fr": "…", "it": "…"}}, "exclude": {{"de": "…", "fr": "…", "it": "…"}}}}')
SUB_PROMPT = (
    "Welche Unterthemen der Année Politique Suisse können parlamentarische Geschäfte zum Thema «{name}» ({scope}) "
    "enthalten?\n\nUnterthemen:\n{lines}\n\nAntworte nur mit JSON: {{\"subtopics\": [<höchstens fünf Nummern>]}}")
SUBS = [(code, f"{APS.sub_name[code]} ({APS.short(c)})") for c in range(24) for code in APS.sub_codes[c]]


def slugify(s: str, n: int = 40) -> str:
    s = s.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return (s[:n].rstrip("-") or "thema")


def parse_json(text: str) -> dict | None:
    """First JSON object in a generated text (code fences and prose around it tolerated)."""
    i = text.find("{")
    while i >= 0:
        depth = 0
        for j in range(i, len(text)):
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            if depth == 0:
                try:
                    v = json.loads(text[i:j + 1])
                    return v if isinstance(v, dict) else None
                except ValueError:
                    break
        i = text.find("{", i + 1)
    return None


def parse_terms(text: str) -> dict:
    """{"terms": {lang: [...]}} from a generated text; a list cut off by the token limit keeps its complete items."""
    v = parse_json(text)
    if isinstance((v or {}).get("terms"), dict):
        return v["terms"]
    out = {}
    for l in LANGS:
        m = re.search(rf'"{l}"\s*:\s*\[(.*?)(?:\]|$)', text, re.S)
        out[l] = re.findall(r'"([^"\n]{2,60})"', m.group(1)) if m else []
    return out


def _clean(s, n: int) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().strip('"«»').strip()[:n]


def parse_scope(gen: dict | None) -> dict:
    """{"include": {lang: text}, "exclude": {lang: text}} from the SCOPE_PROMPT answer; {} when neither list has text."""
    out = {}
    for f in ("include", "exclude"):
        d = (gen or {}).get(f) if isinstance((gen or {}).get(f), dict) else {}
        out[f] = {l: _clean(d.get(l), 300) for l in LANGS}
    return out if any(v for d in out.values() for v in d.values()) else {}


def build_topic(sentence: str, lang: str, gen: dict | None, slug: str, scope_gen: dict | None = None) -> dict:
    """Generated fields (or the fallback) → topic dict for prompts.yesno_prompt; with a parsed SCOPE_PROMPT answer also
    the include / exclude lists of the S30 scope check (prompts.scope_check_prompt)."""
    sentence = _clean(sentence, 400)
    names, scopes = {}, {}
    for l in LANGS:
        nm = _clean(((gen or {}).get("name") or {}).get(l) if isinstance((gen or {}).get("name"), dict) else None, 80)
        sc = _clean(((gen or {}).get("scope") or {}).get(l) if isinstance((gen or {}).get("scope"), dict) else None, 300)
        names[l] = nm or sentence
        if sc and len(sc) > 1.6 * len(sentence) + 30:     # a paraphrase with framing, not a translation: name only
            sc = names[l] if nm else sentence
        scopes[l] = sentence if l == lang else (sc or sentence)
    q, yes = {}, {}
    for l in LANGS:
        sc = f" ({scopes[l]})" if scopes[l] and scopes[l].lower() != names[l].lower() else ""
        q[l] = FRAME[l][0].format(name=names[l], scope=sc)
        yes[l] = FRAME[l][1].format(name=names[l])
    t = dict(id=f"adhoc/{slug}", names=names, scope=scopes, question=q, answer_yes=yes, cutoff=0.5,
             sentence=sentence, lang=lang, generated=bool(gen), verify=True)
    t.update(parse_scope(scope_gen))
    return t


class CapReached(RuntimeError):
    """The run's call budget (QS_ADHOC_MAX_CALLS) is spent; `continue` reads on with a fresh budget."""


class DailyCap(CapReached):
    """Today's list-price ad-hoc spend (QS_ADHOC_DAILY_USD) is reached: no new run and no `continue` until tomorrow."""


class Unreachable(Exception):
    """The model endpoint (or the proxy in front of it) accepts no connection within QS_ADHOC_PROBE_S: nothing started."""


class Job:
    """One Neues-Thema run: topic, terms, period, the affairs to read, and the event log the SSE stream replays."""

    def __init__(self, slug: str, topic: dict, terms: dict, period: tuple[str, str], examples: list[tuple[str, bool]]):
        self.slug, self.topic, self.terms, self.period, self.examples = slug, topic, terms, period, examples
        self.events: list[dict] = []
        self.decisions: dict[int, dict] = {}
        self.cv = threading.Condition()
        self.done, self.error, self.stop = False, None, threading.Event()
        self.t0 = time.time()
        self.info: dict = {}
        self.items: list[dict] = []
        self.calls, self.budget, self.stop_reason = 0, None, None
        self.day: tuple[float, float] | None = None       # (today's ledger USD, client spend) when the run (re)started

    def emit(self, kind: str, data: dict):
        with self.cv:
            self.events.append(dict(event=kind, data=data))
            self.cv.notify_all()

    def summary(self) -> dict:
        d = list(self.decisions.values())
        out = [x for x in d if x["sample"] == "outside"]
        k = sum(x["flag"] for x in out)
        lo, hi = wilson(k, len(out))
        s = dict(read=len(d), flagged=sum(x["flag"] for x in d), verified=sum(x.get("verified") is True for x in d),
                 please_check=sum(x.get("lane") == "please_check" for x in d), seconds=round(time.time() - self.t0, 1), **self.info)
        s.update(period=list(self.period), period_name=self.info.get("period_name"), calls=self.calls, budget=self.budget,
                 unread=max(0, (self.info.get("total") or 0) - len(d)), stop=self.stop_reason)
        if self.info.get("mode") == "candidates":
            n_non = self.info.get("non_candidates", 0)
            s["outside"] = dict(n=len(out), flagged=k, rate=round(k / len(out), 4) if out else None,
                                interval=[round(lo, 4), round(hi, 4)] if out else None,
                                est_missed=round(k / len(out) * n_non, 1) if out else None, population=n_non)
        return s


class Adhoc:
    def __init__(self, store: Store, client: Client | None = None, out: Path | None = None, workers: int = 3):
        self.store, self.workers = store, workers
        self._client = client
        self.out = Path(out or os.environ.get("QS_ADHOC_RUNS") or ROOT / "runs" / "adhoc")
        self.out.mkdir(parents=True, exist_ok=True)     # the ledger lives here: a missing dir failed the first calls
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()
        self.calls = 0
        self.max_calls = int(os.environ.get("QS_ADHOC_MAX_CALLS", "0")) or None       # per run (start / continue)
        self.daily_usd = float(os.environ.get("QS_ADHOC_DAILY_USD", "2.0")) or None   # list-price USD per local day, 0 = off
        self._reach_ok = 0.0                                                            # time of the last successful probe

    @property
    def client(self) -> Client:
        if self._client is None:
            ep = Endpoint.from_env()
            ep.conc = int(os.environ.get("QS_ADHOC_CONC", "3"))
            led = Path(os.environ.get("QS_ADHOC_LEDGER") or self.out / "ledger.jsonl")
            led.parent.mkdir(parents=True, exist_ok=True)
            self._client = Client(ep, ledger=str(led),
                                  cap_usd=float(os.environ.get("QS_ADHOC_CAP", "50.0")), tag="adhoc")   # lifetime safety net; QS_ADHOC_DAILY_USD is the working cap
        return self._client

    def spent_today(self) -> float:
        """List-price USD in the ad-hoc ledger since local midnight (every process that writes to that ledger)."""
        led = Path(self.client.ledger) if self.client.ledger else None
        t0 = time.mktime(dt.date.today().timetuple())
        usd = 0.0
        if led and led.exists():
            with led.open() as f:
                for line in f:
                    try:
                        r = json.loads(line)
                        if r.get("ts", 0) >= t0:
                            usd += r.get("usd", 0)
                    except ValueError:
                        pass
        return usd

    def check_daily(self) -> tuple[float, float] | None:
        """Refuse a start or `continue` once today's spend reached QS_ADHOC_DAILY_USD. Returns the run's baseline
        (today's ledger USD, this process's client spend): its calls are counted on top of it in `_count`."""
        if not self.daily_usd:
            return None
        usd = self.spent_today()
        if usd >= self.daily_usd:
            raise DailyCap(f"today's Neues-Thema spend is USD {usd:.4f} at list price; the daily cap QS_ADHOC_DAILY_USD is "
                           f"{self.daily_usd:g}; try again tomorrow")
        return usd, self.client.spent

    def _count(self, job: "Job | None" = None, n: int = 1):
        """Count a model call: per run against its budget (QS_ADHOC_MAX_CALLS, per start and per continue), against
        today's spend (QS_ADHOC_DAILY_USD), and per process."""
        with self.lock:
            if job is not None and job.budget is not None and job.calls + n > job.budget:
                raise CapReached(f"call budget {job.budget} of this run spent")
            if job is not None and self.daily_usd and job.day is not None \
                    and job.day[0] + self.client.spent - job.day[1] >= self.daily_usd:
                raise DailyCap(f"daily cap QS_ADHOC_DAILY_USD {self.daily_usd:g} reached")
            if job is not None:
                job.calls += n
            self.calls += n

    def reachable(self) -> str | None:
        """None when the model endpoint (or the proxy urllib would use for it) accepts a TCP connection within
        QS_ADHOC_PROBE_S (default 3 s; 0 skips the check); else the reason. A success is remembered for a minute.
        Without it a run on a dead endpoint waits out the client's retries (minutes) before it says anything."""
        secs = float(os.environ.get("QS_ADHOC_PROBE_S", "3"))
        if not secs or time.time() - self._reach_ok < 60:
            return None
        u = urllib.parse.urlsplit(self.client.endpoint.base_url)
        proxy = urllib.request.getproxies().get(u.scheme)
        if proxy and not urllib.request.proxy_bypass(u.hostname or ""):
            u = urllib.parse.urlsplit(proxy if "://" in proxy else f"http://{proxy}")
        host, port = u.hostname or "", u.port or (443 if u.scheme == "https" else 80)
        try:
            with socket.create_connection((host, port), timeout=secs):
                pass
        except OSError as e:
            return f"model endpoint {host}:{port} not reachable ({type(e).__name__}: {e})"[:300]
        self._reach_ok = time.time()
        return None

    def generate(self, sentence: str, prompt: str = TOPIC_PROMPT, max_tokens: int = 200, stop: threading.Event | None = None,
                 timeout: float = 120) -> tuple[dict | None, dict]:
        """One plain generation request (user message only) → the first JSON object in the answer."""
        self._count()
        ch, meta = self.client.chat([{"role": "user", "content": prompt.format(sentence=_clean(sentence, 400))}],
                                    max_tokens=max_tokens, logprobs=None, stop=stop, timeout=timeout)
        text = (ch.get("message") or {}).get("content") or ""
        return parse_json(text), dict(meta, raw=text[:2000])

    def _terms(self, box: dict, sentence: str, given: dict | None, stop: threading.Event | None = None):
        """Search terms off the critical path: generated in parallel with the name/scope request, verified against the
        corpus once the job exists, then sent as a `terms` event."""
        meta = {}
        try:
            if given is None:
                _, meta = self.generate(sentence, TERMS_PROMPT, 320, stop=stop)
                given = parse_terms(meta.get("raw") or "")
        except Exception as e:  # noqa: BLE001 — no terms: the candidate step uses stored subtopics only
            given, meta = {}, dict(error=repr(e)[:300])
        box["ready"].wait()
        job = box["job"]
        job.terms = self.verify_terms(given or {})
        job.info["terms_generation"] = {k: meta.get(k) for k in ("usd", "lat", "ct", "error", "raw") if k in meta}
        job.emit("terms", dict(terms=job.terms, error=meta.get("error")))

    def term_hits(self, term: str) -> int:
        t = term.strip()
        if len(t) < 3:
            return 0
        lo = t.lower()
        r = self.store.one("SELECT COUNT(*) AS n FROM qs_affairs WHERE lower(title) LIKE ? OR title LIKE ? OR title LIKE ?",
                           (f"%{lo}%", f"%{t}%", f"%{t[:1].upper() + t[1:]}%"))
        return int(r["n"])

    def verify_terms(self, terms: dict) -> dict:
        """Keep a proposed term only if it occurs in the corpus titles. A term found in more than QS_TERM_BROAD (0.5%) of
        the titles in its language is kept but marked `broad` and not used to pick candidates."""
        out = {}
        share = float(os.environ.get("QS_TERM_BROAD", "0.005"))
        n_lang = {r["lang"]: r["n"] for r in self.store.all("SELECT lang, COUNT(*) AS n FROM qs_affairs GROUP BY lang")}
        for l in LANGS:
            seen, kept = set(), []
            for t in (terms or {}).get(l) or []:
                t = _clean(t, 60).strip("*").strip()
                if not t or t.lower() in seen:
                    continue
                seen.add(t.lower())
                n = self.term_hits(t)
                if n:
                    kept.append(dict(term=t, hits=n, broad=n > share * max(1, n_lang.get(l, 0))))
            out[l] = kept
        return out

    def newest_week(self, min_day: int | None = None) -> tuple[str, str]:
        """The 7 days ending at the newest begin date (≤ today) on which at least QS_WEEK_MIN_DAY (default 20) affairs
        began; the last days of an export are sparse (affairs dated ahead, late entries), so they do not end the week."""
        min_day = min_day or int(os.environ.get("QS_WEEK_MIN_DAY", "20"))
        today = dt.date.today().isoformat()
        r = self.store.one("SELECT MAX(date) AS d FROM (SELECT date FROM qs_affairs WHERE date <= ? AND date <> '' "
                           "GROUP BY date HAVING COUNT(*) >= ?) x", (today, min_day))
        if not (r and r["d"]):
            r = self.store.one("SELECT MAX(date) AS d FROM qs_affairs WHERE date <= ? AND date <> ''", (today,))
        end = dt.date.fromisoformat(r["d"]) if r and r["d"] else dt.date.today()
        return (end - dt.timedelta(days=6)).isoformat(), end.isoformat()

    PERIODS = ("last_week", "last_month", "scored")

    def period(self, period: str | None, date_from: str | None, date_to: str | None) -> tuple[str, str, str]:
        """(from, to, name). last_week (default): 7 days ending at the newest dense day; last_month: 30 days to the same
        day; scored: QS_SCORED_SINCE (2025-01-01) to that day; from/to dates; `a..b`; a year."""
        if date_from or date_to:
            return date_from or "0000-00-00", date_to or "9999-12-31", "dates"
        if period and ".." in period:
            a, b = period.split("..", 1)
            return a or "0000-00-00", b or "9999-12-31", "dates"
        if period and re.fullmatch(r"\d{4}", period):
            return f"{period}-01-01", f"{period}-12-31", "year"
        if period not in (None, "", *self.PERIODS):
            raise ValueError(f"period: one of {', '.join(self.PERIODS)}, a year, a..b, or from/to dates")
        f, t = self.newest_week()
        if period == "last_month":
            f = (dt.date.fromisoformat(t) - dt.timedelta(days=29)).isoformat()
        elif period == "scored":
            f = os.environ.get("QS_SCORED_SINCE", "2025-01-01")
        return f, t, period or "last_week"

    def estimate(self, f: str, t: str) -> dict:
        """Affairs in the period and the seconds to read them at this process's rate ceiling (1.15 calls per affair: the
        second reading where 0.1 < p < 0.9)."""
        n = int(self.store.one("SELECT COUNT(*) AS n FROM qs_affairs WHERE date >= ? AND date <= ?", (f, t))["n"])
        cut = os.environ.get("QS_SCORED_SINCE", "2025-01-01")
        rate = float(os.environ.get("QS_MAX_RATE", "1.6"))
        out = dict(affairs=n, mode="all" if f >= cut else "candidates", rate=rate, calls_per_affair=1.15,
                   budget=self.max_calls)
        if out["mode"] == "all":
            out["seconds"] = round(n * 1.15 / rate)
        return out

    def propose_subtopics(self, topic: dict, job: "Job | None" = None) -> tuple[list[str], dict]:
        lines = "\n".join(f"{i}. {name}" for i, (_, name) in enumerate(SUBS, 1))
        u = SUB_PROMPT.format(name=topic["names"]["de"], scope=topic["scope"]["de"], lines=lines)
        self._count(job)
        ch, meta = self.client.chat([{"role": "user", "content": u}], max_tokens=60, logprobs=None)
        v = parse_json((ch.get("message") or {}).get("content") or "") or {}
        nums = v.get("subtopics") if isinstance(v.get("subtopics"), list) else []
        codes = []
        for x in nums[:5]:
            try:
                i = int(x)
            except (TypeError, ValueError):
                continue
            if 1 <= i <= len(SUBS) and SUBS[i - 1][0] not in codes:     # on the list, or dropped
                codes.append(SUBS[i - 1][0])
        return codes, meta

    # ------------------------------------------------------------------ selection
    def select(self, job: Job, limit: int | None) -> list[dict]:
        """Affairs to read, newest first; inside the scored slice all of them, before it candidates + outside sample."""
        f, t = job.period
        cut = os.environ.get("QS_SCORED_SINCE", "2025-01-01")
        cols = "id, body_key, level, lang, date, title, title_long, parl, type_h"
        rows = self.store.all(f"SELECT {cols} FROM qs_affairs WHERE date >= ? AND date <= ? ORDER BY date DESC, id DESC", (f, t))
        inside = [dict(r, sample="all") for r in rows if r["date"] >= cut]
        before = [r for r in rows if r["date"] < cut]
        job.info.update(mode="all" if not before else "candidates", period=[f, t], in_period=len(rows), scored_slice_from=cut)
        items = inside
        if before:
            if getattr(job, "terms_thread", None):
                job.terms_thread.join(timeout=120)                  # candidates need the corpus-checked terms
            subs, meta = self.propose_subtopics(job.topic, job) if self.store.one(
                "SELECT 1 AS x FROM topics WHERE scheme = 'aps' AND level = 2 LIMIT 1") else ([], {})
            job.topic["subtopics"] = subs
            terms = [x["term"].lower() for l in LANGS for x in job.terms.get(l, []) if not x.get("broad")]
            hit = {r["id"] for r in before if any(w in (r["title"] + " " + (r["title_long"] or "")).lower() for w in terms)}
            n_terms = len(hit)
            if subs:
                ids = [r["id"] for r in before]
                for i in range(0, len(ids), 900):
                    part = ids[i:i + 900]
                    q = (f"SELECT DISTINCT affair_id FROM topics WHERE valid_to IS NULL AND scheme = 'aps' AND level = 2 AND rank <= 3 "
                         f"AND code IN ({', '.join('?' * len(subs))}) AND affair_id IN ({', '.join('?' * len(part))})")
                    hit |= {r["affair_id"] for r in self.store.all(q, subs + part)}
            cand = [dict(r, sample="candidate") for r in before if r["id"] in hit]
            non = [r for r in before if r["id"] not in hit]
            rng = random.Random(job.slug)
            outside = [dict(r, sample="outside") for r in rng.sample(non, min(len(non), int(os.environ.get("QS_OUTSIDE_N", "40"))))]
            outside.sort(key=lambda r: (r["date"], r["id"]), reverse=True)
            job.info.update(candidates=len(cand), non_candidates=len(non), outside_n=len(outside), subtopics=subs,
                            term_hits=n_terms)
            if limit:                                  # a capped run keeps a third of its reads for the outside sample
                k = min(len(outside), max(1, limit // 3))
                outside = outside[:k]
                items = (inside + cand)[:limit - k] + outside
                job.info["outside_n"] = len(outside)
            else:
                items = inside + cand + outside
        if limit:
            items = items[:limit]
        job.info["total"] = len(items)
        return items

    # ------------------------------------------------------------------ run
    def start(self, sentence: str, lang: str = "de", examples: list | None = None, period: str | None = None,
              date_from: str | None = None, date_to: str | None = None, terms: dict | None = None,
              limit: int | None = None, generate: bool = True, verify: bool = True) -> Job:
        if not sentence or not sentence.strip():
            raise ValueError("sentence is required")
        lang = lang if lang in LANGS else "de"
        per = self.period(period, date_from, date_to)          # a bad period fails before any model call
        day = self.check_daily()                               # so does a spent day (DailyCap)
        why = self.reachable()                                 # and a dead endpoint, in seconds (Unreachable)
        if why:
            raise Unreachable(why)
        box, stop = dict(ready=threading.Event()), threading.Event()     # the job's stop also ends the terms request
        tt = threading.Thread(target=self._terms, args=(box, sentence, terms if (terms is not None or generate) else {}, stop),
                              daemon=True, name="adhoc-terms")
        tt.start()
        gen, meta, sbox, st = (None, {}, {}, None)
        secs = float(os.environ.get("QS_ADHOC_GEN_S", "20"))
        if generate and verify:                                # S30: the scope lists, in parallel with the topic request
            st = threading.Thread(target=lambda: sbox.update(r=self._generate_by(sentence, secs, SCOPE_PROMPT, 600)),
                                  daemon=True, name="adhoc-scope")
            st.start()
        if generate:                                           # the fallback frame needs no model
            gen, meta = self._generate_by(sentence, secs)
        if st is not None:
            st.join(secs + 5)
        scope_gen, scope_meta = sbox.get("r") or (None, dict(error="no scope answer"))
        base = slugify(gen["name"].get("de") or sentence) if (gen and isinstance(gen.get("name"), dict)) else slugify(sentence)
        ex = []
        for e in examples or []:
            if isinstance(e, dict):
                title = e.get("title") or ((self.store.affair(int(e["id"])) or {}).get("title") if e.get("id") else None)
                if title:
                    ex.append((title, bool(e.get("match", e.get("yes", True)))))
        with self.lock:                                        # slug chosen and taken at once: same sentence, own run
            slug = self._unique(base)
            topic = build_topic(sentence, lang, gen, slug, scope_gen)
            topic["verify"] = bool(verify)
            job = Job(slug, topic, {l: [] for l in LANGS}, per[:2], ex)
            job.stop = stop
            self.jobs[slug] = job
        job.budget, job.day = self.max_calls, day
        job.info.update(period_name=per[2], estimate=self.estimate(*per[:2]))
        job.info["generation"] = {k: meta.get(k) for k in ("model", "fp", "usd", "lat", "error") if k in meta}
        if st is not None:
            job.info["scope_generation"] = {k: scope_meta.get(k) for k in ("usd", "lat", "error") if k in scope_meta}
        job.terms_thread = tt
        job.emit("topic", dict(slug=job.slug, topic=job.topic, period=job.period))       # always the first event
        box["job"] = job; box["ready"].set()
        d = self.out / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "topic.json").write_text(json.dumps(dict(topic=topic, period=job.period, examples=ex, generation=meta,
                                                      scope_generation=scope_meta if st is not None else None),
                                                 ensure_ascii=False, indent=1))
        job.thread = threading.Thread(target=self._run, args=(job, limit), daemon=True, name=f"adhoc-{slug}")
        job.thread.start()
        return job

    def _generate_by(self, sentence: str, secs: float, prompt: str = TOPIC_PROMPT, max_tokens: int = 200) -> tuple[dict | None, dict]:
        """The topic request with a deadline: past it the run starts on the fallback frame (the sentence verbatim) and the
        request stops at its next retry, so POST /adhoc answers within about `secs`."""
        box, stop = {}, threading.Event()

        def go():
            try:
                box["r"] = self.generate(sentence, prompt, max_tokens, stop=stop, timeout=secs)
            except Exception as e:  # noqa: BLE001
                box["r"] = (None, dict(error=repr(e)[:300]))
        th = threading.Thread(target=go, daemon=True, name="adhoc-topic")
        th.start(); th.join(secs)
        if "r" not in box:
            stop.set()
            return None, dict(error=f"no answer within {secs:g} s (QS_ADHOC_GEN_S); fallback frame")
        return box["r"]

    def shutdown(self, timeout: float = 15.0):
        """Stop every running job (in-flight requests finish or are interrupted at the rate guard) and wait for them."""
        jobs = list(self.jobs.values())
        for j in jobs:
            j.stop.set()
        t_end = time.time() + timeout
        for j in jobs:
            if getattr(j, "thread", None):
                j.thread.join(max(0.0, t_end - time.time()))

    def _unique(self, base: str) -> str:
        s, k = base, 2
        while s in self.jobs or (S.HERE / "adhoc" / f"{s}.yaml").exists():
            s = f"{base}-{k}"; k += 1
        return s

    def _run(self, job: Job, limit: int | None):
        try:
            job.items = self.select(job, limit)
        except Exception as e:  # noqa: BLE001
            job.error = repr(e)[:300]
            job.stop_reason = "daily_cap" if isinstance(e, DailyCap) else "cap" if isinstance(e, CapReached) else f"error: {job.error}"
            s = job.summary()
            job.emit("done", s); job.done = True; return
        self._read(job, job.items)

    def resume(self, slug: str) -> Job:
        """Read on after a cap or a stop: the affairs not yet decided, with a fresh call budget."""
        job = self.jobs[slug]
        with self.lock:                                        # check and claim at once: two `continue` start one reader
            if not job.done:
                raise RuntimeError("the run is still reading")
            rest = [a for a in job.items if a["id"] not in job.decisions]
            if not rest:
                raise RuntimeError("nothing left to read")
            job.day = self.check_daily()
            why = self.reachable()
            if why:
                raise Unreachable(why)
            job.stop.clear(); job.error = None; job.stop_reason = None; job.done = False
        job.budget = job.calls + self.max_calls if self.max_calls else None
        job.thread = threading.Thread(target=self._read, args=(job, rest), daemon=True, name=f"adhoc-{slug}-cont")
        job.thread.start()
        return job

    def _read(self, job: Job, items: list[dict]):
        job.emit("progress", self._progress(job))
        eng = Engine(self.client, None, job.stop)
        out = (self.out / job.slug / "decisions.jsonl").open("a")
        wlock = threading.Lock()
        # the run's examples as the nightly batch and compose show them (the 4 most similar, never the affair itself)
        tex = dict(job.topic, examples=[dict(title=t, match=m) for t, m in job.examples])

        def one(a: dict):
            if job.stop.is_set():
                return
            a = dict(a, title_long=a.get("title_long") or "", lang=a["lang"] if a.get("lang") in LANGS else "de")
            try:
                ex = topic_examples(tex, a)
                self._count(job)
                ra = eng.yn(job.topic, a, "a", ex)
                rb = None
                if need_yn_b(ra["p_yes"]):
                    self._count(job)
                    rb = eng.yn(job.topic, a, "b", ex)
                d = yn_decision(ra, rb, job.topic["cutoff"])
                verified, pv, ps, vids, vusd = None, None, None, [], 0.0
                if job.topic.get("verify") and d["flag"]:              # S27 (+ S30 scope check), on flags only
                    pv, vids, vusd = self._check(job, eng.verify, a)
                    verified = pv >= 0.5
                    if has_scope_check(job.topic):
                        ps, sids, susd = self._check(job, eng.scope_check, a)
                        verified, vids, vusd = verified and ps >= 0.5, vids + sids, vusd + susd
                    if not verified:
                        d["lane"] = "please_check"                    # the flag stays; a person decides
            except CapReached as e:
                job.stop_reason = job.stop_reason or ("daily_cap" if isinstance(e, DailyCap) else "cap"); job.stop.set(); return
            except (BuildChanged, InterruptedError, RuntimeError) as e:
                if not job.stop.is_set():
                    job.error = job.error or repr(e)[:300]
                job.stop.set(); return
            if self.client.expect_build is None and ra["meta"].get("fp"):
                self.client.expect_build = ra["meta"]["fp"]            # one build per process; a change stops the run
            rec = dict(id=a["id"], p=round(d["p"], 4), flag=bool(d["flag"]), verified=verified,
                       p_verify=None if pv is None else round(pv, 4), p_scope=None if ps is None else round(ps, 4), lane=d["lane"], t=round(time.time() - job.t0, 2),
                       sample=a["sample"], title=a["title"], body=a["body_key"], parl=a.get("parl"), level=a.get("level"),
                       lang=a["lang"], date=a["date"], p_a=round(d["p_a"], 4), p_b=None if d["p_b"] is None else round(d["p_b"], 4),
                       model=ra["meta"].get("model"), build=run_build(dict(fp=ra["meta"].get("fp") or "", mode=ra["meta"].get("mode"))) or None,
                       prompt_id=",".join([ra["pid"]] + ([rb["pid"]] if rb else []) + vids),
                       usd=round(ra["meta"].get("usd", 0) + (rb["meta"].get("usd", 0) if rb else 0) + vusd, 7))
            with wlock:
                job.decisions[a["id"]] = rec
                out.write(json.dumps(rec, ensure_ascii=False) + "\n"); out.flush()
                job.emit("decision", rec)
                job.emit("progress", self._progress(job))

        try:
            with ThreadPoolExecutor(self.workers, thread_name_prefix=f"adhoc-{job.slug}") as ex:
                list(ex.map(one, items))
        finally:
            out.close()
            if getattr(job, "terms_thread", None):
                job.terms_thread.join(timeout=60)          # the terms event precedes `done`
            if job.stop_reason is None:
                job.stop_reason = (f"error: {job.error}" if job.error else "stopped" if job.stop.is_set() else "done")
            s = job.summary()
            if job.error:
                s["error"] = job.error
            (self.out / job.slug / "summary.json").write_text(json.dumps(s, ensure_ascii=False, indent=1))
            job.emit("done", s)
            job.done = True                                # after the last event: a stream never ends before `done`

    def _check(self, job: Job, step, a: dict) -> tuple[float, list[str], float]:
        """One check on a flag (Engine.verify or Engine.scope_check): order a, order b when 0.1 < p < 0.9 → (mean p, ids, usd)."""
        self._count(job)
        rs = [step(job.topic, a, "a")]
        if need_yn_b(rs[0]["p_yes"]):
            self._count(job)
            rs.append(step(job.topic, a, "b"))
        return sum(r["p_yes"] for r in rs) / len(rs), [r["pid"] for r in rs], sum(r["meta"].get("usd", 0) for r in rs)

    def _progress(self, job: Job) -> dict:
        s = job.summary()
        s["line"] = f"read {s['read']} / flagged {s['flagged']} / verified {s['verified']} / please check {s['please_check']} / {s['seconds']:.1f} s"
        return s

    # ------------------------------------------------------------------ save
    def save(self, slug: str, examples: list | None = None, by: str | None = None, load_rows: bool = True) -> dict:
        """Write schemes/adhoc/<slug>.yaml and load the run's decisions as topic rows."""
        job = self.jobs.get(slug)
        if job is None:
            raise KeyError(slug)
        t = job.topic
        ex = [dict(title=x, match=bool(y)) for x, y in job.examples]
        for e in examples or []:
            title = e.get("title") or ((self.store.affair(int(e["id"])) or {}).get("title") if e.get("id") else None)
            if title:
                ex.append(dict(title=title, match=bool(e.get("match", e.get("yes", True)))))
        doc = dict(id=t["id"], names=t["names"], question=t["question"], answer_yes=t["answer_yes"], cutoff=0.5,
                   verify=bool(t.get("verify", True)), **{k: t[k] for k in ("include", "exclude") if t.get(k)}, examples=ex,
                   terms={l: [x["term"] for x in job.terms.get(l, [])] for l in LANGS}, subtopics=t.get("subtopics") or [],
                   sentence=t["sentence"], created=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                   created_by=by or None)
        p = Path(os.environ.get("QS_ADHOC_DIR") or S.HERE / "adhoc") / f"{slug}.yaml"
        p.parent.mkdir(parents=True, exist_ok=True)
        head = ("# Ad-hoc topic, written by Neues Thema from one sentence. Question and yes answer per language in the frame of\n"
                "# digitalisierung.yaml; terms occur in corpus titles; examples are editor decisions. Cut-off fixed at 0.5.\n")
        p.write_text(head + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=140))
        S.adhoc.cache_clear()
        n = 0
        if load_rows and job.decisions:
            now = dt.datetime.now(dt.timezone.utc)
            aff = self.store.affairs(list(job.decisions))
            rows = []
            for d in sorted(job.decisions.values(), key=lambda d: d["id"]):
                rows.append(dict(affair_id=d["id"], body_key=d["body"], scheme=t["id"], level=1,
                                 code=f"{t['id']}:{'yes' if d['flag'] else 'no'}", rank=1, p=d["p"], p_raw=d["p"], lane=d["lane"],
                                 status="suggested", provenance="inferred", evidence=None, model=d["model"], build=d["build"],
                                 cutoffs_id=f"{t['id']}@0.5", prompt_id=d["prompt_id"],
                                 input_hash=(aff.get(d["id"]) or {}).get("input_hash"), valid_from=now, version=VERSION))
            n = self.store.load_topics(rows)["inserted"]
        return dict(path=str(p), slug=slug, id=t["id"], rows=n, yaml=p.read_text())
