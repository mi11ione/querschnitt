"""Lean budget-capped Public AI client for ideation2 spikes (bern2-* tags only).

Drop-in for gateway gw.chat(full=True): returns (choice_dict, meta); meta["resp"] carries model + system_fingerprint.
Same prices as ~/Desktop/hackapertus/gateway/gw.py (list price). Own append-only ledger (ideation2/lib/ledger.jsonl) and
own cache, so it never touches the shared gateway ledger or its work cap (a separate bulk job uses that).
Caps: GLOBAL_CAP_USD across all bern2-* tags (ledger re-read at most every 20 s, plus in-process running total),
and a per-tag cap given by the caller. Key read from the 600 file, never printed or logged.
Rules enforced: tag starts with "bern2-"; no system messages ever; no prefill (trailing assistant message) to -70b names.

    import sys; sys.path.insert(0, '/Users/mi11ion/Desktop/hackapertus/bern/ideation2/lib'); import pai
    choice, meta = pai.chat(messages, model="swiss-ai/apertus-v1.5-8b", max_tokens=1, tag="bern2-s8-dvs", tag_cap_usd=3.0,
                            logprobs=True, top_logprobs=20, continue_final_message=True, add_generation_prompt=False)
"""
import json, hashlib, time, pathlib, urllib.request, urllib.error, fcntl, os, threading

BASE = "https://api.publicai.co/v1/chat/completions"
KEY = (pathlib.Path.home() / ".config/hackapertus/publicai.key").read_text().strip()
HERE = pathlib.Path(__file__).resolve().parent
LEDGER = HERE / "ledger.jsonl"
CACHE = HERE / "cache"; CACHE.mkdir(exist_ok=True)
PRICES = {"swiss-ai/apertus-v1.5-70b": (0.82, 2.92), "swiss-ai/apertus-70b-instruct": (0.82, 2.92),
          "swiss-ai/apertus-v1.5-8b": (0.10, 0.20), "swiss-ai/apertus-8b-instruct": (0.10, 0.20),
          "aisingapore/Qwen-SEA-LION-v4-32B-IT": (0.25, 0.60)}
GLOBAL_CAP_USD = 15.0
_lock = threading.Lock()
_state = {"t": 0.0, "total": 0.0, "by_tag": {}, "local": 0.0, "local_tag": {}}


def _read_ledger():
    tot, by = 0.0, {}
    if LEDGER.exists():
        for line in LEDGER.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line); tot += r["usd"]; by[r["tag"]] = by.get(r["tag"], 0.0) + r["usd"]
    return tot, by


def spent(tag=None):
    tot, by = _read_ledger()
    return by.get(tag, 0.0) if tag else tot


def _totals():
    now = time.time()
    with _lock:
        if now - _state["t"] > 20:
            tot, by = _read_ledger()
            _state.update(t=now, total=tot, by_tag=by, local=0.0, local_tag={})
        return _state["total"] + _state["local"], _state


def _add_local(tag, usd):
    with _lock:
        _state["local"] += usd; _state["local_tag"][tag] = _state["local_tag"].get(tag, 0.0) + usd


def chat(messages, model="swiss-ai/apertus-v1.5-8b", max_tokens=1, temperature=0.0, tag="bern2-untagged",
         tag_cap_usd=1.0, nocache=False, timeout=120, **extra):
    assert tag.startswith("bern2-"), tag
    assert not any(m["role"] == "system" for m in messages), "no system messages"
    if "-70b" in model.lower() or "70B" in model:
        assert messages[-1]["role"] == "user", "no prefill to -70b names"
        assert not extra.get("continue_final_message"), "no prefill to -70b names"
    pin, pout = PRICES[model]
    payload = dict(model=model, messages=messages, max_tokens=max_tokens, temperature=temperature, **extra)
    h = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    cp = CACHE / f"{h}.json"
    if cp.exists() and not nocache:
        d = json.loads(cp.read_text())
        return d["choice"], dict(d["meta"], cached=True)
    est_in = sum(len(m["content"]) for m in messages) / 3.0 + 50
    est = (est_in * pin + max_tokens * pout) / 1e6
    tot, st = _totals()
    if tot + est > GLOBAL_CAP_USD:
        raise RuntimeError(f"BUDGET global {tot:.3f}+{est:.5f} > {GLOBAL_CAP_USD}")
    tag_tot = st["by_tag"].get(tag, 0.0) + st["local_tag"].get(tag, 0.0)
    if tag_tot + est > tag_cap_usd:
        raise RuntimeError(f"BUDGET tag {tag} {tag_tot:.3f}+{est:.5f} > {tag_cap_usd}")
    req = urllib.request.Request(BASE, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                                          "User-Agent": "hackapertus-research/0.1"})
    t0 = time.time(); status = []; d = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                status.append(r.status); d = json.loads(r.read()); break
        except urllib.error.HTTPError as e:
            status.append(e.code)
            if attempt == 5: raise
            time.sleep((10 if e.code == 429 else 4) * (attempt + 1))
        except Exception as e:  # timeouts, disconnects
            status.append(repr(e)[:40])
            if attempt == 5: raise
            time.sleep(4 * (attempt + 1))
    u = d.get("usage", {}) or {}
    pt, ct = u.get("prompt_tokens", int(est_in)), u.get("completion_tokens", max_tokens)
    usd = (pt * pin + ct * pout) / 1e6
    resp = {k: v for k, v in d.items() if k not in ("choices", "usage")}
    row = dict(ts=time.time(), tag=tag, model=model, served=resp.get("model"), fp=resp.get("system_fingerprint"),
               pt=pt, ct=ct, usd=round(usd, 7))
    with open(LEDGER, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX); f.write(json.dumps(row) + "\n"); fcntl.flock(f, fcntl.LOCK_UN)
    _add_local(tag, usd)
    meta = dict(prompt_tokens=pt, completion_tokens=ct, usd=usd, secs=round(time.time() - t0, 2), cached=False,
                http=status, resp=resp)
    if not nocache:
        cp.write_text(json.dumps(dict(choice=d["choices"][0], meta=meta), ensure_ascii=False))
    return d["choices"][0], meta


def read_codes(choice, codes):
    """first generated token's top_logprobs -> {code: logprob} restricted to codes (strip quotes/space)."""
    lp = (choice.get("logprobs") or {}).get("content") or []
    if not lp:
        return {}
    out = {}
    for t in lp[0]["top_logprobs"]:
        s = t["token"].strip().strip('"').strip()
        if s in codes:
            out[s] = max(out.get(s, -1e9), t["logprob"])
    return out


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["spent"]:
        tot, by = _read_ledger(); print(json.dumps(dict(total=round(tot, 4), **{k: round(v, 4) for k, v in by.items()}), indent=1))
    elif sys.argv[1:] == ["fingerprints"]:
        c = {}
        for line in LEDGER.read_text().splitlines():
            r = json.loads(line); k = (r["model"], r["served"], r["fp"]); c[k] = c.get(k, 0) + 1
        for k, v in c.items(): print(v, *k)
    else:
        ch, m = chat([{"role": "user", "content": "Antworte nur mit: ok"}], max_tokens=3, tag="bern2-selftest", tag_cap_usd=0.01,
                     nocache=True)
        print(repr(ch["message"]["content"]), m["resp"].get("model"), m["resp"].get("system_fingerprint"), m["http"])
