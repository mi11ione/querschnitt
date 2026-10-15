"""S30 test: period, population and the arms' flag rules (shared by run.py, flags.py, analyze.py). No model calls."""
import gzip, json
from common import HERE, ROOT

PERIOD = ("2026-03-16", "2026-03-31")
CUT = 0.5


def population():
    X = []
    with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f:
        for line in f:
            x = json.loads(line)
            if x.get("title") and PERIOD[0] <= (x.get("date") or "") <= PERIOD[1]:
                x["lang"] = x["lang"] if x.get("lang") in ("de", "fr", "it") else "de"
                x["title_long"] = x.get("title_long") or ""
                X.append(x)
    return sorted(X, key=lambda x: x["id"])


def _p(r):
    return r is not None and r["p"] >= CUT


# g(step) -> the raw row of that step for one (affair, topic), or None
ARMS = {
    "shipped_yn": lambda g: _p(g("yn")),                      # the yes/no step alone (S19 design)
    "shipped": lambda g: _p(g("yn")) and _p(g("vf")),         # the product now: yes/no, kept by the S27 check
    "variant": lambda g: _p(g("yn")) and _p(g("vf")) and _p(g("sc")),   # dev V4: + the generated-scope check
    "yn_sc": lambda g: _p(g("yn")) and _p(g("sc")),           # secondary (dev V1): yes/no + scope check, no S27 check
}
