"""Raw step rows of a corpus run → one decision per affair → topic rows (docs/CONTRACT.md §1).

Chapter (S9 D1, shipped): P = mean of the available chapter readings; one subtopic request over the top 2–3 chapters;
score(subtopic) = p(subtopic) × P(its chapter); the shipped chapter is the chapter of the best-scoring subtopic and its
confidence is that chapter's share of the scored mass. When P's top chapter is "no policy topic", that is shipped.
Lane: `please_check` when the two code orders disagree on the top chapter; one reading with top p ≥ 0.9 counts as agree.
Ad-hoc yes/no (S8): p = mean of order a and, where run, order b; flag at p ≥ cut-off (0.5);
`please_check` when the orders disagree or 0.3 ≤ p < 0.7."""
from __future__ import annotations

import collections
import gzip
import json
from pathlib import Path

from . import prompts as P
from .engine import mean_p, need_ch2, need_yn_b
from .scheme import APS, adhoc

VERSION = "0.6.0"


def argmax(v):
    return max(range(len(v)), key=lambda i: v[i])


def read_run(*runs: Path) -> tuple[dict, dict]:
    """-> (lock, rows by pid) over one or more run dirs; all must be locked to the same build (never mixed)."""
    rows, lock = {}, None
    for run in runs:
        st = json.loads((Path(run) / "state.json").read_text())
        if lock and st["lock"]["fp"] != lock["fp"]:
            raise ValueError(f"{run}: build {st['lock']['fp']} != {lock['fp']}")
        lock = lock or st["lock"]
        for p in sorted((Path(run) / st["lock"]["key"]).glob("*.jsonl")):
            for line in open(p):
                if line.strip():
                    r = json.loads(line)
                    rows[r["pid"]] = r
    return lock, rows


def chapter_decision(r1: dict, r2: dict | None, rs: dict | None) -> dict:
    PA = mean_p(r1["p"], r2["p"] if r2 else None)
    lane = "please_check" if (r2 and argmax(r1["p"]) != argmax(r2["p"])) else "readings_agree"
    top = argmax(PA)
    out = dict(P=PA, lane=lane, n_readings=2 if r2 else 1)
    if top == 24 or rs is None:
        rank = sorted(range(25), key=lambda i: -PA[i])
        out.update(ch=top, conf=PA[top], rank=rank[:3], subs=[], readback=False)
        return out
    opts = P.subtopic_options(rs["chs"])
    sc = {(c, j): rs["p"][k] * PA[c] for k, (c, j) in enumerate(opts)}
    tot = sum(sc.values()) or 1.0
    best = max(sc, key=sc.get)
    chbest = {}
    for (c, j), v in sc.items():
        chbest[c] = max(chbest.get(c, 0.0), v)
    rk = sorted(chbest, key=lambda c: -chbest[c]) + [c for c in sorted(range(25), key=lambda i: -PA[i]) if c not in chbest]
    conf = sum(v for (c, j), v in sc.items() if c == best[0]) / tot
    subs = sorted(sc, key=lambda k: -sc[k])[:3]
    out.update(ch=best[0], conf=conf, rank=rk[:3], subs=[(APS.sub_codes[c][j], sc[(c, j)] / tot) for c, j in subs],
               readback=True, p_none_sub=rs["p"][-1])
    return out


def yn_decision(ra: dict, rb: dict | None, cutoff: float = 0.5) -> dict:
    pa = ra["p_yes"]; pb = rb["p_yes"] if rb else None
    p = (pa + pb) / 2 if pb is not None else pa
    disagree = pb is not None and (pa >= cutoff) != (pb >= cutoff)
    return dict(p=p, p_a=pa, p_b=pb, flag=p >= cutoff, lane="please_check" if (disagree or 0.3 <= p < 0.7) else "readings_agree")


def decide(a: dict, rows: dict, engine_ch1_prompt, topics: list[dict]) -> dict:
    """All decisions available for one affair (missing steps → missing keys)."""
    out = dict(id=a["id"])
    u, p, _ = engine_ch1_prompt(a)
    r1 = rows.get(P.pid(u, p))
    if r1:
        r2 = None
        if need_ch2(r1["p"]):
            r2 = rows.get(P.pid(*P.chapter_prompt(a, P.S1PERM)))
        if r2 or not need_ch2(r1["p"]):
            chs = P.subtopic_chapters(mean_p(r1["p"], r2["p"] if r2 else None))
            u, p, _, _ = P.subtopic_prompt(a, chs)
            rs = rows.get(P.pid(u, p))
            out["aps"] = chapter_decision(r1, r2, rs)
            out["aps"]["meta"] = r1["meta"]
            out["aps"]["pids"] = [r1["pid"]] + ([r2["pid"]] if r2 else []) + ([rs["pid"]] if rs else [])
            out["aps"]["examples"] = r1.get("ex")
    for t in topics:
        ua, pa_ = P.yesno_prompt(t, a["lang"], a["title"], a["title_long"], "a")
        ra = rows.get(P.pid(ua, pa_))
        if ra:
            rb = None
            if need_yn_b(ra["p_yes"]):
                rb = rows.get(P.pid(*P.yesno_prompt(t, a["lang"], a["title"], a["title_long"], "b")))
                if rb is None:
                    continue
            out[t["id"]] = yn_decision(ra, rb, t.get("cutoff", 0.5))
            out[t["id"]]["meta"] = ra["meta"]
    return out


def topic_rows(a: dict, dec: dict, lock: dict, calib=None, valid_from: str = "") -> list[dict]:
    """Decisions → CONTRACT §1 rows (chapter rank 1–3, subtopic rank 1–3, one row per ad-hoc topic)."""
    base = dict(affair_id=a["id"], body_key=a["body"], status="suggested", provenance="inferred", model=lock["model"],
                build=lock["fp"], input_hash=a["input_hash"], valid_from=valid_from, valid_to=None, version=VERSION)
    out = []
    d = dec.get("aps")
    if d:
        cal = calib("aps", d["conf"]) if calib else None
        for k, c in enumerate(d["rank"][:3], 1):
            pr = d["conf"] if k == 1 else d["P"][c]
            out.append(dict(base, scheme="aps", level=1, code=APS.codes[c], rank=k, p_raw=round(pr, 4),
                            p=round(cal, 4) if (k == 1 and cal is not None) else None, lane=d["lane"] if k == 1 else None,
                            cutoffs_id=f"aps@{lock['fp'][-8:]}", prompt_id=",".join(d["pids"]), evidence=d.get("evidence")))
        for k, (code, pr) in enumerate(d["subs"], 1):
            out.append(dict(base, scheme="aps", level=2, code=code, rank=k, p_raw=round(pr, 4), p=None, lane=None,
                            cutoffs_id=f"aps@{lock['fp'][-8:]}", prompt_id=d["pids"][-1], evidence=None))
    for key, v in dec.items():
        if key.startswith("adhoc/"):
            out.append(dict(base, scheme=key, level=1, code=f"{key}:{'yes' if v['flag'] else 'no'}", rank=1, p_raw=round(v["p"], 4),
                            p=round(v["p"], 4), lane=v["lane"], cutoffs_id=f"{key}@0.5", prompt_id=None, evidence=v.get("evidence")))
    return out
