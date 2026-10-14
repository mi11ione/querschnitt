"""S17 (eval/PREREG-BUILD.md): 200 communal affairs of 2026 with a shipped production chapter → blind packet (S6 guide,
logistics adapted: count, folder) + key outside the packet. No model calls.
Writes eval/s17/packet/{GUIDE.md, items.txt, ann_TEMPLATE.tsv} and eval/s17/key.jsonl."""
import gzip, json, random, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt import prompts as P  # noqa: E402
from querschnitt.compose import decide, read_run  # noqa: E402
from querschnitt.data import load_bodies, parl_name  # noqa: E402
from querschnitt.engine import Engine  # noqa: E402
from querschnitt.examples import ExamplePool  # noqa: E402
from querschnitt.scheme import APS  # noqa: E402

S6 = Path("/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s6-cantonal")
s6_ids = {json.loads(l)["affair_id"] for l in open(S6 / "key.jsonl")}
lock, rows = read_run(ROOT / "runs/main")
eng = Engine(None, ExamplePool.load(ROOT / "data/eval/aps_pool.jsonl"))
B = load_bodies(ROOT.parent / "data/opd-new")
pool = []
with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f:
    for line in f:
        x = json.loads(line)
        if x["level"] == "communal" and "2026-01-01" <= x["date"] <= "2026-10-11" and x["id"] not in s6_ids:
            d = decide(x, rows, eng.ch1_prompt, [])
            if d.get("aps"):
                pool.append((x, d["aps"]))
pool.sort(key=lambda t: t[0]["id"])
pick = random.Random(20261017).sample(pool, 200)
code = lambda ci: "0" if ci == 24 else APS.codes[ci].split(":")[1]
D = HERE / "packet"; D.mkdir(parents=True, exist_ok=True)
items, keys = [], []
for k, (x, a) in enumerate(pick, 1):
    oid = f"M{k:03d}"
    items.append(f"=== {oid} ===\nParlament: {parl_name(x['body'], B, 'de')} (Gemeinde/Stadt)\nTyp: {x['type'] or '-'}\n\n{P.affair_block(x, x['lang'])}\n")
    keys.append(dict(oid=oid, affair_id=x["id"], body=x["body"], lang=x["lang"], title_only=not x["text"], text_kind=x["text_kind"],
                     shipped=code(a["ch"]), top3=[code(c) for c in a["rank"][:3]], lane=a["lane"], conf=round(a["conf"], 4),
                     readings=a["n_readings"]))
(D / "items.txt").write_text("\n".join(items))
(D / "ann_TEMPLATE.tsv").write_text("".join(f"{k['oid']}\t\t\n" for k in keys))
with open(HERE / "key.jsonl", "w") as f:
    for k in keys:
        f.write(json.dumps(k, ensure_ascii=False) + "\n")
g = (S6 / "packet/GUIDE.md").read_text()
g = g.replace("You get 160 parliamentary affairs from Swiss cantonal and municipal parliaments (2015 or later)",
              "You get 200 parliamentary affairs from Swiss municipal parliaments (2026)")
g = re.sub(r"opaque id \(`C001` …\)", "opaque id (`M001` …)", g)
g = g.replace("save it in the s6 folder\n(`.../spikes/s6-cantonal/`)", "save it in the folder you are told to use")
g = g.replace("C001\\t", "M001\\t").replace("C002\\t", "M002\\t").replace("C003\\t", "M003\\t").replace("C001\t", "M001\t").replace("C002\t", "M002\t").replace("C003\t", "M003\t")
(D / "GUIDE.md").write_text(g)
print("pool", len(pool), "packet", len(keys), "lanes", sum(k["lane"] == "please_check" for k in keys))
