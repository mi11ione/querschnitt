#!/usr/bin/env python3
"""Prüfstand task runner: APS chapter accuracy and DVS "Digitalisierung" recall for any Apertus build (OpenAI-compatible).
APS: federal affairs, APS editors' labels; split `s9`: the 1,357 the shipped design was chosen on, split `heldout_s25`: 927
never used while designing. DVS: the 30 affairs on the public list. Spec: task.yaml; card: TASK.md.

    export QS_BASE_URL=https://…/v1 QS_MODEL=swiss-ai/apertus-v1.5-8b QS_API_KEY=…      # or QS_KEY_FILE
    python upstream/eval-task/run.py --out runs/eval-<name> [--limit 50] [--tasks aps dvs] [--conc 2 --max-rate 1.0]
    python upstream/eval-task/run.py --out runs/eval-<name> --split heldout_s25         # the held-out APS split (aps only)
    python upstream/eval-task/run.py --out runs/eval-<name> --score-only [--split …]    # re-score the raw rows

Calls go through querschnitt.client (no system message; JSON-key assistant prefill; max_tokens 1; top_logprobs 20;
temperature 0). Prompts come from querschnitt.prompts, byte-identical to the measured ones (tests/test_prompts.py).
Every response's served model and system_fingerprint is stored; the run locks the first build it sees and stops on any
other, so one results file never mixes builds. Raw rows are appended to <out>/raw.jsonl keyed by prompt id: a re-run
resumes and never re-sends a prompt; both splits can share one --out (results.json for s9, results_heldout_s25.json for the
held-out split). No model is called by --score-only."""
from __future__ import annotations

import argparse
import gzip
import json
import math
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt import prompts as P  # noqa: E402
from querschnitt.calibrate import apply_map, ece, pav  # noqa: E402
from querschnitt.compose import chapter_decision  # noqa: E402
from querschnitt.engine import mean_p, need_ch2, probs  # noqa: E402
from querschnitt.scheme import adhoc  # noqa: E402

IDENT = list(range(25))
SPLITS = {"s9": "data/aps_s9.jsonl.gz", "heldout_s25": "data/aps_heldout_s25.jsonl.gz"}


# ------------------------------------------------------------------ data
def aps_items(limit=None, split="s9"):
    rows = [json.loads(l) for l in gzip.open(HERE / SPLITS[split], "rt")]
    return rows[:limit] if limit else rows


def dvs_items(limit=None):
    rows = [json.loads(l) for l in open(HERE / "data/dvs30.jsonl")]
    return rows[:limit] if limit else rows


def de(it):
    """The version the model reads: German (split s9); the affair's own language as the shipped run sent it (heldout_s25,
    field `lang`: German for 926 of 927)."""
    lang = it.get("lang", "de")
    return dict(id=it["id"], lang=lang, **it[lang])


# ------------------------------------------------------------------ prompts per step (pure)
def p_ch(it, step):
    a = de(it)
    if step == "d0a" or (step == "d3m" and not it["examples"]):   # no examples (held-out split, 10 items): as the engine,
        return P.chapter_prompt(a, IDENT), P.CODES, None        # the first reading is the plain identity-order prompt
    if step == "d0b":
        return P.chapter_prompt(a, P.S1PERM), P.CODES, P.S1PERM
    if step == "d3m":
        return P.chapter_prompt_examples(a, IDENT, [(e["title"], e["chapter"]) for e in it["examples"]]), P.CODES, None
    raise ValueError(step)


def p_sub(it, chs):
    u, pre, opts, codes = P.subtopic_prompt(de(it), chs)
    return (u, pre), codes


def p_yn(it, order):
    return P.yesno_prompt(adhoc("digitalisierung"), it["lang"], it["title"], it["title_long"], order), ["A", "B"]


def mean(a, b):
    return [(x + y) / 2 for x, y in zip(a, b)]


def geo2(a, b):
    g = [math.exp((math.log(max(x, 1e-12)) + math.log(max(y, 1e-12))) / 2) for x, y in zip(a, b)]
    s = sum(g); return [v / s for v in g]


def order(p):
    return sorted(range(len(p)), key=lambda i: -p[i])


def d4e(r1, r2, rs):
    """D4 as the engine composes it (compose.chapter_decision; what ships for federal affairs): prior = mean of d3m and d0b,
    chapter read back from the subtopic request over the prior's top chapters, except when the geometric mean of the two
    readings puts "no policy topic" first (then that, no read-back). r2 is None only for an item without examples whose
    first reading has top p >= 0.9 (the engine then asks one code order)."""
    d = chapter_decision(r1, r2, rs)
    return d["ch"], d["rank"], d["conf"]


def sel_prior(d3m, d0b):
    """S16 D4S prior: d3m alone when its top p >= 0.9, else the mean of d3m and d0b."""
    return d3m if max(d3m) >= 0.9 else mean(d3m, d0b)


def readback(prior, chs, psub):
    """Chapter read back from the chosen subtopic: score = p(subtopic) x prior(its chapter) (S9 D1 / S16)."""
    opts = P.subtopic_options(chs)
    sc = {(c, j): psub[k] * prior[c] for k, (c, j) in enumerate(opts)}
    tot = sum(sc.values()) or 1.0
    best = max(sc, key=sc.get)
    chbest = {}
    for (c, j), v in sc.items():
        chbest[c] = max(chbest.get(c, 0.0), v)
    rk = sorted(chbest, key=lambda c: -chbest[c]) + [c for c in order(prior) if c not in chbest]
    return best[0], rk, sum(v for (c, j), v in sc.items() if c == best[0]) / tot


# ------------------------------------------------------------------ calls
class Runner:
    def __init__(self, out: Path, client=None):
        self.out, self.client = out, client
        self.raw_path = out / "raw.jsonl"
        self.rows = {}
        self.lock = threading.Lock()
        self.build = None
        if self.raw_path.exists():
            for l in open(self.raw_path):
                r = json.loads(l); self.rows[r["pid"]] = r
                self.build = self.build or r["fp"]

    def ask(self, um, codes, perm=None, step=""):
        u, pre = um
        pid = P.pid(u, pre)
        if pid in self.rows:
            return self.rows[pid]
        ch, meta = self.client.chat([{"role": "user", "content": u}, {"role": "assistant", "content": pre}], max_tokens=1)
        from querschnitt.client import generated_code, read_codes
        d = read_codes(ch, codes)
        if not d:                                  # endpoint without log-probabilities: the generated code only
            g = generated_code(ch, codes); d = {g: 0.0} if g else {}
        r = dict(pid=pid, step=step, codes=d, p=probs(d, codes, perm), model=meta.get("model"), fp=meta.get("fp"),
                 logprobs=bool(d) and len(d) > 1, mass=round(sum(math.exp(v) for v in d.values()), 5), t=time.time())
        with self.lock:
            if self.build is None:
                self.build = r["fp"]
            if r["fp"] != self.build:
                raise SystemExit(f"served build changed: {r['fp']} != {self.build} (results would mix builds; stopped)")
            self.rows[pid] = r
            with open(self.raw_path, "a") as f:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        return r

    def aps(self, it):
        r = {s: self.ask(*p_ch(it, s), step=s) for s in ("d0a", "d0b", "d3m")}
        for chs in {tuple(P.subtopic_chapters(mean(r["d0a"]["p"], r["d0b"]["p"]))),
                    tuple(P.subtopic_chapters(sel_prior(r["d3m"]["p"], r["d0b"]["p"]))),
                    tuple(P.subtopic_chapters(mean(r["d3m"]["p"], r["d0b"]["p"])))}:
            self.ask(*p_sub(it, list(chs)), step="sub")

    def dvs(self, it):
        ra = self.ask(*p_yn(it, "a"), step="yn_a")
        pa = ra["p"][0]
        if 0.1 < pa < 0.9:
            self.ask(*p_yn(it, "b"), step="yn_b")


# ------------------------------------------------------------------ scoring (no calls)
# figures: point estimates truncated to 4 decimals (toward zero), interval bounds widened outward to 4 decimals
def tr(v):
    return math.trunc(round(v * 1e4, 6)) / 1e4


def lo(v):
    return math.floor(round(v * 1e4, 6)) / 1e4


def hi(v):
    return math.ceil(round(v * 1e4, 6)) / 1e4


def wilson(k, n, z=1.959964):
    if not n:
        return [None, None]
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [lo((c - h) / d), hi((c + h) / d)]


def ece_crossfit(ps, ys, seed=3):
    """ECE after 2-fold cross-fitted isotonic recalibration (querschnitt.calibrate.crossfit, unrounded)."""
    idx = list(range(len(ps))); random.Random(seed).shuffle(idx)
    half = len(idx) // 2; cal = [0.0] * len(ps)
    for a, b in ((idx[:half], idx[half:]), (idx[half:], idx[:half])):
        f = pav([ps[i] for i in a], [ys[i] for i in a])
        for i in b:
            cal[i] = apply_map(f, ps[i])
    return ece(cal, ys)


def paired(va, vb, n=2000, seed=2026):
    rng = random.Random(seed); m = len(va); ds = []
    for _ in range(n):
        s = [rng.randrange(m) for _ in range(m)]
        ds.append(sum(va[i] - vb[i] for i in s) / m)
    ds.sort()
    return dict(diff=tr((sum(va) - sum(vb)) / m), ci=[lo(ds[int(0.025 * n)]), hi(ds[int(0.975 * n) - 1])])


DESIGNS = ("D0", "D1", "D3", "D4", "D4E", "D4S")
PAIRS = (("D1", "D0"), ("D3", "D0"), ("D4", "D0"), ("D4", "D3"), ("D4", "D1"), ("D4E", "D4"), ("D4S", "D0"), ("D4S", "D3"),
         ("D4S", "D1"))


def score(run: Runner, items_aps, items_dvs, split="s9") -> dict:
    R = dict(build=run.build, models=sorted({r["model"] for r in run.rows.values() if r.get("model")}),
             calls=len(run.rows), logprobs=all(r.get("logprobs") for r in run.rows.values()) if run.rows else None,
             split=split)
    get = lambda um: run.rows.get(P.pid(*um))
    # ---- APS: each design on the items whose readings are all stored (a full run: every item for every design)
    pred, gold, lanes = {d: {} for d in DESIGNS}, {}, {"D0": {}, "D4": {}, "D4E": {}}
    for it in items_aps:
        o = it["id"]
        r = {s: get(p_ch(it, s)[0]) for s in ("d0a", "d0b", "d3m")}
        a, b, m = (r[s]["p"] if r[s] else None for s in ("d0a", "d0b", "d3m"))
        if a and b:
            PA = mean(a, b); d0 = geo2(a, b)
            pred["D0"][o] = (order(d0)[0], order(d0), d0[order(d0)[0]])
            lanes["D0"][o] = order(a)[0] == order(b)[0]
            s1 = get(p_sub(it, P.subtopic_chapters(PA))[0])
            if s1:
                pred["D1"][o] = readback(PA, P.subtopic_chapters(PA), s1["p"])
        if m and b:
            d3, SEL, P4 = geo2(m, b), sel_prior(m, b), mean(m, b)
            pred["D3"][o] = (order(d3)[0], order(d3), d3[order(d3)[0]])
            s4 = get(p_sub(it, P.subtopic_chapters(SEL))[0])
            if s4:
                pred["D4S"][o] = readback(SEL, P.subtopic_chapters(SEL), s4["p"])
            s5 = get(p_sub(it, P.subtopic_chapters(P4))[0])
            if s5:                                              # S16 D4 as registered: every item read back
                pred["D4"][o] = readback(P4, P.subtopic_chapters(P4), s5["p"])
                lanes["D4"][o] = order(m)[0] == order(b)[0]
        if m:
            r2 = r["d0b"] if need_ch2(m, bool(it["examples"])) else None
            if r2 or not need_ch2(m, bool(it["examples"])):
                chs = P.subtopic_chapters(mean_p(m, r2["p"] if r2 else None))
                rs = get(p_sub(it, chs)[0])
                if rs or order(geo2(m, r2["p"]) if r2 else m)[0] == 24:     # "no policy topic": no read-back needed
                    pred["D4E"][o] = d4e(r["d3m"], r2, dict(rs, chs=chs) if rs else None)
                    lanes["D4E"][o] = r2 is None or order(m)[0] == order(r2["p"])[0]
        if any(o in pred[d] for d in pred):
            gold[o] = it["gold_chapter"]
    ids = sorted(gold)
    A = dict(n=len(ids), n_items=len(items_aps), designs={})
    if ids:
        maj = max(set(gold.values()), key=list(gold.values()).count)
        A["baseline_majority"] = dict(chapter=maj, top1=tr(sum(gold[o] == maj for o in ids) / len(ids)))
        hit = {d: {o: int(pred[d][o][0] == gold[o]) for o in pred[d]} for d in pred}
        for d in DESIGNS:
            di = sorted(pred[d]); n = len(di)
            if not n:
                continue
            k1 = sum(hit[d].values()); k3 = sum(gold[o] in pred[d][o][1][:3] for o in di)
            ps = [pred[d][o][2] for o in di]; hs = [hit[d][o] for o in di]
            A["designs"][d] = dict(n=n, top1=tr(k1 / n), top1_ci=wilson(k1, n), top3=tr(k3 / n),
                                   top3_ci=wilson(k3, n), ece_raw=tr(ece(ps, hs)),
                                   ece_isotonic_crossfit=tr(ece_crossfit(ps, hs)) if n >= 20 else None)
        A["paired"] = {}
        for x, y in PAIRS:                                      # over the items both designs have
            both = sorted(set(pred[x]) & set(pred[y]))
            if both:
                A["paired"][f"{x}-{y}"] = dict(n=len(both), **paired([hit[x][o] for o in both], [hit[y][o] for o in both]))
        for d, L in lanes.items():
            if not L:
                continue
            ag = [o for o in L if L[o]]; dis = [o for o in L if not L[o]]
            A[f"lanes_{d}"] = dict(n=len(L), agree_share=tr(len(ag) / len(L)), agree_share_ci=wilson(len(ag), len(L)),
                                   precision_agree=tr(sum(hit[d][o] for o in ag) / max(1, len(ag))),
                                   precision_disagree=tr(sum(hit[d][o] for o in dis) / max(1, len(dis))))
    R["aps"] = A
    # ---- DVS
    k = n = 0; misses = []
    for it in items_dvs:
        ra = get(p_yn(it, "a")[0])
        if not ra:
            continue
        pa = ra["p"][0]; p = pa
        if 0.1 < pa < 0.9:
            rb = get(p_yn(it, "b")[0])
            if not rb:
                continue
            p = (pa + rb["p"][1]) / 2                  # order b: B = yes
        n += 1
        if p >= 0.5:
            k += 1
        else:
            misses.append(dict(id=it["id"], body=it["body"], p=tr(p)))
    R["dvs"] = dict(n=n, n_items=len(items_dvs), found=k, recall=tr(k / n) if n else None, recall_ci=wilson(k, n),
                    misses=misses)
    return R


def markdown(R: dict) -> str:
    A, D = R["aps"], R["dvs"]
    md = [f"# Prüfstand task — build `{R['build']}`", "",
          f"Served model(s): {', '.join(R['models']) or '—'} · calls stored: {R['calls']} · log-probabilities: {R['logprobs']}", "",
          f"## APS chapter vs APS editors, split `{R['split']}` (n = {A['n']} of {A['n_items']})", "",
          "| Design | n | top-1 [95%] | top-3 | ECE raw | ECE isotonic (2-fold) |", "|---|---|---|---|---|---|"]
    for d, v in A.get("designs", {}).items():
        md.append(f"| {d} | {v['n']} | {v['top1']} [{v['top1_ci'][0]}, {v['top1_ci'][1]}] | {v['top3']} | {v['ece_raw']} | {v['ece_isotonic_crossfit']} |")
    if A.get("designs"):
        md += ["", *(f"- {k}: {v['diff']:+} [{v['ci'][0]:+}, {v['ci'][1]:+}] (paired bootstrap, n {v['n']})" for k, v in A["paired"].items())]
        md.append(f"- Majority-chapter baseline: {A['baseline_majority']['top1']}")
        for d in ("D0", "D4", "D4E"):
            L = A.get(f"lanes_{d}")
            if L:
                md.append(f"- {d}: the two code orders agree on {L['agree_share']} of items; precision there {L['precision_agree']}, "
                          f"elsewhere {L['precision_disagree']}")
    md += ["", f"## DVS \"Digitalisierung\" recall (n = {D['n']} of {D['n_items']})", "",
           f"- found {D['found']} / {D['n']} = {D['recall']} [{D['recall_ci'][0]}, {D['recall_ci'][1]}]",
           f"- misses: {', '.join(str(m['id']) + ' (' + m['body'] + ', p ' + str(m['p']) + ')' for m in D['misses']) or '—'}"]
    return "\n".join(md) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--split", default="s9", choices=sorted(SPLITS), help="APS items: s9 (1,357, the design set) or "
                    "heldout_s25 (927, never used while designing)")
    ap.add_argument("--tasks", nargs="*", choices=["aps", "dvs"], help="default: aps dvs for s9, aps for heldout_s25")
    ap.add_argument("--limit", type=int, help="first N items of each task (a smoke run)")
    ap.add_argument("--conc", type=int, default=2)
    ap.add_argument("--max-rate", type=float, default=1.0, help="requests/s ceiling")
    ap.add_argument("--cap", type=float, default=5.0, help="list-price USD cap (querschnitt ledger)")
    ap.add_argument("--score-only", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    tasks = a.tasks if a.tasks is not None else (["aps", "dvs"] if a.split == "s9" else ["aps"])
    IA = aps_items(a.limit, a.split) if "aps" in tasks else []
    ID = dvs_items(a.limit) if "dvs" in tasks else []
    client = None
    if not a.score_only:
        from querschnitt.client import Client, Endpoint
        ep = Endpoint.from_env(); ep.conc, ep.max_rate = a.conc, a.max_rate
        client = Client(ep, ledger=str(out / "ledger.jsonl"), cap_usd=a.cap, tag="pruefstand-task")
    run = Runner(out, client)
    if not a.score_only:
        jobs = [(run.aps, it) for it in IA] + [(run.dvs, it) for it in ID]
        with ThreadPoolExecutor(a.conc) as ex:
            for i, _ in enumerate(ex.map(lambda j: j[0](j[1]), jobs), 1):
                if i % 50 == 0:
                    print(f"{time.strftime('%H:%M:%S')} {i}/{len(jobs)} items, {len(run.rows)} calls", flush=True)
    R = score(run, IA, ID, a.split)
    sfx = "" if a.split == "s9" else f"_{a.split}"
    (out / f"results{sfx}.json").write_text(json.dumps(R, indent=1, ensure_ascii=False) + "\n")
    (out / f"results{sfx}.md").write_text(markdown(R))
    print(markdown(R))
    return 0


if __name__ == "__main__":
    sys.exit(main())
