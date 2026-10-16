"""The shipped lane and calibration beyond the set they were fitted on (computed after the results, not pre-registered; juror
round 9). No model calls. -> eval/lanes/heldout.json
(1) calibration held out: the recalibrated p of the 927 S25 decisions (`eval/s25/decisions.jsonl`, map fitted on S16 only) vs
    whether the APS editors agree — ECE (10 bins, calibrate.ece, the definition of the in-sample 0.0211) and the bins;
(2) the please-check share of the shipped export (`app/data/affairs.json`, the APS chapter lane) by level and by language, as
    counts from the export named in `export`."""
import collections, json, math, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt.calibrate import ece  # noqa: E402


def wil(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return [math.floor((c - h) / d * 1000) / 1000, math.ceil((c + h) / d * 1000) / 1000]


trunc = lambda v, d=4: math.floor(v * 10 ** d) / 10 ** d
share = lambda k, n: dict(k=k, n=n, value=trunc(k / n), ci=wil(k, n)) if n else None

D = [json.loads(l) for l in open(ROOT / "eval/s25/decisions.jsonl")]
D = [d for d in D if d.get("p_cal") is not None]
ps = [d["p_cal"] for d in D]; ys = [int(d["ch"] == d["gold"]) for d in D]
bins = []
for b in range(10):
    idx = [i for i, p in enumerate(ps) if (b / 10 < p <= (b + 1) / 10) or (b == 0 and p == 0)]
    if idx:
        bins.append(dict(bin=f"{b / 10:.1f}–{(b + 1) / 10:.1f}", n=len(idx), mean_p=trunc(sum(ps[i] for i in idx) / len(idx)),
                         **{"correct": share(sum(ys[i] for i in idx), len(idx))}))
steps = collections.defaultdict(list)   # the isotonic map is a step function: accuracy at each of its larger steps
for p, y in zip(ps, ys): steps[p].append(y)
R = dict(note="computed after the results (juror round 9), not pre-registered; no model calls",
         calibration_heldout=dict(n=len(D), ece=trunc(ece(ps, ys)), in_sample_ece_reported=0.0211, bins=bins,
                                  largest_steps=[dict(p_cal=p, **share(sum(v), len(v))) for p, v in
                                                 sorted(steps.items(), key=lambda x: -len(x[1]))[:5]]))

A = json.load(open(ROOT / "app/data/affairs.json"))["cols"]; M = json.load(open(ROOT / "app/data/meta.json"))
bodies = json.load(open(ROOT / "app/data/bodies.json"))
lvl = {}
for b in (bodies if isinstance(bodies, list) else bodies.get("bodies", bodies.values() if isinstance(bodies, dict) else [])):
    if isinstance(b, dict) and b.get("key"):
        lvl[b["key"]] = b.get("level")
by_l, by_lang, by_ll = (collections.defaultdict(lambda: [0, 0]) for _ in range(3))
for i, ln in enumerate(A["lane"]):
    if ln is None:
        continue
    L = "federal" if A["body"][i] == "CHE" else (lvl.get(A["body"][i]) or "?")
    by_l[L][0] += ln; by_l[L][1] += 1
    by_lang[A["lang"][i] or "?"][0] += ln; by_lang[A["lang"][i] or "?"][1] += 1
    by_ll[f'{L} · {A["lang"][i] or "?"}'][0] += ln; by_ll[f'{L} · {A["lang"][i] or "?"}'][1] += 1
R["please_check_share"] = dict(export=M.get("generated_at"),
                               by_level={k: share(*v) for k, v in sorted(by_l.items())},
                               by_language={k: share(*v) for k, v in sorted(by_lang.items()) if v[1] >= 30},
                               by_level_and_language={k: share(*v) for k, v in sorted(by_ll.items()) if v[1] >= 30},
                               all=share(sum(v[0] for v in by_l.values()), sum(v[1] for v in by_l.values())))
(HERE / "heldout.json").write_text(json.dumps(R, indent=1, ensure_ascii=False) + "\n")
print(json.dumps(R, indent=1, ensure_ascii=False))
