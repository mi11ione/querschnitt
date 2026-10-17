#!/usr/bin/env python3
"""The stored rows of the measured runs as run.py raw rows (keyed by the task's own prompt ids), so `run.py --score-only`
re-scores them. No model calls.

    python upstream/eval-task/stored_rows.py --split s9 --out runs/stored-s9
    python upstream/eval-task/run.py --out runs/stored-s9 --score-only --tasks aps

    python upstream/eval-task/stored_rows.py --split heldout_s25 --out runs/stored-s25 [--run runs/s25]
    python upstream/eval-task/run.py --out runs/stored-s25 --score-only --split heldout_s25

s9: eval/spikes/s9-aps/raw (S9 d0a, d0b, d3m, d1) and eval/s16/raw.jsonl (S16 subtopic requests), plus the S8 yes/no rows
of the 30 DVS items (eval/spikes/s8-dvs/raw/a.jsonl, b.jsonl), all in the public repo. Every prompt id is recomputed from
the frozen items.
heldout_s25: the S25 run dir (local, not published; what the engine asked: the first reading with examples, the S1 order,
one subtopic request) and eval/s25b/raw.jsonl (S25b: the identity-order reading without examples), rows keyed by prompt
id. They score D4E on all 927 items, D0 and D3 where both readings exist, and the other designs only where their prompts
coincide with these."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "src"))
import run as T  # noqa: E402
from querschnitt import prompts as P  # noqa: E402
from querschnitt.engine import probs  # noqa: E402

BUILD = "vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840"


def row(pid, step, codes, p, model, fp):
    return dict(pid=pid, step=step, codes=codes, p=p, model=model, fp=fp, logprobs=len(codes) > 1)


def s9() -> dict:
    out = {}
    items = {it["id"]: it for it in T.aps_items(split="s9")}
    raw = ROOT / "eval/spikes/s9-aps/raw"
    for ph in ("d0a", "d0b", "d3m"):
        for line in open(raw / f"{ph}.jsonl"):
            r = json.loads(line); pid = P.pid(*T.p_ch(items[r["oid"]], ph)[0])
            out[pid] = row(pid, ph, r["codes"], r["p"], r["rec"]["model"], r["rec"]["fp"])
    for line in open(raw / "d1.jsonl"):
        r = json.loads(line); pid = P.pid(*T.p_sub(items[r["oid"]], r["chs"])[0])
        out[pid] = row(pid, "sub", r["codes"], r["p"], r["rec"]["model"], r["rec"]["fp"])
    for line in open(ROOT / "eval/s16/raw.jsonl"):           # S16 rows reused from d1 carry no pid or codes of their own
        r = json.loads(line)
        for k in ("d4", "d4s"):
            x = r[k]; pid = P.pid(*T.p_sub(items[r["oid"]], x["chs"])[0])
            assert pid == x.get("pid", pid), (r["oid"], k)
            out.setdefault(pid, dict(row(pid, "sub", {}, x["p"], "swiss-ai/apertus-v1.5-8b", x.get("fp", BUILD)), logprobs=True))
    dvs = {it["id"]: it for it in T.dvs_items()}
    for o in ("a", "b"):
        for line in open(ROOT / f"eval/spikes/s8-dvs/raw/{o}.jsonl"):
            r = json.loads(line)
            if r["id"] in dvs:
                um, codes = T.p_yn(dvs[r["id"]], o); pid = P.pid(*um)
                out[pid] = row(pid, f"yn_{o}", r["codes"], probs(r["codes"], codes), r["served"], r["fp"])
    return out


def s25(run: Path) -> dict:
    out = {}
    for f in sorted((run / json.loads((run / "state.json").read_text())["lock"]["key"]).glob("*.jsonl")):
        for line in open(f):
            if line.strip():
                r = json.loads(line)
                out[r["pid"]] = row(r["pid"], r["step"], r["codes"], r["p"], r["meta"]["model"], r["meta"]["fp"])
    for line in open(ROOT / "eval/s25b/raw.jsonl"):        # p only (codes not stored); read from log-probabilities
        r = json.loads(line)
        out.setdefault(r["pid"], dict(row(r["pid"], "d0a", {}, r["p"], "swiss-ai/apertus-v1.5-8b", r["fp"]), logprobs=True))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=sorted(T.SPLITS))
    ap.add_argument("--out", required=True)
    ap.add_argument("--run", default=str(ROOT / "runs/s25"), help="heldout_s25: the S25 run dir")
    a = ap.parse_args(argv)
    rows = s9() if a.split == "s9" else s25(Path(a.run))
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / "raw.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows.values()))
    print(f"{len(rows)} rows -> {out / 'raw.jsonl'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
