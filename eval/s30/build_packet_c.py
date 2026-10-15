"""S30 tie-break packet: the items where judge A and B differ (packet_c_ids.json from `analyze.py --c-template`), same
columns and guide as packet_A, A's order. No model calls."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
ids = json.loads((HERE / "packet_c_ids.json").read_text())
for slug, want in ids.items():
    if not want:
        continue
    src = HERE / "packet_A" / slug; d = HERE / "packet_C" / slug; d.mkdir(parents=True, exist_ok=True)
    rows = [l for l in (src / "items.tsv").read_text().splitlines() if l.split("\t")[0] in set(want)]
    (d / "items.tsv").write_text("\n".join(rows) + "\n")
    (d / "ann_TEMPLATE.tsv").write_text("".join(r.split("\t")[0] + "\t\n" for r in rows))
    (d / "GUIDE.md").write_text((src / "GUIDE.md").read_text())
    print(slug, len(rows))
