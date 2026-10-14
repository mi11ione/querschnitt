"""Prüfstand confusion picture for the shipped chapter design (D4, S16): gold = APS editors' chapter (S9 items),
prediction = D4 read back from the subtopic, exactly as eval/s16/analyze.py computes it. No model calls.
Writes app/data/pruef_confusion.json (+ data-fixture/). Usage: .venv/bin/python app/dev/make_confusion.py"""
import json
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
REPO = APP.parent
S9 = REPO.parent / "ideation2" / "spikes" / "s9-aps"
S16 = REPO / "eval" / "s16"
sys.path.insert(0, str(REPO / "src"))
from querschnitt import prompts as P  # noqa: E402

load = lambda p: {json.loads(l)["oid"]: json.loads(l) for l in open(p)}
order = lambda p: sorted(range(len(p)), key=lambda i: -p[i])


def readback(prior, chs, psub):  # eval/s16/analyze.py verbatim
    opts = P.subtopic_options(chs)
    sc = {(c, j): psub[k] * prior[c] for k, (c, j) in enumerate(opts)}
    best = max(sc, key=sc.get)
    return best[0]


def main():
    items = {it["oid"]: it for it in json.load(open(S9 / "data/items.json"))}
    raw = {ph: load(S9 / f"raw/{ph}.jsonl") for ph in ("d0a", "d0b", "d1", "d3m")}
    s16 = load(S16 / "raw.jsonl")
    ids = sorted(o for o in items if o in s16 and all(o in raw[k] for k in ("d0a", "d0b", "d1", "d3m")))
    K = 25
    m = [[0] * K for _ in range(K)]
    lanes = {"agree": [0, 0], "disagree": [0, 0]}
    for o in ids:
        x = s16[o]["d4"]
        pr, g = readback(x["prior"], x["chs"], x["p"]), int(items[o]["chapter"])
        m[g][pr] += 1
        ag = order(raw["d3m"][o]["p"])[0] == order(raw["d0b"][o]["p"])[0]
        lanes["agree" if ag else "disagree"][0] += 1
        lanes["agree" if ag else "disagree"][1] += int(pr == g)
    res = json.load(open(S16 / "results.json"))
    n = len(ids)
    out = dict(design="D4", n=n, correct=sum(m[i][i] for i in range(K)), m=m,
               lanes=dict(agree_n=lanes["agree"][0], agree_k=lanes["agree"][1], disagree_n=lanes["disagree"][0], disagree_k=lanes["disagree"][1],
                          published=res.get("lanes_D4")),
               file="querschnitt/eval/s16/raw.jsonl + ideation2/spikes/s9-aps/data/items.json")
    s = json.dumps(out, separators=(",", ":"))
    for d in (APP / "data", APP / "data-fixture"):
        (d / "pruef_confusion.json").write_text(s)
    print(f"n {n}, top-1 {out['correct'] / n:.4f}, agree {lanes['agree']}, disagree {lanes['disagree']}")


if __name__ == "__main__":
    main()
