"""S19 (eval/PREREG-BUILD.md): decisions + keyword baseline → blind packet per topic (no model calls).
Writes eval/s19/packet/<topic>/{GUIDE.md, items.tsv, ann_TEMPLATE.tsv} and eval/s19/key.jsonl (outside the packet)."""
import gzip, json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt import prompts as P  # noqa: E402
from querschnitt.compose import read_run, yn_decision  # noqa: E402
from querschnitt.data import load_bodies, parl_name  # noqa: E402
from querschnitt.scheme import adhoc  # noqa: E402

KW = json.loads((HERE / "keywords_frozen.json").read_text())
TOPICS = {"wolf": "wolf", "hitze": "hitze", "ki-schule": "ki_schule"}
lock, rows = read_run(ROOT / "runs/s19")
ids = [int(x) for x in (ROOT / "runs/s19/ids.txt").read_text().split()]
X = {}
with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f:
    for line in f:
        x = json.loads(line)
        if x["id"] in set(ids):
            X[x["id"]] = x
B = load_bodies(ROOT.parent / "data/opd-new")


def kw_hit(key, x):
    t = " " + (x["title"][:400] + " " + (x["title_long"][:400] if x["title_long"] != x["title"] else "")).lower() + " "
    k = KW[key]
    if isinstance(k, dict):
        return any(s in t for s in k["ai"]) and any(s in t for s in k["school"])
    return any(s in t for s in k)


def clean(s):
    return " ".join((s or "").split())


keys = []
for slug, kkey in TOPICS.items():
    T = adhoc(slug)
    dec = {}
    for i in ids:
        x = X[i]
        ra = rows.get(P.pid(*P.yesno_prompt(T, x["lang"], x["title"], x["title_long"], "a")))
        if not ra:
            continue
        rb = rows.get(P.pid(*P.yesno_prompt(T, x["lang"], x["title"], x["title_long"], "b"))) if 0.1 < ra["p_yes"] < 0.9 else None
        if 0.1 < ra["p_yes"] < 0.9 and not rb:
            continue
        dec[i] = yn_decision(ra, rb)
    strata = {"A∩K": [], "A only": [], "K only": [], "neither": []}
    for i in sorted(dec):
        a, k = dec[i]["flag"], kw_hit(kkey, X[i])
        strata["A∩K" if a and k else "A only" if a else "K only" if k else "neither"].append(i)
    rng = random.Random(20261019)
    pick = [(h, i) for h in ("A∩K", "A only", "K only") for i in strata[h]] + [("neither", i) for i in rng.sample(strata["neither"], min(120, len(strata["neither"])))]
    rng.shuffle(pick)
    d = HERE / "packet" / slug; d.mkdir(parents=True, exist_ok=True)
    with open(d / "items.tsv", "w") as fi, open(d / "ann_TEMPLATE.tsv", "w") as ft:
        for j, (h, i) in enumerate(pick, 1):
            pid = f"{slug[:1].upper()}{j:03d}"; x = X[i]
            tl = clean(x["title_long"]) if x["title_long"] and x["title_long"] != x["title"] else ""
            fi.write("\t".join([pid, parl_name(x["body"], B, "de"), x["level"], clean(x["type"]), x["date"], clean(x["title"]), tl[:300]]) + "\n")
            ft.write(f"{pid}\t\n")
            keys.append(dict(pid=pid, topic=slug, oid=i, stratum=h, N_h=len(strata[h]), n_h=sum(1 for hh, _ in pick if hh == h),
                             p=dec[i]["p"], flag=dec[i]["flag"], kw=kw_hit(kkey, x), lang=x["lang"], level=x["level"], body=x["body"]))
    (d / "GUIDE.md").write_text(f"""# Annotation guide — topic «{T['names']['de']}»

Each line of `items.tsv` is one Swiss parliamentary affair: id, parliament, level, type, date, title, long title (any of
German, French, Italian). Judge only from this text; look nothing up. Question for every affair:

**{T['question']['de']}**

Answer `Y` (yes, the affair concerns this topic) or `N` (no). If you cannot decide, answer the more likely one and add `?`
in a third column. Copy `ann_TEMPLATE.tsv` to your output file (one line per id: `<id>\\tY|N[\\t?]`). Work alone; do not
open any file outside this folder.
""")
    print(slug, {h: len(v) for h, v in strata.items()}, "packet", len(pick))
with open(HERE / "key.jsonl", "w") as f:
    for k in keys:
        f.write(json.dumps(k, ensure_ascii=False) + "\n")
