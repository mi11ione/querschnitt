"""S8 on the full 2026 census (VISION §6.5: "S8 estimates recomputed on the full 2026 census"). No model calls.

Population: the S8 window (6 Oct export; affairs begun 1 Jan–6 Oct 2026 with a title; S8 items_cache). Decision per affair:
the S8 rows (same prompt, same build) where they exist, else the corpus run's row for the same affair (11 Oct export input;
same prompt frame and build). Flags are now counted, not estimated. Precision/recall against the blind AI judge use the same
464-item packet and gold as S8 (score.py), with post-stratified weights: within each packet stratum the S8 Horvitz–Thompson
weights are scaled to the full-census stratum size. Bootstrap within strata, 2,000 resamples (as S8)."""
import collections, gzip, json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt import prompts as P  # noqa: E402
from querschnitt.compose import read_run, yn_decision  # noqa: E402
from querschnitt.scheme import adhoc  # noqa: E402

S8 = HERE.parent / "spikes/s8-dvs"  # vendored S8 (eval/spikes/)


# ---- S8 score.py gold rules, copied verbatim (importing score.py would re-run it)
def _rd(p):
    d = {}
    if not Path(p).exists():
        return d
    for line in Path(p).read_text().splitlines():
        x = line.rstrip("\n").split("\t")
        if len(x) >= 2 and x[0].startswith("D") and x[1].strip():
            d[x[0]] = "Q" if (len(x) > 2 and x[2].strip() == "?") else x[1].strip().upper()
    return d


class S8S:
    K = {r["pid"]: r for r in map(json.loads, (S8 / "key.jsonl").read_text().splitlines())}
    A, B, C = _rd(S8 / "ann_A.tsv"), _rd(S8 / "ann_B.tsv"), _rd(S8 / "ann_C.tsv")
    Qw = _rd(S8.parent / "s8q-crossfamily/ann_Q.tsv")

    @staticmethod
    def gold(i):
        A, B, C = S8S.A, S8S.B, S8S.C
        if A.get(i) in ("Y", "N") and A.get(i) == B.get(i): return A[i]
        return C.get(i) if C.get(i) in ("Y", "N") else None

    @staticmethod
    def gold_maj(i):
        v = [x for x in (S8S.A.get(i), S8S.B.get(i), S8S.Qw.get(i)) if x in ("Y", "N")]
        return None if len(v) < 2 else ("Y" if v.count("Y") * 2 > len(v) else "N" if v.count("N") * 2 > len(v) else None)

T = adhoc("digitalisierung")
IT = {x["id"]: x for x in json.load(gzip.open(S8 / "items_cache.json.gz", "rt", encoding="utf-8"))}  # S8 items_cache.json, stored gzipped
W = [i for i, x in IT.items() if x["in_window"] and x["title"]]
rd = lambda p: {json.loads(l)["id"]: json.loads(l) for l in open(p)}
RA, RB = rd(S8 / "raw/a.jsonl"), rd(S8 / "raw/b.jsonl")
lock, rows = read_run(ROOT / "runs/main")
X = {}
with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f:
    for line in f:
        x = json.loads(line)
        if x["id"] in IT:
            X[x["id"]] = x


def decision(i):
    a = RA.get(i); b = RB.get(i)
    if a and (not (0.1 < a["p_yes"] < 0.9) or b):
        return yn_decision(dict(p_yes=a["p_yes"]), dict(p_yes=b["p_yes"]) if b else None), "s8"
    x = X.get(i)
    if not x:
        return None, None
    ra = rows.get(P.pid(*P.yesno_prompt(T, x["lang"], x["title"], x["title_long"], "a")))
    if not ra:
        return None, None
    rb = rows.get(P.pid(*P.yesno_prompt(T, x["lang"], x["title"], x["title_long"], "b"))) if 0.1 < ra["p_yes"] < 0.9 else None
    if 0.1 < ra["p_yes"] < 0.9 and not rb:
        return None, None
    return yn_decision(ra, rb), "run"


D, src = {}, collections.Counter()
for i in W:
    d, s = decision(i)
    if d:
        D[i] = d; src[s] += 1
R = dict(window=len(W), decided=len(D), sources=dict(src), missing=len(W) - len(D), build=lock["fp"])
swiss = lambda i: IT[i]["body"] != "LIE"
kw = lambda i: IT[i]["kw"]
for name, sel in (("all", lambda i: True), ("swiss", swiss)):
    ids = [i for i in D if sel(i)]
    R[f"flags_{name}"] = dict(apertus=sum(D[i]["flag"] for i in ids), keyword=sum(kw(i) for i in ids),
                              both=sum(D[i]["flag"] and kw(i) for i in ids), please_check=sum(D[i]["lane"] == "please_check" for i in ids),
                              parliaments_flagged=len({IT[i]["body"] for i in ids if D[i]["flag"]}), n=len(ids))
# post-stratified judge-based precision / recall (S8 packet, S8 gold)
stratum = lambda i: ("A∩K" if D[i]["flag"] and kw(i) else "A only" if D[i]["flag"] else "K only" if kw(i) else "neither")
K = S8S.K
Nh = collections.Counter(stratum(i) for i in D if swiss(i))
by = collections.defaultdict(list)
for pid, r in K.items():
    if r["oid"] in D and swiss(r["oid"]):
        by[r["stratum"]].append(pid)
R["packet"] = {h: len(v) for h, v in by.items()}
R["census_strata_swiss"] = dict(Nh)
# map S8 packet strata names to census strata (S8 strata were defined on the S8 p_yes at the snapshot)
w = {}
for h, v in by.items():
    tot = sum(K[p]["final_weight"] for p in v)
    hn = {"A∩K": "A∩K", "A only": "A only", "K only": "K only", "neither": "neither"}.get(h, h)
    for p in v:
        w[p] = K[p]["final_weight"] * Nh.get(hn, 0) / tot if tot else 0


def est(items, g):
    t = collections.Counter()
    for p in items:
        y = g(p)
        if y is None:
            continue
        i = K[p]["oid"]; a = D[i]["flag"]; k = kw(i); ww = w[p]
        t["pos"] += ww * (y == "Y")
        t["a_tp"] += ww * (a and y == "Y"); t["a_fp"] += ww * (a and y == "N"); t["a_fn"] += ww * ((not a) and y == "Y")
        t["k_tp"] += ww * (k and y == "Y"); t["k_fp"] += ww * (k and y == "N"); t["k_fn"] += ww * ((not k) and y == "Y")
    f = lambda tp, x: tp / (tp + x) if tp + x else float("nan")
    return dict(pos=t["pos"], a_P=f(t["a_tp"], t["a_fp"]), a_R=f(t["a_tp"], t["a_fn"]), k_P=f(t["k_tp"], t["k_fp"]), k_R=f(t["k_tp"], t["k_fn"]))


items = [p for v in by.values() for p in v]
for gname, g in (("gold_AB_C", S8S.gold), ("gold_majority_ABQ", S8S.gold_maj)):
    e = est(items, g)
    rng = random.Random(7); boots = collections.defaultdict(list)
    for _ in range(2000):
        s = [rng.choice(v) for v in by.values() for _ in v]
        b = est(s, g)
        for k_, v_ in b.items():
            boots[k_].append(v_)
        boots["dP"].append(b["a_P"] - b["k_P"]); boots["dR"].append(b["a_R"] - b["k_R"])
    ci = lambda v: (round(sorted(v)[int(.025 * len(v))], 3), round(sorted(v)[int(.975 * len(v)) - 1], 3))
    R[gname] = dict(point={k_: round(v_, 3) for k_, v_ in e.items()}, ci={k_: ci([x for x in v_ if x == x]) for k_, v_ in boots.items()})
(HERE / "results.json").write_text(json.dumps(R, indent=1, ensure_ascii=False))
print(json.dumps(R, indent=1, ensure_ascii=False))
