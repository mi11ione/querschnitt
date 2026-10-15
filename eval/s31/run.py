"""S31 test: the single dev winner on the S25 held-out items (one look; to be pre-registered in eval/PREREG-BUILD.md before
any S31 call on them). NOT RUN in S31: no variant passed the dev gate (DEV.md), so the S25 items were not touched.
No fresher APS-labelled federal affairs exist: a new Wayback CDX listing of the process pages from 2026-10-11 on found
0 new process ids with a 200 capture (DEV.md), so the S25 items would be the test.

Inputs and pipeline as S25: the production input (../data/inputs.jsonl.gz), the production example pool (S25 items are not
in it, asserted), the S25 run's rows (runs/s25: ch1, ch2, sub) reused by prompt id; only the readings the winner adds,
and subtopic requests over a chapter list the S25 run did not ask, are asked here (eval/s31/test_raw.jsonl).
The variant changes only the federal German path with examples (D4); every other affair keeps the shipped decision.

Usage: python eval/s31/run.py <variant>"""
from __future__ import annotations

import gzip, json, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(HERE))
from querschnitt import prompts as P  # noqa: E402
from querschnitt.client import Client, Endpoint  # noqa: E402
from querschnitt.compose import read_run  # noqa: E402
from querschnitt.engine import Engine, probs  # noqa: E402
from querschnitt.examples import ExamplePool  # noqa: E402
import dev  # noqa: E402  (variant prompts, decision rule, BUILD, ledger)

RAW = HERE / "test_raw.jsonl"
items = {json.loads(l)["oid"]: json.loads(l) for l in open(ROOT / "eval/s25/items.jsonl")}
POOL5 = ExamplePool.load(ROOT / "data/eval/aps_pool.jsonl", k=5)
POOL10 = ExamplePool.load(ROOT / "data/eval/aps_pool.jsonl", k=10)
assert not {x["oid"] for x in POOL5.pool} & set(items), "an S25 item is in the example pool"
_, RUN = read_run(ROOT / "runs/s25")


def inputs() -> dict:
    out = {}
    with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f:
        for line in f:
            a = json.loads(line)
            if int(a["id"]) in items:
                out[int(a["id"])] = a          # a["id"] stays the production string id
    return out


def ex_prod(a: dict, k: int) -> list[dict]:
    """Production neighbours (ExamplePool.neighbours, own id excluded) as {oid, title, chapter}."""
    return [dict(oid=e["oid"], title=e["title"], chapter=e["chapter"]) for e in (POOL10 if k == 10 else POOL5).neighbours(a)]


def shipped_path(a: dict) -> bool:
    """The affair takes the federal design with examples (engine.ch1_prompt)."""
    return a.get("level") == "federal" and a.get("lang") == "de" and bool(POOL5.neighbours(a))


def step_prompt(step: str, a: dict):
    ex = lambda k: [(e["title"], e["chapter"]) for e in ex_prod(a, k)]
    if step == "r1k10":
        return (*P.chapter_prompt_examples(a, list(range(25)), ex(10)), list(range(25)))
    if step == "r1subn":
        return (*dev.prompt_subnames(a, list(range(25)), ex_prod(a, 5)), list(range(25)))
    if step == "r2ex":
        return (*P.chapter_prompt_examples(a, P.S1PERM, ex(5)), P.S1PERM)
    if step == "r3ex":
        return (*P.chapter_prompt_examples(a, dev.PERM3, ex(5)), dev.PERM3)
    raise KeyError(step)


def base_rows(a: dict):
    """The S25 run's two readings of the shipped design (ch1 with examples, ch2 S1 order), or None."""
    u, p = P.chapter_prompt_examples(a, list(range(25)), [(e["title"], e["chapter"]) for e in ex_prod(a, 5)])
    r1 = RUN.get(P.pid(u, p)); r2 = RUN.get(P.pid(*P.chapter_prompt(a, P.S1PERM)))
    return (r1["p"], r2["p"]) if (r1 and r2) else None


def needs(v: str, a: dict, b) -> list[str]:
    if v == "D4": return []
    if v == "V1": return ["r1k10"]
    if v == "V2": return ["r1subn"]
    if v == "V3": return ["r2ex"]
    if v == "V4": return ["r3ex"] if dev.argmax(b[0]) != dev.argmax(b[1]) else []
    if v == "V5": return ["r2ex", "r3ex?"]
    raise KeyError(v)


def readings(v: str, a: dict, b, raw: dict):
    g = lambda s: (raw.get(f"{s}:{int(a['id'])}") or {}).get("p")
    r1, r2 = b
    if v == "D4": return [r1, r2]
    if v == "V1": return [g("r1k10"), r2] if g("r1k10") else None
    if v == "V2": return [g("r1subn"), r2] if g("r1subn") else None
    if v == "V3": return [r1, g("r2ex")] if g("r2ex") else None
    if v == "V4":
        if dev.argmax(r1) == dev.argmax(r2): return [r1, r2]
        return [r1, r2, g("r3ex")] if g("r3ex") else None
    if v == "V5":
        if not g("r2ex"): return None
        if dev.argmax(r1) == dev.argmax(g("r2ex")): return [r1, g("r2ex")]
        return [r1, g("r2ex"), g("r3ex")] if g("r3ex") else None
    raise KeyError(v)


def sub_lookup(a: dict, raw: dict):
    def f(chs):
        u, p, _, _ = P.subtopic_prompt(a, chs)
        r = RUN.get(P.pid(u, p)) or raw.get(f"sub:{int(a['id'])}:{','.join(map(str, chs))}")
        return r["p"] if r else None
    return f


def load_raw():
    return {json.loads(l)["key"]: json.loads(l) for l in open(RAW)} if RAW.exists() else {}


def main(v: str):
    A = inputs(); raw = load_raw()
    ep = Endpoint.from_env(); ep.max_rate, ep.conc = 0.5, 2
    eng = Engine(Client(ep, ledger=str(dev.LEDGER), cap_usd=dev.CAP_USD, expect_build=dev.BUILD, tag="s31-test"))
    lock = threading.Lock(); n = dict(calls=0)

    def put(row):
        with lock:
            raw[row["key"]] = row
            with open(RAW, "a") as f:
                f.write(json.dumps(row) + "\n")
            n["calls"] += 1

    def task(o):
        a = A.get(o)
        if not a or not shipped_path(a):
            return
        b = base_rows(a)
        if not b:
            return
        for s in needs(v, a, b):
            if s == "r3ex?":   # V5: the third reading only when the two example readings disagree
                s = "r3ex" if dev.argmax(b[0]) != dev.argmax(raw[f"r2ex:{o}"]["p"]) else None
            if s and f"{s}:{o}" not in raw:
                u, p, perm = step_prompt(s, a)
                d, meta = eng._ask(u, p, P.CODES)
                put(dict(key=f"{s}:{o}", oid=o, step=s, pid=P.pid(u, p), codes=d, p=probs(d, P.CODES, perm),
                         fp=meta["fp"], pt=meta["pt"], usd=meta["usd"]))
        ps = readings(v, a, b, raw)
        d = dev.decision(ps, sub_lookup(a, raw)) if ps else None
        if d and "need_sub" in d:
            chs = d["need_sub"]; r = eng.sub(a, chs)
            put(dict(key=f"sub:{o}:{','.join(map(str, chs))}", oid=o, step="sub", chs=chs, pid=r["pid"], p=r["p"],
                     fp=r["meta"]["fp"], pt=r["meta"]["pt"], usd=r["meta"]["usd"]))

    ids = sorted(items)
    with ThreadPoolExecutor(2) as ex:
        for i, _ in enumerate(ex.map(task, ids)):
            if i % 100 == 0:
                print(f"{i}/{len(ids)} · {n['calls']} calls · USD {eng.client.spent:.3f} (S31 ledger)", flush=True)
    print(f"done · {n['calls']} calls · USD {eng.client.spent:.3f} S31 ledger total", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
