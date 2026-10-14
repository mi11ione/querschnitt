"""Topic rows of the production pipeline for a list of affair ids (default: the 1,357 S9 APS-labelled affairs), composed from
the corpus run dirs exactly as the export does → eval/prod_gold/topics.jsonl.gz, so `make eval` scores what ships.
Usage: python eval/prod_gold/rows.py [ids.txt]"""
import gzip, json, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt.compose import decide, read_run, topic_rows  # noqa: E402
from querschnitt.engine import Engine  # noqa: E402
from querschnitt.examples import ExamplePool  # noqa: E402
from querschnitt.calibrate import Calibration  # noqa: E402
ids = {int(x) for x in Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "runs/pipeline/ids_s9_gold.txt").read_text().split()}
lock, rows = read_run(*[ROOT / "runs" / r for r in ("main", "side") if (ROOT / "runs" / r / "state.json").exists()])
eng = Engine(None, ExamplePool.load(ROOT / "data/eval/aps_pool.jsonl"))
cal = Calibration.load(ROOT / "eval/calibration.json")
now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()); n = k = 0
with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f, gzip.open(HERE / "topics.jsonl.gz", "wt") as o, \
        gzip.open(HERE / "inputs.jsonl.gz", "wt") as oi:
    for line in f:
        x = json.loads(line)
        if x["id"] not in ids:
            continue
        n += 1; oi.write(line)
        d = decide(x, rows, eng.ch1_prompt, [])
        for r in topic_rows(x, d, lock, lambda s, v, d=d: cal.apply("aps-fed" if d.get("aps", {}).get("examples") else "aps", v), now):
            o.write(json.dumps(r, ensure_ascii=False) + "\n"); k += 1
print("affairs", n, "rows", k)
