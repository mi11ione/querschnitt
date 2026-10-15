"""S30 blind packets (no model calls). Sample per topic: every affair flagged by any arm (shipped yes/no, its S27 check,
the variant, the frozen keywords) plus 120 random affairs flagged by none (random.Random(20261030) over the id-sorted list).
Packet: id, parliament, level, type, date, title, long title (300), text excerpt (300); the topic sentence; no model output.
Writes packet_A/<topic>/ (shuffled) and packet_B/<topic>/ (same items, reverse order), key.jsonl outside the packets."""
import json, random
from pathlib import Path
from flags import HERE, ROOT, load, kw_hit
from querschnitt.data import load_bodies, parl_name

T, X, F = load()
B = load_bodies(ROOT.parent / "data/opd-new")
clean = lambda s: " ".join((s or "").split())
PREFIX = {"licht": "L", "drohnen": "D", "pestizide": "P"}
GUIDE = """# Annotation guide

Each line of `items.tsv` is one Swiss parliamentary affair: id, parliament, level, type, date, title, long title, and the
start of its text where one exists (any of German, French, Italian). Judge only from this text; look nothing up. The topic
was defined by a user in one sentence:

**«{s}»**

Question for every affair: **Does this affair concern the topic defined by this sentence?** Answer `Y` (yes) or `N` (no). If
you cannot decide, answer the more likely one and add `?` in a third column. Copy `ann_TEMPLATE.tsv` to your output file (one
line per id: `<id>\\tY|N[\\t?]`). Work alone; do not open any file outside this folder.
"""
keys = []
for slug, t in T.items():
    ids = sorted(X)
    any_ = [i for i in ids if any(F[(i, slug)].values())]
    rest = [i for i in ids if not any(F[(i, slug)].values())]
    rng = random.Random(20261030)
    pick = [("any", i) for i in any_] + [("neither", i) for i in rng.sample(rest, min(120, len(rest)))]
    rng.shuffle(pick)
    rows = []
    for j, (h, i) in enumerate(pick, 1):
        x = X[i]; pid = f"{PREFIX[slug]}{j:03d}"
        tl = clean(x["title_long"]) if x["title_long"] and x["title_long"] != x["title"] else ""
        rows.append("\t".join([pid, parl_name(x["body"], B, "de"), x["level"], clean(x["type"]), x["date"], clean(x["title"]),
                               tl[:300], clean(x.get("text"))[:300]]))
        keys.append(dict(pid=pid, topic=slug, oid=i, stratum=h, N_h=len(any_) if h == "any" else len(rest),
                         n_h=len(any_) if h == "any" else min(120, len(rest)), lang=x["lang"], level=x["level"], **F[(i, slug)]))
    for name, order in (("packet_A", rows), ("packet_B", rows[::-1])):
        d = HERE / name / slug; d.mkdir(parents=True, exist_ok=True)
        (d / "items.tsv").write_text("\n".join(order) + "\n")
        (d / "ann_TEMPLATE.tsv").write_text("".join(r.split("\t")[0] + "\t\n" for r in order))
        (d / "GUIDE.md").write_text(GUIDE.format(s=t["sentence"]))
    print(slug, "any", len(any_), "rest", len(rest), "packet", len(pick))
with open(HERE / "key.jsonl", "w") as f:
    for k in keys:
        f.write(json.dumps(k, ensure_ascii=False) + "\n")
