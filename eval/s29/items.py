"""S29 items and gold (eval/PREREG-BUILD.md S29). Data only, no model calls, no network.
Items: every Ticino Gran Consiglio affair (OPD body TI) in ../data/inputs.jsonl.gz begun 1 Jan 2023 - 11 Oct 2026 that has a
lead-department entry in OPD's contributors export (role leading_department, position 1).
Gold: that entry's name; the six named units map to the scheme option of the same name, «Consiglio di Stato del Ticino» and
«Gran Consiglio (Ticino)» map to the none option.
`named_in_input`: the input block (title, long title, text as fed) names any of the six units (lower case, typographic
apostrophes folded, whitespace collapsed) -- the primary population is the items where this is False.
-> eval/s29/items.jsonl, runs/s29/ids.txt"""
import gzip, json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt.scheme import named  # noqa: E402

S = named("ti-dipartimenti")
UNITS = [o["name"]["it"] for o in S["options"]]
NONE_GOLD = {"Consiglio di Stato del Ticino", "Gran Consiglio (Ticino)"}
SINCE, UNTIL = "2023-01-01", "2026-10-11"


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").lower().replace("’", "'").replace("`", "'"))


def main():
    lead = {}
    with gzip.open(ROOT.parent / "data/opd-new/contributors.ndjson.gz", "rt") as f:
        for line in f:
            r = json.loads(line)
            if r["body_key"] == "TI" and r.get("role_harmonized") == "leading_department":
                k = (r.get("position") or 99, r["id"])
                if r["affair_id"] not in lead or k < lead[r["affair_id"]][0]:
                    lead[r["affair_id"]] = (k, r.get("fullname") or "")
    out = []
    with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f:
        for line in f:
            x = json.loads(line)
            if x["body"] != "TI" or not x["date"] or not (SINCE <= x["date"] <= UNTIL) or x["id"] not in lead:
                continue
            raw = lead[x["id"]][1]
            gold = raw if raw in UNITS else (S["none"]["name"]["it"] if raw in NONE_GOLD else None)
            assert gold is not None, raw
            blk = norm(" ".join((x["title"], x["title_long"], x["text"])))
            out.append(dict(id=x["id"], number=x["number"], date=x["date"], type=x["type"], gold=gold, gold_raw=raw,
                            position=lead[x["id"]][0][0], named_in_input=any(norm(u) in blk for u in UNITS),
                            text=bool(x["text"]), input_hash=x["input_hash"]))
    out.sort(key=lambda r: r["id"])
    (HERE / "items.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out))
    (ROOT / "runs/s29").mkdir(parents=True, exist_ok=True)
    (ROOT / "runs/s29/ids.txt").write_text("\n".join(str(r["id"]) for r in out) + "\n")
    prim = [r for r in out if not r["named_in_input"]]
    print(f"items {len(out)} · primary (no unit named in input) {len(prim)} · with text {sum(r['text'] for r in out)}")


if __name__ == "__main__":
    main()
