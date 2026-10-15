"""S25b (eval/PREREG-BUILD.md): plain list prompting (S9 D0) on the S25 items — the identity-order reading without examples
(d0a); d0b is the S25 run's second reading. Resumable (raw.jsonl keyed by oid). Analysis: eval/s25b/analyze.py."""
import gzip, json, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt import prompts as P  # noqa: E402
from querschnitt.client import Client, Endpoint  # noqa: E402
from querschnitt.engine import Engine  # noqa: E402
BUILD = "vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840"
ids = {json.loads(l)["oid"] for l in open(ROOT / "eval/s25/items.jsonl")}
X = [json.loads(l) for l in gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") if json.loads(l)["id"] in ids]
out = HERE / "raw.jsonl"
done = {json.loads(l)["oid"] for l in open(out)} if out.exists() else set()
ep = Endpoint.from_env(); ep.max_rate, ep.conc = 0.6, 3
eng = Engine(Client(ep, ledger=str(HERE / "ledger.jsonl"), cap_usd=2.0, expect_build=BUILD, tag="s25b"))
lock = threading.Lock()


def task(a):
    if a["id"] in done: return
    u, p = P.chapter_prompt(a, list(range(25)))   # no examples, identity order: S9 d0a
    r = eng.ch1(a, (u, p, None))
    with lock:
        with open(out, "a") as f:
            f.write(json.dumps(dict(oid=a["id"], pid=r["pid"], p=r["p"], fp=r["meta"]["fp"])) + "\n")


with ThreadPoolExecutor(3) as tp:
    list(tp.map(task, X))
print("done", sum(1 for _ in open(out)), "of", len(X))
