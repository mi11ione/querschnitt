#!/usr/bin/env python3
"""render: docs/REPORT.md -> one print-ready HTML page (tools/report/report.css, the app's own fonts from app/fonts, figures
from docs/img). tools/report/chrome.mjs then prints it to A4 PDF; `make report` runs both -> dist/querschnitt-report.pdf.

Usage:  python3 tools/report/render.py [docs/REPORT.md] [--out dist/querschnitt-report.html] [--date 2026-10-19]

The Markdown is rendered as written (CommonMark + tables, markdown-it-py). Added around it, never inside it: the title block
(date, repository, live app, commit), three figures with one-line captions placed after the sections named in FIGURES, and
typesetting only: relative links become absolute GitHub links, numbers in tables and every [lo, hi] interval are set in
Fragment Mono, all-numeric table columns are right-aligned. REPORT_DATE=YYYY-MM-DD (or --date) fixes the printed date."""
import argparse, datetime, html, os, posixpath, re, subprocess, sys

try:
    from markdown_it import MarkdownIt
except ImportError:
    sys.exit("render.py needs markdown-it-py: make install (dev extras), or .venv/bin/pip install 'markdown-it-py>=3'")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
REPO = "https://github.com/mi11ione/querschnitt"
LIVE = "https://querschnitt.mi11ion.io"
CHALLENGE = "Hack Apertus Liebefeld, 18–19 Oct 2026 · challenge «Topic classification for OpenParlData»"

# (where, image, caption, narrow). where: "lead" = after the opening paragraphs, before the first section;
# otherwise a regex on a section heading, and the figure closes that section. A figure whose heading is gone goes to the end.
FIGURES = [
    ("lead", "docs/img/ueberblick.png",
     "Überblick in the app (German interface): one small Switzerland per topic, every canton shaded by the topic's share "
     "of its affairs; at right, this week's affairs.", False),
    (r"method", "docs/img/entscheid.png",
     "Why this label: an affair of Bern's Grand Council, the chapter asked in German and in French, two different answers, "
     "so a person checks: the German version of a question about public wifi reads as telecoms, the French one as environment.", False),
    (r"results on human labels", "docs/img/pruefstand.png",
     "Prüfstand, held-out APS chapters: precision against coverage on the 927 new federal affairs (black) and the 1,357 "
     "design affairs (grey). Red: the shipped cut, recalibrated p ≥ 0.7.", True),
]

NUM = r"[+−-]?\d+(?:[.,]\d+)*%?"
INTERVAL = re.compile(r"\[\s*" + NUM + r"\s*,\s*" + NUM + r"\s*\]")
EST_CI = re.compile(r"(?<![\w.,])(" + NUM + r")(\s+)(?=\x00)")      # a point estimate right before its interval
TABLE_NUM = re.compile(r"(?<![\w.,/\[−+-])" + NUM + r"(?![\w])")
NUMERIC_CELL = re.compile(r"^\s*[+−-]?[\d.,\s]+%?\s*$")


def github_url(href, src_dir):
    """../eval/claims.tsv (relative to docs/) -> https://github.com/.../blob/main/eval/claims.tsv; external links unchanged."""
    if re.match(r"^[a-z][a-z0-9+.-]*:", href, re.I) or href.startswith(("#", "//")):
        return href
    path, _, frag = href.partition("#")
    rel = posixpath.normpath(posixpath.join(src_dir, path)) if path else src_dir
    if rel.startswith(".."):
        return href
    kind = "tree" if os.path.isdir(os.path.join(ROOT, rel)) else "blob"
    return f"{REPO}/{kind}/main/{rel}" + (f"#{frag}" if frag else "")


def plain(inline_tok):
    return "".join(c.content for c in (inline_tok.children or []) if c.type in ("text", "code_inline"))


def prepare(tokens, src_dir):
    """Token pass: absolute links, lane code mark, numeric table columns, sub-rows that start with a dash."""
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t.type == "inline":
            for c in t.children or []:
                if c.type in ("link_open",):
                    c.attrSet("href", github_url(c.attrGet("href") or "", src_dir))
                if c.type == "image":
                    c.attrSet("src", os.path.relpath(os.path.join(ROOT, src_dir, c.attrGet("src")), os.path.join(ROOT, "dist")))
        if t.type == "table_open":
            cols, heads, j, row, in_body, tr = {}, {}, i, None, False, None
            while tokens[j].type != "table_close":
                tj = tokens[j]
                if tj.type == "tbody_open":
                    in_body = True
                elif tj.type == "tr_open":
                    row, tr = 0, tj
                elif tj.type in ("td_open", "th_open"):
                    cell = plain(tokens[j + 1])
                    if tj.type == "th_open":
                        heads[row] = tj
                    else:
                        cols.setdefault(row, []).append((tj, cell))
                        if row == 0 and re.match(r"^\s*[—–]\s", cell):
                            tr.attrJoin("class", "sub")
                    row += 1
                j += 1
            for col, cells in cols.items():
                if all(NUMERIC_CELL.match(c) for _, c in cells if c.strip()):
                    for tok, _ in cells:
                        tok.attrJoin("class", "r")
                    if col in heads:
                        heads[col].attrJoin("class", "r")
            i = j
        i += 1


def set_numbers(body):
    """Text-node pass over the rendered HTML: Fragment Mono for intervals (with their point estimate) everywhere and for every
    number inside table cells. Tags, code, and the section numbers are left alone."""
    parts = re.split(r"(<[^>]+>)", body)
    in_cell = in_code = 0
    out = []
    for p in parts:
        if p.startswith("<"):
            name = re.match(r"</?\s*([a-zA-Z0-9]+)", p)
            name = name.group(1).lower() if name else ""
            closing = p.startswith("</")
            if name in ("td", "th"):
                in_cell += -1 if closing else 1
            elif name in ("code", "pre", "h1", "h2", "h3"):
                in_code += -1 if closing else 1
            out.append(p)
            continue
        if in_code or not p:
            out.append(p)
            continue
        # placeholders keep the interval spans from being matched again by the plain-number pass
        cis = []
        def ci(m):
            cis.append(m.group(0))
            return "\x00" + chr(0xF0000 + len(cis) - 1)   # no digits, so the number passes cannot touch it
        s = INTERVAL.sub(ci, p)
        if in_cell:
            s = TABLE_NUM.sub(lambda m: f'<span class="m">{m.group(0)}</span>', s)
        else:
            s = EST_CI.sub(r'<span class="m">\1</span>\2', s)
        s = re.sub("\x00(.)", lambda m: f'<span class="m ci">{cis[ord(m.group(1)) - 0xF0000]}</span>', s)
        out.append(s)
    return "".join(out)


def figure_html(n, src, caption, narrow):
    rel = os.path.relpath(os.path.join(ROOT, src), os.path.join(ROOT, "dist"))
    alt = html.escape(caption, quote=True)
    cls = "fig narrow" if narrow else "fig"
    return (f'<figure class="{cls}"><img src="{html.escape(rel)}" alt="{alt}">'
            f'<figcaption><span class="fno">Figure {n}</span><span>{html.escape(caption)}</span></figcaption></figure>\n')


def place_figures(body):
    heads = [(m.start(), re.sub(r"<[^>]+>", "", m.group(1))) for m in re.finditer(r"<h2[^>]*>(.*?)</h2>", body, re.S)]
    inserts, missing = [], []
    for n, (where, src, cap, narrow) in enumerate(FIGURES, 1):
        if not os.path.exists(os.path.join(ROOT, src)):
            print(f"render: figure {src} missing, skipped", file=sys.stderr)
            continue
        fig = figure_html(n, src, cap, narrow)
        if where == "lead":
            pos = heads[0][0] if heads else len(body)
        else:
            k = next((k for k, (_, h) in enumerate(heads) if re.search(where, h, re.I)), None)
            if k is None:
                print(f"render: no section matching /{where}/ for {src}; placed at the end", file=sys.stderr)
                missing.append(fig)
                continue
            pos = heads[k + 1][0] if k + 1 < len(heads) else len(body)
        inserts.append((pos, n, fig))
    for pos, _, fig in sorted(inserts, key=lambda x: (-x[0], -x[1])):
        body = body[:pos] + fig + body[pos:]
    return body + "".join(missing)


def git(*args):
    try:
        return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", default=os.path.join(ROOT, "docs", "REPORT.md"))
    ap.add_argument("--out", default=os.path.join(ROOT, "dist", "querschnitt-report.html"))
    ap.add_argument("--date", default=os.environ.get("REPORT_DATE") or datetime.date.today().isoformat())
    a = ap.parse_args()
    src = os.path.abspath(a.src)
    src_rel = os.path.relpath(src, ROOT).replace(os.sep, "/")
    text = open(src, encoding="utf-8").read()

    md = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False}).enable(["table", "strikethrough"])
    tokens = md.parse(text)
    # the first H1 becomes the title block; the paragraphs before the first H2 are the lead
    title = "Querschnitt — evaluation report"
    for k, t in enumerate(tokens):
        if t.type == "heading_open" and t.tag == "h1":
            title = tokens[k + 1].content
            del tokens[k:k + 3]
            break
    prepare(tokens, posixpath.dirname(src_rel))
    for k, t in enumerate(tokens):
        if t.type == "heading_open" and t.tag == "h2":
            break
        if t.type == "paragraph_open":
            t.attrJoin("class", "lead")
    body = md.renderer.render(tokens, md.options, {})
    body = re.sub(r"<h2>(\d+(?:\.\d+)*)\.?\s+", r'<h2><span class="no">\1</span>', body)
    body = re.sub(r"<code>(please_check)</code>", r'<code class="lane">\1</code>', body)
    body = set_numbers(body)
    body = place_figures(body)

    d = datetime.date.fromisoformat(a.date)
    commit = git("rev-parse", "--short", "HEAD")
    dirty = bool(git("status", "--porcelain", "--", src_rel))
    made = f"{src_rel} at {commit}{' + local edits' if dirty else ''}" if commit else src_rel
    css = open(os.path.join(HERE, "report.css"), encoding="utf-8").read()
    fonts = os.path.relpath(os.path.join(ROOT, "app", "fonts"), os.path.join(ROOT, "dist"))
    css = css.replace("{{FONTS}}", fonts.replace(os.sep, "/"))
    footer = title.replace("\\", "\\\\").replace('"', '\\"')
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<meta name="author" content="Querschnitt">
<style>
{css}
@page {{ @bottom-left {{ content: "{footer}"; }} }}
</style>
</head>
<body>
<header class="title">
<h1>{html.escape(title)}</h1>
<dl class="meta">
<div><dt>date</dt><dd>{d.day} {d:%B %Y}</dd></div>
<div><dt>repository</dt><dd><a href="{REPO}">{REPO.split('//', 1)[1]}</a></dd></div>
<div><dt>live app</dt><dd><a href="{LIVE}">{LIVE.split('//', 1)[1]}</a></dd></div>
<div><dt>source</dt><dd><a href="{REPO}/blob/main/{src_rel}">{html.escape(made)}</a></dd></div>
</dl>
<p class="event">{html.escape(CHALLENGE)}</p>
</header>
<main>
{body}</main>
</body>
</html>
"""
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(page)
    print(a.out)


if __name__ == "__main__":
    main()
