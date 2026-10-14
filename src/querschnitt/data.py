"""OPD bulk exports → one input row per affair (`inputs.jsonl.gz`): title, long title and up to 1,500 characters of the
affair's own text in its language, plus the fields the views filter on (parliament, level, type, state, submitter, party).

Only OPD's published downloads are read (files.openparldata.ch/exports/; no API calls). Text choice, in order:
1. OPD `texts` rows that are the affair's own text (submitted text, description, summary), never a reply;
2. the first document attached to the affair that is not a reply; else a reply whose opening restates the affair
   (names the instrument and at least half of the title's long words; S6 rule). Replies that do not are skipped.
Every row records `text_src`, so an affair that gains text later gets a new input hash and is re-scored."""
from __future__ import annotations

import collections
import gzip
import hashlib
import html
import json
import os
import re
import sys
from pathlib import Path

TAG = re.compile(r"<[^>]+>")
TRIM_DOCS = os.environ.get("QS_TRIM_DOCS", "0") == "1"   # switch on with the post-slice rebuild (changes ~24% of document input hashes → re-scored, never mixed)


def clean(s: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG.sub(" ", s or ""))).strip()


def demojibake(s: str) -> str:
    """Repair UTF-8 read as Latin-1 upstream ("GrÃ¼ne" → "Grüne"); unchanged when it does not apply."""
    if s and ("Ã" in s or "Â" in s):
        try:
            return s.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return s
    return s


def rows(path: Path):
    with gzip.open(path, "rt") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


# ---------------------------------------------------------------- bodies, levels, languages
def load_bodies(d: Path) -> dict:
    return {b["body_key"]: b for b in rows(d / "bodies.ndjson.gz")}


def level(key: str, B: dict) -> str:
    if key == "CHE":
        return "federal"
    t = (B.get(key) or {}).get("type")
    if t == "canton" and re.fullmatch(r"[A-Z]{2}", key):
        return "cantonal"
    if key.isdigit() and t in ("city", "municipality"):
        return "communal"
    return "other"


def pick_lang(a: dict, B: dict) -> tuple[str, str | None]:
    """(prompt language, text language): the body's language if the title exists in it, else de > fr > it (S8 rule)."""
    main = ((B.get(a["body_key"]) or {}).get("lang") or "").lower()
    has = lambda l: bool((a.get("title_" + l) or "").strip())
    if main in ("de", "fr", "it") and has(main):
        return main, main
    for l in ("de", "fr", "it"):
        if has(l):
            return l, l
    if has("rm"):
        return "de", "rm"
    return "de", None


PARL_FALLBACK = {"CHE": "Bundesversammlung", "LIE": "Landtag (Liechtenstein)"}


def parl_name(key: str, B: dict, lang: str = "de") -> str:
    """The parliament's name in `lang`: its own name when that is its language, else OPD's translation (OPD's French
    field holds the English "Grand Council" for some cantons; that one is replaced by "Grand Conseil")."""
    b = B.get(key) or {}
    own = (b.get("lang") or "").lower() == lang and b.get("legislative_name")
    tr = b.get(f"legislative_name_{lang}")
    if tr == "Grand Council" and lang == "fr":
        tr = "Grand Conseil"
    return own or tr or b.get("legislative_name") or PARL_FALLBACK.get(key) or b.get(f"name_{lang}") or b.get("name") or key


# ---------------------------------------------------------------- text choice
OWN_TEXT = re.compile(r"^(eingereichter text|texte déposé|testo depositato|begründung|développement|motivazione|lead|beschreibung|"
                      r"résumé|resume|zusammenfassung|text des vorstosses|vorstoss|antrag|texte soumis|contenu|teaser|kurzbeschrieb|"
                      r"kurzbeschreibung|frage vom)", re.I)
CHE_ORDER = ["eingereichter text", "texte déposé", "testo depositato", "lead", "begründung", "développement", "motivazione"]
REPLY_TYPE = re.compile(r"^(antwort|réponse|reponse|risposta|stellungnahme)", re.I)
ANS_NAME = re.compile(r"antwort|beantwortung|stellungnahme des (regierungs|stadt|gemeinde)rat|réponse|reponse|risposta|"
                      r"rapport du conseil (d.etat|communal|municipal)|messaggio municipale.*risposta", re.I)
ANS_HEAD = re.compile(r"^.{0,300}?(antwort des (regierungs|stadt|gemeinde)rates|beantwortung der|der (regierungs|stadt|gemeinde)rat "
                      r"beantwortet|réponse du (conseil|gouvernement|municipal)|le conseil (d.etat|communal|municipal) répond|"
                      r"risposta del (consiglio|municipio)|il municipio risponde|il consiglio di stato risponde)", re.I)
INSTR = re.compile(r"anfrage|interpellation|motion|postulat|auftrag|vorstoss|erkundigt|fragen|interrogazion|interpellanz|mozion|"
                   r"chiede|domand|question|résolution|resolution|rappel|demande", re.I)
WORD = re.compile(r"[A-Za-zÀ-ÿ]{5,}")
NON_TEXT_CATS = {"recording_video", "recording_audio", "image"}


def trim_to_title(text: str, title: str, min_len: int = 15, max_skip: int = 1200) -> str:
    """Documents often start with a letterhead, addresses or a form header before the affair itself; start the text at the
    first occurrence of the title (its first 40 characters) when it appears within the first `max_skip` characters."""
    key = (title or "")[:40].lower()
    if len(key) < min_len:
        return text
    i = text.lower().find(key)
    return text[i:] if 0 < i <= max_skip else text


def restates(t: str, title: str) -> bool:
    if not INSTR.search(t):
        return False
    tw = {w.lower() for w in WORD.findall(title or "")}
    if not tw:
        return True
    low = t.lower()
    return sum(w in low for w in tw) >= max(1, len(tw) / 2)


def texts_index(d: Path) -> dict[int, list[tuple[str, str, str, int]]]:
    """affair id -> [(type, lang, cleaned text, text row id)] for the affair's own texts (never replies)."""
    out = collections.defaultdict(list)
    for p in sorted((d / "texts").glob("*.ndjson.gz")):
        for r in rows(p):
            for lang in ("de", "fr", "it", "rm"):
                t, ty = r.get(f"text_{lang}"), (r.get(f"type_{lang}") or r.get("type_de") or r.get("type_fr") or "")
                if not t or REPLY_TYPE.match(ty) or ty.lower().startswith("titel des gesch"):
                    continue
                if not OWN_TEXT.match(ty) and r["body_key"] != "LIE":
                    continue
                c = clean(t)
                if len(c) >= 40:
                    out[r["affair_id"]].append((ty, lang, c, r["id"]))
    return out


def pick_text_rows(lst, tlang: str | None, body: str):
    if not lst:
        return None
    same = [x for x in lst if x[1] == tlang] or lst
    if body == "CHE":
        for want in CHE_ORDER:
            for x in same:
                if x[0].lower().startswith(want):
                    return x
    return same[0]


def docs_index(path: Path, ids: set[int]) -> dict[int, list[dict]]:
    out = collections.defaultdict(list)
    if not path.exists():
        return out
    for r in rows(path):
        if r["a"] in ids and r.get("cat") not in NON_TEXT_CATS:
            out[r["a"]].append(r)
    for v in out.values():
        v.sort(key=lambda r: (r.get("date") or "9999", r["id"]))
    return out


def pick_doc(docs: list[dict], title: str, n: int = 1500):
    ans_ok, skipped = None, 0
    for r in docs:
        t = r["head"]
        if len(t) <= 300:
            continue
        if ANS_NAME.search(r.get("name") or "") or ANS_HEAD.search(t[:400]):
            if ans_ok is None and restates(t[:n], title):
                ans_ok = r
            else:
                skipped += 1
            continue
        return r, "doc", skipped
    if ans_ok:
        return ans_ok, "doc-reply-restating", skipped
    return None, None, skipped


# ---------------------------------------------------------------- submitters
def submitters(d: Path, ids: set[int]) -> dict[int, dict]:
    """First author per affair (person or group) with harmonised party where OPD has it, the number of co-signers and
    the leading department (Bern: the lead directorate) where OPD has one."""
    best: dict[int, tuple] = {}
    n_cos = collections.Counter()
    dept: dict[int, str] = {}
    for r in rows(d / "contributors.ndjson.gz"):
        a = r.get("affair_id")
        if a not in ids:
            continue
        role = r.get("role_harmonized")
        if role in ("cosign", "co-signer"):
            n_cos[a] += 1
            continue
        if role == "leading_department":
            dept.setdefault(a, r.get("fullname") or r.get("lastname") or "")
            continue
        if role != "author":
            continue
        rank = (r.get("position") or 99, r["id"])
        if a not in best or rank < best[a][0]:
            best[a] = (rank, dict(name=demojibake(r.get("fullname") or ""), party=demojibake(r.get("party_harmonized_de") or r.get("party_de") or ""),
                                  party_fr=demojibake(r.get("party_harmonized_fr") or r.get("party_fr") or ""), kind=r.get("type") or ""))
    out = {a: dict(v[1], n=n_cos[a]) for a, v in best.items()}
    for a, v in dept.items():
        out.setdefault(a, dict(name="", party="", party_fr="", kind="", n=n_cos[a]))["dept"] = v
    return out


def submitter_type(a: dict, sub: dict | None) -> str:
    th = (a.get("type_harmonized_de") or "").lower()
    if "regierung" in th or "bundesrat" in (a.get("type_name_de") or "").lower():
        return "executive"
    if sub and sub.get("kind") == "group":
        return "group"
    if sub and sub.get("kind") == "person":
        return "member"
    if any(k in th for k in ("motion", "postulat", "interpellation", "anfrage", "fragestunde", "initiative", "auftrag")):
        return "member"
    return "other"


def input_hash(x: dict) -> str:
    s = json.dumps([x["lang"], x["title"], x["title_long"], x["text"]], ensure_ascii=False)
    return hashlib.sha256(s.encode()).hexdigest()[:16]


# ---------------------------------------------------------------- build
def build(d: Path, out: Path, since: str = "0000", docs_path: Path | None = None) -> dict:
    B = load_bodies(d)
    A = list(rows(d / "affairs.ndjson.gz"))
    ids = {a["id"] for a in A}
    T = texts_index(d)
    D = docs_index(docs_path or d / "docs_slim.jsonl.gz", ids)
    S = submitters(d, ids)
    stats = collections.Counter()
    tmp = out.with_suffix(".tmp")
    with gzip.open(tmp, "wt") as f:
        for a in A:
            lang, tl = pick_lang(a, B)
            if not tl:
                stats["no_title"] += 1
                continue
            title = clean(a.get(f"title_{tl}"))
            tlong = clean(a.get(f"title_long_{tl}"))
            text, src, kind = "", None, None
            tr = pick_text_rows(T.get(a["id"]), tl, a["body_key"])
            if tr:
                text, src, kind = tr[2][:1500], f"text:{tr[3]}", "text"
            else:
                r, kind, _ = pick_doc(D.get(a["id"], []), title)
                if r:
                    text, src = (trim_to_title(r["head"], title) if TRIM_DOCS else r["head"])[:1500], f"doc:{r['id']}"
            sub = S.get(a["id"])
            body = a["body_key"]
            alt = next((l for l in ("fr", "de", "it") if l != tl and (a.get(f"title_{l}") or "").strip()
                        and clean(a.get(f"title_{l}")) != title), None)
            x = dict(id=a["id"], body=body, level=level(body, B), canton=(B.get(body) or {}).get("canton_key") or (body if len(body) == 2 else None),
                     parl=parl_name(body, B, "de"), parl_fr=parl_name(body, B, "fr"), lang=lang, text_lang=tl, number=a.get("number"),
                     date=(a.get("begin_date") or "")[:10], title=title, title_long=tlong, text=text, text_src=src, text_kind=kind,
                     type=a.get(f"type_name_{tl}") or a.get("type_name_de") or a.get(f"type_harmonized_{lang}") or "",
                     type_h=a.get("type_harmonized_de") or "", type_h_fr=a.get("type_harmonized_fr") or "",
                     state=a.get(f"state_name_{tl}") or a.get("state_name_de") or "",
                     url=a.get(f"url_external_{tl}") or a.get("url_external_de") or a.get("url_external_fr") or "",
                     submitter=(sub or {}).get("name", ""), party=(sub or {}).get("party", ""), n_signers=(sub or {}).get("n", 0),
                     submitter_type=submitter_type(a, sub), dept=(sub or {}).get("dept", ""), updated=a.get("updated_at"),
                     alt_lang=alt, title_alt=clean(a.get(f"title_{alt}")) if alt else "", title_long_alt=clean(a.get(f"title_long_{alt}")) if alt else "")
            langs = {l.strip().lower() for l in ((B.get(body) or {}).get("languages") or "").split(",") if l.strip()}
            x["bilingual"] = {"de", "fr"} <= langs
            x["input_hash"] = input_hash(x)
            stats["rows"] += 1; stats[f"text_{kind}"] += 1; stats[f"level_{x['level']}"] += 1
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    tmp.rename(out)
    return dict(stats)


if __name__ == "__main__":
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    print(json.dumps(build(src, dst), indent=1))
