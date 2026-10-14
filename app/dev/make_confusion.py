"""Prüfstand confusion picture and lanes bar for the shipped chapter design: gold = APS editors' chapter. Held out first:
the 927 S25 affairs as composed by eval/s25/analyze.py (eval/s25/decisions.jsonl); without that file, the design set (D4 on
the S9 items, read back from the subtopic exactly as eval/s16/analyze.py computes it). No model calls.
Writes app/data/pruef_confusion.json (+ data-fixture/). Usage: .venv/bin/python app/dev/make_confusion.py"""
import json
import math
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
REPO = APP.parent
S9 = REPO / "eval" / "spikes" / "s9-aps"
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


def wout(k, n, z=1.959964):
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return [math.floor((c - h) / d * 1000) / 1000, math.ceil((c + h) / d * 1000) / 1000]


def lane(rows, n):
    k = sum(r["ch"] == r["gold"] for r in rows)
    return dict(coverage=round(len(rows) / n, 4), precision=round(k / len(rows), 4), k=k, n=len(rows), ci=wout(k, len(rows)))


def held_out():
    """S25: the shipped pipeline on 927 APS-labelled federal affairs never used while designing."""
    rows = [json.loads(l) for l in open(REPO / "eval/s25/decisions.jsonl")]
    m = [[0] * 25 for _ in range(25)]
    for r in rows:
        m[r["gold"]][r["ch"]] += 1
    n = len(rows); f = "eval/s25/decisions.jsonl"
    srt = sorted(rows, key=lambda r: -(r["p_cal"] or 0)); pts, k = [], 0
    for i, r in enumerate(srt, 1):   # routing by recalibrated p: coverage vs precision of the routed share
        k += r["ch"] == r["gold"]
        if i % 5 == 0 or i == n:
            pts.append([round(i / n, 4), round(k / i, 4)])
    pas = lane([r for r in rows if r["lane"] == "pass"], n)
    curve = dict(points=pts, n=n, file=f, test="APS-Kapitel, 927 neue Bundesgeschäfte (hold-out), ausgeliefert",
                 test_fr="Chapitre APS, 927 nouveaux objets fédéraux (hors échantillon), livré",
                 op=dict(coverage=pas["coverage"], precision=pas["precision"], n=pas["n"], label_de="ausgeliefert: p ≥ 0.7", label_fr="livré : p ≥ 0,7"))
    return dict(design="D4", heldout=True, curve=curve, n=n, correct=sum(m[i][i] for i in range(25)), m=m, file=f,
                title_de="Verwechslungen (ausgeliefert, 927 neue Geschäfte)", title_fr="Confusions (livré, 927 nouveaux objets)",
                lanes_tau=dict(pass_=lane([r for r in rows if r["lane"] == "pass"], n), check=lane([r for r in rows if r["lane"] != "pass"], n),
                               readings_agree=lane([r for r in rows if r["readings"] == "agree"], n), file=f))


def main():
    if (REPO / "eval/s25/decisions.jsonl").exists():
        out = held_out()
        s = json.dumps(out, separators=(",", ":"))
        for d in (APP / "data", APP / "data-fixture"):
            (d / "pruef_confusion.json").write_text(s)
        print(f"held out: n {out['n']}, top-1 {out['correct'] / out['n']:.4f}, pass {out['lanes_tau']['pass_']}"); return
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
    lr = REPO / "eval" / "lanes" / "results.json"
    tau = json.load(open(lr))["D4"] if lr.exists() else None
    n = len(ids)
    out = dict(design="D4", n=n, correct=sum(m[i][i] for i in range(K)), m=m,
               lanes=dict(agree_n=lanes["agree"][0], agree_k=lanes["agree"][1], disagree_n=lanes["disagree"][0], disagree_k=lanes["disagree"][1],
                          published=res.get("lanes_D4")),
               file="querschnitt/eval/s16/raw.jsonl + ideation2/spikes/s9-aps/data/items.json",
               lanes_tau=dict(pass_=tau["calibrated_tau_0_7"], check=tau["calibrated_tau_0_7_check"], readings_agree=tau["readings_agree"],
                              file="querschnitt/eval/lanes/results.json") if tau else None)
    s = json.dumps(out, separators=(",", ":"))
    for d in (APP / "data", APP / "data-fixture"):
        (d / "pruef_confusion.json").write_text(s)
    print(f"n {n}, top-1 {out['correct'] / n:.4f}, agree {lanes['agree']}, disagree {lanes['disagree']}")


if __name__ == "__main__":
    main()
