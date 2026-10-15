#!/usr/bin/env python3
"""Writes ../migrations/0002_topic_schemes_seed.up.sql and .down.sql from Querschnitt's scheme files
(src/querschnitt/schemes/): every scheme the topics file can carry, so a load of that file finds each scheme_id.

    python3 upstream/opd/tools/gen_seed.py            # from the repo root; needs PyYAML (in the querschnitt venv)
    python3 upstream/opd/tools/gen_seed.py --scheme adhoc/<slug> --name 0004_topic_scheme_<slug>
                                                      # a later migration for one new or changed scheme file

Scheme ids are fixed (SCHEME_IDS) so the export preview (../export/to_opd.py) and the database agree; a scheme file
without an id here stops the generator (add it to SCHEME_IDS). The version of a scheme is sha256[:8] of its file.

Without --scheme it writes the INITIAL seed. Once 0002 is applied, a changed or new scheme file goes in as a new
migration written with --scheme (../../MERGE_REQUEST.md, "Changing a scheme"): it deactivates the scheme's current
version, adds the new one with an identity id and its codes, and its down migration reverses that. Applying a
regenerated 0002 to a database that already holds an older version fails on the fixed id, by design."""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                       # repo root
SCHEMES = ROOT / "src/querschnitt/schemes"
OUT = HERE.parent / "migrations/0002_topic_schemes_seed.up.sql"
OUT_DOWN = HERE.parent / "migrations/0002_topic_schemes_seed.down.sql"

SCHEME_IDS = {"aps": 1, "adhoc/digitalisierung": 2, "be-directorates": 3, "adhoc/hitze": 4, "adhoc/ki-schule": 5,
              "adhoc/wolf": 6, "bs-themen": 7}
# Body schemes: who publishes the codes, under which licence (SPDX; None = to be agreed with the source).
BODY_SCHEMES = {
    "be-directorates": dict(name_en="Canton of Bern: lead directorate", licence=None,
                            source_name="Kanton Bern (directorate names); remits written by Querschnitt",
                            source_url="https://www.be.ch"),
    "bs-themen": dict(name_en="Basel-Stadt: themes of cantonal and urban development (Grand Council)", licence="CC-BY-4.0",
                      source_name="Kanton Basel-Stadt, Kantons- und Stadtentwicklung (OGD dataset 100086)",
                      source_url="https://data.bs.ch/explore/dataset/100086/"),
}
NO = {"de": "nein", "fr": "non", "it": "no"}


def q(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def version(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:8]


def schemes(strict: bool = True) -> list[tuple[dict, list[dict]]]:
    """-> [(scheme row, [code rows])] in SCHEME_IDS order. strict=False: a scheme without a fixed id gets id None
    (the export preview and --scheme do not need one)."""
    out = []
    # APS: 24 chapters x subtopics + "no policy topic"
    p = SCHEMES / "aps.yaml"; d = yaml.safe_load(p.read_text())
    codes, pos = [], 0
    for ch in d["chapters"]:
        pos += 1
        codes.append(dict(code=ch["code"], level=1, parent_code=None, position=pos, external_id=ch["code"].split(":", 1)[1],
                          label_de=ch["name"].get("de"), label_fr=ch["name"].get("fr"), label_it=ch["name"].get("it")))
    pos += 1
    codes.append(dict(code=d["none"]["code"], level=1, parent_code=None, position=pos, external_id=None,
                      label_de=d["none"]["name"]["de"], label_fr=d["none"]["name"]["fr"], label_it=d["none"]["name"]["it"]))
    for ch in d["chapters"]:
        for s in ch["subtopics"]:
            pos += 1
            codes.append(dict(code=s["code"], level=2, parent_code=ch["code"], position=pos, external_id=s["code"].split(":", 1)[1],
                              label_de=s["name"].get("de"), label_fr=s["name"].get("fr"), label_it=s["name"].get("it")))
    out.append((dict(id=1, scheme_key="aps", version=version(p), type="standard", levels=2,
                     name_de=d["title"]["de"], name_fr=d["title"]["fr"], name_it=None, name_rm=None,
                     name_en="Année Politique Suisse: 24 chapters, 190 subtopics",
                     question_de=None, question_fr=None, question_it=None, body_key=None,
                     licence=None, source_name="Année Politique Suisse (Universität Bern)", source_url="https://anneepolitique.swiss",
                     notes="Chapter codes and keyword identifiers as published by APS. Italian chapter labels: unofficial translation. "
                           "Subtopic labels are published by APS in German only. Publishing subtopic labels under OPD is to be agreed with APS; "
                           "until then the public export carries level 1 only.",
                     code_count=len(codes)), codes))
    # ad-hoc topics (yes / no): every file in schemes/adhoc/
    for p in sorted((SCHEMES / "adhoc").glob("*.yaml")):
        d = yaml.safe_load(p.read_text())
        n = d["names"]
        codes = [dict(code=f"{d['id']}:yes", level=1, parent_code=None, position=1, external_id=None,
                      label_de=n.get("de"), label_fr=n.get("fr"), label_it=n.get("it")),
                 dict(code=f"{d['id']}:no", level=1, parent_code=None, position=2, external_id=None,
                      label_de=f"{n['de']}: {NO['de']}" if n.get("de") else None,
                      label_fr=f"{n['fr']} : {NO['fr']}" if n.get("fr") else None,
                      label_it=f"{n['it']}: {NO['it']}" if n.get("it") else None)]
        dvs = d["id"] == "adhoc/digitalisierung"
        notes = f"Yes/no topic; p = probability of yes; flagged at p >= {d.get('cutoff', 0.5)}."
        if d.get("verify"):
            notes += " A flag is checked by a second, stricter question; an unconfirmed flag stays a flag with lane please_check."
        if d.get("scored_period"):
            notes += f" Scored only for affairs begun {d['scored_period'][0]} to {d['scored_period'][1]}; no row = not scored."
        out.append((dict(id=_id(d["id"], strict), scheme_key=d["id"], version=version(p), type="adhoc", levels=1,
                         name_de=n.get("de"), name_fr=n.get("fr"), name_it=n.get("it"), name_rm=None,
                         name_en="Digitalisation" if dvs else None,
                         question_de=d["question"].get("de"), question_fr=d["question"].get("fr"), question_it=d["question"].get("it"),
                         body_key=None, licence="CC-BY-4.0",
                         source_name="Querschnitt (question and scope note)" + ("; use case Digitale Verwaltung Schweiz" if dvs else ""),
                         source_url="https://www.digitale-verwaltung-schweiz.ch/aktuelles/politische-geschaefte" if dvs else None,
                         notes=notes, code_count=len(codes)), codes))
    # a parliament's own scheme (kind flat or named, with the parliament's body key)
    for p in sorted(SCHEMES.glob("*.yaml")):
        d = yaml.safe_load(p.read_text())
        if d.get("kind") not in ("flat", "named"):
            continue
        meta = BODY_SCHEMES.get(d["id"])
        if meta is None:
            if strict:
                raise SystemExit(f"{p.name}: add its publisher and licence to BODY_SCHEMES")
            meta = dict(name_en=None, licence=None, source_name=d.get("source") or d["id"], source_url=None)
        codes = []
        for i, o in enumerate(d["options"], 1):
            codes.append(dict(code=o["code"], level=1, parent_code=None, position=i,
                              external_id=(o.get("abbr") or {}).get("de"),
                              label_de=o["name"].get("de"), label_fr=o["name"].get("fr"), label_it=o["name"].get("it")))
        if d.get("none"):
            codes.append(dict(code=d["none"]["code"], level=1, parent_code=None, position=len(codes) + 1, external_id=None,
                              label_de=d["none"]["name"].get("de"), label_fr=d["none"]["name"].get("fr"),
                              label_it=d["none"]["name"].get("it")))
        body_key = d.get("body") or ("BE" if d["id"] == "be-directorates" else None)
        out.append((dict(id=_id(d["id"], strict), scheme_key=d["id"], version=version(p), type="body", levels=1,
                         name_de=d["title"].get("de"), name_fr=d["title"].get("fr"), name_it=None, name_rm=None,
                         name_en=meta["name_en"], question_de=None, question_fr=None, question_it=None, body_key=body_key,
                         licence=meta["licence"], source_name=meta["source_name"], source_url=meta["source_url"],
                         notes=d.get("source"), code_count=len(codes)), codes))
    return sorted(out, key=lambda x: (x[0]["id"] is None, x[0]["id"] or 0, x[0]["scheme_key"]))


def _id(key: str, strict: bool = True) -> int | None:
    if key not in SCHEME_IDS and strict:
        raise SystemExit(f"scheme {key!r} has no fixed id: add it to SCHEME_IDS in {Path(__file__).name}")
    return SCHEME_IDS.get(key)


COLS = ["id", "scheme_key", "version", "type", "levels", "name_de", "name_fr", "name_it", "name_rm", "name_en",
        "question_de", "question_fr", "question_it", "body_id", "body_key", "licence", "source_name", "source_url",
        "notes", "code_count", "active"]


def one_scheme(key: str, name: str) -> int:
    """A later migration for one scheme file: new version active, previous version kept (inactive) with its rows."""
    hit = [x for x in schemes(strict=False) if x[0]["scheme_key"] == key]
    if not hit:
        raise SystemExit(f"no scheme file with id {key!r} in {SCHEMES}")
    s, codes = hit[0]
    k, v = q(s["scheme_key"]), q(s["version"])
    body = f"(SELECT id FROM bodies WHERE body_key = {q(s['body_key'])})" if s["body_key"] else "NULL"
    cols = [c for c in COLS if c != "id"]
    vals = [q(s[c]) if c not in ("body_id", "active") else (body if c == "body_id" else "true") for c in cols]
    rows = ",\n".join(f"  ({q(c['code'])}, {c['level']}, {q(c['parent_code'])}, {c['position']}, {q(c['external_id'])}, "
                      f"{q(c['label_de'])}, {q(c['label_fr'])}, {q(c['label_it'])})" for c in codes)
    up = "\n".join([
        f"-- {name} (up): scheme {s['scheme_key']} version {s['version']}, GENERATED by upstream/opd/tools/gen_seed.py --scheme.",
        "-- Makes this version the active one: rows loaded from now on get its scheme_id and labels; rows loaded before keep",
        "-- the version they were loaded with. Re-running it is a no-op.",
        "BEGIN;",
        f"UPDATE topic_schemes SET active = false, updated_at = now() AT TIME ZONE 'utc' WHERE scheme_key = {k} AND active AND version <> {v};",
        f"INSERT INTO topic_schemes ({', '.join(cols)})\nVALUES ({', '.join(vals)})",
        "ON CONFLICT (scheme_key, version) DO UPDATE SET active = true, updated_at = now() AT TIME ZONE 'utc';",
        "INSERT INTO topic_codes (scheme_id, scheme_key, code, level, parent_code, position, external_id, label_de, label_fr, label_it)",
        "SELECT s.id, s.scheme_key, c.code, c.level, c.parent_code, c.position, c.external_id, c.label_de, c.label_fr, c.label_it",
        f"FROM topic_schemes s, (VALUES\n{rows}\n) AS c (code, level, parent_code, position, external_id, label_de, label_fr, label_it)",
        f"WHERE s.scheme_key = {k} AND s.version = {v}",
        "ON CONFLICT (scheme_id, code) DO NOTHING;",
        "COMMIT;", ""])
    down = "\n".join([
        f"-- {name} (down): removes version {s['version']} of {s['scheme_key']} with its codes and the topic rows loaded against it",
        "-- (export them first), and makes the latest remaining version of the scheme active again.",
        "BEGIN;",
        f"DELETE FROM topics WHERE scheme_id IN (SELECT id FROM topic_schemes WHERE scheme_key = {k} AND version = {v});",
        f"DELETE FROM topic_schemes WHERE scheme_key = {k} AND version = {v};",
        f"UPDATE topic_schemes SET active = true, updated_at = now() AT TIME ZONE 'utc'",
        f"WHERE id = (SELECT max(id) FROM topic_schemes WHERE scheme_key = {k}) AND NOT EXISTS (SELECT 1 FROM topic_schemes WHERE scheme_key = {k} AND active);",
        "COMMIT;", ""])
    mig = HERE.parent / "migrations"
    (mig / f"{name}.up.sql").write_text(up)
    (mig / f"{name}.down.sql").write_text(down)
    print(f"wrote {mig.relative_to(ROOT)}/{name}.up.sql and .down.sql", file=sys.stderr)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scheme", help="scheme id (e.g. adhoc/wolf): write a later migration for this one scheme file")
    ap.add_argument("--name", help="migration name for --scheme, e.g. 0004_topic_scheme_wolf")
    a = ap.parse_args(argv)
    if a.scheme:
        if not a.name:
            ap.error("--scheme needs --name")
        return one_scheme(a.scheme, a.name)
    all_schemes = schemes()
    lines = ["-- 0002_topic_schemes_seed (up): the schemes Querschnitt ships, with their codes and labels.",
             "-- GENERATED by upstream/opd/tools/gen_seed.py from src/querschnitt/schemes/ (do not edit by hand).",
             "-- Re-running it is a no-op (ON CONFLICT DO NOTHING). It is the initial seed: a changed or new scheme file later is a",
             "-- new migration (MERGE_REQUEST.md, \"Changing a scheme\"). Needs the bodies table (body_id of body schemes).",
             "BEGIN;", ""]
    for s, codes in all_schemes:
        body = f"(SELECT id FROM bodies WHERE body_key = {q(s['body_key'])})" if s["body_key"] else "NULL"
        vals = [q(s[c]) if c not in ("body_id", "active") else (body if c == "body_id" else "true") for c in COLS]
        lines.append(f"INSERT INTO topic_schemes ({', '.join(COLS)})\nVALUES ({', '.join(vals)})\nON CONFLICT (scheme_key, version) DO NOTHING;")
        lines.append("INSERT INTO topic_codes (scheme_id, scheme_key, code, level, parent_code, position, external_id, label_de, label_fr, label_it, label_rm) VALUES")
        rows = [f"  ({s['id']}, {q(s['scheme_key'])}, {q(c['code'])}, {c['level']}, {q(c['parent_code'])}, {c['position']}, "
                f"{q(c['external_id'])}, {q(c['label_de'])}, {q(c['label_fr'])}, {q(c['label_it'])}, NULL)" for c in codes]
        lines.append(",\n".join(rows) + "\nON CONFLICT (scheme_id, code) DO NOTHING;\n")
    lines.append("SELECT setval(pg_get_serial_sequence('topic_schemes', 'id'), (SELECT max(id) FROM topic_schemes));")
    lines.append("COMMIT;")
    OUT.write_text("\n".join(lines) + "\n")
    keys = ", ".join(f"({q(s['scheme_key'])}, {q(s['version'])})" for s, _ in all_schemes)
    OUT_DOWN.write_text("\n".join([
        "-- 0002_topic_schemes_seed (down): removes the seeded scheme versions, their codes (ON DELETE CASCADE) and the topic rows",
        "-- of those versions. GENERATED by upstream/opd/tools/gen_seed.py. Topic rows are lost: export topics.ndjson.gz first.",
        "-- Order: 0003 down first (topic_feed_bodies references topic_schemes; with 0003 applied this fails on that key).",
        "BEGIN;",
        f"DELETE FROM topics WHERE scheme_id IN (SELECT id FROM topic_schemes WHERE (scheme_key, version) IN ({keys}));",
        f"DELETE FROM topic_schemes WHERE (scheme_key, version) IN ({keys});",
        "COMMIT;", ""]))
    print(f"wrote {OUT.relative_to(ROOT)}, {OUT_DOWN.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
