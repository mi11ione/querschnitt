"""Resumable corpus run: one worker per affair in flight, all calls through one shared rate guard.

    python -m querschnitt.batch run --inputs inputs.jsonl.gz --out runs/main --since 2025-01-01 [--topics digitalisierung]
    python -m querschnitt.batch status --out runs/main

Rows are appended to <out>/<build>/<step>.jsonl. A step is done when its prompt id is in the current build's rows
(identical prompts are sent once; a changed input re-runs only what changed). The first served build is locked in
<out>/state.json; a different build stops the run (STOP.md) and nothing is mixed. Progress: <out>/PROGRESS.md.
A run made with QS_PREFILL=0 (unmeasured no-prefill mode) records `mode` in the lock and writes to its own build dir; a
run dir is never resumed in the other mode. An endpoint that refuses prefill or logprobs stops the run (STOP.md)."""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import os
import shutil
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import prompts as P
from .client import BuildChanged, CapabilityError, Client, Endpoint
from .engine import Engine, mean_p, need_ch2, need_yn_b
from .examples import ExamplePool, topic_examples
from .scheme import APS, adhoc, flat, named

BILINGUAL = {"BE", "FR", "VS"}   # fallback for inputs built before the `bilingual` field (OPD body languages)

ROOT = Path(__file__).resolve().parents[2]


def load_inputs(path, since="0000", until="9999", ids=None):
    out = []
    with gzip.open(path, "rt") as f:
        for line in f:
            x = json.loads(line)
            if ids is not None:
                if x["id"] in ids:
                    out.append(x)
            elif x["date"] and since <= x["date"] <= until:
                out.append(x)
    out.sort(key=lambda x: (x["date"], x["id"]), reverse=True)
    return out


class Store:
    def __init__(self, out: Path):
        self.out = out
        out.mkdir(parents=True, exist_ok=True)
        self.state_p = out / "state.json"
        self.state = json.loads(self.state_p.read_text()) if self.state_p.exists() else {}
        self.lock = threading.Lock()
        self.done: dict[str, dict] = {}       # pid -> row (current build)
        self.files: dict[str, object] = {}
        if self.build_dir():
            self._scan()

    def build_dir(self) -> Path | None:
        b = self.state.get("lock")
        return (self.out / b["key"]) if b else None

    def _scan(self):
        for p in sorted(self.build_dir().glob("*.jsonl")):
            with open(p, "rb+") as f:
                data = f.read()
                if data and not data.endswith(b"\n"):          # torn last line after a kill
                    cut = data.rfind(b"\n") + 1
                    f.seek(cut); f.truncate()
                    data = data[:cut]
            for line in data.splitlines():
                r = json.loads(line)
                self.done[r["pid"]] = r

    def lock_build(self, model: str, fp: str, mode: str | None = None):
        with self.lock:
            if "lock" in self.state:
                return
            key = (fp or "nofp").split("-")[-1] + "-" + time.strftime("%Y%m%d") + ("-" + mode if mode else "")
            self.state["lock"] = dict(model=model, fp=fp, key=key, first_seen=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
            if mode:   # unmeasured mode (QS_PREFILL=0); absent for the measured design
                self.state["lock"]["mode"] = mode
            self.state_p.write_text(json.dumps(self.state, indent=1))
            self.build_dir().mkdir(exist_ok=True)

    def write(self, row: dict):
        fn = ("yn_" + row["step"].split(":")[1].split("/")[-1]) if row["step"].startswith("yn:") else \
            ("vf_" + row["step"].split(":")[1].split("/")[-1]) if row["step"].startswith("vf:") else \
            ("named_" + row["step"].split(":")[1]) if row["step"].startswith("named:") else row["step"].replace(":", "_").replace("/", "_")
        with self.lock:
            f = self.files.get(fn)
            if f is None:
                f = self.files[fn] = open(self.build_dir() / f"{fn}.jsonl", "a")
            f.write(json.dumps(row, ensure_ascii=False) + "\n"); f.flush()
            self.done[row["pid"]] = row


class Runner:
    def __init__(self, args):
        self.args = args
        self.out = Path(args.out)
        self.store = Store(self.out)
        lock = self.store.state.get("lock")
        if lock and lock.get("mode") != P.mode():
            sys.exit(f"{self.out} was run in mode {lock.get('mode') or 'prefill (measured)'}, this process is in "
                     f"{P.mode() or 'prefill (measured)'} mode (QS_PREFILL); use another --out, never mix the two")
        ep = Endpoint.from_env()
        ep.max_rate, ep.conc = args.max_rate, args.conc
        self.client = Client(ep, ledger=str(self.out / "ledger.jsonl"), cap_usd=args.cap, expect_build=lock["fp"] if lock else None,
                             tag="batch")
        self.stop = threading.Event()
        pool = ExamplePool.load(ROOT / "data/eval/aps_pool.jsonl") if args.examples else None
        self.engine = Engine(self.client, pool, self.stop)
        self.topics = [adhoc(t) for t in args.topics]
        self.counts = collections.Counter()
        self.t0 = time.time()
        self.extra = {}
        if args.read_from:   # decisions made in other run dirs (same build), e.g. evidence for the main run's rows
            from .compose import read_run
            lk, self.extra = read_run(*[Path(r) for r in args.read_from])
            assert not lock or lk["fp"] == lock["fp"], "read-from runs are on another build"
        self.events = collections.deque(maxlen=50000)

    # ------------------------------------------------------------------ one call, cached by prompt id
    def _step(self, pid: str, fn):
        r = self.store.done.get(pid)
        if r is not None:
            self.counts["cached"] += 1
            return r
        try:
            r = fn()
        except BuildChanged as e:
            self.halt("Served build changed", str(e)); raise
        m = r["meta"]
        if not self.store.state.get("lock"):
            self.store.lock_build(m["model"], m["fp"], m.get("mode"))
            self.client.expect_build = m["fp"]
        r["ts"] = round(time.time(), 2)
        self.store.write(r)
        self.counts["calls"] += 1; self.counts[r["step"].split(":")[0]] += 1
        self.events.append(time.time())
        return r

    def affair(self, a: dict):
        if self.stop.is_set():
            return
        S, ih = self.args.steps, a["input_hash"]
        try:
            built = self.engine.ch1_prompt(a)
            r1 = self._step(P.pid(built[0], built[1]), lambda: dict(self.engine.ch1(a, built), aid=a["id"], ih=ih)) if "ch" in S \
                else self.store.done.get(P.pid(built[0], built[1]))
            r2 = None
            if r1 and need_ch2(r1["p"], bool(r1.get("ex"))):
                u, p = P.chapter_prompt(a, P.S1PERM)
                r2 = self._step(P.pid(u, p), lambda: dict(self.engine.ch2(a), aid=a["id"], ih=ih)) if "ch" in S \
                    else self.store.done.get(P.pid(u, p))
            if "sub" in S and r1 and (r2 or not need_ch2(r1["p"], bool(r1.get("ex")))):
                chs = P.subtopic_chapters(mean_p(r1["p"], r2["p"] if r2 else None))
                u, p, _, _ = P.subtopic_prompt(a, chs)
                self._step(P.pid(u, p), lambda: dict(self.engine.sub(a, chs), aid=a["id"], ih=ih))
            if "yn" in S:
                for t in self.topics:
                    ex = topic_examples(t, a)   # editor decisions on this topic become examples (None = unchanged prompt)
                    u, p = P.yesno_prompt(t, a["lang"], a["title"], a["title_long"], "a", ex)
                    ra = self._step(P.pid(u, p), lambda: dict(self.engine.yn(t, a, "a", ex), aid=a["id"], ih=ih))
                    rb = None
                    if need_yn_b(ra["p_yes"]):
                        u, p = P.yesno_prompt(t, a["lang"], a["title"], a["title_long"], "b", ex)
                        rb = self._step(P.pid(u, p), lambda: dict(self.engine.yn(t, a, "b", ex), aid=a["id"], ih=ih))
                    pm = (ra["p_yes"] + rb["p_yes"]) / 2 if rb else ra["p_yes"]
                    if t.get("verify") and pm >= t.get("cutoff", 0.5):   # S27: a second, stricter question on flags only
                        u, p = P.verify_prompt(t, a["lang"], a["title"], a["title_long"], "a")
                        va = self._step(P.pid(u, p), lambda: dict(self.engine.verify(t, a, "a"), aid=a["id"], ih=ih))
                        if need_yn_b(va["p_yes"]):
                            u, p = P.verify_prompt(t, a["lang"], a["title"], a["title_long"], "b")
                            self._step(P.pid(u, p), lambda: dict(self.engine.verify(t, a, "b"), aid=a["id"], ih=ih))
            if "bi" in S and a.get("bilingual", a["body"] in BILINGUAL) and a.get("alt_lang") in ("de", "fr"):
                # bilingual parliaments: the other language version is the second reading (S10: titles only)
                b = dict(title=a["title_alt"], title_long=a["title_long_alt"], text="", lang=a["alt_lang"])
                u, p = P.chapter_prompt(b, list(range(25)))
                self._step(P.pid(u, p), lambda: dict(self.engine.ch_lang(b), aid=a["id"], ih=ih))
                if a["lang"] in ("de", "fr"):
                    m = dict(title=a["title"], title_long=a["title_long"], text="", lang=a["lang"])
                    u, p = P.chapter_prompt(m, list(range(25)))
                    self._step(P.pid(u, p), lambda: dict(self.engine.ch_lang(m), aid=a["id"], ih=ih))
            if "be" in S and a["body"] == "BE":
                sch = flat("be-directorates")
                for t, l in ((a["title"], a["lang"]), (a.get("title_alt"), a.get("alt_lang"))):
                    if t and l in ("de", "fr"):
                        u, p, codes = P.flat_prompt(sch, t, l)
                        self._step(P.pid(u, p), lambda t=t, l=l: dict(self.engine.flat(sch, t, l), aid=a["id"], ih=ih))
            for sid in (self.args.named or []):
                sch = named(sid)
                n = len(sch["options"]) + 1
                u, p, _ = P.named_prompt(sch, a)
                ra = self._step(P.pid(u, p), lambda: dict(self.engine.named(sch, a), aid=a["id"], ih=ih))
                if max(ra["p"]) < 0.9:
                    u, p, _ = P.named_prompt(sch, a, P.named_perm(n))
                    self._step(P.pid(u, p), lambda: dict(self.engine.named(sch, a, True), aid=a["id"], ih=ih))
            if "ev" in S:
                self.evidence(a, r1, r2, ih)
            self.counts["affairs"] += 1
        except (BuildChanged, InterruptedError):
            self.stop.set()
        except Exception as e:  # noqa: BLE001 — logged, item retried on next start
            self.counts["errors"] += 1
            with open(self.out / "errors.jsonl", "a") as f:
                f.write(json.dumps(dict(ts=time.time(), aid=a["id"], err=repr(e)[:400])) + "\n")
            if isinstance(e, CapabilityError) and e.certain:   # retrying cannot help: the endpoint lacks a capability
                self.halt(f"Endpoint capability: {e.capability}", str(e))
            elif "BUDGET" in str(e):      # not an outage: ops/pipeline.py and ops/watchdog.sh resume `Errors` stops by themselves
                self.halt("Budget", repr(e)[:400])
            elif self.counts["errors"] > 200:
                self.halt("Errors", repr(e)[:400])

    def evidence(self, a, r1, r2, ih):
        """Evidence sentence for what an editor sees: the shipped chapter (where the read-back exists) and every
        ad-hoc flag or please-check row."""
        from .compose import decide
        rows = collections.ChainMap(self.store.done, self.extra) if self.extra else self.store.done
        d = decide(a, rows, self.engine.ch1_prompt, self.topics)
        jobs = []
        if d.get("aps") and d["aps"]["ch"] < 24 and (a["text"] or a["title_long"]):
            jobs.append(APS.names["de"][d["aps"]["ch"]])
        for t in self.topics:
            v = d.get(t["id"])
            if v and (v["flag"] or v["lane"] == "please_check"):
                jobs.append(t["names"]["de"])
        for name in jobs:
            sents = P.sentences(a)
            if not sents:
                continue
            u, p = P.evidence_prompt([x for _, x in sents], name)
            self._step(P.pid(u, p), lambda: dict(self.engine.evidence(a, name) or {}, aid=a["id"], ih=ih, name=name))

    def halt(self, title: str, body: str):
        self.stop.set()
        (self.out / "STOP.md").write_text(f"# {title}\n\n{time.strftime('%Y-%m-%d %H:%M:%S')}\n\n{body}\n")

    # ------------------------------------------------------------------ progress
    def progress(self, total: int, status: str = "running"):
        now = time.time()
        recent = [t for t in self.events if now - t < 600]
        rate10 = len(recent) / 600 if recent else 0.0
        lock = self.store.state.get("lock") or {}
        c = self.client.stats
        txt = (f"# Querschnitt corpus run\n\n- Status: **{status}** · updated {time.strftime('%Y-%m-%d %H:%M:%S')} · PID {os.getpid()}\n"
               f"- Scope: begin date {self.args.since} … {self.args.until}, newest first · topics: {', '.join(self.args.topics) or '—'}"
               f" · steps {' '.join(self.args.steps)} · examples {'on' if self.args.examples else 'off'}\n"
               f"- Affairs complete this session: **{self.counts['affairs']:,} / {total:,}** (cached steps reused: {self.counts['cached']:,})\n"
               f"- Calls this session: {self.counts['calls']:,} ({', '.join(f'{k} {v:,}' for k, v in self.counts.items() if k not in ('calls', 'affairs', 'cached', 'errors'))})"
               f" · errors {self.counts['errors']}\n"
               f"- Rate: {rate10:.2f} req/s (last 10 min) · guard {self.client.guard.rate:.2f}/s (cap {self.client.guard.max_rate}) · HTTP 429s {c['n429']:,} · transient {c['transient']}\n"
               f"- List-price estimate (ledger): USD {self.client.spent:.3f} of cap {self.args.cap}\n"
               f"- Build: `{lock.get('model')}` · `{lock.get('fp')}`\n"
               + (f"- Mode: **{lock['mode']}**: unmeasured; refit and pass the quality gate before use\n" if lock.get("mode") else ""))
        (self.out / "PROGRESS.md").write_text(txt)

    def run(self):
        ids = None
        if self.args.ids:
            ids = {int(x) for x in Path(self.args.ids).read_text().split()}
        items = load_inputs(self.args.inputs, self.args.since, self.args.until, ids)
        if self.args.limit:
            items = items[: self.args.limit]
        (self.out / "PID").write_text(str(os.getpid()))
        signal.signal(signal.SIGTERM, lambda *_: self.stop.set())
        print(f"{time.strftime('%H:%M:%S')} items {len(items):,} cached prompts {len(self.store.done):,}", flush=True)

        def ticker():
            while not self.stop.wait(60):
                try:  # live rate ceiling: <out>/control.json {"max_rate": 2.5}
                    c = json.loads((self.out / "control.json").read_text())
                    mr = float(c.get("max_rate", self.client.guard.max_rate))
                    if 0.05 <= mr <= 20 and mr != self.client.guard.max_rate:
                        with self.client.guard.cv:
                            self.client.guard.max_rate = mr; self.client.guard.rate = min(self.client.guard.rate, mr)
                except (FileNotFoundError, ValueError):
                    pass
                free = shutil.disk_usage(self.out).free
                if free < 1.5e9:   # pause before the disk fills; everything done is on disk, resume with the same command
                    self.halt("Disk low", f"{free / 1e9:.2f} GB free on the run's disk; free space, delete STOP.md, resume.")
                self.progress(len(items))
        threading.Thread(target=ticker, daemon=True).start()
        with ThreadPoolExecutor(self.args.conc) as ex:
            for _ in ex.map(self.affair, items):
                if self.stop.is_set():
                    break
        self.progress(len(items), "stopped" if self.stop.is_set() else "finished")
        print(f"{time.strftime('%H:%M:%S')} end stop={self.stop.is_set()} counts={dict(self.counts)}", flush=True)
        (self.out / "PID").unlink(missing_ok=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--inputs", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--since", default="2025-01-01")
    r.add_argument("--until", default="9999")
    r.add_argument("--ids")
    r.add_argument("--limit", type=int)
    r.add_argument("--topics", nargs="*", default=["digitalisierung"])
    r.add_argument("--steps", nargs="*", default=["ch", "sub", "yn"], help="ch sub yn bi be ev")
    r.add_argument("--no-examples", dest="examples", action="store_false")
    r.add_argument("--named", nargs="*", default=[], help="named scheme files to score (e.g. bs-themen)")
    r.add_argument("--read-from", nargs="*", default=[], help="other run dirs whose rows decide what evidence to fetch")
    r.add_argument("--conc", type=int, default=6)
    r.add_argument("--max-rate", type=float, default=1.6)
    r.add_argument("--cap", type=float, default=60.0)
    s = sub.add_parser("status")
    s.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "status":
        print((Path(a.out) / "PROGRESS.md").read_text())
        return
    if (Path(a.out) / "STOP.md").exists():
        sys.exit(f"{a.out}/STOP.md exists; read it, then remove it to resume")
    Runner(a).run()


if __name__ == "__main__":
    main()
