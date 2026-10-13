"""Neues Thema: a topic in one sentence → a yes/no topic file → one Apertus decision per affair, streamed.

1. Topic. One plain generation request (user message only, no system message, no prefill) asks Apertus for the topic's
   name and scope note in de/fr/it and up to six search terms per language, as JSON. The scope note in the sentence's own
   language is the sentence itself. Unparseable or missing fields fall back to the sentence verbatim in every frame.
   The question is built in the frame of the shipped "Digitalisierung" file (S3 E6 / S8), so `prompts.yesno_prompt`
   is unchanged.
2. Terms. A proposed term is kept only if it occurs in the corpus titles (count shown); nothing else is stored.
3. Period. Default: the newest 7 days in the loaded affairs. Inside the scored slice (begin date ≥ QS_SCORED_SINCE,
   default 2025-01-01) every affair is read. Before it, candidates = title hits of the kept terms ∪ affairs whose stored
   APS subtopic (rank ≤ 3) is one Apertus names as able to hold the topic (a closed choice over the 190 subtopics,
   checked against the list); a random outside sample (QS_OUTSIDE_N, default 40) is read as well and its flag rate,
   with a Wilson interval, estimates what the candidate step misses (VISION §4.1).
4. Decisions. `engine.Engine.yn`, order a; order b when 0.1 < p < 0.9 (as in the batch); p, flag and lane by
   `compose.yn_decision` (the nightly rows' rule). 3 worker threads, newest affair first, each decision an SSE event.
5. Save. `schemes/adhoc/<slug>.yaml` (id, names, question, answer_yes, cutoff 0.5, examples, terms, subtopics) and the
   run's decisions as `adhoc/<slug>` topic rows; the nightly job picks up every file in schemes/adhoc/."""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import random
import re
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from . import scheme as S
from .client import BuildChanged, Client, Endpoint
from .compose import VERSION, yn_decision
from .engine import Engine, need_yn_b
from .scheme import APS
from .store import ROOT, Store

LANGS = ("de", "fr", "it")
FRAME = {  # question and yes answer, the frame of schemes/adhoc/digitalisierung.yaml
    "de": ("Betrifft das folgende parlamentarische Geschäft das Thema «{name}»{scope}?", "Ja, das Geschäft betrifft {name}"),
    "fr": ("L'objet parlementaire suivant concerne-t-il le thème « {name} »{scope} ?", "Oui, l'objet concerne le thème « {name} »"),
    "it": ("Il seguente oggetto parlamentare riguarda il tema «{name}»{scope}?", "Sì, l'oggetto riguarda il tema «{name}»"),
}
TOPIC_PROMPT = (
    "Eine Redaktion beschreibt in einem Satz ein Thema, nach dem sie parlamentarische Geschäfte aller Schweizer Parlamente "
    "durchsuchen will:\n\n«{sentence}»\n\n"
    "Gib dem Thema einen kurzen Namen (höchstens fünf Wörter) auf Deutsch, Französisch und Italienisch, übersetze den Satz "
    "als Umschreibung des Themas in diese drei Sprachen und schlage pro Sprache bis zu sechs Suchbegriffe vor (einzelne "
    "Wörter oder Wortstämme, wie sie in Titeln von Geschäften vorkommen).\n\n"
    "Antworte nur mit JSON in dieser Form:\n"
    '{{"name": {{"de": "…", "fr": "…", "it": "…"}}, "scope": {{"de": "…", "fr": "…", "it": "…"}}, '
    '"terms": {{"de": ["…"], "fr": ["…"], "it": ["…"]}}}}')
SUB_PROMPT = (
    "Welche Unterthemen der Année Politique Suisse können parlamentarische Geschäfte zum Thema «{name}» ({scope}) "
    "enthalten?\n\nUnterthemen:\n{lines}\n\nAntworte nur mit JSON: {{\"subtopics\": [<höchstens fünf Nummern>]}}")
SUBS = [(code, f"{APS.sub_name[code]} ({APS.short(c)})") for c in range(24) for code in APS.sub_codes[c]]


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float | None, float | None]:
    if n == 0:
        return None, None
    ph = k / n; d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


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


def _clean(s, n: int) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().strip('"«»').strip()[:n]


def build_topic(sentence: str, lang: str, gen: dict | None, slug: str) -> dict:
    """Generated fields (or the fallback) → topic dict for prompts.yesno_prompt."""
    sentence = _clean(sentence, 400)
    names, scopes = {}, {}
    for l in LANGS:
        nm = _clean(((gen or {}).get("name") or {}).get(l) if isinstance((gen or {}).get("name"), dict) else None, 80)
        sc = _clean(((gen or {}).get("scope") or {}).get(l) if isinstance((gen or {}).get("scope"), dict) else None, 300)
        names[l] = nm or sentence
        scopes[l] = sentence if l == lang else (sc or sentence)
    q, yes = {}, {}
    for l in LANGS:
        sc = f" ({scopes[l]})" if scopes[l] and scopes[l].lower() != names[l].lower() else ""
        q[l] = FRAME[l][0].format(name=names[l], scope=sc)
        yes[l] = FRAME[l][1].format(name=names[l])
    return dict(id=f"adhoc/{slug}", names=names, scope=scopes, question=q, answer_yes=yes, cutoff=0.5,
                sentence=sentence, lang=lang, generated=bool(gen))


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

    def emit(self, kind: str, data: dict):
        with self.cv:
            self.events.append(dict(event=kind, data=data))
            self.cv.notify_all()

    def summary(self) -> dict:
        d = list(self.decisions.values())
        out = [x for x in d if x["sample"] == "outside"]
        k = sum(x["flag"] for x in out)
        lo, hi = wilson(k, len(out))
        s = dict(read=len(d), flagged=sum(x["flag"] for x in d), seconds=round(time.time() - self.t0, 1), **self.info)
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
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()
        self.calls = 0
        self.max_calls = int(os.environ.get("QS_ADHOC_MAX_CALLS", "0")) or None

    @property
    def client(self) -> Client:
        if self._client is None:
            ep = Endpoint.from_env()
            ep.conc = int(os.environ.get("QS_ADHOC_CONC", "3"))
            self._client = Client(ep, ledger=os.environ.get("QS_ADHOC_LEDGER") or str(self.out / "ledger.jsonl"),
                                  cap_usd=float(os.environ.get("QS_ADHOC_CAP", "2.0")), tag="adhoc")
        return self._client

    def _count(self, n: int = 1):
        with self.lock:
            if self.max_calls and self.calls + n > self.max_calls:
                raise RuntimeError(f"QS_ADHOC_MAX_CALLS {self.max_calls} reached")
            self.calls += n

    # ------------------------------------------------------------------ topic, terms, period
    def generate(self, sentence: str) -> tuple[dict | None, dict]:
        self._count()
        ch, meta = self.client.chat([{"role": "user", "content": TOPIC_PROMPT.format(sentence=_clean(sentence, 400))}],
                                    max_tokens=600, logprobs=None)
        text = (ch.get("message") or {}).get("content") or ""
        return parse_json(text), dict(meta, raw=text[:2000])

    def term_hits(self, term: str) -> int:
        t = term.strip()
        if len(t) < 3:
            return 0
        lo = t.lower()
        r = self.store.one("SELECT COUNT(*) AS n FROM qs_affairs WHERE lower(title) LIKE ? OR title LIKE ? OR title LIKE ?",
                           (f"%{lo}%", f"%{t}%", f"%{t[:1].upper() + t[1:]}%"))
        return int(r["n"])

    def verify_terms(self, terms: dict) -> dict:
        """Keep a proposed term only if it occurs in the corpus titles."""
        out = {}
        for l in LANGS:
            seen, kept = set(), []
            for t in (terms or {}).get(l) or []:
                t = _clean(t, 60).strip("*").strip()
                if not t or t.lower() in seen:
                    continue
                seen.add(t.lower())
                n = self.term_hits(t)
                if n:
                    kept.append(dict(term=t, hits=n))
            out[l] = kept
        return out

    def newest_week(self) -> tuple[str, str]:
        today = dt.date.today().isoformat()
        r = self.store.one("SELECT MAX(date) AS d FROM qs_affairs WHERE date <= ? AND date <> ''", (today,))
        end = dt.date.fromisoformat(r["d"]) if r and r["d"] else dt.date.today()
        return (end - dt.timedelta(days=6)).isoformat(), end.isoformat()

    def period(self, period: str | None, date_from: str | None, date_to: str | None) -> tuple[str, str]:
        if date_from or date_to:
            return date_from or "0000-00-00", date_to or "9999-12-31"
        if period and ".." in period:
            a, b = period.split("..", 1)
            return a or "0000-00-00", b or "9999-12-31"
        if period and re.fullmatch(r"\d{4}", period):
            return f"{period}-01-01", f"{period}-12-31"
        return self.newest_week()

    def propose_subtopics(self, topic: dict) -> tuple[list[str], dict]:
        lines = "\n".join(f"{i}. {name}" for i, (_, name) in enumerate(SUBS, 1))
        u = SUB_PROMPT.format(name=topic["names"]["de"], scope=topic["scope"]["de"], lines=lines)
        self._count()
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
            subs, meta = self.propose_subtopics(job.topic) if self.store.one(
                "SELECT 1 AS x FROM topics WHERE scheme = 'aps' AND level = 2 LIMIT 1") else ([], {})
            job.topic["subtopics"] = subs
            terms = [x["term"].lower() for l in LANGS for x in job.terms.get(l, [])]
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
            items = inside + cand + outside
        if limit:
            items = items[:limit]
        job.info["total"] = len(items)
        return items

    # ------------------------------------------------------------------ run
    def start(self, sentence: str, lang: str = "de", examples: list | None = None, period: str | None = None,
              date_from: str | None = None, date_to: str | None = None, terms: dict | None = None,
              limit: int | None = None, generate: bool = True) -> Job:
        if not sentence or not sentence.strip():
            raise ValueError("sentence is required")
        lang = lang if lang in LANGS else "de"
        gen, meta = (None, {})
        if generate:
            try:
                gen, meta = self.generate(sentence)
            except Exception as e:  # noqa: BLE001 — the fallback frame needs no model
                meta = dict(error=repr(e)[:300])
        base = slugify((gen or {}).get("name", {}).get("de") if isinstance((gen or {}).get("name"), dict) else sentence) \
            if gen else slugify(sentence)
        slug = self._unique(base)
        topic = build_topic(sentence, lang, gen, slug)
        proposed = terms if terms is not None else ((gen or {}).get("terms") if isinstance((gen or {}).get("terms"), dict) else {})
        kept = self.verify_terms(proposed)
        ex = []
        for e in examples or []:
            if isinstance(e, dict):
                title = e.get("title") or ((self.store.affair(int(e["id"])) or {}).get("title") if e.get("id") else None)
                if title:
                    ex.append((title, bool(e.get("match", e.get("yes", True)))))
        job = Job(slug, topic, kept, self.period(period, date_from, date_to), ex)
        job.info["generation"] = {k: meta.get(k) for k in ("model", "fp", "usd", "lat", "error") if k in meta}
        with self.lock:
            self.jobs[slug] = job
        d = self.out / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "topic.json").write_text(json.dumps(dict(topic=topic, terms=kept, period=job.period, examples=ex,
                                                      generation=meta), ensure_ascii=False, indent=1))
        threading.Thread(target=self._run, args=(job, limit), daemon=True, name=f"adhoc-{slug}").start()
        return job

    def _unique(self, base: str) -> str:
        s, k = base, 2
        while s in self.jobs or (S.HERE / "adhoc" / f"{s}.yaml").exists():
            s = f"{base}-{k}"; k += 1
        return s

    def _run(self, job: Job, limit: int | None):
        job.emit("topic", dict(slug=job.slug, topic=job.topic, terms=job.terms, period=job.period))
        try:
            items = self.select(job, limit)
        except Exception as e:  # noqa: BLE001
            job.error = repr(e)[:300]; job.done = True
            job.emit("error", dict(error=job.error)); return
        job.emit("progress", self._progress(job))
        eng = Engine(self.client, None, job.stop)
        out = (self.out / job.slug / "decisions.jsonl").open("a")
        wlock = threading.Lock()

        def one(a: dict):
            if job.stop.is_set():
                return
            a = dict(a, title_long=a.get("title_long") or "", lang=a["lang"] if a.get("lang") in LANGS else "de")
            try:
                self._count()
                ra = eng.yn(job.topic, a, "a", job.examples or None)
                rb = None
                if need_yn_b(ra["p_yes"]):
                    self._count()
                    rb = eng.yn(job.topic, a, "b", job.examples or None)
            except (BuildChanged, InterruptedError, RuntimeError) as e:
                job.error = job.error or repr(e)[:300]; job.stop.set(); return
            if self.client.expect_build is None and ra["meta"].get("fp"):
                self.client.expect_build = ra["meta"]["fp"]            # one build per process; a change stops the run
            d = yn_decision(ra, rb, job.topic["cutoff"])
            rec = dict(id=a["id"], p=round(d["p"], 4), flag=bool(d["flag"]), lane=d["lane"], t=round(time.time() - job.t0, 2),
                       sample=a["sample"], title=a["title"], body=a["body_key"], parl=a.get("parl"), level=a.get("level"),
                       lang=a["lang"], date=a["date"], p_a=round(d["p_a"], 4), p_b=None if d["p_b"] is None else round(d["p_b"], 4),
                       model=ra["meta"].get("model"), build=ra["meta"].get("fp"), prompt_id=",".join([ra["pid"]] + ([rb["pid"]] if rb else [])),
                       usd=round(ra["meta"].get("usd", 0) + (rb["meta"].get("usd", 0) if rb else 0), 7))
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
            job.done = True
            s = job.summary()
            if job.error:
                s["error"] = job.error
            (self.out / job.slug / "summary.json").write_text(json.dumps(s, ensure_ascii=False, indent=1))
            job.emit("done", s)

    def _progress(self, job: Job) -> dict:
        s = job.summary()
        s["line"] = f"read {s['read']} / flagged {s['flagged']} / {s['seconds']:.1f} s"
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
        doc = dict(id=t["id"], names=t["names"], question=t["question"], answer_yes=t["answer_yes"], cutoff=0.5, examples=ex,
                   terms={l: [x["term"] for x in job.terms.get(l, [])] for l in LANGS}, subtopics=t.get("subtopics") or [],
                   sentence=t["sentence"], created=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                   created_by=by or None)
        p = Path(os.environ.get("QS_ADHOC_DIR") or S.HERE / "adhoc") / f"{slug}.yaml"
        p.parent.mkdir(parents=True, exist_ok=True)
        head = (f"# Ad-hoc topic, written by Neues Thema from one sentence. Question and yes answer per language in the frame of\n"
                f"# digitalisierung.yaml; terms occur in corpus titles; examples are editor decisions. Cut-off fixed at 0.5.\n")
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
