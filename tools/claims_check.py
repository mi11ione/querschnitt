#!/usr/bin/env python3
"""claims_check: flag every number in a Markdown/HTML file that is not backed by eval/claims.tsv or eval/pruefstand.json.

Usage:  python3 -I tools/claims_check.py README.md docs/REPORT.md pitch.md [--claims eval/claims.tsv] [--pruefstand eval/pruefstand.json]
        [--allow 2.5,7] [--quiet]
Exit code 1 when anything is flagged.

A number passes when its normalised form equals the "written" value of a claims.tsv row with status OK or ROUNDED, or a value
stored in pruefstand.json (exactly as stored, or at 3 decimals / as a percentage with the same digits). A number that only matches a
MISMATCH row is reported with the correct value from that row. Section refs (§6.1), test ids (S9, D3, P8.5), years, calendar days,
clock times, inline code and HTML tags are skipped. Spelled-out ratios ("seven in ten") are checked as "7 in 10". Stdlib only."""
import argparse, csv, html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORDS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
                                     "sixteen seventeen eighteen nineteen twenty".split())}
MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?"
SKIP = [
    r"^\s*#+\s*\d+(?:\.\d+)*\.?",                  # heading numbers "## 6.1"
    r"^\s*\d+\.\s",                               # ordered-list markers
    r"\bp\d{2}\b|\bGate \d\b",                     # percentile names (p90), "Gate 1"
    r"`[^`]*`",                                    # inline code
    r"<[^>]+>",                                    # HTML tags
    r"\]\([^)]*\)",                                # markdown link targets
    r"https?://\S+",
    r"§\s?\d+(?:\.\d+)*",                          # section refs
    r"\b(?:S\d+[a-z]?|[DPHVEQRAMLC]\d+(?:\.\d+)?[a-z]?|W\d\d|G\d)\b",  # test / design / step ids (S9c, D3, P8.5, L1, E6 …)
    r"\btop-\d\b|\btop\s\d\b|\bF1\b",              # metric names (top-1, F1)
    r"\b\d{4}-\d{2}-\d{2}(?:T[\d:.]+Z?)?\b",       # ISO dates
    r"\b\d{1,2}:\d{2}(?:[–-]\d{1,2}:\d{2})?\b",    # clock times / pitch timings
    r"\b\d{1,2}\s?(?:[–-]\s?\d{1,2}\s)?" + MONTHS, # calendar days "16 Sep", "1 Jan"
    r"\b(?:19[5-9]\d|20[0-4]\d)(?:[–-]\d{2,4})?\b",  # years and year ranges
    r"\bv\d+(?:\.\d+)*\b|\b\d+\.\d+\.\d+\b",       # versions, APS codes like 1.7.2
    r"\b\d+(?:\.\d+)?[bB]\b|\b\d+B\b",             # model sizes 8b / 70B
    r"\b[A-Z]{2,}-\d+\b",                          # identifiers like CC-BY-4.0 fragments
    r"\bCC[- ]BY[- ]\d\.\d\b|Apache-2\.0|CDLA-Permissive-2\.0",
]
SKIP_RE = re.compile("|".join(SKIP))
NUM_RE = re.compile(
    r"(?<![A-Za-z_\d.])(?:"
    r"(?P<frac>\d+(?:[,']\d{3})*\s?/\s?\d+(?:[,']\d{3})*)"                      # 27/30
    r"|(?P<num>[−\-+]?\d{1,3}(?:[,'’ ]\d{3})+(?:\.\d+)?%?|[−\-+]?\d*\.?\d+%?))")
WORD_RATIO = re.compile(r"\b(" + "|".join(WORDS) + r")\s+in\s+(" + "|".join(WORDS) + r")\b", re.I)


def norm(tok):
    """'1,357' -> '1357'; '−0.021' -> '-0.021'; '+0.049' -> '0.049'; '91 %' -> '91%'; '27 / 30' -> '27/30'."""
    t = tok.strip().replace("−", "-").replace("–", "-").replace(" ", "").replace(" ", "")
    t = re.sub(r"(?<=\d)[,'’ ](?=\d{3}\b)", "", t)
    t = t.replace(" ", "")
    if t.startswith("+"): t = t[1:]
    if t.startswith("-0") or t.startswith("-."): pass
    if re.fullmatch(r"-?\.\d+%?", t): t = t.replace(".", "0.", 1)
    return t


def extract(text):
    """-> list of (line_no, token_as_written, normalised)."""
    out = []
    for ln, line in enumerate(text.splitlines(), 1):
        for m in WORD_RATIO.finditer(line):
            out.append((ln, m.group(0), f"{WORDS[m.group(1).lower()]} in {WORDS[m.group(2).lower()]}"))
        clean = SKIP_RE.sub(lambda m: " " * len(m.group(0)), line)
        for m in NUM_RE.finditer(clean):
            tok = m.group(0)
            if re.fullmatch(r"[+\-−]", tok): continue
            out.append((ln, tok.strip(), norm(tok)))
    return out


def variants(v):
    """String forms a stored number may legitimately take in prose (no rounding beyond what is stored)."""
    s = set()
    if isinstance(v, bool) or v is None: return s
    if isinstance(v, (int, float)):
        s.add(norm(repr(v)) if isinstance(v, float) else str(v))
        if isinstance(v, float):
            for d in (1, 2, 3, 4):
                f = f"{v:.{d}f}"
                if float(f) == round(v, d) and abs(float(f) - v) < 1e-12: s.add(norm(f))
            if abs(v) >= 100:
                s.add(str(round(v))); s.add(norm(f"{v:.1f}"))   # estimated counts: whole affairs
            if abs(v * 1000 - round(v * 1000)) > 1e-9:
                s.add(norm(f"{v:.3f}"))   # 3-decimal display used by every results.md
            if 0 <= v <= 1:
                pct = v * 100
                if abs(pct - round(pct, 1)) < 1e-9: s.add(norm(f"{round(pct, 1):g}%"))
    elif isinstance(v, str) and re.fullmatch(r"[−\-+]?[\d.,]+%?|\d+/\d+", v.strip()):
        s.add(norm(v))
    return s


WORD = re.compile(r"[A-Za-zÀ-ÿ]{4,}")


def same_claim(rows, line):
    """A MISMATCH row whose context shares most of its words with this line (the sentence was reused)."""
    words = {w.lower() for w in WORD.findall(line)}
    for r in rows:
        ctx = {w.lower() for w in WORD.findall(r.get("context") or "")}
        if len(ctx) >= 3 and len(ctx & words) >= 0.6 * len(ctx):
            return r
    return None


def load_claims(path):
    ok, bad = {}, {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            st = (r.get("status") or "").strip()
            for tok in re.split(r"\s*\|\s*", r.get("written", "")):
                if not tok: continue
                toks = [x[2] for x in extract(tok)] or [norm(tok)]
                for n in toks:
                    if st in ("OK", "ROUNDED"): ok.setdefault(n, r)
                    elif st == "MISMATCH": bad.setdefault(n, []).append(r)
    return ok, bad


PATH_KEYS = {"file", "key", "anchor", "build", "system_fingerprint", "model", "judge_build", "source", "sources", "raw", "items",
             "rules", "schema", "generated_utc", "date", "paths_relative_to", "endpoint", "ci_at", "training_size_at", "line", "lines", "prereg", "prereg_more"}


def load_pruefstand(path):
    vals = set()
    def walk(o, key=None):
        if key in PATH_KEYS: return
        if isinstance(o, dict):
            for k, v in o.items(): walk(v, k)
        elif isinstance(o, list):
            for v in o: walk(v, key)
        elif isinstance(o, str):
            vals.update(variants(o)); vals.update(x[2] for x in extract(o))
        else:
            vals.update(variants(o))
    if os.path.exists(path):
        walk(json.load(open(path, encoding="utf-8")))
    return vals


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="+")
    ap.add_argument("--claims", default=os.path.join(ROOT, "eval", "claims.tsv"))
    ap.add_argument("--pruefstand", default=os.path.join(ROOT, "eval", "pruefstand.json"))
    ap.add_argument("--allow", default="", help="comma-separated extra numbers to accept (e.g. 5,2)")
    ap.add_argument("--quiet", action="store_true", help="print only flagged numbers")
    a = ap.parse_args(argv)
    ok, bad = load_claims(a.claims)
    ps = load_pruefstand(a.pruefstand)
    allow = {norm(x) for x in a.allow.split(",") if x.strip()}
    flagged = 0
    for fn in a.files:
        text = open(fn, encoding="utf-8").read()
        if fn.endswith((".html", ".htm")):
            text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", text)
            text = html.unescape(re.sub(r"<br\s*/?>|</p>|</li>|</tr>|</h\d>", "\n", text))
        n_ok = 0
        lines = text.splitlines()
        for ln, tok, n in extract(text):
            hit = same_claim(bad.get(n, []), lines[ln - 1])
            if hit is None and (n in ok or n in ps or n in allow):
                n_ok += 1; continue
            flagged += 1
            if hit is not None or n in bad:
                r = hit or bad[n][0]
                print(f"{fn}:{ln}: MISMATCH {tok!r} -> write {r.get('correct') or r.get('source_value')} "
                      f"(source {r.get('source_value')}, {r.get('file')} {r.get('key')}) {r.get('note', '')}".rstrip())
            else:
                print(f"{fn}:{ln}: NOT IN CLAIMS {tok!r}")
        if not a.quiet:
            print(f"{fn}: {n_ok} numbers backed", file=sys.stderr)
    if not a.quiet:
        print(f"flagged: {flagged}", file=sys.stderr)
    return 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(main())
