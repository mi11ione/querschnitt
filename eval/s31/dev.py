"""S31 dev: variants of the shipped federal design D4, measured ONLY on the design set (the 1,357 S9/S16 items).

Leave-one-out: every example list excludes the affair itself (the S9 frozen neighbours, `d3_neighbours.json`, were built
that way; extra neighbours for k=10 come from the shipped BM25 over data/eval/aps_pool.jsonl, own oid excluded).
Existing rows are reused (S9 d0b/d3m chapter readings, S9 d1 and S16 subtopic rows when the chapter list matches); only
missing readings are asked. Resumable: eval/s31/dev_raw.jsonl (one row per asked step, keyed).

Variants (chosen by reasoning on the free dev analysis in DEV.md, before any S31 call):
  D4    shipped: r1 = identity order + 5 examples (S9 d3m), r2 = S1 order without examples (S9 d0b); subtopic read-back
  V1    k10: r1 with the 10 nearest examples (frozen 5 + next 5), r2 as D4
  V2    subn: r1 with the 5 examples showing chapter AND the editors' main subtopic, r2 as D4
  V3    ex2: r2 also with the 5 examples (S1 order), r1 as D4
  V4    third: D4 + a third reading (5 examples, a third code order) only when r1 and r2 disagree on the top chapter
  V5    ex2+third (fixed after V1–V4 were seen on the 400-item subset, still dev only; see DEV.md): r1 = d3m, r2 = r2ex
        (both code orders with the 5 examples, as V3); when r1 and r2 disagree on the top chapter, r3ex as in V4
Decision for every design (the production rule, compose.chapter_decision generalised to n readings): P = mean of the
readings, G = their normalised geometric mean; "no policy topic" if G's top is it, else subtopic request over
P.subtopic_chapters(P) and the chapter read back from score = p(sub) × P(chapter).

Usage: python eval/s31/dev.py call --variants V1,V2,V3,V4 --set sub400 | python eval/s31/dev.py score [--set all]"""
from __future__ import annotations

import argparse, json, math, random, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt import prompts as P  # noqa: E402
from querschnitt.client import Client, Endpoint  # noqa: E402
from querschnitt.engine import Engine, probs  # noqa: E402
from querschnitt.examples import ExamplePool, toks  # noqa: E402
from querschnitt.scheme import APS  # noqa: E402

BUILD = "vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840"
S9 = HERE.parent / "spikes/s9-aps"
LEDGER = HERE / "ledger.jsonl"
CAP_USD = 4.0                      # list price, the whole S31 (dev + test share this ledger)
RAW = HERE / "dev_raw.jsonl"

load = lambda p: {json.loads(l)["oid"]: json.loads(l) for l in open(p)}
items = {it["oid"]: it for it in json.load(open(S9 / "data/items.json"))}
IDS = sorted(items)
SUB400 = sorted(random.Random(31).sample(IDS, 400))     # fixed dev subset (cost control)
s9 = {ph: load(S9 / f"raw/{ph}.jsonl") for ph in ("d0b", "d1", "d3m")}
s16 = load(HERE.parent / "s16/raw.jsonl")
FROZEN = {int(k): v for k, v in json.load(open(S9 / "data/d3_neighbours.json")).items()}
POOL = ExamplePool.load(ROOT / "data/eval/aps_pool.jsonl")
PERM3 = list(range(25)); random.Random(31).shuffle(PERM3)   # third code order (V4)
assert PERM3 not in (list(range(25)), P.S1PERM)


def _subnames() -> dict[int, str]:
    """Editors' main subtopic per pool affair (S9 items, S9 aps_ext, S5 aps_gold_sample); only names APS publishes."""
    known = {s for l in APS.subs_de.values() for s in l}
    out = {}
    for path in (HERE.parent / "spikes/s2-oracles/data/aps_gold_sample.jsonl", S9 / "data/aps_ext.jsonl"):
        for l in open(path):
            x = json.loads(l)
            out[x.get("opd_affair_id") or x.get("oid")] = x.get("subtopic_name")
    for o, it in items.items():
        out[o] = it.get("subtopic_name") or out.get(o)
    return {o: s for o, s in out.items() if s in known}


SUBN = _subnames()


def affair(o: int) -> dict:
    d = items[o]["de"]
    return dict(id=o, title=d["title"], title_long=d["title_long"], text=d["text"], lang="de", level="federal")


def examples(o: int, k: int) -> list[dict]:
    """Leave-one-out: the frozen S9 five, then (k > 5) the next BM25 neighbours from the pool, own oid excluded."""
    fz = [dict(oid=n["oid"], title=n["title"], chapter=n["chapter"]) for n in FROZEN[o]]
    if k <= 5:
        return fz[:k]
    a = affair(o); seen = {o} | {e["oid"] for e in fz}
    q = toks(a["title"]) * 2 + toks((a.get("text") or "")[:400])
    extra = [POOL.pool[j] for j, _ in POOL.bm.top(q, k + 40) if POOL.pool[j]["oid"] not in seen][: k - 5]
    return fz + [dict(oid=e["oid"], title=e["title"], chapter=e["chapter"]) for e in extra]


EX_SUB = "  → Thema: {code} ({name}), Unterthema: {sub}"


def prompt_subnames(a: dict, perm: list[int], exs: list[dict]) -> tuple[str, str]:
    """V2: the shipped example prompt (P.chapter_prompt_examples), each example also naming the editors' main subtopic."""
    t = P.T["de"]; names = APS.chapter_names_de_with_none; inv = {perm[i]: i for i in range(25)}
    themes = "\n".join(f"{P.CODES[i]} = {P._chapter_line(perm[i], names)}" for i in range(25))
    lines = []
    for e in exs:
        c = e["chapter"]; s = SUBN.get(e["oid"])
        lines.append(f"- {e['title']}\n" + (EX_SUB.format(code=P.CODES[inv[c]], name=names[c], sub=s) if s
                                           else f"  → Thema: {P.CODES[inv[c]]} ({names[c]})"))
    user = (f"{t['ask']}\n\n{t['themes']}:\n{themes}\n\n{P.EX_HEAD}\n" + "\n".join(lines) +
            f"\n\n{t['item']}:\n{P.affair_block(a, 'de')}\n\n{t['fmt_code']}")
    return user, '{"' + t["key"] + '": "'


def step_prompt(step: str, o: int) -> tuple[str, str, list[int]]:
    """-> user, prefill, perm for the variant readings."""
    a = affair(o)
    ex = lambda k: [(e["title"], e["chapter"]) for e in examples(o, k)]
    if step == "r1k10":
        return (*P.chapter_prompt_examples(a, list(range(25)), ex(10)), list(range(25)))
    if step == "r1subn":
        return (*prompt_subnames(a, list(range(25)), examples(o, 5)), list(range(25)))
    if step == "r2ex":
        return (*P.chapter_prompt_examples(a, P.S1PERM, ex(5)), P.S1PERM)
    if step == "r3ex":
        return (*P.chapter_prompt_examples(a, PERM3, ex(5)), PERM3)
    raise KeyError(step)


# ---------------------------------------------------------------------------------------------------- rows
def load_raw() -> dict:
    return {json.loads(l)["key"]: json.loads(l) for l in open(RAW)} if RAW.exists() else {}


def sub_cache(raw: dict) -> dict:
    """(oid, chs) -> subtopic p: S9 d1, S16 d4/d4s and S31 rows (the same prompt: P.subtopic_prompt, German frame)."""
    c = {}
    for o, r in s9["d1"].items():
        c[(o, tuple(r["chs"]))] = r["p"]
    for o, r in s16.items():
        for n in ("d4", "d4s"):
            c[(o, tuple(r[n]["chs"]))] = r[n]["p"]
    for r in raw.values():
        if r["step"] == "sub":
            c[(r["oid"], tuple(r["chs"]))] = r["p"]
    return c


def readings(v: str, o: int, raw: dict) -> list[list[float]] | None:
    """The chapter readings of design v for item o (None if a needed row is missing)."""
    g = lambda s: (raw.get(f"{s}:{o}") or {}).get("p")
    d3m, d0b = s9["d3m"][o]["p"], s9["d0b"][o]["p"]
    if v == "D4":
        return [d3m, d0b]
    if v == "V1":
        return [g("r1k10"), d0b] if g("r1k10") else None
    if v == "V2":
        return [g("r1subn"), d0b] if g("r1subn") else None
    if v == "V3":
        return [d3m, g("r2ex")] if g("r2ex") else None
    if v == "V4":
        if argmax(d3m) == argmax(d0b):
            return [d3m, d0b]
        return [d3m, d0b, g("r3ex")] if g("r3ex") else None
    if v == "V5":
        return V5(o, raw)
    raise KeyError(v)


def V5(o, raw):   # fixed after V1–V4 on the 400 subset; see DEV.md
    r1, r2 = s9["d3m"][o]["p"], (raw.get(f"r2ex:{o}") or {}).get("p")
    if r2 is None:
        return None
    if argmax(r1) == argmax(r2):
        return [r1, r2]
    r3 = (raw.get(f"r3ex:{o}") or {}).get("p")
    return [r1, r2, r3] if r3 else None


NEEDS = {"V1": lambda o: ["r1k10"], "V2": lambda o: ["r1subn"], "V3": lambda o: ["r2ex"],
         "V4": lambda o: ["r3ex"] if argmax(s9["d3m"][o]["p"]) != argmax(s9["d0b"][o]["p"]) else [],
         "D4": lambda o: [], "V5": lambda o: ["r2ex", "r3ex?"]}


def argmax(v):
    return max(range(len(v)), key=lambda i: v[i])


def mean(ps):
    return [sum(x) / len(ps) for x in zip(*ps)]


def geo(ps):
    g = [math.exp(sum(math.log(max(x, 1e-12)) for x in xs) / len(ps)) for xs in zip(*ps)]
    s = sum(g); return [v / s for v in g]


def decision(ps: list[list[float]], psub_for) -> dict | None:
    """compose.chapter_decision for n readings. psub_for(chs) -> subtopic p or None (missing)."""
    PA, G = mean(ps), geo(ps)
    if argmax(G) == 24:
        rank = sorted(range(25), key=lambda i: -G[i])
        return dict(ch=24, rank=rank[:3], conf=G[24], chs=None, P=PA)
    chs = P.subtopic_chapters(PA)
    ps_ = psub_for(chs)
    if ps_ is None:
        return dict(need_sub=chs)
    opts = P.subtopic_options(chs)
    sc = {(c, j): ps_[k] * PA[c] for k, (c, j) in enumerate(opts)}
    tot = sum(sc.values()) or 1.0
    best = max(sc, key=sc.get)
    chbest = {}
    for (c, j), v in sc.items():
        chbest[c] = max(chbest.get(c, 0.0), v)
    rk = sorted(chbest, key=lambda c: -chbest[c]) + [c for c in sorted(range(25), key=lambda i: -PA[i]) if c not in chbest]
    conf = sum(v for (c, j), v in sc.items() if c == best[0]) / tot
    return dict(ch=best[0], rank=rk[:3], conf=conf, chs=chs, P=PA, sub=APS.sub_codes[best[0]][best[1]])


# ---------------------------------------------------------------------------------------------------- calls
def call(variants: list[str], ids: list[int]):
    raw = load_raw(); subs = sub_cache(raw)
    ep = Endpoint.from_env(); ep.max_rate, ep.conc = 0.5, 2
    eng = Engine(Client(ep, ledger=str(LEDGER), cap_usd=CAP_USD, expect_build=BUILD, tag="s31-dev"))
    lock = threading.Lock(); n = dict(calls=0)

    def put(row):
        with lock:
            raw[row["key"]] = row
            if row["step"] == "sub":
                subs[(row["oid"], tuple(row["chs"]))] = row["p"]
            with open(RAW, "a") as f:
                f.write(json.dumps(row) + "\n")
            n["calls"] += 1

    def ask(step, o):
        u, p, perm = step_prompt(step, o)
        d, meta = eng._ask(u, p, P.CODES)
        put(dict(key=f"{step}:{o}", oid=o, step=step, pid=P.pid(u, p), codes=d, p=probs(d, P.CODES, perm),
                 fp=meta["fp"], pt=meta["pt"], usd=meta["usd"]))

    def task(o):
        for v in variants:
            for s in NEEDS[v](o):
                if s == "r3ex?":   # V5: the third reading only when the two example readings disagree
                    s = "r3ex" if argmax(s9["d3m"][o]["p"]) != argmax(raw[f"r2ex:{o}"]["p"]) else None
                if s and f"{s}:{o}" not in raw:
                    ask(s, o)
            ps = readings(v, o, raw)
            if ps is None:
                continue
            d = decision(ps, lambda chs: subs.get((o, tuple(chs))))
            if d and "need_sub" in d:
                chs = d["need_sub"]
                if f"sub:{o}:{','.join(map(str, chs))}" not in raw:
                    r = eng.sub(affair(o), chs)
                    put(dict(key=f"sub:{o}:{','.join(map(str, chs))}", oid=o, step="sub", chs=chs, pid=r["pid"],
                             p=r["p"], fp=r["meta"]["fp"], pt=r["meta"]["pt"], usd=r["meta"]["usd"]))

    with ThreadPoolExecutor(2) as ex:
        for i, _ in enumerate(ex.map(task, ids)):
            if i % 50 == 0:
                print(f"{i}/{len(ids)} items · {n['calls']} calls · USD {eng.client.spent:.3f} (ledger)", flush=True)
    print(f"done · {n['calls']} calls this session · USD {eng.client.spent:.3f} ledger total", flush=True)


# ---------------------------------------------------------------------------------------------------- scoring
def trunc(v, d=4):
    return math.floor(v * 10 ** d) / 10 ** d


def wout(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return [math.floor((c - h) / d * 1000) / 1000, math.ceil((c + h) / d * 1000) / 1000]


def paired(va, vb, seed=2026, B=2000):
    rng = random.Random(seed); n = len(va); diffs = []
    for _ in range(B):
        s = [rng.randrange(n) for _ in range(n)]
        diffs.append(sum(va[i] - vb[i] for i in s) / n)
    diffs.sort()
    return dict(diff=math.trunc((sum(va) - sum(vb)) / n * 1e4) / 1e4, ci=[math.floor(diffs[49] * 1e4) / 1e4, math.ceil(diffs[1950] * 1e4) / 1e4])


def score(ids: list[int], variants: list[str]) -> dict:
    raw = load_raw(); subs = sub_cache(raw)
    gold = {o: items[o]["chapter"] for o in ids}
    D = {}
    for v in variants:
        D[v] = {}
        for o in ids:
            ps = readings(v, o, raw)
            d = decision(ps, lambda chs: subs.get((o, tuple(chs)))) if ps else None
            if d and "need_sub" not in d:
                D[v][o] = d
    common = [o for o in ids if all(o in D[v] for v in variants)]
    R = dict(n_items=len(ids), n_scored_all=len(common), designs={})
    base = [int(D["D4"][o]["ch"] == gold[o]) for o in common]
    for v in variants:
        k1 = sum(D[v][o]["ch"] == gold[o] for o in common); k3 = sum(gold[o] in D[v][o]["rank"] for o in common)
        R["designs"][v] = dict(top1=trunc(k1 / len(common)), top1_ci=wout(k1, len(common)), k1=k1,
                               top3=trunc(k3 / len(common)), n_missing=len(ids) - len(D[v]))
        if v != "D4":
            R["designs"][v]["minus_D4"] = paired([int(D[v][o]["ch"] == gold[o]) for o in common], base)
    return R


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["call", "score"])
    ap.add_argument("--variants", default="V1,V2,V3,V4")
    ap.add_argument("--set", default="sub400", choices=["sub400", "all"])
    a = ap.parse_args()
    ids = SUB400 if a.set == "sub400" else IDS
    vs = a.variants.split(",")
    if a.cmd == "call":
        call(vs, ids)
    else:
        print(json.dumps(score(ids, ["D4"] + [v for v in vs if v != "D4"]), indent=1))
