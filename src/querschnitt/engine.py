"""The topic engine: every decision is a choice among listed codes, read from Apertus's next-token distribution.

Steps per affair (all measured in the spikes; S-numbers name the evaluation):
  ch1   APS chapter, codes A–Y in identity order; for federal affairs with APS-labelled neighbours, the five most similar
        labelled affairs are shown as examples (S9 D3)
  ch2   the same question in a second code order (S1 permutation) when ch1's top probability is below 0.9 (S6)
  sub   one request over the subtopics of the top 2–3 chapters, top chapter first (S5/S9 D1); the shipped chapter is the
        one read back from the chosen subtopic
  yn:<topic>  ad-hoc yes/no (S3 E6 frame), order a (A = yes); order b when 0.1 < p < 0.9 (S8)
  ev    evidence: one numbered sentence of the input, checked as an exact substring (S12)
A step's row stores the raw code log-probabilities, the served model and fingerprint, and the prompt id; `compose`
turns rows into topic rows.

With QS_PREFILL=0 (an endpoint without assistant prefill) every step sends one user message instead
(prompts.no_prefill_user), reads the code after the JSON opening (first such token's top_logprobs, else the generated
text) and marks `meta.mode = "no-prefill"`. That mode was measured on the S25 held-out items (S28) but has no calibration map; its prompt ids differ
from the prefill ones."""
from __future__ import annotations

import math
import threading

from . import prompts as P
from .client import CapabilityError, Client, capability_message, code_after, generated_code, prefill_ignored, read_codes, \
    read_codes_after
from .scheme import APS


def probs(d: dict[str, float], codes: list[str], perm: list[int] | None = None) -> list[float]:
    """Code log-probabilities -> normalised probability per option (perm maps code position -> option index)."""
    n = len(codes)
    pv = [0.0] * n
    for c, l in d.items():
        i = codes.index(c)
        pv[perm[i] if perm else i] = math.exp(l)
    s = sum(pv)
    return [v / s for v in pv] if s else pv


NOPRE_TOKENS = 12   # no-prefill mode: room for the JSON opening (and a code fence) before the code


class Engine:
    def __init__(self, client: Client, examples=None, stop: threading.Event | None = None):
        self.client, self.examples, self.stop = client, examples, stop
        if client is not None:
            self._prefill()

    def _prefill(self) -> bool:
        """The mode of this call: QS_PREFILL decides the prompts and ids, so the endpoint must be configured alike."""
        on = P.prefill_on()
        if self.client is not None and getattr(self.client.endpoint, "prefill", True) != on:
            raise ValueError(f"QS_PREFILL says prefill={on} but endpoint '{self.client.endpoint.name}' has prefill="
                             f"{self.client.endpoint.prefill}; build the endpoint with Endpoint.from_env()")
        return on

    def _call(self, user: str, prefill: str, codes: list[str], max_tokens: int) -> tuple[dict, dict, dict]:
        """One closed choice -> (choice, meta, code log-probabilities). Prefill mode is the measured request, unchanged."""
        if self._prefill():
            ch, meta = self.client.chat([{"role": "user", "content": user}, {"role": "assistant", "content": prefill}],
                                        max_tokens=max_tokens, stop=self.stop)
            d = read_codes(ch, codes)
            if not d and prefill_ignored(ch, prefill):
                raise CapabilityError("prefill", capability_message(
                    "prefill", self.client.endpoint.name, "accepted the prefill request but started a new answer instead of "
                    f"continuing it ({((ch.get('message') or {}).get('content') or '')[:80]!r})"))
            return ch, meta, d
        ch, meta = self.client.chat([{"role": "user", "content": P.no_prefill_user(user, prefill)}],
                                    max_tokens=max_tokens + NOPRE_TOKENS, stop=self.stop)
        meta["mode"] = P.NO_PREFILL
        return ch, meta, read_codes_after(ch, codes, prefill)

    def _ask(self, user: str, prefill: str, codes: list[str], max_tokens: int = 1) -> tuple[dict, dict]:
        ch, meta, d = self._call(user, prefill, codes, max_tokens)
        if not d:  # endpoint without log-probabilities: the generated code, checked against the list
            g = generated_code(ch, codes) if meta.get("mode") is None else code_after(ch, codes, prefill)
            d = {g: 0.0} if g else {}
        meta["mass"] = round(sum(math.exp(v) for v in d.values()), 5)
        return d, meta

    # ------------------------------------------------------------------ prompts (pure; used for cache keys too)
    def ch1_prompt(self, a: dict):
        ex = self.examples.neighbours(a) if (self.examples and a.get("level") == "federal" and a.get("lang") == "de") else None
        if ex:
            u, p = P.chapter_prompt_examples(a, list(range(25)), [(e["title"], e["chapter"]) for e in ex])
            return u, p, [e["oid"] for e in ex]
        u, p = P.chapter_prompt(a, list(range(25)))
        return u, p, None

    # ------------------------------------------------------------------ steps
    def ch1(self, a: dict, built=None) -> dict:
        u, p, ex = built or self.ch1_prompt(a)
        d, meta = self._ask(u, p, P.CODES)
        return dict(step="ch1", pid=P.pid(u, p), codes=d, p=probs(d, P.CODES), ex=ex, meta=meta)

    def ch2(self, a: dict) -> dict:
        u, p = P.chapter_prompt(a, P.S1PERM)
        d, meta = self._ask(u, p, P.CODES)
        return dict(step="ch2", pid=P.pid(u, p), codes=d, p=probs(d, P.CODES, P.S1PERM), meta=meta)

    def ch_lang(self, a: dict) -> dict:
        """Chapter reading of one language version (identity order); bilingual parliaments' second reading (S10)."""
        u, p = P.chapter_prompt(a, list(range(25)))
        d, meta = self._ask(u, p, P.CODES)
        return dict(step=f"bi:{a['lang']}", pid=P.pid(u, p), codes=d, p=probs(d, P.CODES), meta=meta)

    def flat(self, scheme: dict, title: str, lang: str) -> dict:
        """A flat scheme file (e.g. Bern's directorates, S6): one closed choice over its options + none."""
        u, p, codes = P.flat_prompt(scheme, title, lang)
        d, meta = self._ask(u, p, codes)
        return dict(step=f"flat:{scheme['id']}", pid=P.pid(u, p), codes=d, p=probs(d, codes), lang=lang, meta=meta)

    def named(self, scheme: dict, a: dict, second: bool = False) -> dict:
        """A named scheme file (topic names only, S20): one closed choice; `second` = the other code order."""
        n = len(scheme["options"]) + 1
        perm = P.named_perm(n) if second else list(range(n))
        u, p, codes = P.named_prompt(scheme, a, perm)
        d, meta = self._ask(u, p, codes)
        return dict(step=f"named:{scheme['id']}:{'b' if second else 'a'}", pid=P.pid(u, p), codes=d, p=probs(d, codes, perm), meta=meta)

    def sub(self, a: dict, chs: list[int]) -> dict:
        u, p, opts, codes = P.subtopic_prompt(a, chs)
        d, meta = self._ask(u, p, codes)
        return dict(step="sub", pid=P.pid(u, p), codes=d, chs=chs, p=probs(d, codes), meta=meta)

    def yn(self, topic: dict, a: dict, order: str = "a", examples=None) -> dict:
        u, p = P.yesno_prompt(topic, a["lang"], a["title"], a["title_long"], order, examples)
        d, meta = self._ask(u, p, ["A", "B"])
        pa, pb = math.exp(d.get("A", -50)), math.exp(d.get("B", -50))
        py = (pa if order == "a" else pb) / (pa + pb)
        return dict(step=f"yn:{topic['id']}:{order}", pid=P.pid(u, p), codes=d, p_yes=py, meta=meta)

    def verify(self, topic: dict, a: dict, order: str = "a") -> dict:
        """S27: is the topic central to the affair, not just touched on or merely similar? (asked on flags only)"""
        u, p = P.verify_prompt(topic, a["lang"], a["title"], a["title_long"], order)
        d, meta = self._ask(u, p, ["A", "B"])
        pa, pb = math.exp(d.get("A", -50)), math.exp(d.get("B", -50))
        return dict(step=f"vf:{topic['id']}:{order}", pid=P.pid(u, p), codes=d, p_yes=(pa if order == "a" else pb) / (pa + pb), meta=meta)

    def scope_check(self, topic: dict, a: dict, order: str = "a") -> dict:
        """S30: does the affair belong to the topic, given its generated include / exclude list? (asked on flags only)"""
        u, p = P.scope_check_prompt(topic, a["lang"], a["title"], a["title_long"], order)
        d, meta = self._ask(u, p, ["A", "B"])
        pa, pb = math.exp(d.get("A", -50)), math.exp(d.get("B", -50))
        return dict(step=f"sc:{topic['id']}:{order}", pid=P.pid(u, p), codes=d, p_yes=(pa if order == "a" else pb) / (pa + pb), meta=meta)

    def evidence(self, a: dict, name: str) -> dict | None:
        sents = P.sentences(a)
        if not sents:
            return None
        u, p = P.evidence_prompt([s for _, s in sents], name)
        codes = [str(i) for i in range(1, len(sents) + 1)]
        ch, meta, d = self._call(u, p, codes, 3)
        if d:
            k = max(d, key=d.get)
        elif meta.get("mode") is None:
            raw = ((ch.get("message") or {}).get("content") or "").strip().strip('"').split('"')[0].strip()
            k = raw if raw in codes else None
        else:
            k = code_after(ch, codes, p)
        if not k:
            return dict(step="ev", pid=P.pid(u, p), ok=False, meta=meta)
        src, s = sents[int(k) - 1]
        hay = dict(P.evidence_parts(a))[src]
        i = hay.find(s)
        return dict(step="ev", pid=P.pid(u, p), ok=i >= 0, field=src, start=i, end=i + len(s), quote=s, k=int(k),
                    p=round(math.exp(d[k]), 4) if d else None, meta=meta)


def need_ch2(p1: list[float], examples: bool = False) -> bool:
    """Second code order: always with examples (federal design D4, S16 primary); otherwise when the first reading's top
    probability is below 0.9 (S6)."""
    return examples or max(p1) < 0.9


def mean_p(p1: list[float], p2: list[float] | None) -> list[float]:
    return [(x + y) / 2 for x, y in zip(p1, p2)] if p2 else list(p1)


def need_yn_b(p_a: float) -> bool:
    return 0.1 < p_a < 0.9
