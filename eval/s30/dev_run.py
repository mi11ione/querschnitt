"""S30 dev (tuning allowed; S19 packets + gold, S19/S27 rows): scope prompt (V3 first-stage wording = V1 second stage) on every
S19 packet item, the contrast check (V2) on S19 flags. Resumable: dev_raw.jsonl keyed by (pid, variant)."""
import gzip, json, sys, threading
from concurrent.futures import ThreadPoolExecutor
from common import HERE, ROOT, client, scope_prompt, two, two_contrast
SC = json.loads((HERE / "dev_scopes.json").read_text())
K = [json.loads(l) for l in open(ROOT / "eval/s19/key.jsonl")]
X = {}
want = {k["oid"] for k in K}
with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f:
    for line in f:
        x = json.loads(line)
        if int(x["id"]) in want: X[int(x["id"])] = x
c = client(HERE / "ledger.jsonl", "s30-dev")
out = HERE / "dev_raw.jsonl"
done = {(r["pid"], r["v"]) for r in map(json.loads, open(out))} if out.exists() else set()
lock = threading.Lock()
jobs = [(k, "contrast") for k in K if k["flag"]] + [(k, "scope") for k in K]   # V2 (central+scope) replaced by the contrast check before any V2 call


def run(job):
    k, v = job
    if (k["pid"], v) in done: return
    x = X[k["oid"]]; s = SC[k["topic"]]; lang = x["lang"] if x["lang"] in ("de", "fr", "it") else "de"
    if v == "contrast":
        r = two_contrast(c, s["names"], s["scope"], lang, x["title"], x["title_long"] or "")
    else:
        r = two(c, scope_prompt, s["names"], s["scope"], lang, x["title"], x["title_long"] or "")
    with lock, open(out, "a") as f:
        f.write(json.dumps(dict(pid=k["pid"], topic=k["topic"], v=v, **r)) + "\n")


with ThreadPoolExecutor(2) as tp:
    list(tp.map(run, jobs))
print("done", sum(1 for _ in open(out)), "usd", round(c.spent, 4))
