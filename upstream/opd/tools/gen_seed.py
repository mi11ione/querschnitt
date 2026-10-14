#!/usr/bin/env python3
"""Writes ../migrations/0002_topic_schemes_seed.sql from Querschnitt's scheme files (src/querschnitt/schemes/).

    python3 upstream/opd/tools/gen_seed.py            # from the repo root; needs PyYAML (in the querschnitt venv)

Scheme ids are fixed (1 aps, 2 adhoc/digitalisierung, 3 be-directorates) so the export preview (../export/to_opd.py) and
the database agree. The version of a scheme is sha256[:8] of its file: a changed file is a new version row."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                       # repo root
SCHEMES = ROOT / "src/querschnitt/schemes"
OUT = HERE.parent / "migrations/0002_topic_schemes_seed.sql"

SCHEME_IDS = {"aps": 1, "adhoc/digitalisierung": 2, "be-directorates": 3}
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


def schemes() -> list[tuple[dict, list[dict]]]:
    """-> [(scheme row, [code rows])] in SCHEME_IDS order."""
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
    # ad-hoc topic: Digitalisierung (yes / no)
    p = SCHEMES / "adhoc/digitalisierung.yaml"; d = yaml.safe_load(p.read_text())
    n = d["names"]
    codes = [dict(code=f"{d['id']}:yes", level=1, parent_code=None, position=1, external_id=None,
                  label_de=n["de"], label_fr=n["fr"], label_it=n["it"]),
             dict(code=f"{d['id']}:no", level=1, parent_code=None, position=2, external_id=None,
                  label_de=f"{n['de']}: {NO['de']}", label_fr=f"{n['fr']} : {NO['fr']}", label_it=f"{n['it']}: {NO['it']}")]
    out.append((dict(id=2, scheme_key=d["id"], version=version(p), type="adhoc", levels=1,
                     name_de=n["de"], name_fr=n["fr"], name_it=n["it"], name_rm=None, name_en="Digitalisation",
                     question_de=d["question"]["de"], question_fr=d["question"]["fr"], question_it=d["question"]["it"], body_key=None,
                     licence="CC-BY-4.0", source_name="Querschnitt (question and scope note); use case Digitale Verwaltung Schweiz",
                     source_url="https://www.digitale-verwaltung-schweiz.ch/aktuelles/politische-geschaefte",
                     notes="Yes/no topic; p = probability of yes; flagged at p >= 0.5.", code_count=len(codes)), codes))
    # a parliament's own scheme: Bern's directorates
    p = SCHEMES / "be-directorates.yaml"; d = yaml.safe_load(p.read_text())
    codes = []
    for i, o in enumerate(d["options"], 1):
        codes.append(dict(code=o["code"], level=1, parent_code=None, position=i, external_id=o["abbr"].get("de"),
                          label_de=o["name"].get("de"), label_fr=o["name"].get("fr"), label_it=None))
    if d.get("none"):
        codes.append(dict(code=d["none"]["code"], level=1, parent_code=None, position=len(codes) + 1, external_id=None,
                          label_de=d["none"]["name"].get("de"), label_fr=d["none"]["name"].get("fr"), label_it=None))
    out.append((dict(id=3, scheme_key=d["id"], version=version(p), type="body", levels=1,
                     name_de=d["title"]["de"], name_fr=d["title"]["fr"], name_it=None, name_rm=None, name_en="Canton of Bern: lead directorate",
                     question_de=None, question_fr=None, question_it=None, body_key="BE",
                     licence=None, source_name="Kanton Bern (directorate names); remits written by Querschnitt",
                     source_url="https://www.be.ch", notes=d.get("source"), code_count=len(codes)), codes))
    return out


def main() -> int:
    lines = ["-- 0002_topic_schemes_seed: the schemes Querschnitt ships, with their codes and labels.",
             "-- GENERATED by upstream/opd/tools/gen_seed.py from src/querschnitt/schemes/ (do not edit by hand).",
             "-- Idempotent: ON CONFLICT DO NOTHING. A new scheme file version is a new topic_schemes row.", "BEGIN;", ""]
    for s, codes in schemes():
        body = "(SELECT id FROM bodies WHERE body_key = 'BE')" if s["body_key"] else "NULL"
        cols = ["id", "scheme_key", "version", "type", "levels", "name_de", "name_fr", "name_it", "name_rm", "name_en",
                "question_de", "question_fr", "question_it", "body_id", "body_key", "licence", "source_name", "source_url",
                "notes", "code_count", "active"]
        vals = [q(s[c]) if c not in ("body_id", "active") else (body if c == "body_id" else "true") for c in cols]
        lines.append(f"INSERT INTO topic_schemes ({', '.join(cols)})\nVALUES ({', '.join(vals)})\nON CONFLICT (scheme_key, version) DO NOTHING;")
        lines.append("INSERT INTO topic_codes (scheme_id, scheme_key, code, level, parent_code, position, external_id, label_de, label_fr, label_it, label_rm) VALUES")
        rows = [f"  ({s['id']}, {q(s['scheme_key'])}, {q(c['code'])}, {c['level']}, {q(c['parent_code'])}, {c['position']}, "
                f"{q(c['external_id'])}, {q(c['label_de'])}, {q(c['label_fr'])}, {q(c['label_it'])}, NULL)" for c in codes]
        lines.append(",\n".join(rows) + "\nON CONFLICT (scheme_id, code) DO NOTHING;\n")
    lines.append("SELECT setval(pg_get_serial_sequence('topic_schemes', 'id'), (SELECT max(id) FROM topic_schemes));")
    lines.append("COMMIT;")
    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
