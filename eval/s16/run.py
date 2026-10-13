"""S16 (eval/PREREG-BUILD.md): read-back combined with examples on the 1,357 S9 items. Reuses S9 rows; new subtopic calls only
where P4's chapter list differs from the S9 D1 list. Resumable (raw.jsonl keyed by oid). Usage: python eval/s16/run.py"""
import json, os, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
from querschnitt import prompts as P
from querschnitt.client import Client, Endpoint
from querschnitt.engine import Engine

S9 = Path("/Users/mi11ion/Desktop/hackapertus/bern/ideation2/spikes/s9-aps")
BUILD = "vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840"
load = lambda p: {json.loads(l)["oid"]: json.loads(l) for l in open(p)}
items = {it["oid"]: it for it in json.load(open(S9 / "data/items.json"))}
raw = {ph: load(S9 / f"raw/{ph}.jsonl") for ph in ("d0b", "d1", "d3m")}
done = load(HERE / "raw.jsonl") if (HERE / "raw.jsonl").exists() else {}
ep = Endpoint.from_env(); ep.max_rate, ep.conc = 0.6, 2
eng = Engine(Client(ep, ledger=str(HERE / "ledger.jsonl"), cap_usd=1.0, expect_build=BUILD, tag="s16"))
lock = threading.Lock()


def task(o):
    if o in done or o not in raw["d3m"] or o not in raw["d0b"]:
        return
    it = items[o]; a = dict(title=it["de"]["title"], title_long=it["de"]["title_long"], text=it["de"]["text"])
    full = [(x + y) / 2 for x, y in zip(raw["d3m"][o]["p"], raw["d0b"][o]["p"])]
    sel = full if max(raw["d3m"][o]["p"]) < 0.9 else raw["d3m"][o]["p"]
    out = dict(oid=o)
    for name, prior in (("d4", full), ("d4s", sel)):
        chs = P.subtopic_chapters(prior)
        old = raw["d1"].get(o)
        if old and old["chs"] == chs:
            out[name] = dict(chs=chs, p=old["p"], src="s9-d1")
        elif name == "d4s" and out.get("d4", {}).get("chs") == chs:
            out[name] = dict(out["d4"], src=out["d4"]["src"])
        else:
            r = eng.sub(a, chs)
            out[name] = dict(chs=chs, p=r["p"], src="new", fp=r["meta"]["fp"], pid=r["pid"])
        out[name]["prior"] = prior
    with lock:
        with open(HERE / "raw.jsonl", "a") as f:
            f.write(json.dumps(out) + "\n")


with ThreadPoolExecutor(2) as ex:
    list(ex.map(task, sorted(items)))
print("done", sum(1 for _ in open(HERE / "raw.jsonl")))
