"""Build app/data/integration.json for the «Anbindung» view from the repo (no runtime fetch of repo files):
the `topics` table of upstream/opd/migrations/0001_topics.up.sql, the main path of upstream/hop/load_topics.hpl with the
run line of upstream/hop/README.md, a stored /changes sample from app/data/topics.jsonl.gz, and the compose footprint
of eval/ci_footprint.txt. Usage: python3 app/dev/make_integration.py"""
import gzip
import json
import re
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
REPO = APP.parent
SQL = REPO / "upstream/opd/migrations/0001_topics.up.sql"
HPL = REPO / "upstream/hop/load_topics.hpl"
HOP_README = REPO / "upstream/hop/README.md"
TOPICS = APP / "data/topics.jsonl.gz"
FOOT = REPO / "eval/ci_footprint.txt"

MACHINE = {"p", "p_raw", "lane", "evidence_field", "evidence_text_id", "evidence_doc_id", "evidence_char_start", "evidence_char_end",
           "evidence_quote", "model", "model_build", "cutoffs_id", "prompt_id", "input_hash", "content_hash", "engine_version"}
DECISION = {"status", "provenance", "confirmed_by", "confirmed_by_body_id", "confirmed_at"}


def table():
    sql = SQL.read_text()
    body = sql[sql.index("CREATE TABLE IF NOT EXISTS topics ("):]
    body = body[:body.index("\n);")]
    cols = []
    for line in body.splitlines()[1:]:
        m = re.match(r"\s+([a-z_]+)\s+([a-z]+(?: [a-z]+)?)\b(.*)", line)
        if not m or m.group(1) == "constraint":
            continue
        name, typ, rest = m.group(1), m.group(2), m.group(3)
        note = rest.split("--", 1)[1].strip() if "--" in rest else ""
        chk = re.search(r"CHECK \(([a-z_]+) IN \(([^)]*)\)\)", rest)
        if chk and not note:
            note = chk.group(2).replace("'", "")
        cols.append(dict(name=name, type=typ.replace(" generated", ""), note=note,
                         group="machine" if name in MACHINE else "decision" if name in DECISION else "key"))
    return dict(file=str(SQL.relative_to(REPO)), columns=cols)


def hop():
    x = HPL.read_text()
    types = dict(re.findall(r"<transform>\s*<name>([^<]+)</name>\s*<type>([^<]+)</type>", x))
    edges = re.findall(r"<hop><from>([^<]+)</from><to>([^<]+)</to>", x)
    nxt = {}
    for a, b in edges:
        if not b.startswith("skip"):
            nxt[a] = b
    start = next(a for a, _ in edges if a not in {b for _, b in edges})
    path, cur = [start], start
    while cur in nxt:
        cur = nxt[cur]; path.append(cur)
    skips = [dict(after=a, name=b) for a, b in edges if b.startswith("skip")]
    rd = HOP_README.read_text()
    run = re.search(r"(\./hop-run\.sh[^\n]*\n[^\n]*)", rd)
    return dict(file=str(HPL.relative_to(REPO)), steps=[dict(name=n, type=types.get(n, "")) for n in path], skips=skips,
                run=re.sub(r"\s*\\\s*\n\s*", " ", run.group(1)).strip() if run else None, readme=str(HOP_README.relative_to(REPO)))


def changes_sample():
    rows, total = [], 0
    with gzip.open(TOPICS, "rt") as f:
        for line in f:
            total += 1
            if len(rows) < 3:
                r = json.loads(line)
                rows.append({k: r.get(k) for k in ("affair_id", "body_key", "scheme", "level", "code", "rank", "p", "lane", "status",
                                                    "provenance", "build", "valid_from", "valid_to")})
    return dict(sample=True, total=total, rows=rows, file=str(TOPICS.relative_to(REPO)))


def footprint():
    txt = FOOT.read_text()
    mem = {m.group(1): float(m.group(2)) for m in re.finditer(r"\| querschnitt-([a-z-]+)-1 \| ([\d.]+)MiB", txt)}
    img = re.search(r"image (\d+)\s*MB", txt)
    run = re.search(r"run (\d+) (https://\S+)", txt)
    full = sum(v for k, v in mem.items() if k in ("api", "db", "nightly"))
    return dict(containers=mem, full_mib=round(full, 2), lite_mib=mem.get("nightly-lite"), image_mb=int(img.group(1)) if img else None,
                run_id=run.group(1) if run else None, run_url=run.group(2) if run else None, file=str(FOOT.relative_to(REPO)))


def main():
    out = dict(table=table(), hop=hop(), changes=changes_sample(), footprint=footprint())
    s = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    for d in (APP / "data", APP / "data-fixture"):
        (d / "integration.json").write_text(s)
    print(len(out["table"]["columns"]), "columns ·", " → ".join(x["name"] for x in out["hop"]["steps"]), "·", out["changes"]["total"], "rows ·",
          out["footprint"]["full_mib"], "MiB full")


if __name__ == "__main__":
    main()
