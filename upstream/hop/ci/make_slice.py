#!/usr/bin/env python3
"""A reduced copy of a Querschnitt topics file for the `hop` CI job: every row of a set of affairs chosen so that each
(scheme, level, code) the file carries appears on several affairs, each body on a few, and a parliament's own scheme
(type body: Ticino, Basel, Bern) on many. Deterministic (lowest affair ids first), so a rerun on the same file writes
the same bytes.

    python3 upstream/hop/ci/make_slice.py --topics app/data/topics.jsonl.gz --out upstream/hop/ci/topics.app-slice.jsonl.gz

Used when the app's export carries rows of a scheme the latest release does not have yet (the release is loaded by the
same job): the slice goes through the same Hop load and to_opd.py check before any release."""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import sys

PER_CODE, PER_OWN_CODE, PER_BODY = 3, 25, 4
OWN = ("be-directorates", "bs-themen", "ti-dipartimenti")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--topics", default="app/data/topics.jsonl.gz")
    ap.add_argument("--out", default="upstream/hop/ci/topics.app-slice.jsonl.gz")
    a = ap.parse_args(argv)
    lines = collections.defaultdict(list)                       # affair_id -> raw lines
    by_code = collections.defaultdict(set); by_body = collections.defaultdict(set)
    with gzip.open(a.topics, "rt", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line); aid = int(r["affair_id"])
            lines[aid].append(line if line.endswith("\n") else line + "\n")
            by_code[(r["scheme"], int(r["level"]), r["code"])].add(aid)
            by_body[r.get("body_key")].add(aid)
    pick = set()
    for (scheme, _, _), ids in by_code.items():
        pick |= set(sorted(ids)[: PER_OWN_CODE if scheme in OWN else PER_CODE])
    for ids in by_body.values():
        pick |= set(sorted(ids)[:PER_BODY])
    n = 0
    with open(a.out, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as g:
        for aid in sorted(pick):
            for line in lines[aid]:
                g.write(line.encode("utf-8")); n += 1
    schemes = collections.Counter(k[0] for k, ids in by_code.items() if ids & pick)
    print(json.dumps(dict(affairs=len(pick), rows=n, bodies=sum(1 for ids in by_body.values() if ids & pick),
                          codes_per_scheme=dict(sorted(schemes.items())))), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
