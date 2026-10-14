"""Lane rule (14 Oct, after juror round 3): route by recalibrated p vs by reading agreement, on the S16 items, 2-fold
cross-fitted isotonic calibration (seed 3, as S9c). Chosen rule: please check when recalibrated p < 0.7. Tested held out in
S25. No model calls. -> eval/lanes/results.json"""
import json, math, random
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
src = (ROOT / "eval/s16/analyze.py").read_text().split("R = dict(n=len(ids)")[0]
ns = {"__file__": str(ROOT / "eval/s16/analyze.py")}; exec(compile(src, "s16", "exec"), ns)
import sys; sys.path.insert(0, str(ROOT / "src"))
from querschnitt.calibrate import pav, apply_map  # noqa: E402
ids, pred, gold, raw, order = ns["ids"], ns["pred"], ns["gold"], ns["raw"], ns["order"]


def wil(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return [math.floor((c - h) / d * 1000) / 1000, math.ceil((c + h) / d * 1000) / 1000]


R = {}
for design, (ra, rb) in (("D4", ("d3m", "d0b")), ("D1", ("d0a", "d0b"))):
    P = pred[design]; ps = [P[o][2] for o in ids]; ys = [int(P[o][0] == gold[o]) for o in ids]
    agree = [int(order(raw[ra][o]["p"])[0] == order(raw[rb][o]["p"])[0]) for o in ids]
    n = len(ids); idx = list(range(n)); random.Random(3).shuffle(idx); half = n // 2; cal = [0.0] * n
    for tr, te in ((idx[:half], idx[half:]), (idx[half:], idx[:half])):
        f = pav([ps[i] for i in tr], [ys[i] for i in tr])
        for i in te: cal[i] = apply_map(f, ps[i])
    def st(sel):
        k = sum(ys[i] for i in sel); return dict(coverage=round(len(sel) / n, 4), precision=round(k / len(sel), 4), k=k, n=len(sel), ci=wil(k, len(sel)))
    A = [i for i in range(n) if agree[i]]
    R[design] = dict(n=n, readings_agree=st(A),
                     calibrated_same_coverage=st(sorted(range(n), key=lambda i: (-cal[i], -ps[i]))[:len(A)]),
                     calibrated_tau_0_7=st([i for i in range(n) if cal[i] >= 0.7]),
                     calibrated_tau_0_7_check=st([i for i in range(n) if cal[i] < 0.7]))
(HERE / "results.json").write_text(json.dumps(R, indent=1)); print(json.dumps(R, indent=1))
