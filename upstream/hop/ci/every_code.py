#!/usr/bin/env python3
"""One machine row per code of every scheme file in src/querschnitt/schemes/ (recursive), for the `hop` CI job: the file
is loaded through Hop against migrations 0001-0003, so a scheme file whose codes the seed (0002, written by
../../opd/tools/gen_seed.py) does not carry fails CI on the push that adds it, before any topics file has rows of it.

    python3 upstream/hop/ci/every_code.py --out every_code.jsonl.gz      # needs PyYAML

Reads the scheme files itself (not through gen_seed.py, which is what is under test). A scheme file of a shape it does not
know stops it: add the shape here. Each row sits on its own stand-in affair (ids from 900000001; the job adds them to
the stand-in affairs table), body CHE for APS and ad-hoc topics, the scheme's own body for a parliament's scheme."""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SCHEMES = ROOT / "src/querschnitt/schemes"


def codes(p: Path) -> tuple[str, str, list[tuple[int, str]]]:
    """-> (scheme id, body key, [(level, code)])."""
    d = yaml.safe_load(p.read_text())
    if "chapters" in d:                                            # APS: chapters, subtopics, no policy topic
        cs = [(1, ch["code"]) for ch in d["chapters"]] + [(1, d["none"]["code"])]
        cs += [(2, s["code"]) for ch in d["chapters"] for s in ch.get("subtopics", [])]
        return d["id"], "CHE", cs
    if p.parent.name == "adhoc":                                   # yes / no
        return d["id"], "CHE", [(1, f"{d['id']}:yes"), (1, f"{d['id']}:no")]
    if d.get("kind") in ("flat", "named"):                         # a parliament's own scheme
        cs = [(1, o["code"]) for o in d["options"]] + ([(1, d["none"]["code"])] if d.get("none") else [])
        body = d.get("body") or d["options"][0]["code"].split(":", 1)[0].upper()
        return d["id"], body, cs
    raise SystemExit(f"{p.relative_to(ROOT)}: unknown scheme file shape; add it to {Path(__file__).name}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    rows = []
    for p in sorted(SCHEMES.rglob("*.yaml")):
        if "\nstatus: test" in "\n" + p.read_text():   # an on-site partner scheme (make scheme-eval): never shipped, never seeded
            continue
        key, body, cs = codes(p)
        for level, code in cs:
            rows.append(dict(affair_id=900000001 + len(rows), body_key=body, status="suggested", provenance="inferred",
                             model="ci", build="ci", input_hash=None, valid_from="2026-01-01T00:00:00Z", valid_to=None,
                             version="ci", scheme=key, level=level, code=code, rank=1, p_raw=0.5, p=None, lane="please_check",
                             cutoffs_id=None, prompt_id=None, evidence=None))
    with open(a.out, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as g:
        for r in rows:
            g.write((json.dumps(r, ensure_ascii=False) + "\n").encode("utf-8"))
    print(f"{len(rows)} rows, {len({r['scheme'] for r in rows})} schemes -> {a.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
