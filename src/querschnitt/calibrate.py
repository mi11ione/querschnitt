"""Recalibration of the engine's raw confidence: isotonic regression (pool-adjacent-violators), fitted per served build on
a fixed calibration set with human labels (the S9 APS items), 2-fold cross-fitted for the reported ECE (S9c method).
Keys: `aps` (chapter read back from the subtopic, no examples), `aps-fed` (federal design with APS-labelled examples).
The file records the build it was fitted on (`build`); compose applies it only to rows of that build."""
from __future__ import annotations

import json
import random
from pathlib import Path


def pav(xs: list[float], ys: list[int]) -> list[tuple[float, float, float]]:
    blocks: list[list[float]] = []
    for x, y in sorted(zip(xs, ys)):
        blocks.append([x, x, y, 1])
        while len(blocks) > 1 and blocks[-2][2] / blocks[-2][3] > blocks[-1][2] / blocks[-1][3]:
            b = blocks.pop(); blocks[-1][1] = b[1]; blocks[-1][2] += b[2]; blocks[-1][3] += b[3]
    return [(b[0], b[1], b[2] / b[3]) for b in blocks]


def apply_map(f: list, x: float) -> float:
    for lo, hi, v in f:
        if x <= hi:
            return v
    return f[-1][2]


def ece(ps: list[float], ys: list[int], bins: int = 10) -> float:
    e, n = 0.0, len(ps)
    for b in range(bins):
        idx = [i for i, p in enumerate(ps) if (b / bins < p <= (b + 1) / bins) or (b == 0 and p == 0)]
        if idx:
            e += len(idx) / n * abs(sum(ps[i] for i in idx) / len(idx) - sum(ys[i] for i in idx) / len(idx))
    return e


def crossfit(ps: list[float], ys: list[int], seed: int = 3) -> dict:
    idx = list(range(len(ps))); random.Random(seed).shuffle(idx)
    half = len(idx) // 2; cal = [0.0] * len(ps)
    for tr, te in ((idx[:half], idx[half:]), (idx[half:], idx[:half])):
        f = pav([ps[i] for i in tr], [ys[i] for i in tr])
        for i in te:
            cal[i] = apply_map(f, ps[i])
    return dict(n=len(ps), acc=round(sum(ys) / len(ys), 4), ece_raw=round(ece(ps, ys), 4), ece_crossfit=round(ece(cal, ys), 4))


class Calibration:
    def __init__(self, maps: dict, meta: dict):
        self.maps, self.meta = maps, meta
        self.build = meta.get("build")   # the served build the maps were fitted on (system_fingerprint)

    @classmethod
    def load(cls, p: str | Path) -> "Calibration":
        d = json.loads(Path(p).read_text())
        return cls({k: [tuple(t) for t in v["map"]] for k, v in d["maps"].items()}, d)

    def apply(self, key: str, x: float) -> float | None:
        f = self.maps.get(key) or self.maps.get("aps")
        return apply_map(f, x) if f else None

    def coverage_precision(self, key: str, ps: list[float], ys: list[int]) -> list[tuple[float, float]]:
        order = sorted(range(len(ps)), key=lambda i: -ps[i])
        out, k = [], 0
        for n, i in enumerate(order, 1):
            k += ys[i]
            out.append((n / len(ps), k / n))
        return out
