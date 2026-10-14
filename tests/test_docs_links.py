"""Every relative link in README.md and docs/*.md resolves to a file in the repository (so it also works on GitHub):
the target exists, the path never climbs above the repository root (not even on the way, as in ../../../bern/querschnitt/x),
and, in a git checkout, the target is not git-ignored (an ignored file exists locally but not in the published repo)."""
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]

FENCE = re.compile(r"^(```|~~~).*?^\1", re.S | re.M)
CODE = re.compile(r"`[^`\n]*`")
INLINE = re.compile(r"!?\[(?:[^\[\]]|\[[^\]]*\])*\]\(\s*(<[^>]*>|[^)\s]+)(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)")
REFDEF = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(<[^>]*>|\S+)", re.M)
SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def links(md):
    """(line, target) for every inline link/image and reference definition outside code."""
    text = FENCE.sub(lambda m: "\n" * m.group(0).count("\n"), md)
    text = CODE.sub(lambda m: " " * len(m.group(0)), text)
    for rx in (INLINE, REFDEF):
        for m in rx.finditer(text):
            yield text.count("\n", 0, m.start()) + 1, m.group(1).strip("<>")


def relative_targets():
    out = []
    for doc in DOCS:
        for line, t in links(doc.read_text(encoding="utf-8")):
            if not t or t.startswith("#") or t.startswith("//") or SCHEME.match(t):
                continue
            path = unquote(t.split("#", 1)[0].split("?", 1)[0])
            if path:
                out.append((doc, line, t, path))
    return out


def escapes(doc, path):
    """True when the path, walked segment by segment from the doc's folder, ever leaves the repository root."""
    if path.startswith("/"):
        return True
    depth = len(doc.parent.relative_to(ROOT).parts)
    for seg in path.split("/"):
        if seg == "..":
            depth -= 1
            if depth < 0:
                return True
        elif seg not in ("", "."):
            depth += 1
    return False


TARGETS = relative_targets()


def test_docs_have_links():
    assert DOCS[0].exists() and len(DOCS) > 1
    assert len(TARGETS) > 100  # PRUEFSTAND.md alone links several hundred sources


def test_no_link_leaves_the_repo():
    bad = [f"{d.relative_to(ROOT)}:{ln}: {t}" for d, ln, t, p in TARGETS if escapes(d, p)]
    assert not bad, f"{len(bad)} links leave the repository root:\n" + "\n".join(bad[:50])


def test_every_link_resolves():
    bad = [f"{d.relative_to(ROOT)}:{ln}: {t}" for d, ln, t, p in TARGETS
           if not escapes(d, p) and not (d.parent / p).exists()]
    assert not bad, f"{len(bad)} links point to missing files:\n" + "\n".join(bad[:50])


@pytest.mark.skipif(shutil.which("git") is None or not (ROOT / ".git").exists(), reason="not a git checkout")
def test_no_link_to_an_ignored_file():
    rel = sorted({str((d.parent / p).resolve().relative_to(ROOT)) for d, _, _, p in TARGETS
                  if not escapes(d, p) and (d.parent / p).exists()})
    r = subprocess.run(["git", "check-ignore", "--stdin"], cwd=ROOT, input="\n".join(rel), capture_output=True, text=True)
    ignored = [l for l in r.stdout.splitlines() if l]
    assert not ignored, "links to git-ignored files (missing on GitHub):\n" + "\n".join(ignored)
