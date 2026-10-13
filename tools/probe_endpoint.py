"""Capability probe for any OpenAI-compatible Apertus endpoint (on site: the CSCS endpoint, hour 1).

    QS_BASE_URL=https://… QS_MODEL=… QS_API_KEY=… python tools/probe_endpoint.py [--replay runs/main] [--n 60]

Checks, in order, and writes eval/probe-<name>-<time>.json:
  1. /models lists the model; one request answers; served `model` and `system_fingerprint`
  2. top_logprobs returned (20) — needed for chapter probabilities and recalibrated p; lanes work without them
  3. assistant prefill honoured (continue_final_message): the first generated token is a code
  4. determinism: the same request twice
  5. throughput at 1 / 4 / 8 / 16 concurrent requests: req/s, HTTP p50/p95, 429s
  6. replay: chapter prompts already answered on Public AI (from a run dir) → top-1 agreement and mean |Δp| on the
     same prompts, i.e. whether cut-offs fitted on the old build can be reused or must be refitted."""
from __future__ import annotations

import argparse
import json
import math
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
from querschnitt.client import Client, Endpoint, read_codes  # noqa: E402

A = dict(title="Rechenzentren im Kanton Bern", title_long="Wie viel Strom und Wasser brauchen Rechenzentren im Kanton Bern?",
         text="", lang="de")


def one(c: Client, msgs, **kw):
    t0 = time.time()
    ch, meta = c.chat(msgs, **kw)
    return ch, meta, time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", default=str(ROOT / "runs/main"))
    ap.add_argument("--n", type=int, default=60)
    a = ap.parse_args()
    ep = Endpoint.from_env(); ep.max_rate, ep.conc = 50.0, 16
    c = Client(ep, ledger=str(ROOT / f"runs/probe-{ep.name}-ledger.jsonl"), cap_usd=2.0, tag="probe")
    R: dict = dict(endpoint=ep.base_url, model=ep.model, t=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    # 1 models
    try:
        req = urllib.request.Request(ep.base_url.rstrip("/") + "/models", headers={"Authorization": f"Bearer {ep.key()}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            R["models"] = [m.get("id") for m in json.loads(r.read()).get("data", [])]
    except Exception as e:  # noqa: BLE001
        R["models"] = f"error: {e!r}"[:200]
    u, p = P.chapter_prompt(A, list(range(25)))
    msgs = [{"role": "user", "content": u}, {"role": "assistant", "content": p}]
    ch, meta, dt = one(c, msgs)
    R["served_model"], R["fingerprint"], R["latency_s"] = meta["model"], meta["fp"], round(dt, 3)
    lp = (ch.get("logprobs") or {}).get("content") or []
    R["logprobs"] = bool(lp and lp[0].get("top_logprobs"))
    R["top_logprobs_n"] = len(lp[0]["top_logprobs"]) if R["logprobs"] else 0
    gen = ((ch.get("message") or {}).get("content") or "").strip()
    R["generated"] = gen
    R["prefill_ok"] = gen.strip('"').strip()[:1] in P.CODES
    d = read_codes(ch, P.CODES)
    R["code_mass"] = round(sum(math.exp(v) for v in d.values()), 4) if d else None
    ch2, meta2, _ = one(c, msgs)
    R["deterministic"] = ((ch2.get("message") or {}).get("content") == (ch.get("message") or {}).get("content")
                          and read_codes(ch2, P.CODES) == d)
    # 5 throughput
    R["throughput"] = []
    for conc in (1, 4, 8, 16):
        lat, n429 = [], [0]
        lock = threading.Lock()
        n = max(8, conc * 4)

        def go(i):
            m = [{"role": "user", "content": u.replace("Rechenzentren", f"Rechenzentren ({i})")}, {"role": "assistant", "content": p}]
            ch_, meta_, dt_ = one(c, m)
            with lock:
                lat.append(meta_["lat"]); n429[0] += sum(1 for s in meta_["http"] if s == 429)
        t0 = time.time()
        with ThreadPoolExecutor(conc) as ex:
            list(ex.map(go, range(n)))
        wall = time.time() - t0
        s = sorted(lat)
        R["throughput"].append(dict(conc=conc, n=n, req_per_s=round(n / wall, 3), p50=round(statistics.median(s), 3),
                                    p95=round(s[int(0.95 * (len(s) - 1))], 3), n429=n429[0]))
        print(R["throughput"][-1], flush=True)
    # 6 replay
    run = Path(a.replay)
    if (run / "state.json").exists():
        st = json.loads((run / "state.json").read_text())
        rows = [json.loads(l) for l in open(run / st["lock"]["key"] / "ch1.jsonl")][: a.n]
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
    R["usd_list_price"] = round(c.spent, 4)
    out = ROOT / f"eval/probe-{ep.name}-{time.strftime('%Y%m%d-%H%M')}.json"
    out.write_text(json.dumps(R, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in R.items() if k != "models"}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
