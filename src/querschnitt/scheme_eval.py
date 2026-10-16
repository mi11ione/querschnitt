"""`make scheme-eval GOLD=their.csv`: a partner's own labels -> their own scheme file -> a scored, pre-registered test.

    querschnitt scheme-eval their.csv [--id COL] [--label COL] [--n 200] [--examples 5] [--cap 2] [--dry-run]

1. Read the list: CSV (delimiter sniffed among , ; tab |; utf-8-sig, utf-8, cp1252, latin-1) or XLSX (openpyxl, when
   installed). The header is the first of the first ten rows with at least 60% of the most filled cells (a title line
   above it is skipped).
   Key column: an OPD affair id, or a business number (Curia «24.4266», cantonal numbers such as «PL 9402») joined to the
   inputs by (body, number); detected from the data (share of values that join), or --id. A number found in several
   parliaments is resolved by a body column (--body-col, or detected: values like CHE, BS, ZH), --body, or the body most
   of the other rows joined to; otherwise it is reported as ambiguous. Label column: --label (several: «Thema 1+Thema 2»),
   else a column named like label / Kategorie / Thema / topic, else the text column with the fewest distinct values;
   numbered siblings («Thema 2» beside «Thema 1») become further labels. A cell may hold several labels (| ; or , between
   labels that also occur alone; --sep forces one): the first is the primary label, all count for «any label in top-k».
   An affair listed on several rows (a long export, one row per category) is merged: first row's label first.
2. Scheme file `src/querschnitt/schemes/partner-<slug>.yaml` (kind named, `status: test`): the distinct label names
   verbatim, alphabetical, codes generated, then the none option; the frame in the language most joined affairs are in
   (de, fr or it; --lang); `body` when every joined affair is from one parliament, else `bodies`. At most 51 labels (the
   code list A–Z, a–y): beyond that the 51 most frequent are kept and rows whose primary label is dropped are reported.
   `status: test` keeps the file out of compose and the static export (scheme.named_schemes) until a person ships it.
   Keyword baseline frozen in the run dir before any call (S20 rule: first 5 letters of every word of 4+ letters).
3. Sample --n affairs (random.Random(2026), proportional to the primary label: largest remainders). Arm «names only»: the
   shipped named step through the batch runner (`--named <id> --ids … --conc 2 --max-rate 0.5 --cap`) into
   runs/scheme-<slug>/, build locked before the first call (runs/main's build when its model is the endpoint's model;
   --build first locks the first served build). With --examples k > 0, arm «examples» in the S21 shape: two folds by
   affair id parity over every joined affair; each sampled affair gets the k BM25-nearest labelled affairs of the other
   fold as examples (identity order) and the permuted names-only reading (reused from the first arm where it exists);
   decision = top of the mean; lanes = the two readings agree or not.
4. Score: top-1 = primary label, top-3, any label at top-1 / in the top-3, per-label recall and precision, the majority
   label and the frozen keywords on the same items, Apertus − keyword (paired bootstrap, 2,000, random.Random(2026)),
   lanes with accuracy each, examples − names (paired) when both arms ran. Wilson 95% intervals, points truncated, bounds
   rounded outward. -> runs/scheme-<slug>/report.json and the printed report.
5. Before the first model call the plan is pre-registered with tools/prereg_append.py --no-push (eval/PREREG-BUILD.md;
   --prereg local writes runs/scheme-<slug>/PREREG.md instead, for tooling checks; --prereg off skips it). Text: PREREG
   below, filled from the plan. Pushing it is a decision made on site: --register-only stops after the entry, so it can be
   pushed before the first call; the rerun finds the entry (same plan) and does not register twice."""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import os
import random
import re
import subprocess
import sys
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from . import prompts as P
from . import scheme as SCH
from .evaluate import _down, _up, fmt_p, prop

ROOT = Path(__file__).resolve().parents[2]
SEED = 2026
MAX_LABELS = len(P.CODES_NAMED) - 1          # 51 labels + none
ID_HINTS = ("affair_id", "opd_id", "opd", "id", "oid", "affair", "geschaeft_id", "geschäft_id")
NUM_HINTS = ("number", "nummer", "nr", "signatur", "geschäftsnummer", "geschaeftsnummer", "geschäfts-nr", "geschäftsnr",
             "curia", "business_number", "numero", "numéro", "n°", "no", "objet", "oggetto", "shortid", "reference")
LABEL_HINTS = ("label", "labels", "gold", "code", "kategorie", "kategorien", "category", "categories", "catégorie", "categoria",
               "thema", "themen", "theme", "thème", "themes", "topic", "topics", "tema", "temi", "sachgebiet", "sachbereich",
               "rubrik", "politikbereich", "politikfeld", "bereich", "domaine", "settore", "schlagwort", "schlagworte",
               "deskriptor", "tag", "tags", "class", "klasse", "dossier")
BODY_HINTS = ("body", "body_key", "kanton", "canton", "cantone", "parlament", "parliament", "parlement", "parlamento", "ebene")
BODY_ALIAS = {"CH": "CHE", "BUND": "CHE", "EIDG": "CHE", "BUNDESVERSAMMLUNG": "CHE", "CONFEDERATION": "CHE", "FL": "LIE"}
EMPTY = {"", "-", "–", "—", "n/a", "na", "none", "null", "nan", "?"}
SEPS = ("|", ";", ",", "\n")

FRAMES = {
    "de": dict(ask="Ordne das folgende parlamentarische Geschäft genau einem Thema der folgenden Liste zu.", head="Themen",
               key="thema", fmt='Antworte nur mit dem Buchstaben des Themas als JSON: {"thema": "<Buchstabe>"}',
               none="Keines dieser Themen"),
    "fr": dict(ask="Attribue l'objet parlementaire suivant à exactement un thème de la liste suivante.", head="Thèmes",
               key="theme", fmt='Réponds uniquement par la lettre du thème en JSON : {"theme": "<lettre>"}',
               none="Aucun de ces thèmes"),
    "it": dict(ask="Assegna il seguente oggetto parlamentare a esattamente un tema dell'elenco seguente.", head="Temi",
               key="tema", fmt='Rispondi solo con la lettera del tema in JSON: {"tema": "<lettera>"}',
               none="Nessuno di questi temi"),
}
KW_STOP = {"dell", "dello", "della", "delle", "degli", "dalla", "dalle", "nella", "nelle", "sulla", "alla", "alle", "avec",
           "pour", "dans", "sans", "sous", "oder", "sowie", "ohne"}

PREREG = """Question: how well does the shipped named-scheme step assign {who}'s affairs to {who}'s own labels, given only the label
names{q_ex}? (`make scheme-eval`, generic template; filled from the plan before any call of this run.)
Labels: `{gold}` (sha256 {gold_sha}), {n_rows} data rows; label column {label_cols}{multi}; key column «{key_col}» ({key_kind}).
Joined to `{inputs}`: {n_joined} affairs ({join_line}).
Scheme: `src/querschnitt/schemes/{sid}.yaml` (kind named, status test): the {n_labels} distinct label names verbatim,
alphabetical, then «{none}»; frame {lang}; {body_line}; no descriptions, nothing tuned.
Sample: {n_sample} of {n_joined} affairs, {strat}, random.Random(2026); ids `runs/scheme-{slug}/ids.txt` (sha256 {ids_sha}).
Arm names only (as shipped, S20): identity order; the second code order (random.Random(7) permutation) when the first top
probability is below 0.9; decision = top of the mean; lane = the two orders disagree.{arm_ex}
Primary: top-1 = the primary label (first label of the row), Wilson 95%, point truncated, bounds rounded outward.
Secondary: top-3 contains it; any of the row's labels at top-1 / in the top-3; per-label recall; lanes (readings agree /
disagree) with accuracy each.{sec_ex}
Baselines on the same items: the majority primary label (computed at scoring); frozen keyword stems
`runs/scheme-{slug}/keywords_frozen.json` (sha256 {kw_sha}; title only, S20 rule); Apertus − keyword, paired bootstrap 2,000
resamples, random.Random(2026).
Run: batch runner into `runs/scheme-{slug}` (`--named {sid} --ids runs/scheme-{slug}/ids.txt --topics --steps --conc {conc}
--max-rate {max_rate} --cap {cap}`), `{model}` at {endpoint}; {build_line} Never a system message. Reported as measured."""

PREREG_EX = """
Arm examples (S21 shape): two folds by OPD affair id parity over all {n_joined} joined affairs; each sampled affair is asked
once in identity order with the {k} BM25-nearest labelled affairs of the other fold as examples (title → label), plus the
permuted names-only reading (reused from the first arm where it was asked); decision = top of the mean; lane = the two
readings disagree."""


# ---------------------------------------------------------------------------------------------------- reading the list
def _decode(raw: bytes) -> tuple[str, str]:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    raise AssertionError("latin-1 decodes every byte")


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, (dt.date, dt.datetime)):
        return v.isoformat()[:10]
    return str(v).strip()


def read_table(path: str | Path, sheet: str | None = None) -> tuple[list[str], list[list[str]], dict]:
    """-> (header, data rows as lists of stripped strings, meta {format, encoding, delimiter, sheet, header_row})."""
    path = Path(path)
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        try:
            import openpyxl  # noqa: PLC0415
        except ImportError:
            raise SystemExit(f"{path}: reading XLSX needs openpyxl, which is not installed here. Either "
                             f"`.venv/bin/pip install openpyxl`, or save the sheet as CSV (Excel: File > Save As > "
                             f"«CSV UTF-8») and run again with GOLD=<that .csv>.") from None
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb[sheet] if sheet else wb.worksheets[0]
        grid = [[_cell(v) for v in r] for r in ws.iter_rows(values_only=True)]
        meta = dict(format="xlsx", sheet=ws.title)
        wb.close()
    elif path.suffix.lower() == ".xls":
        raise SystemExit(f"{path}: old Excel .xls is not read; save it as .xlsx or as CSV UTF-8 and run again.")
    else:
        text, enc = _decode(path.read_bytes())
        try:
            delim = csv.Sniffer().sniff(text[:8192], delimiters=",;\t|").delimiter
        except csv.Error:
            delim = max(",;\t|", key=lambda d: text[:8192].count(d))
        grid = [[(c or "").strip() for c in r] for r in csv.reader(io.StringIO(text), delimiter=delim)]
        meta = dict(format="csv", encoding=enc, delimiter=delim)
    grid = [r for r in grid if any(r)]
    if not grid:
        raise SystemExit(f"{path}: no rows")
    filled = [sum(bool(c) for c in r) for r in grid[:10]]
    head = next(i for i, k in enumerate(filled) if k >= max(2, 0.6 * max(filled)) or k == max(filled))
    header = [c or f"col{j + 1}" for j, c in enumerate(grid[head])]
    w = len(header)
    rows = [(r + [""] * w)[:w] for r in grid[head + 1:]]
    meta["header_row"] = head + 1
    return header, rows, meta


# ---------------------------------------------------------------------------------------------------- inputs index
def norm_num(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace(" ", " ")).strip().upper()


def compact(s: str) -> str:
    """«PL 9402» = «PL9402»: whitespace only (dots, dashes and slashes carry meaning in business numbers)."""
    return re.sub(r"\s", "", norm_num(s))


DATE = re.compile(r"\d{4}-\d{2}-\d{2}(?:[ T][\d:.]+)?|\d{1,2}\.\d{1,2}\.\d{4}")


class Inputs:
    """Slim index of the inputs file: id -> (body, number, lang, title), number -> ids (exact and compacted form)."""

    def __init__(self, rows: list[dict]):
        self.meta = {}
        self.by_num: dict[str, list[int]] = collections.defaultdict(list)
        self.by_compact: dict[str, list[int]] = collections.defaultdict(list)
        for x in rows:
            i = int(x["id"])
            self.meta[i] = dict(body=x.get("body"), number=x.get("number") or "", lang=x.get("lang") or "de",
                                title=x.get("title") or "", date=x.get("date") or "", parl=x.get("parl") or "")
            if x.get("number"):
                self.by_num[norm_num(x["number"])].append(i)
                self.by_compact[compact(x["number"])].append(i)
        self.bodies = {m["body"] for m in self.meta.values()}

    @classmethod
    def load(cls, path: str | Path) -> "Inputs":
        op = gzip.open if str(path).endswith(".gz") else open
        keep = ("id", "body", "number", "lang", "title", "date", "parl")
        with op(path, "rt") as f:
            return cls([{k: x.get(k) for k in keep} for x in map(json.loads, f) if x])

    def number_ids(self, v: str) -> list[int]:
        return self.by_num.get(norm_num(v)) or self.by_compact.get(compact(v)) or []


def as_id(v: str) -> int | None:
    v = v.strip()
    return int(v) if v.isdigit() else None


# ---------------------------------------------------------------------------------------------------- column detection
def _hint(col: str, hints) -> bool:
    c = col.strip().lower()
    return c in hints or re.sub(r"[\s_\-.]*\d+$", "", c) in hints


def detect_key(header, rows, idx: Inputs, want: str | None = None) -> tuple[list[tuple[int, str, float]], dict]:
    """-> ([(column index, 'id' | 'number', join rate)] best first: the key and, if another column also joins, a fallback),
    rates per column."""
    rates = {}
    sample = rows[:1500]
    for j, col in enumerate(header):
        vals = [r[j] for r in sample if r[j]]
        if not vals or sum(bool(DATE.fullmatch(v)) for v in vals) > len(vals) / 2:   # empty, or dates
            continue
        rid = sum(as_id(v) in idx.meta for v in vals) / len(vals)
        rnum = sum(bool(idx.number_ids(v)) for v in vals) / len(vals)
        rates[col] = dict(id=round(rid, 3), number=round(rnum, 3))
    if want:
        if want not in header:
            raise SystemExit(f"ID={want}: no such column; columns: {header}")
        r = rates.get(want, dict(id=0, number=0))
        kind = "id" if r["id"] >= r["number"] else "number"
        return [(header.index(want), kind, r[kind])], rates
    cand = []
    for col, r in rates.items():
        for kind in ("id", "number"):
            hint = _hint(col, ID_HINTS if kind == "id" else NUM_HINTS)
            cand.append((r[kind] + (0.05 if hint else 0) + (0.01 if kind == "id" else 0), header.index(col), kind, r[kind]))
    cand.sort(key=lambda c: (-c[0], c[1]))
    if not cand or cand[0][3] < 0.2:
        raise SystemExit("no column joins to the inputs (OPD affair id or business number); join rate per column: "
                         + "; ".join(f"«{c}» id {r['id']:.2f} number {r['number']:.2f}" for c, r in rates.items())
                         + ". Pass ID=<column>, or check that the inputs file covers these affairs.")
    best = cand[0]
    out = [(best[1], best[2], best[3])]
    other = next((c for c in cand[1:] if c[1] != best[1] and c[3] >= 0.2), None)
    if other:
        out.append((other[1], other[2], other[3]))
    return out, rates


def detect_label(header, rows, want: str | None, skip: set[int]) -> list[int]:
    """-> label column indices (primary first, then numbered siblings or the ones given with +)."""
    if want:
        cols = [c.strip() for c in want.split("+")]
        bad = [c for c in cols if c not in header]
        if bad:
            raise SystemExit(f"LABEL={want}: no column {bad}; columns: {header}")
        return [header.index(c) for c in cols]
    named_ = [j for j, c in enumerate(header) if j not in skip and _hint(c, LABEL_HINTS)
              and any(r[j] for r in rows)]
    if named_:
        prim = named_[0]
    else:
        best = None
        for j, c in enumerate(header):
            vals = [r[j] for r in rows if r[j]]
            if j in skip or len(vals) < max(2, len(rows) // 5):
                continue
            if sum(bool(re.fullmatch(r"[\d\s.,:/\-]+|https?://\S+", v)) for v in vals) > len(vals) / 2:
                continue        # numbers, dates, links
            dist = len(set(vals)); mean_len = sum(map(len, vals)) / len(vals)
            if dist < 2 or mean_len > 80 or dist > max(60, len(vals) // 2):
                continue
            key = (dist / len(vals), j)
            best = min(best, (key, j)) if best else (key, j)
        if not best:
            raise SystemExit(f"no label column found; pass LABEL=<column>; columns: {header}")
        prim = best[1]
    out = [prim]
    stem = re.sub(r"[\s_\-.]*1$", "", header[prim].strip())
    if stem != header[prim].strip():   # «Thema 1» -> «Thema 2», «Thema 3» …
        for j, c in enumerate(header):
            m = re.fullmatch(re.escape(stem) + r"[\s_\-.]*(\d+)", c.strip())
            if j != prim and m and int(m.group(1)) > 1:
                out.append(j)
    return out


def choose_sep(cells: list[str], force: str | None = None) -> str | None:
    """The separator between several labels in one cell: | ; , or a line break, only when the parts also occur as whole
    labels on their own (so «Kinder, Jugendliche & Familien» stays one label); | and ; also when no cell holds a single
    label. `force`: a separator, or 'none'."""
    if force:
        return None if force.lower() == "none" else {"\\n": "\n", "tab": "\t"}.get(force, force)
    single = {c for c in cells if c and not any(s in c for s in SEPS)}
    for s in SEPS:
        multi = [c for c in cells if s in c]
        if not multi:
            continue
        parts = [p.strip() for c in multi for p in c.split(s) if p.strip()]
        if single and parts and sum(p in single for p in parts) / len(parts) >= 0.5:
            return s
        if not single and s in ("|", ";", "\n"):
            return s
    return None


def labels_of(cells: list[str], sep: str | None) -> list[str]:
    out = []
    for c in cells:
        for p in (c.split(sep) if sep else [c]):
            p = re.sub(r"\s+", " ", p).strip()
            if p.lower() not in EMPTY and p not in out:
                out.append(p)
    return out


def detect_body_col(header, rows, bodies: set[str], skip: set[int]) -> int | None:
    for j, c in enumerate(header):
        if j in skip or not _hint(c, BODY_HINTS):
            continue
        vals = [r[j] for r in rows if r[j]]
        if vals and sum(norm_body(v) in bodies for v in vals) / len(vals) >= 0.8:
            return j
    return None


def norm_body(v: str) -> str:
    v = v.strip().upper()
    return BODY_ALIAS.get(v, v)


# ---------------------------------------------------------------------------------------------------- join
def join(header, rows, idx: Inputs, key_cols, label_cols, sep, body_col=None, body=None) -> tuple[list[dict], dict]:
    """-> (items [{id, labels, rows}], report {joined_by, not_joined: reason -> n, examples: reason -> [values]})."""
    rep = dict(rows=len(rows), joined_by=collections.Counter(), not_joined=collections.Counter(),
               examples=collections.defaultdict(list), merged_rows=0)
    pending, ambiguous = [], []
    for k, r in enumerate(rows, 1):
        labs = labels_of([r[j] for j in label_cols], sep)
        if not labs:
            rep["not_joined"]["no label"] += 1
            continue
        hit, why, val = None, None, None
        b = norm_body(r[body_col]) if body_col is not None and r[body_col] else (body.upper() if body else None)
        for j, kind, _ in key_cols:
            v = r[j]
            if not v:
                why = why or "empty key"; continue
            val = val or v
            if kind == "id":
                i = as_id(v)
                if i in idx.meta:
                    hit = ("id", i); break
                why = why or ("id not in the inputs" if i is not None else "id not a number")
            else:
                ids = idx.number_ids(v)
                if b:
                    ids = [i for i in ids if idx.meta[i]["body"] == b]
                if len(ids) == 1:
                    hit = ("number", ids[0]); break
                if len(ids) > 1:
                    if len({idx.meta[i]["body"] for i in ids}) == 1:   # one parliament, several affairs: the newest
                        hit = ("number", max(ids, key=lambda i: (idx.meta[i]["date"], i))); break
                    ambiguous.append((k, v, ids, labs)); hit = ("later", None); break
                why = why or ("number not in the inputs" + (f" for body {b}" if b else ""))
        if hit and hit[0] == "later":
            continue
        if not hit:
            rep["not_joined"][why or "empty key"] += 1
            if len(rep["examples"][why or "empty key"]) < 8:
                rep["examples"][why or "empty key"].append(val)
            continue
        rep["joined_by"][hit[0]] += 1
        pending.append((hit[1], labs))
    if ambiguous:   # a number in several parliaments: the body most other rows joined to, if clear
        bc = collections.Counter(idx.meta[i]["body"] for i, _ in pending)
        top = bc.most_common(1)[0] if bc else None
        dom = top[0] if top and top[1] >= 0.8 * sum(bc.values()) else None
        for k, v, ids, labs in ambiguous:
            pick = [i for i in ids if idx.meta[i]["body"] == dom] if dom else []
            if pick:
                rep["joined_by"][f"number (body {dom}, from the other rows)"] += 1
                pending.append((max(pick, key=lambda i: (idx.meta[i]["date"], i)), labs))
            else:
                why = "number in several parliaments (pass BODY= or a body column)"
                rep["not_joined"][why] += 1
                if len(rep["examples"][why]) < 8:
                    rep["examples"][why].append(f"{v} ({', '.join(sorted({idx.meta[i]['body'] for i in ids}))})")
    items: dict[int, dict] = {}
    for i, labs in pending:
        if i in items:
            rep["merged_rows"] += 1
            items[i]["labels"] += [l for l in labs if l not in items[i]["labels"]]
            items[i]["rows"] += 1
        else:
            items[i] = dict(id=i, labels=list(labs), rows=1)
    rep["joined_by"] = dict(rep["joined_by"]); rep["not_joined"] = dict(rep["not_joined"])
    rep["examples"] = dict(rep["examples"])
    return sorted(items.values(), key=lambda x: x["id"]), rep


# ---------------------------------------------------------------------------------------------------- scheme + keywords
def slugify(s: str, n: int = 40) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:n].strip("-") or "x"


def choose_labels(items: list[dict]) -> tuple[list[str], list[str]]:
    """-> (kept label names, alphabetical; dropped names). Primary-label frequency first, then any-label frequency."""
    prim = collections.Counter(x["labels"][0] for x in items)
    anyl = collections.Counter(l for x in items for l in x["labels"])
    order = sorted(anyl, key=lambda l: (-prim[l], -anyl[l], l))
    return sorted(order[:MAX_LABELS]), sorted(order[MAX_LABELS:])


def build_scheme(sid: str, names: list[str], lang: str, bodies: list[str], source: str, title: str) -> dict:
    f = FRAMES[lang]
    pre = sid.removeprefix("partner-")
    codes, seen = [], set()
    for nm in names:
        c = slugify(nm, 48); k = c; i = 2
        while k in seen:
            k = f"{c}-{i}"; i += 1
        seen.add(k); codes.append(f"{pre}:{k}")
    frame = {k: v for k, v in f.items() if k != "none"}
    doc = dict(id=sid, kind="named", status="test",
               title={lang: title, **({"de": title} if lang != "de" else {})}, source=source,
               frame={lang: frame, **({"de": frame} if lang != "de" else {})},
               options=[dict(code=c, name={lang: n, **({"de": n} if lang != "de" else {})}) for c, n in zip(codes, names)],
               none=dict(code=f"{pre}:none", name={lang: f["none"], **({"de": f["none"]} if lang != "de" else {})}))
    if len(bodies) == 1:
        doc["body"] = bodies[0]
    else:
        doc["bodies"] = bodies
    return doc


def scheme_yaml(doc: dict) -> str:
    head = ("# Generated by `make scheme-eval` from a partner's labels (names verbatim). `status: test` keeps it out of compose\n"
            "# and the static export (scheme.named_schemes); remove that line to ship the scheme. In `de` slots of a non-German\n"
            "# scheme: the frame and names verbatim in their own language (named_prompt reads `de`), as in ti-dipartimenti.yaml.\n")
    return head + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=120)


def keyword_stems(names: list[str]) -> dict[str, list[str]]:
    """S20 rule: first 5 letters of every word of 4+ letters (lower case); words in every name (3+ names) and a few
    function words (S29: articulated prepositions) left out."""
    words = {n: [w.lower() for w in re.findall(r"[^\W\d_]+", n) if len(w) >= 4] for n in names}
    common = set.intersection(*(set(v) for v in words.values())) if len(names) >= 3 else set()
    return {n: sorted({w[:5] for w in ws if w not in common and w not in KW_STOP}) for n, ws in words.items()}


def kw_predict(title: str, stems: dict[str, list[str]], forder: list[str]) -> str:
    t = (title or "").lower()
    sc = {n: sum(s in t for s in st) for n, st in stems.items()}
    best = max(sc.values()) if sc else 0
    return forder[0] if best == 0 else next(n for n in forder if sc.get(n, 0) == best)


# ---------------------------------------------------------------------------------------------------- sample
def stratified_sample(items: list[dict], n: int, seed: int = SEED) -> tuple[list[dict], str]:
    """Proportional to the primary label (largest remainders, ties by label name), random within each label."""
    if n >= len(items):
        return list(items), "all joined affairs"
    rng = random.Random(seed)
    by = collections.defaultdict(list)
    for x in sorted(items, key=lambda x: x["id"]):
        by[x["labels"][0]].append(x)
    N = len(items)
    quota = {l: n * len(v) / N for l, v in by.items()}
    alloc = {l: int(q) for l, q in quota.items()}
    rest = n - sum(alloc.values())
    for l in sorted(by, key=lambda l: (-(quota[l] - alloc[l]), l))[:rest]:
        alloc[l] += 1
    out = []
    for l in sorted(by):
        v = by[l][:]
        rng.shuffle(v)
        out += v[:alloc[l]]
    return sorted(out, key=lambda x: x["id"]), "proportional to the primary label (largest remainders)"


# ---------------------------------------------------------------------------------------------------- scoring
def argmax(v):
    return max(range(len(v)), key=lambda i: v[i])


def boot_diff(a: list[int], b: list[int], n: int = 2000, seed: int = SEED) -> dict:
    if not a:
        return dict(diff=None, ci=None)
    rng = random.Random(seed); N = len(a); ds = []
    for _ in range(n):
        s = [rng.randrange(N) for _ in range(N)]
        ds.append(sum(a[i] - b[i] for i in s) / N)
    ds.sort()
    d = (sum(a) - sum(b)) / N
    return dict(diff=_down(d, 4) if d >= 0 else -_down(-d, 4), ci=[_down(ds[int(0.025 * n)], 4), _up(ds[int(0.975 * n) - 1], 4)])


def score_arm(res: list[dict], names: list[str]) -> dict:
    """res: [{id, labels, rank (option indices, best first), lane, kw}] -> metrics."""
    N = len(res)
    k1 = [int(names[r["rank"][0]] == r["labels"][0]) for r in res]
    out = dict(n=N, top1=prop(sum(k1), N),
               top3=prop(sum(r["labels"][0] in [names[i] for i in r["rank"][:3]] for r in res), N),
               any_top1=prop(sum(names[r["rank"][0]] in r["labels"] for r in res), N),
               any_top3=prop(sum(any(names[i] in r["labels"] for i in r["rank"][:3]) for r in res), N))
    lanes = {}
    for ln in ("readings_agree", "please_check"):
        s = [r for r in res if r["lane"] == ln]
        lanes[ln] = dict(n=len(s), share=_down(len(s) / N, 4) if N else None,
                         top1=prop(sum(names[r["rank"][0]] == r["labels"][0] for r in s), len(s)))
    out["lanes"] = lanes
    per = {}
    for l in sorted({r["labels"][0] for r in res} | {names[r["rank"][0]] for r in res}):
        sup = [r for r in res if r["labels"][0] == l]; pred = [r for r in res if names[r["rank"][0]] == l]
        tp = sum(names[r["rank"][0]] == l for r in sup)
        per[l] = dict(support=len(sup), predicted=len(pred), recall=prop(tp, len(sup)) if sup else None,
                      precision=prop(tp, len(pred)) if pred else None)
    out["per_label"] = per
    return out, k1


def baselines(res: list[dict], titles: dict[int, str], stems: dict) -> tuple[dict, list[int], list[str]]:
    freq = collections.Counter(r["labels"][0] for r in res)
    forder = [l for l, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))] + sorted(l for l in stems if l not in freq)
    maj = forder[0] if forder else None
    kk = [int(kw_predict(titles.get(r["id"], ""), stems, forder) == r["labels"][0]) for r in res]
    N = len(res)
    return dict(majority=dict(label=maj, top1=prop(freq[maj], N) if maj else None), keyword=prop(sum(kk), N)), kk, forder


# ---------------------------------------------------------------------------------------------------- run helpers
def default_inputs() -> Path:
    for p in (os.environ.get("QS_INPUTS"), ROOT.parent / "data/inputs.jsonl.gz", ROOT / "data/inputs.jsonl.gz"):
        if p and Path(p).exists():
            return Path(p)
    raise SystemExit("no inputs file (QS_INPUTS, ../data/inputs.jsonl.gz or data/inputs.jsonl.gz)")


def sha(path: Path | bytes) -> str:
    return hashlib.sha256(path if isinstance(path, bytes) else Path(path).read_bytes()).hexdigest()[:12]


def rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        try:
            return "../" + str(Path(p).resolve().relative_to(ROOT.parent))
        except ValueError:
            return str(p)


def pin_build(out: Path, build: str | None, model: str) -> dict | None:
    """Pre-seed the run's build lock before the first call (as S29): --build <fp>, or runs/main's build when its model is
    the endpoint's model; 'first' = the batch locks the first served build."""
    st = out / "state.json"
    if st.exists():
        return json.loads(st.read_text()).get("lock")
    if build == "first":
        return None
    fp, src = build, "BUILD="
    if not fp:
        m = ROOT / "runs/main/state.json"
        lk = json.loads(m.read_text()).get("lock") if m.exists() else None
        if not lk or lk.get("model") != model or lk.get("mode") != P.mode():
            return None
        fp, src = lk["fp"], "runs/main"
    lock = dict(model=model, fp=fp, key=fp.split("-")[-1] + "-" + dt.date.today().strftime("%Y%m%d") +
                ("-" + P.mode() if P.mode() else ""), first_seen=dt.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
                note=f"pre-seeded by make scheme-eval before the first call (build from {src}); a call reporting another "
                     f"fingerprint stops the run")
    if P.mode():
        lock["mode"] = P.mode()
    (out / lock["key"]).mkdir(parents=True, exist_ok=True)   # the batch writes rows there (it creates it only when it locks)
    st.write_text(json.dumps(dict(lock=lock), indent=1))
    return lock


BATCH_IN_PROCESS = False   # tests: run the batch in this process (no subprocess)


def run_batch(args: list[str]) -> int:
    if BATCH_IN_PROCESS:
        from . import batch
        batch.main(["run"] + args)
        return 0
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src") + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else ""))
    return subprocess.call([sys.executable, "-m", "querschnitt.batch", "run"] + args, env=env, cwd=ROOT)


def prereg(mode: str, out: Path, title: str, body: str) -> str:
    """Append the entry with tools/prereg_append.py --no-push (mode 'log': eval/PREREG-BUILD.md; 'local': out/PREREG.md)."""
    f = out / "prereg_entry.md"
    f.write_text(body + "\n")
    if mode == "off":
        return "off (not pre-registered; the entry text is in " + rel(f) + ")"
    env = dict(os.environ)
    if mode == "local":
        env["QS_PREREG_LOG"] = str(out / "PREREG.md")
    else:
        env.pop("QS_PREREG_LOG", None)
    r = subprocess.run([sys.executable, "-I", str(ROOT / "tools/prereg_append.py"), title, str(f), "--no-push"], env=env,
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"pre-registration failed, no call made: {r.stderr.strip() or r.stdout.strip()}")
    where = rel(out / "PREREG.md") if mode == "local" else "eval/PREREG-BUILD.md"
    return f"{where} · {r.stdout.strip()}"


# ---------------------------------------------------------------------------------------------------- examples arm (S21)
def fold_pools(S: dict, items: list[dict], titles: dict[int, str], k: int) -> dict:
    """S21: two folds by OPD affair id parity; fold f's pool = its labelled affairs (title -> option index of the primary
    label). An affair of fold f takes its examples from the pool of fold 1 - f, so never itself."""
    from .examples import ExamplePool
    names = [o["name"]["de"] for o in S["options"]] + [S["none"]["name"]["de"]]
    ix = {l: i for i, l in enumerate(names)}
    return {f: ExamplePool([dict(oid=x["id"], title=titles[x["id"]], chapter=ix[x["labels"][0]]) for x in items
                            if x["id"] % 2 == f and x["labels"][0] in ix], k) for f in (0, 1)}


def examples_arm(S: dict, items: list[dict], sample: list[dict], full: dict[int, dict], titles: dict[int, str], k: int,
                 out: Path, lock: dict, rows: dict, cap: float, conc: int, max_rate: float) -> dict:
    """-> pid-keyed rows of the arm's new calls (written to out/examples, resumable)."""
    from .batch import Store as RunStore
    from .client import BuildChanged, Client, Endpoint
    from .engine import Engine
    n = len(S["options"]) + 1
    pools = fold_pools(S, items, titles, k)
    exd = out / "examples"
    exd.mkdir(parents=True, exist_ok=True)
    if not (exd / "state.json").exists():
        (exd / "state.json").write_text(json.dumps(dict(lock=lock), indent=1))
    (exd / lock["key"]).mkdir(exist_ok=True)
    st = RunStore(exd)
    if st.state["lock"]["fp"] != lock["fp"]:
        raise SystemExit(f"{exd}: locked to {st.state['lock']['fp']}, the first arm to {lock['fp']}; never mixed")
    ep = Endpoint.from_env(); ep.max_rate, ep.conc = max_rate, conc
    cl = Client(ep, ledger=str(out / "ledger.jsonl"), cap_usd=cap, expect_build=lock["fp"], tag="scheme-eval-ex")
    stop = threading.Event()
    eng = Engine(cl, None, stop)
    err = collections.Counter()

    def one(x):
        a = full.get(x["id"])
        if stop.is_set() or a is None:
            return
        ex = [(e["title"], e["chapter"]) for e in pools[1 - x["id"] % 2].neighbours(a)]
        try:
            u, p, _ = P.named_prompt(S, a, None, ex)
            if P.pid(u, p) not in st.done and P.pid(u, p) not in rows:
                st.write(dict(eng.named(S, a, examples=ex), aid=a["id"], ih=a.get("input_hash")))
            u, p, _ = P.named_prompt(S, a, P.named_perm(n))
            if P.pid(u, p) not in st.done and P.pid(u, p) not in rows:
                st.write(dict(eng.named(S, a, True), aid=a["id"], ih=a.get("input_hash")))
        except BuildChanged as e:
            stop.set(); (exd / "STOP.md").write_text(f"# Served build changed\n\n{e}\n")
        except Exception as e:  # noqa: BLE001 — counted; the affair is not scored, a rerun resumes it
            err[type(e).__name__] += 1
            with open(exd / "errors.jsonl", "a") as f:
                f.write(json.dumps(dict(aid=x["id"], err=repr(e)[:300])) + "\n")
            if "BUDGET" in str(e):
                stop.set()

    with ThreadPoolExecutor(conc) as tp:
        list(tp.map(one, sample))
    return dict(errors=dict(err), stopped=stop.is_set())


def arm_results(S, sample, full, rows, examples_k=0, pools=None) -> tuple[list[dict], int]:
    names = [o["name"]["de"] for o in S["options"]] + [S["none"]["name"]["de"]]
    n = len(names)
    res, missing = [], 0
    for x in sample:
        a = full.get(x["id"])
        if a is None:            # gone from the inputs since the plan
            missing += 1; continue
        if examples_k:
            ex = [(e["title"], e["chapter"]) for e in pools[1 - x["id"] % 2].neighbours(a)]
            ra = rows.get(P.pid(*P.named_prompt(S, a, None, ex)[:2]))
            rb = rows.get(P.pid(*P.named_prompt(S, a, P.named_perm(n))[:2]))
            if not (ra and rb):
                missing += 1; continue
        else:
            ra = rows.get(P.pid(*P.named_prompt(S, a)[:2]))
            rb = rows.get(P.pid(*P.named_prompt(S, a, P.named_perm(n))[:2])) if ra and max(ra["p"]) < 0.9 else None
            if not ra or (max(ra["p"]) < 0.9 and not rb):
                missing += 1; continue
        pm = [(u + v) / 2 for u, v in zip(ra["p"], rb["p"])] if rb else list(ra["p"])
        lane = "please_check" if rb and argmax(ra["p"]) != argmax(rb["p"]) else "readings_agree"
        res.append(dict(id=x["id"], labels=[l for l in x["labels"]], rank=sorted(range(n), key=lambda i: (-pm[i], i)),
                        lane=lane, p=round(pm[argmax(pm)], 4), fps=sorted({ra["meta"]["fp"], *([rb["meta"]["fp"]] if rb else [])})))
    return res, missing


# ---------------------------------------------------------------------------------------------------- report
def fmt_d(d: dict) -> str:
    if not d or d.get("diff") is None:
        return "–"
    return f"{d['diff']:+.3f} [{_down(d['ci'][0], 3):+.3f}, {_up(d['ci'][1], 3):+.3f}]"


def report_text(R: dict) -> str:
    j = R["join"]; L = []
    L.append(f"gold {R['gold']} · {j['rows']} rows · label {' + '.join('«' + c + '»' for c in R['label_cols'])}"
             f"{' (cells split on ' + repr(R['sep']) + ')' if R['sep'] else ''} · key «{R['key_col']}» ({R['key_kind']})")
    nj = sum(j["not_joined"].values())
    L.append(f"joined {sum(j['joined_by'].values())} rows → {R['n_joined']} affairs ("
             + ", ".join(f"by {k} {v}" for k, v in j["joined_by"].items()) + f"; {j['merged_rows']} rows merged into affairs listed twice)"
             + (f" · not joined {nj}: " + "; ".join(f"{k} {v}" + (f" (e.g. {', '.join(map(str, j['examples'][k][:4]))})" if j['examples'].get(k) else "")
                                                  for k, v in j["not_joined"].items()) if nj else ""))
    if R.get("dropped_labels"):
        L.append(f"labels beyond the {MAX_LABELS} most frequent dropped: {len(R['dropped_labels'])} ({R['n_dropped_items']} affairs left out)")
    L.append(f"scheme {R['scheme']} ({rel(Path(R['scheme_file']))}) · {R['n_labels']} labels + none · frame {R['lang']} · "
             f"{'body ' + R['body'] if R.get('body') else str(len(R.get('bodies') or [])) + ' bodies'}")
    L.append(f"sample {R['n_sample']} of {R['n_joined']} ({R['strat']}, random.Random(2026)) · build {R.get('build')} · "
             f"USD {R['usd']:.4f} list price · pre-registration {R['prereg']}")
    for arm in ("names", "examples"):
        A = R["arms"].get(arm)
        if not A:
            continue
        head = "names only (shipped named step)" if arm == "names" else f"with {R['examples']} examples of the other fold (S21 shape)"
        L.append(f"\n{head} · scored {A['n']} · not scored {A['not_scored']}")
        if not A["n"]:
            continue
        L.append(f"  top-1 {fmt_p(A['top1'])} · top-3 {fmt_p(A['top3'])}")
        L.append(f"  any label at top-1 {fmt_p(A['any_top1'])} · any label in top-3 {fmt_p(A['any_top3'])}")
        la = A["lanes"]
        L.append(f"  lanes: readings agree {la['readings_agree']['n']} ({la['readings_agree']['share']}) top-1 "
                 f"{fmt_p(la['readings_agree']['top1'])} · disagree {la['please_check']['n']} ({la['please_check']['share']}) top-1 "
                 f"{fmt_p(la['please_check']['top1'])}")
        b = A["baselines"]
        L.append(f"  baselines: majority «{b['majority']['label']}» {fmt_p(b['majority']['top1'])} · keyword {fmt_p(b['keyword'])}"
                 f" · Apertus − keyword {fmt_d(A['minus_keyword'])}")
    if R["arms"].get("examples_minus_names"):
        d = R["arms"]["examples_minus_names"]
        L.append(f"\nexamples − names, paired on {d['n']} affairs: {fmt_d(d)}")
    A = R["arms"].get("examples") or R["arms"].get("names")
    if A and A.get("n"):
        L.append(f"\nper label ({'examples' if R['arms'].get('examples') else 'names only'} arm; support ≥ 1, by support):")
        for l, v in sorted(A["per_label"].items(), key=lambda kv: (-kv[1]["support"], kv[0])):
            if v["support"]:
                L.append(f"  {l[:44]:44} n {v['support']:>4}  recall {fmt_p(v['recall'])}  precision {fmt_p(v['precision'])}")
    return "\n".join(L)


# ---------------------------------------------------------------------------------------------------- main
def plan(a) -> dict:
    gold = Path(a.gold)
    if not gold.exists():
        raise SystemExit(f"no such file: {gold}")
    header, rows, meta = read_table(gold, a.sheet)
    inputs = Path(a.inputs) if a.inputs else default_inputs()
    print(f"reading {rel(inputs)} …", flush=True)
    idx = Inputs.load(inputs)
    keys, rates = detect_key(header, rows, idx, a.id)
    skip = {k[0] for k in keys}
    body_col = header.index(a.body_col) if a.body_col else detect_body_col(header, rows, idx.bodies, skip)
    if body_col is not None:
        skip.add(body_col)
    lcols = detect_label(header, rows, a.label, skip)
    sep = choose_sep([r[j] for r in rows for j in lcols], a.sep)
    items, rep = join(header, rows, idx, keys, lcols, sep, body_col, a.body)
    if not items:
        raise SystemExit("no row joined: " + json.dumps(rep["not_joined"], ensure_ascii=False))
    kept, dropped = choose_labels(items)
    n_drop = 0
    if dropped:
        keep = set(kept)
        before = len(items)
        items = [dict(x, labels=[l for l in x["labels"] if l in keep]) for x in items if x["labels"][0] in keep]
        n_drop = before - len(items)
    slug = slugify(a.name or gold.stem)
    sid = f"partner-{slug}"
    langs = collections.Counter(idx.meta[x["id"]]["lang"] for x in items)
    lang = a.lang or next((l for l, _ in langs.most_common() if l in FRAMES), "de")
    bodies = sorted({idx.meta[x["id"]]["body"] for x in items})
    parl = next((idx.meta[x["id"]]["parl"] for x in items if idx.meta[x["id"]].get("parl")), "") if len(bodies) == 1 else ""
    who = a.who or (f"{parl} ({bodies[0]})" if parl else bodies[0] if len(bodies) == 1 else "the partner")
    src = (f"Label names verbatim from {gold.name} (sha256 {sha(gold)}), column{'s' if len(lcols) > 1 else ''} "
           + ", ".join(f"«{header[j]}»" for j in lcols) + f"; {len(kept)} distinct labels; alphabetical order; no "
           f"descriptions added. Generated by make scheme-eval {dt.date.today().isoformat()}.")
    S = build_scheme(sid, kept, lang, bodies, src, a.title or f"Eigenes Schema: {gold.stem} ({len(kept)} Themen)")
    sample, strat = stratified_sample(items, a.n)
    titles = {x["id"]: idx.meta[x["id"]]["title"] for x in items}
    return dict(gold=gold, header=header, meta=meta, rates=rates, keys=keys, body_col=body_col, lcols=lcols, sep=sep,
                items=items, rep=rep, kept=kept, dropped=dropped, n_drop=n_drop, slug=slug, sid=sid, lang=lang, langs=langs,
                bodies=bodies, who=who, S=S, sample=sample, strat=strat, titles=titles, inputs=inputs, idx=idx)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="querschnitt scheme-eval", description=__doc__.split("\n\n")[0])
    ap.add_argument("gold", help="CSV or XLSX: one row per affair (or per affair and label)")
    ap.add_argument("--id", help="key column (OPD affair id or business number); default: detected from the data")
    ap.add_argument("--label", help="label column; several joined by + (first = primary); default: detected")
    ap.add_argument("--sep", help="separator between several labels in one cell (| ; , \\n, or none); default: detected")
    ap.add_argument("--body", help="parliament (OPD body key, e.g. CHE, BS) for business numbers without a body column")
    ap.add_argument("--body-col", help="column holding the body key per row")
    ap.add_argument("--sheet", help="XLSX sheet name (default: the first)")
    ap.add_argument("--name", help="slug for the scheme and run dir (default: the file name)")
    ap.add_argument("--title", help="scheme title"); ap.add_argument("--who", help="the partner's name in the pre-registration")
    ap.add_argument("--lang", choices=sorted(FRAMES), help="frame language (default: the joined affairs' majority)")
    ap.add_argument("--n", type=int, default=200); ap.add_argument("--examples", type=int, default=5)
    ap.add_argument("--cap", type=float, default=2.0, help="list-price cap in USD for this run dir's ledger")
    ap.add_argument("--conc", type=int, default=2); ap.add_argument("--max-rate", type=float, default=0.5)
    ap.add_argument("--build", help="pin the build (a fingerprint), or 'first' (the first served build); default runs/main's")
    ap.add_argument("--prereg", choices=["log", "local", "off"], default="log",
                    help="log: eval/PREREG-BUILD.md (--no-push); local: the run dir's PREREG.md (tooling checks)")
    ap.add_argument("--inputs", help="inputs.jsonl.gz (default QS_INPUTS, ../data/inputs.jsonl.gz, data/inputs.jsonl.gz)")
    ap.add_argument("--out", help="run dir (default runs/scheme-<slug>)")
    ap.add_argument("--dry-run", action="store_true", help="read, join, scheme, sample; no file in schemes/, no call")
    ap.add_argument("--register-only", action="store_true",
                    help="write the scheme file and the pre-registration, then stop (push it, then rerun without this)")
    a = ap.parse_args(argv)
    from .client import Endpoint
    ep = Endpoint.from_env()
    if "-70b" in ep.model.lower():
        raise SystemExit(f"QS_MODEL={ep.model}: the -70b route is answered by another model; use the 8b model")
    if a.examples < 0 or a.n < 1:
        raise SystemExit("--n ≥ 1 and --examples ≥ 0")
    pl = plan(a)
    S, sid, slug, items, sample = pl["S"], pl["sid"], pl["slug"], pl["items"], pl["sample"]
    out = Path(a.out) if a.out else ROOT / "runs" / f"scheme-{slug}"
    out.mkdir(parents=True, exist_ok=True)
    names = [o["name"]["de"] for o in S["options"]] + [S["none"]["name"]["de"]]
    hdr, rep = pl["header"], pl["rep"]
    key_col, key_kind = hdr[pl["keys"][0][0]], pl["keys"][0][1]
    # scheme file (compared on what the prompt reads: frame, options, none)
    sfile = SCH.HERE / f"{sid}.yaml"
    if sfile.exists() and not a.dry_run:
        old = yaml.safe_load(sfile.read_text())
        if [old.get(k) for k in ("frame", "options", "none")] != [S.get(k) for k in ("frame", "options", "none")]:
            raise SystemExit(f"{rel(sfile)} exists with other labels or frame; use --name <other> or delete it")
    text = scheme_yaml(S)
    (out / "scheme.yaml").write_text(text)
    if not a.dry_run:
        if not sfile.exists():
            sfile.write_text(text)
        SCH.flat.cache_clear()
    stems = keyword_stems(names[:-1])
    kwf = out / "keywords_frozen.json"
    if kwf.exists() and set(json.loads(kwf.read_text())["stems"]) != set(stems):   # e.g. a dry run with another LABEL=
        if (out / "ledger.jsonl").exists():
            raise SystemExit(f"{rel(out)} has calls for another label set; use NAME=<other> for this one")
        kwf.unlink()
    if not kwf.exists():   # frozen before any call; never rewritten once a call is made
        kwf.write_text(json.dumps(dict(note=f"keyword baseline for {sid}, frozen {dt.datetime.now().astimezone():%Y-%m-%d %H:%M %Z} "
                                            "before any call of this run (make scheme-eval): first 5 letters of every word of "
                                            "4+ letters of the label name (lower case), words in every name and a few function "
                                            "words left out; prediction = the label with the most stem hits in the title "
                                            "(case-insensitive substring); ties and no hit -> the first among the tied in the "
                                            "frequency order of the primary label on the scored items (computed at scoring).",
                                       stems=stems), ensure_ascii=False, indent=1))
    stems = json.loads(kwf.read_text())["stems"]
    ids_txt = "\n".join(str(x["id"]) for x in sample) + "\n"
    (out / "ids.txt").write_text(ids_txt)
    plan_d = dict(gold=str(pl["gold"]), gold_sha=sha(pl["gold"]), table=pl["meta"], key_rates=pl["rates"],
                  key=[dict(col=hdr[j], kind=k, rate=r) for j, k, r in pl["keys"]], label_cols=[hdr[j] for j in pl["lcols"]],
                  sep=pl["sep"], body_col=hdr[pl["body_col"]] if pl["body_col"] is not None else None, join=rep,
                  n_joined=len(items), labels=pl["kept"], dropped_labels=pl["dropped"], n_dropped_items=pl["n_drop"],
                  scheme=sid, lang=pl["lang"], bodies=pl["bodies"], n_sample=len(sample), strat=pl["strat"],
                  examples=a.examples, ids_sha=sha(ids_txt.encode()))
    (out / "plan.json").write_text(json.dumps(plan_d, ensure_ascii=False, indent=1, default=str))
    jl = ", ".join(f"by {k} {v}" for k, v in rep["joined_by"].items())
    nj = "; ".join(f"{k} {v}" for k, v in rep["not_joined"].items())
    print(f"key «{key_col}» ({key_kind}) · labels {' + '.join(hdr[j] for j in pl['lcols'])}"
          f"{' split on ' + repr(pl['sep']) if pl['sep'] else ''} · joined {len(items)} affairs ({jl})"
          + (f" · not joined: {nj}" if nj else "") + f" · {len(pl['kept'])} labels · frame {pl['lang']} · sample {len(sample)}")
    if a.dry_run:
        print(f"dry run: plan in {rel(out)}/plan.json, scheme draft {rel(out)}/scheme.yaml; nothing called, nothing registered")
        return 0
    lock = pin_build(out, a.build, ep.model)
    if (out / "STOP.md").exists():
        raise SystemExit(f"{rel(out)}/STOP.md exists: read it (a build change: --build first in a new --name), remove it, rerun")
    # pre-registration, once per plan (a changed plan, e.g. the examples arm added, is a new entry before its calls)
    phash = sha(json.dumps({k: plan_d[k] for k in ("gold_sha", "labels", "ids_sha", "examples", "scheme", "lang")},
                           ensure_ascii=False, sort_keys=True).encode())
    reg_f = out / "prereg.json"
    regs = json.loads(reg_f.read_text()) if reg_f.exists() else {}
    if phash not in regs:
        js = "; ".join(f"{k} {v}" for k, v in rep["not_joined"].items())
        body = PREREG.format(
            who=pl["who"], q_ex=f", and with {a.examples} of their own labelled affairs as examples" if a.examples else "",
            gold=rel(pl["gold"]), gold_sha=plan_d["gold_sha"], n_rows=rep["rows"],
            label_cols=" + ".join(f"«{c}»" for c in plan_d["label_cols"]),
            multi=f", cells split on {pl['sep']!r}" if pl["sep"] else "", key_col=key_col,
            key_kind="OPD affair id" if key_kind == "id" else "business number joined by (body, number)",
            inputs=rel(pl["inputs"]), n_joined=len(items), join_line=jl + (f"; not joined: {js}" if js else ""),
            sid=sid, n_labels=len(pl["kept"]), none=S["none"]["name"]["de"], lang=pl["lang"],
            body_line=f"body {S['body']}" if S.get("body") else f"{len(pl['bodies'])} bodies",
            n_sample=len(sample), strat=pl["strat"], slug=slug, ids_sha=plan_d["ids_sha"],
            arm_ex=PREREG_EX.format(n_joined=len(items), k=a.examples) if a.examples else "",
            sec_ex=" Examples arm: the same outcomes, and examples − names paired on the same affairs (bootstrap as below)."
            if a.examples else "", kw_sha=sha(kwf), conc=a.conc, max_rate=a.max_rate, cap=a.cap, model=ep.model,
            endpoint=ep.base_url, build_line=(f"build locked before the first call to {lock['fp']} (a call reporting another "
                                              f"fingerprint stops the run)." if lock else "build locked to the first served "
                                              "fingerprint (a later call reporting another stops the run)."))
        title = f"make scheme-eval {sid}: own labels of {pl['who']} (before any call of this run)"
        where = prereg(a.prereg, out, title, body)
        regs[phash] = dict(at=dt.datetime.now().astimezone().isoformat(timespec="seconds"), where=where, title=title)
        reg_f.write_text(json.dumps(regs, indent=1, ensure_ascii=False))
        print(f"pre-registered: {where}")
    if a.register_only:
        print(f"registered, no call made (entry text {rel(out)}/prereg_entry.md); push eval/PREREG-BUILD.* if it should be "
              f"public first, then rerun the same command without REGISTER=1 (it finds the entry and starts the calls)")
        return 0
    # arm 1: the shipped named step through the batch runner
    cmd = ["--inputs", str(pl["inputs"]), "--out", str(out), "--ids", str(out / "ids.txt"), "--topics", "--steps",
           "--named", sid, "--conc", str(a.conc), "--max-rate", str(a.max_rate), "--cap", str(a.cap)]
    (out / "ARGS").write_text(" ".join(cmd) + "\n")
    print("batch " + " ".join(cmd), flush=True)
    rc = run_batch(cmd)
    if (out / "STOP.md").exists():
        print(f"batch stopped: {(out / 'STOP.md').read_text()[:400]}")
    elif rc:
        print(f"batch exited {rc}")
    from .batch import load_inputs
    from .compose import read_run
    if not (out / "state.json").exists() or "lock" not in json.loads((out / "state.json").read_text()):
        raise SystemExit("no call answered (no build lock): see the batch output above")
    lock, rows = read_run(out)
    full = {x["id"]: x for x in load_inputs(pl["inputs"], ids={x["id"] for x in sample})}
    titles = pl["titles"]
    R = dict(gold=rel(pl["gold"]), **{k: plan_d[k] for k in ("label_cols", "sep", "join", "n_joined", "dropped_labels",
                                                             "n_dropped_items", "scheme", "lang", "n_sample", "strat")},
             key_col=key_col, key_kind=key_kind, scheme_file=str(sfile), n_labels=len(pl["kept"]), body=S.get("body"),
             bodies=pl["bodies"], examples=a.examples, build=lock["fp"], model=lock["model"], mode=lock.get("mode"),
             prereg=regs[phash]["where"], arms={})
    names_res, miss = arm_results(S, sample, full, rows)
    ex_res = None
    if a.examples and not (out / "STOP.md").exists():
        print(f"examples arm: {len(sample)} affairs, {a.examples} examples each from the other fold", flush=True)
        info = examples_arm(S, items, sample, full, titles, a.examples, out, lock, rows, a.cap, a.conc, a.max_rate)
        if info["errors"] or info["stopped"]:
            print(f"examples arm: errors {info['errors']} stopped {info['stopped']} (rerun the same command to resume)")
    if a.examples and (out / "examples" / "state.json").exists():
        lock2, rows2 = read_run(out, out / "examples")
        pools = fold_pools(S, items, titles, a.examples)
        ex_res, miss2 = arm_results(S, sample, full, rows2, a.examples, pools)
    for arm, res, m in (("names", names_res, miss), ("examples", ex_res, miss2 if ex_res is not None else 0)):
        if res is None:
            continue
        A, k1 = score_arm(res, names)
        b, kk, forder = baselines(res, titles, stems)
        A.update(not_scored=m, baselines=b, minus_keyword=boot_diff(k1, kk), freq_order=forder[:10],
                 builds=sorted({f for r in res for f in r["fps"]}))
        R["arms"][arm] = A
    if ex_res:
        a1 = {r["id"]: int(names[r["rank"][0]] == r["labels"][0]) for r in names_res}
        a2 = {r["id"]: int(names[r["rank"][0]] == r["labels"][0]) for r in ex_res}
        both = sorted(set(a1) & set(a2))
        R["arms"]["examples_minus_names"] = dict(n=len(both), **boot_diff([a2[i] for i in both], [a1[i] for i in both]))
    R["usd"] = round(sum(json.loads(l)["usd"] for l in open(out / "ledger.jsonl")), 5) if (out / "ledger.jsonl").exists() else 0.0
    R["items"] = {arm: [dict(id=r["id"], labels=r["labels"], top3=[names[i] for i in r["rank"][:3]], p=r["p"], lane=r["lane"])
                        for r in res] for arm, res in (("names", names_res), ("examples", ex_res or [])) if res}
    (out / "report.json").write_text(json.dumps(R, ensure_ascii=False, indent=1))
    print("\n" + report_text(R))
    print(f"\n→ {rel(out)}/report.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
