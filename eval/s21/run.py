"""S21 (eval/PREREG-BUILD.md): Basel-Stadt with the canton's own labels as examples (2-fold by id parity). Resumable
(raw.jsonl keyed by affair id). Reuses S20 rows (runs/s20) for the permuted reading where they exist."""
import csv, gzip, json, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt import prompts as P  # noqa: E402
from querschnitt.client import Client, Endpoint  # noqa: E402
from querschnitt.compose import read_run  # noqa: E402
from querschnitt.engine import probs  # noqa: E402
from querschnitt.client import read_codes  # noqa: E402
from querschnitt.examples import ExamplePool  # noqa: E402
from querschnitt.scheme import named  # noqa: E402

BUILD = "vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840"
S = named("bs-themen"); NAMES = [o["name"]["de"] for o in S["options"]] + [S["none"]["name"]["de"]]; n = len(NAMES)
G = {r["Signatur"]: r for r in csv.DictReader(open(ROOT.parent / "data/manual/bs_100086.csv", encoding="utf-8-sig"), delimiter=";")}
X = []
with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f:
    for line in f:
        x = json.loads(line)
        if x["body"] == "BS" and x["number"] in G:
            X.append(x)
pools = {k: ExamplePool([dict(oid=x["id"], title=x["title"], chapter=NAMES.index(G[x["number"]]["Thema 1"])) for x in X if x["id"] % 2 == k]) for k in (0, 1)}
_, s20 = read_run(ROOT / "runs/s20")
out = HERE / "raw.jsonl"
done = {json.loads(l)["id"] for l in open(out)} if out.exists() else set()
ep = Endpoint.from_env(); ep.max_rate, ep.conc = 0.6, 3
c = Client(ep, ledger=str(HERE / "ledger.jsonl"), cap_usd=3.0, expect_build=BUILD, tag="s21")
lock = threading.Lock()


def ask(u, p, codes, perm):
    ch, meta = c.chat([{"role": "user", "content": u}, {"role": "assistant", "content": p}], max_tokens=1)
    return probs(read_codes(ch, codes), codes, perm), meta["fp"]


def task(x):
    if x["id"] in done:
        return
    ex = [(e["title"], e["chapter"]) for e in pools[1 - x["id"] % 2].neighbours(x)]
    u, p, codes = P.named_prompt(S, x, None, ex)
    pa, fpa = ask(u, p, codes, None)
    perm = P.named_perm(n)
    ub, pb_, _ = P.named_prompt(S, x, perm)
    r = s20.get(P.pid(ub, pb_))
    if r:
        pb, fpb, src = r["p"], r["meta"]["fp"], "s20"
    else:
        pb, fpb = ask(ub, pb_, codes, perm); src = "new"
    with lock:
        with open(out, "a") as f:
            f.write(json.dumps(dict(id=x["id"], pa=pa, pb=pb, fp=[fpa, fpb], b_src=src, ex=[e[1] for e in ex])) + "\n")


with ThreadPoolExecutor(3) as tp:
    list(tp.map(task, sorted(X, key=lambda x: x["id"])))
print("done", sum(1 for _ in open(out)))
