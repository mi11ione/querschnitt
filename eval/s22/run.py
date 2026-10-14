"""S22 (eval/PREREG-BUILD.md): Italian D1 on the S9 items. Resumable (raw.jsonl keyed by oid)."""
import gzip, json, re, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt import prompts as P  # noqa: E402
from querschnitt.client import Client, Endpoint  # noqa: E402
from querschnitt.engine import Engine, mean_p  # noqa: E402
from querschnitt.data import clean  # noqa: E402
BUILD = "vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840"
S9 = Path("/Users/mi11ion/Desktop/hackapertus/bern/ideation2/spikes/s9-aps")
items = {x["oid"]: x for x in json.load(open(S9 / "data/items.json"))}
A, T = {}, {}
for l in gzip.open(ROOT.parent / "data/opd-new/affairs.ndjson.gz", "rt"):
    a = json.loads(l)
    if a["id"] in items: A[a["id"]] = a
for l in gzip.open(ROOT.parent / "data/opd-new/texts/texts_CHE.ndjson.gz", "rt"):
    r = json.loads(l)
    if r["affair_id"] in items and (r.get("type_it") or "").lower().startswith("testo depositato"):
        T[r["affair_id"]] = (r.get("text_it"), r.get("text_fr"))
X = []
for o, a in A.items():
    if a.get("title_it") and a["title_it"] != a.get("title_fr"):
        ti, tf = T.get(o, (None, None))
        text = clean(ti)[:1500] if ti and ti != tf else ""
        X.append(dict(id=o, title=clean(a["title_it"]), title_long=clean(a.get("title_long_it")), text=text, lang="it"))
out = HERE / "raw.jsonl"
done = {json.loads(l)["oid"] for l in open(out)} if out.exists() else set()
ep = Endpoint.from_env(); ep.max_rate, ep.conc = 0.6, 3
eng = Engine(Client(ep, ledger=str(HERE / "ledger.jsonl"), cap_usd=3.0, expect_build=BUILD, tag="s22"))
lock = threading.Lock()


def task(x):
    if x["id"] in done: return
    r1 = eng.ch1(x, P.chapter_prompt(x, list(range(25))) + (None,)); r2 = eng.ch2(x)
    chs = P.subtopic_chapters(mean_p(r1["p"], r2["p"])); rs = eng.sub(x, chs)
    with lock:
        with open(out, "a") as f:
            f.write(json.dumps(dict(oid=x["id"], text=bool(x["text"]), p1=r1["p"], p2=r2["p"], chs=chs, psub=rs["p"],
                                    fp=[r1["meta"]["fp"], r2["meta"]["fp"], rs["meta"]["fp"]])) + "\n")


with ThreadPoolExecutor(3) as tp:
    list(tp.map(task, X))
print("done", sum(1 for _ in open(out)), "of", len(X))
