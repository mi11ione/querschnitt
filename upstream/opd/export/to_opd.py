#!/usr/bin/env python3
"""Querschnitt topics.jsonl.gz (docs/CONTRACT.md rows) -> OpenParlData bulk-export shape (EXPORT.md).

    python3 upstream/opd/export/to_opd.py --topics app/data/topics.jsonl.gz \
        --bodies ../data/opd-new/bodies.ndjson.gz --out /tmp/opd-export [--split] [--with-subtopics] [--sample 12]

Writes topics.ndjson.gz (or topics/topics_<body_key>.ndjson.gz with --split), topic_schemes.ndjson.gz,
topic_codes.ndjson.gz and index.fragment.json (entries in the shape of files.openparldata.ch/exports/index.json).
Columns are those of the `topics` table (../migrations/0001_topics.up.sql) minus the loader's `content_hash`; `id` is
null here because OPD's own export dumps the table and carries the table id. Timestamps: naive ISO 8601 in UTC, as in
OPD's exports. APS level-2 rows and codes (subtopics) are left out unless --with-subtopics (to be agreed with APS;
../../MERGE_REQUEST.md, open questions).
Needs PyYAML (scheme labels come from the same files as the seed migration)."""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import gzip
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("gen_seed", HERE.parent / "tools/gen_seed.py")
gen_seed = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(gen_seed)

COLUMNS = ["id", "affair_id", "body_id", "body_key", "scheme_id", "scheme_key", "level", "code", "parent_code", "rank",
           "label_de", "label_fr", "label_it", "label_rm", "p", "p_raw", "lane", "status", "provenance",
           "evidence_field", "evidence_text_id", "evidence_doc_id", "evidence_char_start", "evidence_char_end", "evidence_quote",
           "model", "model_build", "cutoffs_id", "prompt_id", "input_hash", "engine_version",
           "valid_from", "valid_to", "confirmed_by", "confirmed_by_body_id", "confirmed_at", "created_at", "updated_at"]


def ts(v: str | None) -> str | None:
    """Any ISO 8601 -> naive UTC 'YYYY-MM-DDTHH:MM:SS' (OPD export style)."""
    if not v:
        return None
    t = dt.datetime.fromisoformat(v.replace("Z", "+00:00"))
    if t.tzinfo:
        t = t.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return t.replace(microsecond=0).isoformat()


def human(n: int) -> str:
    for unit in ("B", "K", "M", "G"):
        if n < 1024 or unit == "G":
            return f"{n:.1f}{unit}" if unit != "B" else f"{n}B"
        n /= 1024
    return str(n)


def evidence(ev: dict | None) -> dict:
    out = dict(evidence_field=None, evidence_text_id=None, evidence_doc_id=None, evidence_char_start=None,
               evidence_char_end=None, evidence_quote=None)
    if not ev:
        return out
    src = str(ev.get("source") or "")
    if src.startswith("text:"):
        out["evidence_text_id"] = int(src[5:])
    elif src.startswith("doc:"):
        out["evidence_doc_id"] = int(src[4:])
    out["evidence_field"] = "doc" if src.startswith("doc:") else ev.get("field")
    out["evidence_char_start"] = ev.get("char_start", ev.get("start"))
    out["evidence_char_end"] = ev.get("char_end", ev.get("end"))
    out["evidence_quote"] = ev.get("quote")
    return out


def convert(r: dict, schemes: dict, codes: dict, bodies: dict) -> dict:
    s = schemes[r["scheme"]]
    c = codes.get((r["scheme"], r["code"]), {})
    vf, vt = ts(r.get("valid_from")), ts(r.get("valid_to"))
    row = dict(id=None, affair_id=int(r["affair_id"]), body_id=bodies.get(r.get("body_key")), body_key=r.get("body_key"),
               scheme_id=s["id"], scheme_key=r["scheme"], level=int(r["level"]), code=r["code"], parent_code=c.get("parent_code"),
               rank=int(r.get("rank") or 1), label_de=c.get("label_de"), label_fr=c.get("label_fr"), label_it=c.get("label_it"),
               label_rm=None, p=r.get("p"), p_raw=r.get("p_raw"), lane=r.get("lane"), status=r.get("status") or "suggested",
               provenance=r.get("provenance") or "inferred", **evidence(r.get("evidence")),
               model=r.get("model"), model_build=r.get("build"), cutoffs_id=r.get("cutoffs_id"), prompt_id=r.get("prompt_id"),
               input_hash=r.get("input_hash"), engine_version=r.get("version"), valid_from=vf, valid_to=vt,
               confirmed_by=r.get("confirmed_by"), confirmed_by_body_id=None, confirmed_at=ts(r.get("confirmed_at")),
               created_at=vf, updated_at=vt or vf)
    return {k: row[k] for k in COLUMNS}


def write_ndjson_gz(path: Path, rows) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n"); n += 1
    return n


def entry(entity: str, path: Path, out: Path, n: int, base: str) -> dict:
    size = path.stat().st_size
    created = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rel = path.relative_to(out).as_posix()
    head = dict(entity=entity, type="single", format="ndjson.gz") if "/" not in rel else {}
    return head | dict(filename=path.name, url=f"{base}/{rel}", size=size, size_human=human(size), row_count=n, created=created)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--topics", required=True, help="Querschnitt topics.jsonl.gz")
    ap.add_argument("--bodies", help="OPD bodies.ndjson.gz (for body_id); without it body_id is null")
    ap.add_argument("--out", required=True)
    ap.add_argument("--split", action="store_true", help="per-body files topics/topics_<body_key>.ndjson.gz (OPD's docs/texts pattern)")
    ap.add_argument("--with-subtopics", action="store_true", help="include APS level-2 rows")
    ap.add_argument("--sample", type=int, default=0, help="also write sample/topics.sample.ndjson with N rows (plain JSON lines)")
    ap.add_argument("--base-url", default="https://files.openparldata.ch/exports")
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    schemes, codes = {}, {}
    for s, cs in gen_seed.schemes(strict=False):   # a scheme without a fixed id gets scheme_id null here
        schemes[s["scheme_key"]] = s
        for c in cs:
            codes[(s["scheme_key"], c["code"])] = c
    bodies = {}
    if a.bodies:
        with gzip.open(a.bodies, "rt") as f:
            for line in f:
                b = json.loads(line); bodies[b["body_key"]] = b["id"]

    by_body: dict[str, list] = collections.defaultdict(list)
    skipped = collections.Counter(); n_in = 0
    with gzip.open(a.topics, "rt") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line); n_in += 1
            if r["scheme"] not in schemes:
                skipped["unknown scheme"] += 1; continue
            if r["scheme"] == "aps" and int(r["level"]) == 2 and not a.with_subtopics:
                skipped["aps level 2 (held back)"] += 1; continue
            by_body[r.get("body_key") or "_none"].append(convert(r, schemes, codes, bodies))

    index = []
    if a.split:
        files = []
        for bk in sorted(by_body):
            p = out / "topics" / f"topics_{bk}.ndjson.gz"
            n = write_ndjson_gz(p, by_body[bk]); files.append(entry("topics", p, out, n, a.base_url))
        index.append(dict(entity="topics", type="split", format="ndjson.gz", directory="topics/", url=f"{a.base_url}/topics/",
                          file_count=len(files), total_size=sum(x["size"] for x in files),
                          total_size_human=human(sum(x["size"] for x in files)), total_row_count=sum(x["row_count"] for x in files),
                          files=files))
    else:
        p = out / "topics.ndjson.gz"
        n = write_ndjson_gz(p, (r for bk in sorted(by_body) for r in by_body[bk])); index.append(entry("topics", p, out, n, a.base_url))
    s_rows = [{k: v for k, v in s.items()} | dict(body_id=bodies.get(s["body_key"]) if s["body_key"] else None, active=True)
              for s in schemes.values()]
    p = out / "topic_schemes.ndjson.gz"; index.append(entry("topic_schemes", p, out, write_ndjson_gz(p, s_rows), a.base_url))
    c_rows = [dict(id=None, scheme_id=schemes[sk]["id"], scheme_key=sk, **c, label_rm=None) for (sk, _), c in codes.items()
              if a.with_subtopics or not (sk == "aps" and c["level"] == 2)]
    p = out / "topic_codes.ndjson.gz"; index.append(entry("topic_codes", p, out, write_ndjson_gz(p, c_rows), a.base_url))
    (out / "index.fragment.json").write_text(json.dumps(dict(files=index), indent=1, ensure_ascii=False) + "\n")

    if a.sample:
        flat = [r for bk in sorted(by_body) for r in by_body[bk]]
        pick = [r for r in flat if r["scheme_key"] == "aps" and r["rank"] == 1][: a.sample // 2]
        pick += [r for r in flat if r["scheme_key"].startswith("adhoc/") and r["code"].endswith(":yes")][: a.sample - len(pick)]
        sp = out / "sample" / "topics.sample.ndjson"; sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in pick))
    n_out = sum(len(v) for v in by_body.values())
    print(json.dumps(dict(rows_in=n_in, rows_out=n_out, bodies=len(by_body), skipped=dict(skipped),
                          files=[(x.get("filename") or x.get("directory"), x.get("size_human") or x.get("total_size_human")) for x in index]),
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
