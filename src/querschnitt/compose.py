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
import math
from pathlib import Path

from . import prompts as P
from .engine import mean_p, need_ch2, need_yn_b
from .scheme import APS, adhoc, flat

VERSION = "0.6.0"


def geo(a, b):
    g = [math.exp((math.log(max(x, 1e-12)) + math.log(max(y, 1e-12))) / 2) for x, y in zip(a, b)]
    s = sum(g)
    return [v / s for v in g]


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
    G = geo(r1["p"], r2["p"]) if r2 else r1["p"]   # S6: "no policy topic" is read from the geometric mean of the readings
    top = argmax(G)
    out = dict(P=PA, lane=lane, n_readings=2 if r2 else 1)
    if top == 24 or rs is None:
        rank = sorted(range(25), key=lambda i: -G[i])
        out.update(ch=top, conf=G[top], rank=rank[:3], subs=[], readback=False)
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
        if need_ch2(r1["p"], bool(r1.get("ex"))):
            r2 = rows.get(P.pid(*P.chapter_prompt(a, P.S1PERM)))
        if r2 or not need_ch2(r1["p"], bool(r1.get("ex"))):
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
            out[t["id"]]["pids"] = [ra["pid"]] + ([rb["pid"]] if rb else [])
            out[t["id"]]["evidence"] = evidence_of(a, t["names"]["de"], rows)
    if "aps" in out:
        d = out["aps"]
        if d["ch"] < 24:
            d["evidence"] = evidence_of(a, APS.names["de"][d["ch"]], rows)
        bi = bilingual(a, rows)
        if bi:
            d["bilingual"] = bi
            d["lane"] = bi["lane"]
    if a["body"] == "BE" and a["lang"] in ("de", "fr"):
        sch = flat("be-directorates")
        u, p, codes = P.flat_prompt(sch, a["title"], a["lang"])
        r = rows.get(P.pid(u, p))
        if r:
            i = argmax(r["p"])
            out["be-directorates"] = dict(code=(sch["options"][i]["code"] if i < len(sch["options"]) else sch["none"]["code"]),
                                          p=r["p"][i], gold=a.get("dept") or None)
    return out


BILINGUAL = {"BE", "FR", "VS"}


def bilingual(a: dict, rows: dict) -> dict | None:
    """Bilingual parliaments: the German and the French title are the two readings (S10); they disagree → please check."""
    if a["body"] not in BILINGUAL or a.get("alt_lang") not in ("de", "fr") or a["lang"] not in ("de", "fr"):
        return None
    m = dict(title=a["title"], title_long=a["title_long"], text="", lang=a["lang"])
    o = dict(title=a["title_alt"], title_long=a["title_long_alt"], text="", lang=a["alt_lang"])
    rm, ro = rows.get(P.pid(*P.chapter_prompt(m, list(range(25))))), rows.get(P.pid(*P.chapter_prompt(o, list(range(25)))))
    if not (rm and ro):
        return None
    tm, to = argmax(rm["p"]), argmax(ro["p"])
    return dict(lane="readings_agree" if tm == to else "please_check", top={a["lang"]: tm, a["alt_lang"]: to})


def evidence_of(a: dict, name: str, rows: dict) -> dict | None:
    sents = P.sentences(a)
    if not sents:
        return None
    u, p = P.evidence_prompt([x for _, x in sents], name)
    r = rows.get(P.pid(u, p))
    if not r or not r.get("ok"):
        return None
    return dict(field=r["field"], start=r["start"], end=r["end"], quote=r["quote"])


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
                            p=round(v["p"], 4), lane=v["lane"], cutoffs_id=f"{key}@0.5", prompt_id=",".join(v.get("pids") or []) or None, evidence=v.get("evidence")))
    return out
