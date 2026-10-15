"""Capability probe for an OpenAI-compatible Apertus endpoint (on site: the CSCS endpoint, hour 1).

    QS_BASE_URL=https://… QS_MODEL=… QS_API_KEY=… python tools/probe_endpoint.py [--replay runs/main] [--n 60]

The measured design (every Prüfstand number) needs assistant prefill (vLLM `continue_final_message`) and next-token
top_logprobs. The probe tests both itself, whatever QS_PREFILL / QS_NO_LOGPROBS say, then prints the env settings to use
for this endpoint and a one-line verdict. Checks, in order, and writes eval/probe-<name>-<time>.json:
  1. /models lists the model; one request answers; served `model` and `system_fingerprint`
  2. top_logprobs returned (20): honoured / absent / rejected
  3. assistant prefill: honoured (the first generated token is a code) / ignored (accepted, but a new answer starts) /
     rejected (4xx); when not honoured, the no-prefill mode (QS_PREFILL=0) is tried: is the code read?
  4. determinism: the same request twice
  5. throughput at 1 / 4 / 8 / 16 concurrent requests: req/s, HTTP p50/p95, 429s
  6. replay (prefill honoured only): chapter prompts already answered on Public AI (from a run dir) → top-1 agreement
     and mean |Δp| on the same prompts, i.e. whether cut-offs fitted on the old build can be reused or must be refitted."""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt import prompts as P  # noqa: E402
from querschnitt.client import CapabilityError, Client, Endpoint, code_after, read_codes, read_codes_after  # noqa: E402
from querschnitt.engine import NOPRE_TOKENS  # noqa: E402

A = dict(title="Rechenzentren im Kanton Bern", title_long="Wie viel Strom und Wasser brauchen Rechenzentren im Kanton Bern?",
         text="", lang="de")

MEASURED = "measured design runs as measured"
UNMEASURED = "runs in an unmeasured mode — refit + quality gate before use"


def one(c: Client, msgs, **kw):
    t0 = time.time()
    ch, meta = c.chat(msgs, **kw)
    return ch, meta, time.time() - t0


def _gen(ch: dict) -> str:
    return ((ch.get("message") or {}).get("content") or "").strip()


def probe(c: Client, conc: list[int], replay: Path | None = None, n: int = 60) -> dict:
    """All checks against the client's endpoint (its prefill/logprobs flags are set by the probe). -> report dict."""
    ep = c.endpoint
    ep.prefill, ep.logprobs = True, True
    R: dict = dict(endpoint=ep.base_url, name=ep.name, model=ep.model, t=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    # 1 models
    try:
        req = urllib.request.Request(ep.base_url.rstrip("/") + "/models", headers={"Authorization": f"Bearer {ep.key()}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            R["models"] = [m.get("id") for m in json.loads(r.read()).get("data", [])]
    except Exception as e:  # noqa: BLE001
        R["models"] = f"error: {e!r}"[:200]
    u, p = P.chapter_prompt(A, list(range(25)))
    pre_msgs = [{"role": "user", "content": u}, {"role": "assistant", "content": p}]
    nop_msgs = [{"role": "user", "content": P.no_prefill_user(u, p)}]
    # 2 + 3 the measured request: prefill + logprobs; a refused field is recorded and the other one tested alone
    ch = meta = dt = None
    R["logprobs_status"], R["prefill"] = "honoured", "honoured"
    for _ in range(3):
        try:
            ch, meta, dt = one(c, pre_msgs)
            break
        except CapabilityError as e:
            if e.capability == "logprobs":
                R["logprobs_status"], R["logprobs_error"] = "rejected", str(e)[:400]; ep.logprobs = False
            else:
                R["prefill"], R["prefill_error"] = "rejected", str(e)[:400]
                break
    if ch is None:   # prefill refused: identity from a plain request (the no-prefill one)
        try:
            ch, meta, dt = one(c, nop_msgs, max_tokens=1 + NOPRE_TOKENS)
        except CapabilityError as e:
            R["logprobs_status"], R["logprobs_error"] = "rejected", str(e)[:400]; ep.logprobs = False
            ch, meta, dt = one(c, nop_msgs, max_tokens=1 + NOPRE_TOKENS)
    R["served_model"], R["fingerprint"], R["latency_s"] = meta["model"], meta["fp"], round(dt, 3)
    lp = (ch.get("logprobs") or {}).get("content") or []
    R["logprobs"] = bool(lp and lp[0].get("top_logprobs"))
    R["top_logprobs_n"] = len(lp[0]["top_logprobs"]) if R["logprobs"] else 0
    if R["logprobs_status"] == "honoured" and not R["logprobs"]:
        R["logprobs_status"] = "absent"
    if R["prefill"] == "honoured":
        gen = _gen(ch)
        R["generated"] = gen
        R["prefill_ok"] = gen.strip('"').strip()[:1] in P.CODES
        if not R["prefill_ok"]:
            R["prefill"] = "ignored"
        d = read_codes(ch, P.CODES)
        R["code_mass"] = round(sum(math.exp(v) for v in d.values()), 4) if d else None
    else:
        R["prefill_ok"] = False
    # 3b no-prefill mode, when prefill is not honoured
    msgs, kw = pre_msgs, {}
    if R["prefill"] != "honoured":
        ep.prefill = False
        msgs, kw = nop_msgs, dict(max_tokens=1 + NOPRE_TOKENS)
        ch, meta, _ = one(c, msgs, **kw)
        d = read_codes_after(ch, P.CODES, p)
        g = code_after(ch, P.CODES, p)
        R["noprefill"] = dict(generated=_gen(ch)[:80], code=g, logprobs=bool(d),
                              code_mass=round(sum(math.exp(v) for v in d.values()), 4) if d else None)
        R["noprefill_ok"] = bool(d or g)

    def reading(x):
        return read_codes(x, P.CODES) if ep.prefill else (read_codes_after(x, P.CODES, p) or code_after(x, P.CODES, p))
    # 4 determinism
    ch2, _, _ = one(c, msgs, **kw)
    R["deterministic"] = _gen(ch2) == _gen(ch) and reading(ch2) == reading(ch)
    # 5 throughput
    R["throughput"] = []
    for k in conc:
        lat, n429 = [], [0]
        lock = threading.Lock()
        m_n = max(8, k * 4)

        def go(i):
            m = [dict(x, content=x["content"].replace("Rechenzentren", f"Rechenzentren ({i})")) if x["role"] == "user" else x
                 for x in msgs]
            _, meta_, _ = one(c, m, **kw)
            with lock:
                lat.append(meta_["lat"]); n429[0] += sum(1 for s in meta_["http"] if s == 429)
        t0 = time.time()
        with ThreadPoolExecutor(k) as ex:
            list(ex.map(go, range(m_n)))
        wall = time.time() - t0
        s = sorted(lat)
        R["throughput"].append(dict(conc=k, n=m_n, req_per_s=round(m_n / wall, 3), p50=round(statistics.median(s), 3),
                                    p95=round(s[int(0.95 * (len(s) - 1))], 3), n429=n429[0]))
        print(R["throughput"][-1], flush=True)
    # 6 replay: measured prompt ids exist only for the prefill design
    if replay and (replay / "state.json").exists() and R["prefill"] == "honoured":
        st = json.loads((replay / "state.json").read_text())
        rows = [json.loads(l) for l in open(replay / st["lock"]["key"] / "ch1.jsonl")][:n]
        inputs = {}
        import gzip
        need = {r["aid"] for r in rows}
        with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f:
            for line in f:
                x = json.loads(line)
                if x["id"] in need:
                    inputs[x["id"]] = x
        from querschnitt.engine import Engine
        from querschnitt.examples import ExamplePool
        eng = Engine(c, ExamplePool.load(ROOT / "data/eval/aps_pool.jsonl"))
        agree, dps = 0, []
        for r in rows:
            x = inputs.get(r["aid"])
            if not x:
                continue
            built = eng.ch1_prompt(x)
            if P.pid(built[0], built[1]) != r["pid"]:
                continue
            new = eng.ch1(x, built)
            top_old = max(range(25), key=lambda i: r["p"][i]); top_new = max(range(25), key=lambda i: new["p"][i])
            agree += top_old == top_new
            dps.append(abs(r["p"][top_old] - new["p"][top_old]))
        R["replay"] = dict(n=len(dps), top1_agree=agree, mean_abs_dp=round(sum(dps) / len(dps), 4) if dps else None,
                           old_build=st["lock"]["fp"])
    elif replay:
        R["replay"] = "skipped: needs prefill (measured prompt ids) and a run dir"
    R["usd_list_price"] = round(c.spent, 4)
    cal = ROOT / "eval/calibration.json"
    R["calibration_build"] = json.loads(cal.read_text()).get("build") if cal.exists() else None
    R["env"], R["batch_args"], R["verdict"] = advise(R)
    return R


def advise(R: dict) -> tuple[dict, str, str]:
    """Probe report -> (env settings for this endpoint, batch arguments, one-line verdict)."""
    env = {"QS_BASE_URL": R["endpoint"], "QS_MODEL": R["model"]}   # the route asked for (the served id may differ)
    reasons = []
    if R.get("prefill") != "honoured":
        env["QS_PREFILL"] = "0"
        reasons.append(f"prefill {R.get('prefill')}")
        if not R.get("noprefill_ok"):
            reasons.append("no-prefill mode reads no code either: do not use this endpoint")
    if not R.get("logprobs"):
        env["QS_NO_LOGPROBS"] = "1"
        reasons.append("no top_logprobs: codes from the text, no probabilities")
    ok = [t for t in R.get("throughput") or [] if not t["n429"]]
    batch = ""
    if ok:   # 80 % of the best 429-free rate; the batch takes its own --conc/--max-rate (QS_MAX_RATE: serve, Neues Thema)
        best = max(ok, key=lambda t: t["req_per_s"])
        env["QS_MAX_RATE"] = f"{max(0.2, round(0.8 * best['req_per_s'], 1))}"
        batch = f"--conc {best['conc']} --max-rate {env['QS_MAX_RATE']}"
    if R.get("deterministic") is False:
        reasons.append("not deterministic")
    if reasons:
        return env, batch, f"{UNMEASURED} ({'; '.join(reasons)})"
    return env, batch, MEASURED


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", default=str(ROOT / "runs/main"))
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--conc", default="1,4,8,16", help="concurrency levels for the throughput test")
    ap.add_argument("--out", help="report path (default eval/probe-<name>-<time>.json)")
    ap.add_argument("--ledger", help="ledger path (default runs/probe-<name>-ledger.jsonl)")
    a = ap.parse_args()
    for k in ("QS_PREFILL", "QS_NO_LOGPROBS"):   # the probe tests both capabilities itself
        if os.environ.pop(k, None) is not None:
            print(f"(ignoring {k}: the probe tests it)", flush=True)
    ep = Endpoint.from_env(); ep.max_rate, ep.conc = 50.0, 16
    c = Client(ep, ledger=a.ledger or str(ROOT / f"runs/probe-{ep.name}-ledger.jsonl"), cap_usd=2.0, tag="probe")
    c.guard.rate = ep.max_rate   # measure the endpoint, not the guard's slow start (it begins at 1 req/s)
    R = probe(c, [int(x) for x in a.conc.split(",") if x], Path(a.replay) if a.replay else None, a.n)
    out = Path(a.out) if a.out else ROOT / f"eval/probe-{ep.name}-{time.strftime('%Y%m%d-%H%M')}.json"
    out.write_text(json.dumps(R, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in R.items() if k not in ("models", "env", "batch_args", "verdict")}, indent=1,
                     ensure_ascii=False))
    print("\nprefill:", R["prefill"], "· logprobs:", R["logprobs_status"], "· deterministic:", R["deterministic"])
    print("\n# env for this endpoint (plus QS_API_KEY or QS_KEY_FILE)")
    for k, v in R["env"].items():
        print(f"export {k}={v}")
    for k in ("QS_PREFILL", "QS_NO_LOGPROBS"):
        if k not in R["env"]:
            print(f"unset {k}")
    if R["batch_args"]:
        print(f"# batch: python -m querschnitt.batch run … {R['batch_args']}")
    if R["calibration_build"] and R["fingerprint"] != R["calibration_build"]:
        print(f"# served build {R['fingerprint']} != calibration build {R['calibration_build']}: p is null until refitted (S16)")
    print("\nverdict:", R["verdict"])


if __name__ == "__main__":
    main()
