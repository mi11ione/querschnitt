"""One model client for every Apertus call: an OpenAI-compatible chat endpoint, a shared adaptive rate guard, a build
guard, a list-price ledger and, per call, the served model and `system_fingerprint`.

The measured design (every Prüfstand number) needs two endpoint capabilities beyond plain OpenAI chat: assistant prefill
(vLLM's `continue_final_message` / `add_generation_prompt` with a final assistant message) and next-token
`top_logprobs`. `Endpoint.prefill` / `Endpoint.logprobs` state them (env QS_PREFILL=0, QS_NO_LOGPROBS=1); an endpoint
that refuses one raises `CapabilityError` naming it and its switch. Nothing is retried in another mode mid-run: the
no-prefill mode has its own prompt ids (prompts.no_prefill_user) and is not measured.

Rules it enforces: no system message, ever; no assistant prefill to a `-70b` name (that route is answered by another
model when it gets one). The key is read from a file or env and never logged."""
from __future__ import annotations

import json
import os
import pathlib
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

PRICES = {  # USD per 1M tokens (in, out), Public AI list price
    "swiss-ai/apertus-v1.5-8b": (0.10, 0.20), "swiss-ai/apertus-8b-instruct": (0.10, 0.20),
    "swiss-ai/apertus-v1.5-70b": (0.82, 2.92), "swiss-ai/apertus-70b-instruct": (0.82, 2.92),
}


@dataclass
class Endpoint:
    name: str = "publicai"
    base_url: str = "https://api.publicai.co/v1"
    model: str = "swiss-ai/apertus-v1.5-8b"
    key_file: str = "~/.config/hackapertus/publicai.key"
    key_env: str = "QS_API_KEY"
    logprobs: bool = True          # the endpoint returns top_logprobs (Public AI: measured)
    prefill: bool = True           # the endpoint continues a final assistant message (vLLM continue_final_message)
    max_rate: float = 1.6          # requests/s ceiling for this process
    conc: int = 6

    def key(self) -> str:
        if os.environ.get(self.key_env):
            return os.environ[self.key_env].strip()
        p = pathlib.Path(self.key_file).expanduser()
        return p.read_text().strip() if p.exists() else ""

    @classmethod
    def from_env(cls) -> "Endpoint":
        e = cls()
        for f in ("name", "base_url", "model", "key_file"):
            v = os.environ.get(f"QS_{f.upper()}")
            if v:
                setattr(e, f, v)
        if os.environ.get("QS_MAX_RATE"):
            e.max_rate = float(os.environ["QS_MAX_RATE"])
        if os.environ.get("QS_NO_LOGPROBS"):
            e.logprobs = False
        e.prefill = prefill_from_env()
        return e


def prefill_from_env() -> bool:
    """QS_PREFILL=0 (or false/no/off) selects the unmeasured no-prefill mode; unset or anything else = prefill."""
    return os.environ.get("QS_PREFILL", "1").strip().lower() not in ("0", "false", "no", "off")


PREFILL_FIELDS = ("continue_final_message", "add_generation_prompt")


class CapabilityError(RuntimeError):
    """The endpoint lacks a capability the request needs (`capability`: "prefill" or "logprobs"). Not retried.
    `certain`: the reply names the field (or the prefill was visibly ignored); False for a bare 400/422 to a prefill
    request, which the batch logs as an ordinary error (it may also be a passing fault) instead of stopping on it."""

    def __init__(self, capability: str, msg: str, certain: bool = True):
        super().__init__(msg)
        self.capability, self.certain = capability, certain


SWITCH = {"prefill": "QS_PREFILL=0", "logprobs": "QS_NO_LOGPROBS=1"}


def capability_message(cap: str, endpoint: str, what: str) -> str:
    need = ("assistant prefill (a final assistant message continued via the vLLM fields continue_final_message / "
            "add_generation_prompt)" if cap == "prefill" else "next-token top_logprobs")
    return (f"endpoint '{endpoint}': {what}. The measured design needs {need}; nothing was retried in another mode. "
            f"Check the endpoint with tools/probe_endpoint.py. To run without it set {SWITCH[cap]}: an unmeasured mode "
            f"with its own prompt ids; refit and pass the quality gate before use.")


def capability_error(code: int, text: str, payload: dict, endpoint: str) -> CapabilityError | None:
    """A 4xx reply to a request that carried prefill or logprobs fields → the capability it most likely concerns.
    Conservative: the reply names the field (OpenAI "Unrecognized request argument supplied: …", TGI/pydantic "unknown
    field" / "Extra inputs are not permitted" with the field, litellm "does not support parameters: [...]", Mistral-style
    "last role … assistant"), or it is a bare 400/422 to a prefill request that names nothing else (context length)."""
    if code == 429 or code >= 500:
        return None
    low = text.lower()
    head = f"HTTP {code} {text[:240]!r}"
    if payload.get("logprobs") and "logprob" in low:
        return CapabilityError("logprobs", capability_message("logprobs", endpoint, f"refused top_logprobs ({head})"))
    if not any(f in payload for f in PREFILL_FIELDS):
        return None
    if any(f in low for f in PREFILL_FIELDS) or any(w in low for w in ("prefill", "final message", "last message", "last role",
                                                                       "assistant")):
        return CapabilityError("prefill", capability_message("prefill", endpoint, f"refused assistant prefill ({head})"))
    other = ("context length", "context window", "maximum context", "too long", "max_tokens", "model", "api key", "auth")
    if code in (400, 422) and not any(w in low for w in other):
        return CapabilityError("prefill", capability_message(
            "prefill", endpoint, f"refused a request carrying the prefill fields; the reply names no field, so prefill is the "
                                 f"likely cause ({head})"), certain=False)
    return None


class Guard:
    """In-flight cap + AIMD request rate shared by all threads. A 429 makes every worker wait out Retry-After and cuts
    the rate ×0.7; each quiet minute adds 0.1/s up to the ceiling. The job therefore yields when others share the key."""

    def __init__(self, conc: int, max_rate: float, start: float = 1.0, floor: float = 0.15):
        self.limit, self.max_rate, self.floor = conc, max_rate, floor
        self.rate = min(max_rate, start)
        self.inflight, self.next_t, self.pause_until = 0, 0.0, 0.0
        self.last429, self.last_raise, self.fail_run = 0.0, time.time(), 0
        self.cv = threading.Condition()

    def acquire(self, stop: threading.Event | None = None) -> bool:
        with self.cv:
            while not (stop and stop.is_set()):
                now = time.time()
                if self.inflight < self.limit and now >= self.pause_until and now >= self.next_t:
                    self.inflight += 1
                    self.next_t = max(now, self.next_t) + 1.0 / self.rate
                    return True
                self.cv.wait(max(0.05, min(5.0, max(self.pause_until, self.next_t) - now)))
            return False

    def release(self, status: str, retry_after: float = 0.0):
        with self.cv:
            self.inflight -= 1
            now = time.time()
            if status == "429":
                if now - self.last429 > 2:
                    self.rate = max(self.floor, self.rate * 0.7)
                self.last429 = now
                self.pause_until = max(self.pause_until, now + max(retry_after, 4.0))
            elif status == "transient":
                self.fail_run += 1
                self.pause_until = max(self.pause_until, now + min(300, 5 * 2 ** min(self.fail_run - 1, 6)))
            else:
                self.fail_run = 0
                if self.rate < self.max_rate and now - self.last429 > 60 and now - self.last_raise > 60:
                    self.rate = min(self.max_rate, self.rate + 0.1)
                    self.last_raise = now
            self.cv.notify_all()


class BuildChanged(RuntimeError):
    pass


@dataclass
class Client:
    endpoint: Endpoint = field(default_factory=Endpoint.from_env)
    ledger: str | None = None              # jsonl path; one row per HTTP success (list-price USD)
    cap_usd: float = 200.0                 # list-price cap for this ledger
    expect_build: str | None = None        # system_fingerprint the caller locked; mismatch raises BuildChanged
    tag: str = "querschnitt"

    def __post_init__(self):
        self.guard = Guard(self.endpoint.conc, self.endpoint.max_rate)
        self._key = self.endpoint.key()
        self._lock = threading.Lock()
        self.spent = 0.0
        self.stats = dict(ok=0, n429=0, transient=0, errors=0)
        if self.ledger and os.path.exists(self.ledger):
            with open(self.ledger) as f:
                for line in f:
                    try:
                        self.spent += json.loads(line)["usd"]
                    except Exception:
                        pass

    # -------------------------------------------------------------- one request, retried on 429 / 5xx / network
    def chat(self, messages: list[dict], max_tokens: int = 1, temperature: float = 0.0, logprobs: int | None = 20,
             prefill: bool = True, stop: threading.Event | None = None, timeout: float = 120, **extra) -> tuple[dict, dict]:
        ep = self.endpoint
        assert not any(m["role"] == "system" for m in messages), "no system messages"
        if "-70b" in ep.model.lower():
            assert messages[-1]["role"] == "user", "no prefill to -70b names"
            prefill = False
        if not ep.prefill and messages[-1]["role"] == "assistant":
            raise CapabilityError("prefill", capability_message(
                "prefill", ep.name, "is set without prefill (QS_PREFILL=0) but the request ends with an assistant message"))
        payload = dict(model=ep.model, messages=messages, max_tokens=max_tokens, temperature=temperature, **extra)
        if prefill and messages[-1]["role"] == "assistant":
            payload.update(continue_final_message=True, add_generation_prompt=False)
        if logprobs and ep.logprobs:
            payload.update(logprobs=True, top_logprobs=logprobs)
        pin, pout = PRICES.get(ep.model, (0.10, 0.20))
        if self.spent > self.cap_usd:
            raise RuntimeError(f"BUDGET {self.spent:.2f} > {self.cap_usd} (list price, {self.ledger})")
        body = json.dumps(payload).encode()
        statuses, t_first = [], time.time()
        for attempt in range(12):
            if not self.guard.acquire(stop):
                raise InterruptedError("stopped")
            t0 = time.time(); st, ra = "ok", 0.0
            try:
                req = urllib.request.Request(ep.base_url.rstrip("/") + "/chat/completions", data=body, method="POST",
                                             headers={"Authorization": f"Bearer {self._key}", "Content-Type": "application/json",
                                                      "User-Agent": "querschnitt/0.6"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    d = json.loads(r.read()); statuses.append(r.status)
            except urllib.error.HTTPError as e:
                statuses.append(e.code)
                if e.code == 429:
                    st = "429"
                    try:
                        ra = float((e.headers or {}).get("Retry-After") or 0)
                    except ValueError:
                        ra = 0.0
                elif e.code >= 500:
                    st = "transient"
                else:
                    self.guard.release("ok")
                    with self._lock:
                        self.stats["errors"] += 1
                    txt = e.read()[:600].decode("utf-8", "replace")
                    cap = capability_error(e.code, txt, payload, ep.name)
                    if cap:
                        raise cap
                    raise RuntimeError(f"HTTP {e.code}: {txt[:300].encode()!r}")
            except Exception as e:  # timeouts, resets
                statuses.append(type(e).__name__); st = "transient"
            self.guard.release(st, ra)
            with self._lock:
                self.stats["n429" if st == "429" else st if st == "transient" else "ok"] += 1
            if st == "ok":
                break
        else:
            raise RuntimeError(f"gave up after {statuses}")
        lat = time.time() - t0
        u = d.get("usage") or {}
        pt, ct = u.get("prompt_tokens", 0), u.get("completion_tokens", 0)
        usd = (pt * pin + ct * pout) / 1e6
        meta = dict(model=d.get("model"), fp=d.get("system_fingerprint"), pt=pt, ct=ct, usd=round(usd, 7),
                    lat=round(lat, 3), wall=round(time.time() - t_first, 3), http=statuses, endpoint=ep.name, id=d.get("id"))
        with self._lock:
            self.spent += usd
            if self.ledger:
                with open(self.ledger, "a") as f:
                    f.write(json.dumps(dict(ts=round(time.time(), 3), tag=self.tag, model=meta["model"], fp=meta["fp"],
                                            pt=pt, ct=ct, usd=meta["usd"])) + "\n")
        if self.expect_build and meta["fp"] != self.expect_build:
            raise BuildChanged(f"served build {meta['model']} {meta['fp']} != locked {self.expect_build}")
        return d["choices"][0], meta


def read_codes(choice: dict, codes: list[str]) -> dict[str, float]:
    """First generated token's top log-probabilities, restricted to `codes` (quotes and spaces stripped)."""
    lp = (choice.get("logprobs") or {}).get("content") or []
    if not lp:
        return {}
    out: dict[str, float] = {}
    for t in lp[0].get("top_logprobs") or []:
        s = t["token"].strip().strip('"').strip()
        if s in codes:
            out[s] = max(out.get(s, -1e9), t["logprob"])
    return out


def generated_code(choice: dict, codes: list[str]) -> str | None:
    """Without log-probabilities: the generated text, checked against the code list (None if it is not on it)."""
    s = ((choice.get("message") or {}).get("content") or choice.get("text") or "").strip().strip('"').strip()
    return s if s in codes else None


def _compact(s: str) -> str:
    return "".join(s.split())


def read_codes_after(choice: dict, codes: list[str], prefix: str) -> dict[str, float]:
    """No-prefill mode: the top log-probabilities of the first generated token after the answer has spelled out `prefix`
    (e.g. `{"kapitel": "`; whitespace ignored, a code token that carries its opening quote counts), restricted to
    `codes`. Empty when the answer never reaches the prefix or there are no log-probabilities.
    Before the opening quote only a generated token that carries the quote and the code together (` "B`) is read: when
    the model generates the quote alone (` "`, Apertus's usual tokenisation, S28), that token's alternatives are rare
    merged tokens (log-probabilities near -15), not the code distribution, which is on the next token."""
    lp = (choice.get("logprobs") or {}).get("content") or []
    want = _compact(prefix)
    core = want.rstrip('"')
    seen = ""
    for t in lp:
        tok = (t.get("token") or "").strip()
        merged = tok.startswith('"') and tok.strip('"').strip() in codes
        if seen.endswith(want) or (seen.endswith(core) and merged):
            out: dict[str, float] = {}
            for x in t.get("top_logprobs") or []:
                s = x["token"].strip().strip('"').strip()
                if s in codes:
                    out[s] = max(out.get(s, -1e9), x["logprob"])
            if out:
                return out
        seen += _compact(t.get("token") or "")
    return {}


def code_after(choice: dict, codes: list[str], prefix: str) -> str | None:
    """No-prefill mode without log-probabilities: the code that follows `prefix` in the generated text (a bare code as
    the whole answer also counts); None if it is not on the list."""
    txt = _compact((choice.get("message") or {}).get("content") or choice.get("text") or "")
    want = _compact(prefix)
    i = txt.find(want)
    if i >= 0:
        s = txt[i + len(want):].split('"')[0]
        return s if s in codes else None
    return generated_code(choice, codes)


def prefill_ignored(choice: dict, prefix: str) -> bool:
    """Prefill mode: the endpoint accepted the request but started a new answer instead of continuing the prefill (the
    text repeats the opening of `prefix`, or opens a code fence). vLLM-style servers ignore unknown fields silently."""
    txt = _compact((choice.get("message") or {}).get("content") or choice.get("text") or "")
    want = _compact(prefix)
    return bool(txt) and (txt.startswith(want[:4]) or txt.startswith("```"))
