"""S27 (eval/PREREG-BUILD.md, with amendment): verification question on every S19 flag; resumable (raw.jsonl by pid)."""
import gzip, json, math, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt import prompts as P  # noqa: E402
from querschnitt.client import Client, Endpoint, read_codes  # noqa: E402
from querschnitt.scheme import adhoc  # noqa: E402
K = {json.loads(l)["pid"]: json.loads(l) for l in open(ROOT / "eval/s19/key.jsonl")}
X = {}
with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f:
    want = {k["oid"] for k in K.values() if k["flag"]}
    for line in f:
        x = json.loads(line)
        if x["id"] in want: X[x["id"]] = x
BUILD = "vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840"
ep = Endpoint.from_env(); ep.max_rate, ep.conc = 0.8, 3
c = Client(ep, ledger=str(HERE / "ledger.jsonl"), cap_usd=2.0, expect_build=BUILD, tag="s27")
out = HERE / "raw.jsonl"; done = {json.loads(l)["pid"] for l in open(out)} if out.exists() else set()
lock = threading.Lock()


def ask(t, x, order):
    u, p = P.verify_prompt(t, x["lang"], x["title"], x["title_long"], order)
    ch, meta = c.chat([{"role": "user", "content": u}, {"role": "assistant", "content": p}], max_tokens=1)
    d = read_codes(ch, ["A", "B"]); pa, pb = math.exp(d.get("A", -50)), math.exp(d.get("B", -50))
    return (pa if order == "a" else pb) / (pa + pb), meta["fp"]


def run(pid):
    if pid in done: return
    k = K[pid]; x = X[k["oid"]]; t = adhoc(k["topic"])
    pa, fp = ask(t, x, "a"); pb = ask(t, x, "b")[0] if 0.1 < pa < 0.9 else None
    pm = (pa + pb) / 2 if pb is not None else pa
    with lock:
        with open(out, "a") as f:
            f.write(json.dumps(dict(pid=pid, topic=k["topic"], p_verify=pm, keep=pm >= 0.5, fp=fp)) + "\n")


with ThreadPoolExecutor(3) as tp:
    list(tp.map(run, [p for p, k in K.items() if k["flag"]]))
print("done", sum(1 for _ in open(out)))
