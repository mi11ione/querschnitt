"""A fake OpenAI-compatible chat endpoint for tests and CI. No model is called; nothing leaves the machine.

    python -m querschnitt.fake_endpoint --port 8099 [--mode logprobs|nologprobs|noprefill|ignoreprefill|error|bad|429]
    QS_BASE_URL=http://127.0.0.1:8099/v1 QS_API_KEY=x querschnitt serve

Answers by request shape, the way the engine reads Apertus:
  yes/no prefill (`{"antwort": "` …)  top_logprobs over A/B; p(yes) = 0.92 if the item block contains a yes word
                                      (--yes, default: digital, numérique, digitale, wolf, loup, lupo), 0.6 for a maybe
                                      word ("eventuell"), else 0.04; A = yes in order a, B = yes in order b
  chapter / subtopic / evidence       top_logprobs with one peaked code (deterministic from the prompt)
  no prefill, the no-prefill line      (QS_PREFILL=0 prompts) the answer `{"kapitel": "X"}`: the same choice as with prefill,
                                      its top_logprobs on the token after the JSON opening
  no prefill, `"terms"` in the prompt the ad-hoc topic JSON (names, scope, terms)
  no prefill, `"subtopics"`            {"subtopics": [10, 11]}
A system message is refused with HTTP 400 (the engine never sends one). Mode `noprefill` refuses the vLLM prefill fields
the way OpenAI's API does (HTTP 400 "Unrecognized request argument supplied: continue_final_message"); mode
`ignoreprefill` accepts them and starts a new answer (a server that drops unknown fields). Requests are kept in `.requests`.
In-process: `with FakeEndpoint() as f: Endpoint(base_url=f.url, ...)`."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

YES_WORDS = ["digital", "numérique", "digitale", "wolf", "loup", "lupo"]
NO_ANSWERS = ("Nein, anderes Thema", "Non, autre thème", "No, altro tema")
VERIFY_Q = re.compile(r"zentrales Thema|thème central|tema centrale")
ITEM = re.compile(r"\n(?:Geschäft|Objet|Oggetto):\n(.*?)\n\n", re.S)
NOPRE_LINE = re.compile(r"\n\n(?:Beginne deine Antwort genau mit|Commence ta réponse exactement par|Inizia la risposta "
                        r"esattamente con) `(.+?)` [^\n]*$", re.S)


def _lp(p: float) -> float:
    return math.log(max(p, 1e-9))


def _top(dist: dict[str, float]) -> list[dict]:
    return [dict(token=k, logprob=_lp(v), bytes=None) for k, v in sorted(dist.items(), key=lambda x: -x[1])][:20]


class FakeEndpoint:
    def __init__(self, mode: str = "logprobs", yes_words: list[str] | None = None, fingerprint: str = "fp_fake_1",
                 model: str = "swiss-ai/apertus-v1.5-8b", host: str = "127.0.0.1", port: int = 0, latency: float = 0.0,
                 n429: int = 0, topic_json: dict | None = None, gen_text: str | None = None):
        self.mode, self.yes_words, self.fp, self.model = mode, [w.lower() for w in (yes_words or YES_WORDS)], fingerprint, model
        self.latency, self.n429, self.topic_json, self.gen_text = latency, n429, topic_json, gen_text
        self.central_words: list[str] | None = None      # verify question (S27): «central» only for these (default: yes words)
        self.requests: list[dict] = []
        self.lock = threading.Lock()
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code: int, obj: dict, headers: dict | None = None):
                b = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b)))
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.end_headers(); self.wfile.write(b)

            def do_GET(self):
                if self.path.rstrip("/").endswith("/models"):
                    return self._send(200, dict(object="list", data=[dict(id=fake.model, object="model")]))
                self._send(404, {"error": "fake: POST /v1/chat/completions"})

            def do_POST(self):
                n = int(self.headers.get("Content-Length", 0))
                try:
                    body = json.loads(self.rfile.read(n) or b"{}")
                except ValueError:
                    return self._send(400, {"error": "not JSON"})
                with fake.lock:
                    fake.requests.append(body)
                    k429 = fake.n429 > 0
                    if k429:
                        fake.n429 -= 1
                if fake.latency:
                    time.sleep(fake.latency)
                if fake.mode == "error":
                    return self._send(500, {"error": "fake: mode error"})
                if fake.mode == "bad":
                    return self._send(400, {"error": "fake: mode bad (a request the endpoint refuses)"})
                if k429 or fake.mode == "429":
                    return self._send(429, {"error": "rate"}, {"Retry-After": "0"})
                msgs = body.get("messages") or []
                if any(m.get("role") == "system" for m in msgs):
                    return self._send(400, {"error": "fake: system message refused"})
                if fake.mode == "noprefill" and ("continue_final_message" in body or "add_generation_prompt" in body):
                    f = "continue_final_message" if "continue_final_message" in body else "add_generation_prompt"
                    return self._send(400, {"error": dict(message=f"Unrecognized request argument supplied: {f}",
                                                          type="invalid_request_error", param=None, code=None)})
                self._send(200, fake.answer(body))

        self.srv = ThreadingHTTPServer((host, port), H)
        self.srv.daemon_threads = True
        self.url = f"http://{host}:{self.srv.server_address[1]}/v1"

    # ------------------------------------------------------------------ answers
    def p_yes(self, item: str) -> float:
        low = item.lower()
        if any(w in low for w in self.yes_words):
            return 0.92
        return 0.6 if "eventuell" in low else 0.04

    def answer(self, body: dict) -> dict:
        msgs = body["messages"]
        user = next((m["content"] for m in reversed(msgs) if m["role"] == "user"), "")
        prefill = msgs[-1]["content"] if msgs[-1]["role"] == "assistant" else None
        opening = None                                   # no-prefill mode: the answer spells out the prefill first
        if prefill is None and (m := NOPRE_LINE.search(user)):
            opening, prefill, user = m.group(1), m.group(1), user[:m.start()]
        elif self.mode == "ignoreprefill" and prefill is not None:
            opening = prefill                            # the prefill is dropped; a new answer repeats its opening
        dist: dict[str, float] | None = None
        if prefill is not None:
            if any(k in prefill for k in ('"antwort"', '"reponse"', '"risposta"')):
                m = ITEM.search(user + "\n\n")
                item = m.group(1) if m else user
                if VERIFY_Q.search(user):                  # the stricter second question on flags
                    words = [w.lower() for w in (self.central_words or self.yes_words)]
                    py = 0.9 if any(w in item.lower() for w in words) else 0.15
                else:
                    py = self.p_yes(item)
                a_is_no = any(f"A = {n}" in user for n in NO_ANSWERS) or bool(re.search(r"^A = (Nein|Non|No)$", user, re.M))
                dist = {"A": 1 - py, "B": py} if a_is_no else {"A": py, "B": 1 - py}
            else:
                codes = re.findall(r"^([A-Za-z]|\d+)(?: =|\.) ", user, re.M)
                codes = list(dict.fromkeys(codes)) or ["A"]
                h = int(hashlib.sha256(user.encode()).hexdigest(), 16)
                top = codes[h % len(codes)]
                rest = [c for c in codes if c != top][:4]
                dist = {top: 0.8, **{c: 0.2 / max(1, len(rest)) for c in rest}}
            content = max(dist, key=dist.get)
        elif self.gen_text is not None:
            content = self.gen_text
        elif '"terms"' in user or '"scope"' in user:
            content = json.dumps(self.topic_json or dict(
                name=dict(de="Wolf und Herdenschutz", fr="loup et protection des troupeaux", it="lupo e protezione delle greggi"),
                scope=dict(de="Wolf, Herdenschutz, Abschuss", fr="loup, protection des troupeaux, tirs", it="lupo, protezione, abbattimenti"),
                terms=dict(de=["Wolf", "Herdenschutz", "Grossraubtier"], fr=["loup", "prédateur"], it=["lupo"])), ensure_ascii=False)
        elif '"subtopics"' in user:
            content = '{"subtopics": [10, 11]}'
        else:
            content = "ok"
        lp = self.mode != "nologprobs" and body.get("logprobs") and dist is not None
        toks = [dict(token=content, logprob=_lp(dist[content]), top_logprobs=_top(dist))] if lp else None
        if opening is not None and dist is not None:
            toks = [dict(token=opening, logprob=-0.01, top_logprobs=[dict(token=opening, logprob=-0.01, bytes=None)])] + \
                (toks or []) + [dict(token='"}', logprob=-0.01, top_logprobs=[dict(token='"}', logprob=-0.01, bytes=None)])]
            content = opening + content + '"}'
        choice = dict(index=0, message=dict(role="assistant", content=content), finish_reason="stop",
                      logprobs=dict(content=toks) if lp else None)
        return dict(id="fake-" + str(len(self.requests)), object="chat.completion", created=int(time.time()), model=self.model,
                    system_fingerprint=self.fp, choices=[choice],
                    usage=dict(prompt_tokens=len(user) // 4, completion_tokens=max(1, len(content) // 4)))

    def __enter__(self):
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *a):
        self.srv.shutdown(); self.srv.server_close()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m querschnitt.fake_endpoint")
    ap.add_argument("--port", type=int, default=8099)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--mode", default="logprobs", choices=["logprobs", "nologprobs", "noprefill", "ignoreprefill", "error", "bad", "429"])
    ap.add_argument("--yes", nargs="*", help="yes words (lower case substrings of the item)")
    ap.add_argument("--latency", type=float, default=0.0)
    a = ap.parse_args(argv)
    f = FakeEndpoint(a.mode, a.yes, host=a.host, port=a.port, latency=a.latency)
    print(f"fake endpoint ({a.mode}) at {f.url}", flush=True)
    try:
        f.srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        f.srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
