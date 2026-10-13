"""Reuse the S8 census rows ("Digitalisierung" yes/no, same prompt bytes, same build) in a corpus-run store.
A row is imported only when the prompt built from today's input is byte-identical to the S8 prompt (pid match).
Usage: python tools/seed_s8.py <inputs.jsonl.gz> <run dir> <s8 dir>"""
import gzip, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from querschnitt import prompts as P
from querschnitt.scheme import adhoc

inp, out, s8 = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
T = adhoc("digitalisierung")
st = json.loads((out / "state.json").read_text())
bd = out / st["lock"]["key"]
X = {}
with gzip.open(inp, "rt") as f:
    for l in f:
        x = json.loads(l); X[x["id"]] = x
S8I = {x["id"]: x for x in json.load(open(s8 / "items_cache.json"))}
have = set()
fn = bd / "yn_digitalisierung.jsonl"
if fn.exists():
    have = {json.loads(l)["pid"] for l in open(fn)}
n = skip = 0
with open(fn, "a") as o:
    for order in "ab":
        for l in open(s8 / "raw" / f"{order}.jsonl"):
            r = json.loads(l); x = X.get(r["id"]); s = S8I.get(r["id"])
            if not x or not s or r["fp"] != st["lock"]["fp"]:
                skip += 1; continue
            u, p = P.yesno_prompt(T, x["lang"], x["title"], x["title_long"], order)
            u8, p8 = P.yesno_prompt(T, s["lang"], s["title"], s["title_long"], order)
            if (u, p) != (u8, p8):
                skip += 1; continue
            pid = P.pid(u, p)
            if pid in have:
                continue
            row = dict(step=f"yn:{T['id']}:{order}", pid=pid, codes=r["codes"], p_yes=r["p_yes"],
                       meta=dict(model=r["served"], fp=r["fp"], pt=r.get("pt"), usd=None, lat=r.get("latency"), http=r.get("http"),
                                 endpoint="publicai", src="s8"), aid=r["id"], ih=x["input_hash"], ts=r["ts"])
            o.write(json.dumps(row, ensure_ascii=False) + "\n"); have.add(pid); n += 1
print("imported", n, "skipped", skip)
