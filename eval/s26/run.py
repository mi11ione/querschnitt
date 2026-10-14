"""S26 (eval/PREREG-BUILD.md): editor decisions as examples on the S19 topics. 30 judged items per topic (random.Random(26)
over the pid-sorted packet) become the topic's examples; every other packet item is re-scored with the shipped yes/no rule
and the 4 nearest examples (examples.topic_examples). Resumable (raw.jsonl keyed by pid)."""
import gzip, json, random, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt.client import Client, Endpoint  # noqa: E402
from querschnitt.engine import Engine, need_yn_b  # noqa: E402
from querschnitt.examples import topic_examples  # noqa: E402
from querschnitt.scheme import adhoc  # noqa: E402
S19 = ROOT / "eval/s19"
K = {json.loads(l)["pid"]: json.loads(l) for l in open(S19 / "key.jsonl")}
def rd(p):
    d = {}
    if (S19 / p).exists():
        for line in (S19 / p).read_text().splitlines():
            x = line.split("\t")
            if len(x) >= 2 and x[1].strip(): d[x[0]] = x[1].strip().upper()[:1]
    return d
A, B, C = rd("ann_A.tsv"), rd("ann_B.tsv"), rd("ann_C.tsv")
gold = lambda p: A[p] if A.get(p) in ("Y", "N") and A.get(p) == B.get(p) else C.get(p)
X = {}
with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f:
    want = {k["oid"] for k in K.values()}
    for line in f:
        x = json.loads(line)
        if x["id"] in want: X[x["id"]] = x
BUILD = "vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840"
ep = Endpoint.from_env(); ep.max_rate, ep.conc = 0.8, 3
eng = Engine(Client(ep, ledger=str(HERE / "ledger.jsonl"), cap_usd=2.0, expect_build=BUILD, tag="s26"))
out = HERE / "raw.jsonl"; done = {json.loads(l)["pid"] for l in open(out)} if out.exists() else set()
lock = threading.Lock(); tasks = []; split = {}
for slug in ("wolf", "hitze", "ki-schule"):
    pids = sorted(p for p, k in K.items() if k["topic"] == slug and gold(p) in ("Y", "N"))
    ed = random.Random(26).sample(pids, 30)
    split[slug] = dict(editor=ed, test=[p for p in pids if p not in set(ed)])
    t = dict(adhoc(slug)); t["examples"] = [dict(affair_id=K[p]["oid"], title=X[K[p]["oid"]]["title"], match=gold(p) == "Y") for p in ed]
    tasks += [(slug, t, p) for p in split[slug]["test"]]
(HERE / "split.json").write_text(json.dumps(split))


def run(task):
    slug, t, p = task
    if p in done: return
    x = X[K[p]["oid"]]; ex = topic_examples(t, x)
    ra = eng.yn(t, x, "a", ex); rb = eng.yn(t, x, "b", ex) if need_yn_b(ra["p_yes"]) else None
    pm = (ra["p_yes"] + rb["p_yes"]) / 2 if rb else ra["p_yes"]
    with lock:
        with open(out, "a") as f:
            f.write(json.dumps(dict(pid=p, topic=slug, p=pm, flag=pm >= 0.5, n_ex=len(ex or []), fp=ra["meta"]["fp"])) + "\n")


with ThreadPoolExecutor(3) as tp:
    list(tp.map(run, tasks))
print("done", sum(1 for _ in open(out)), "of", len(tasks))
