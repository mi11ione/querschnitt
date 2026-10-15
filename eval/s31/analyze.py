"""S31 analysis. No model calls.
  python eval/s31/analyze.py dev            -> dev table (400 subset and all 1,357) into results.json["dev"]
  python eval/s31/analyze.py test <variant> -> the pre-registered test on the S25 items into results.json["test"]
Points truncated (4 decimals), intervals outward (Wilson 95%: 3 decimals; paired bootstrap 2,000, percentile 95%: 4)."""
from __future__ import annotations

import gzip, json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(HERE))
import dev  # noqa: E402

OUT = HERE / "results.json"


def save(key, val):
    R = json.loads(OUT.read_text()) if OUT.exists() else {}
    R[key] = val
    OUT.write_text(json.dumps(R, indent=1, ensure_ascii=False))


def calls_usd():
    rows = [json.loads(l) for l in open(dev.LEDGER)] if dev.LEDGER.exists() else []
    by = {}
    for r in rows:
        b = by.setdefault(r["tag"], dict(calls=0, usd=0.0))
        b["calls"] += 1; b["usd"] += r["usd"]
    builds = sorted({r["fp"] for r in rows})
    return dict(by_tag={k: dict(calls=v["calls"], usd=round(v["usd"], 4)) for k, v in by.items()},
                calls=len(rows), usd_list_price=round(sum(r["usd"] for r in rows), 4), builds=builds)


def test(v: str):
    import run
    from querschnitt.compose import decide
    from querschnitt.engine import Engine
    A = run.inputs(); raw = run.load_raw()
    eng = Engine(None, run.POOL5)
    gold = {o: run.items[o]["chapter"] for o in run.items}
    ship, var, mism, path = {}, {}, 0, 0
    for o, a in sorted(A.items()):
        d = decide(a, run.RUN, eng.ch1_prompt, []).get("aps")
        if not d:
            continue
        ship[o] = (d["ch"], d["rank"][:3])
        if run.shipped_path(a) and (b := run.base_rows(a)):
            path += 1
            s = dev.decision(list(b), run.sub_lookup(a, raw))
            mism += s.get("ch") != d["ch"]          # the n-reading rule reproduces the shipped decision
            ps = run.readings(v, a, b, raw)
            x = dev.decision(ps, run.sub_lookup(a, raw)) if ps else None
            if x and "need_sub" not in x:
                var[o] = (x["ch"], x["rank"][:3])
        else:
            var[o] = ship[o]                        # not on the example path: the variant is the shipped design
    ids = sorted(o for o in ship if o in var)
    n = len(ids)
    k_s = sum(ship[o][0] == gold[o] for o in ids); k_v = sum(var[o][0] == gold[o] for o in ids)
    t3 = lambda D: sum(gold[o] in D[o][1] for o in ids)
    R = dict(prereg="eval/PREREG-BUILD.md S31 (one look)", variant=v, items=len(run.items), scored=n,
             missing_variant=len(ship) - n, on_example_path=path, shipped_rule_mismatch=mism,
             shipped=dict(top1=dev.trunc(k_s / n), top1_ci=dev.wout(k_s, n), k=k_s, top3=dev.trunc(t3(ship) / n)),
             winner=dict(top1=dev.trunc(k_v / n), top1_ci=dev.wout(k_v, n), k=k_v, top3=dev.trunc(t3(var) / n)),
             primary_winner_minus_shipped=dev.paired([int(var[o][0] == gold[o]) for o in ids],
                                                     [int(ship[o][0] == gold[o]) for o in ids]),
             changed=sum(var[o][0] != ship[o][0] for o in ids))
    return R


GATE = 0.02   # a dev winner: paired difference vs D4 on all 1,357 >= +0.02 with its 95% interval above 0


def dev_all() -> dict:
    """Stage 1: the five variants on the fixed 400-item subset; stage 2: the best two (V1, V3; tie at +0.0125) on all
    1,357, also split into the 400 and the 957 items stage 1 did not see; the gate decides whether S25 is used."""
    rest = [o for o in dev.IDS if o not in set(dev.SUB400)]
    R = dict(stage1_sub400=dev.score(dev.SUB400, ["D4", "V1", "V2", "V3", "V4", "V5"]),
             stage2_all=dev.score(dev.IDS, ["D4", "V1", "V3"]),
             stage2_rest957=dev.score(rest, ["D4", "V1", "V3"]))
    R["gate"] = {v: dict(diff=d["minus_D4"]["diff"], ci=d["minus_D4"]["ci"],
                         passes=d["minus_D4"]["diff"] >= GATE and d["minus_D4"]["ci"][0] > 0)
                 for v, d in R["stage2_all"]["designs"].items() if v != "D4"}
    R["winner"] = next((v for v, g in R["gate"].items() if g["passes"]), None)
    R["note"] = ("D4 is scored with the production decision rule (no policy topic read from the geometric mean of the "
                 "readings, compose.chapter_decision): 0.7376 on all 1,357; S16 reported 0.7406 with the S16 rule, which "
                 "has no such check (4 items differ).")
    return R


if __name__ == "__main__":
    if sys.argv[1] == "dev":
        R = dev_all(); R["calls"] = calls_usd()
        save("dev", R); print(json.dumps(R, indent=1))
    elif sys.argv[1] == "test":
        R = test(sys.argv[2]); R["calls"] = calls_usd()
        save("test", R); print(json.dumps(R, indent=1))
    elif sys.argv[1] == "check":   # no-call check that the shipped decision is reproduced on S25 (before any test call)
        R = test("D4")
        print({k: R[k] for k in ("scored", "on_example_path", "shipped_rule_mismatch", "shipped", "changed")})
