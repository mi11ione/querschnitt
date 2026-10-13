"""Build app/data/geo.json from swiss-maps 4.7.0 (2026 boundaries; BFS GEOSTAT via Interactive Things, BSD-3 code).

Pre-projects at build time (no runtime projection): WGS84 -> LV95 (swisstopo approximate formulas, ~1 m) -> viewBox
units, Douglas-Peucker per shared arc (borders stay shared), cantons as SVG paths keyed by abbreviation, lakes and the
country outline as one path each, and {bfs: [x, y]} area centroids for all 2026 municipalities in the same units.

Usage: python app/dev/make_geo.py [src.json] [out.json ...]"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "geo-src" / "swiss-maps-4.7.0-2026-ch-combined.json"
OUTS = [HERE.parent / "data" / "geo.json", HERE.parent / "data-fixture" / "geo.json"]
W = 1000.0  # viewBox width
TOL = 0.55  # simplification tolerance in viewBox units

CANTONS = "ZH BE LU UR SZ OW NW GL ZG FR SO BS BL SH AR AI SG GR AG TG TI VD VS NE GE JU".split()


def lv95(lon: float, lat: float) -> tuple[float, float]:
    p = (lat * 3600 - 169028.66) / 10000
    l = (lon * 3600 - 26782.5) / 10000
    e = 2600072.37 + 211455.93 * l - 10938.51 * l * p - 0.36 * l * p * p - 44.54 * l ** 3
    n = 1200147.07 + 308807.95 * p + 3745.25 * l * l + 76.63 * p * p - 194.56 * l * l * p + 119.79 * p ** 3
    return e, n


def decode(topo: dict) -> list[list[tuple[float, float]]]:
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    out = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx; y += dy
            pts.append(lv95(x * sx + tx, y * sy + ty))
        out.append(pts)
    return out


def dp(pts, tol):
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts); keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        (x1, y1), (x2, y2) = pts[a], pts[b]
        dx, dy = x2 - x1, y2 - y1
        L = (dx * dx + dy * dy) ** .5 or 1e-9
        best, bi = -1, -1
        for i in range(a + 1, b):
            x0, y0 = pts[i]
            d = abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / L if (dx or dy) else ((x0 - x1) ** 2 + (y0 - y1) ** 2) ** .5
            if d > best:
                best, bi = d, i
        if best > tol:
            keep[bi] = True
            stack += [(a, bi), (bi, b)]
    return [p for p, k in zip(pts, keep) if k]


def ring(arcs, idx):
    pts = []
    for i in idx:
        seg = arcs[i] if i >= 0 else arcs[~i][::-1]
        pts.extend(seg if not pts else seg[1:])
    return pts


def polys(g):
    return [g["arcs"]] if g["type"] == "Polygon" else g["arcs"]


def area_centroid(rings):
    A = cx = cy = 0.0
    for r in rings:
        for (x0, y0), (x1, y1) in zip(r, r[1:] + r[:1]):
            c = x0 * y1 - x1 * y0
            A += c; cx += (x0 + x1) * c; cy += (y0 + y1) * c
    if abs(A) < 1e-9:
        xs = [p[0] for r in rings for p in r]; ys = [p[1] for r in rings for p in r]
        return sum(xs) / len(xs), sum(ys) / len(ys), 0.0
    return cx / (3 * A), cy / (3 * A), abs(A) / 2


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC
    outs = [Path(p) for p in sys.argv[2:]] or OUTS
    topo = json.loads(src.read_text())
    raw = decode(topo)
    xs = [p[0] for a in raw for p in a]; ys = [p[1] for a in raw for p in a]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    k = W / (x1 - x0)
    H = round((y1 - y0) * k, 1)
    to = lambda p: ((p[0] - x0) * k, (y1 - p[1]) * k)
    proj = [[to(p) for p in a] for a in raw]
    simp = [dp(a, TOL) for a in proj]
    fmt = lambda v: f"{v:.1f}".rstrip("0").rstrip(".")

    def path(g, arcs):
        s = []
        for poly in polys(g):
            for r in poly:
                pts = ring(arcs, r)
                if len(pts) < 3:
                    continue
                s.append("M" + "L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts) + "Z")
        return "".join(s)

    O = topo["objects"]
    cantons, ccent = {}, {}
    for g in O["cantons"]["geometries"]:
        ab = CANTONS[int(g["id"]) - 1]
        cantons[ab] = path(g, simp)
        best = max((area_centroid([ring(proj, r) for r in poly]) for poly in polys(g)), key=lambda t: t[2])
        ccent[ab] = [round(best[0], 1), round(best[1], 1)]
    lakes = "".join(path(g, simp) for g in O["lakes"]["geometries"])
    country = "".join(path(g, simp) for g in O["country"]["geometries"])
    cent = {}
    for g in O["municipalities"]["geometries"]:
        best = max((area_centroid([ring(proj, r) for r in poly]) for poly in polys(g)), key=lambda t: t[2])
        cent[str(g["id"])] = [round(best[0], 1), round(best[1], 1)]
    doc = dict(
        source="swiss-maps 4.7.0 (2026), Interactive Things, BSD-3-Clause; geodata: BFS GEOSTAT / swisstopo",
        projection="LV95 (swisstopo approximate formulas), scaled to viewBox", viewBox=[0, 0, W, H],
        cantons=cantons, canton_centroids=ccent, lakes=lakes, country=country, communes=cent)
    s = json.dumps(doc, separators=(",", ":"), ensure_ascii=False)
    for o in outs:
        o.parent.mkdir(parents=True, exist_ok=True)
        o.write_text(s)
    print(f"geo.json {len(s) // 1024} KB, viewBox {W} x {H}, {len(cantons)} cantons, {len(cent)} communes")


if __name__ == "__main__":
    main()
