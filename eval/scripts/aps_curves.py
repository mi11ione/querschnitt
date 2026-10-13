"""Coverage-precision curves for the shipped APS designs, recomputed from S9 raw logs (no model calls, no network).
Rules copied from ideation2/spikes/s9-aps/scripts/analyze.py (D1 = read-back, D3 = five APS-labelled examples):
confidence = top-1 probability (D3: geometric mean of d3m and d0b) or the read-back mass share (D1); items ranked by raw
confidence, descending, stable over ascending oid; coverage c keeps the first max(1, round(c*n)) items; precision = top-1
chapter equals the APS editors' chapter; Wilson 95%. p_cal_insample = isotonic fit on all 1,357 items (in-sample, for the
dial only; the cross-fitted ECE is S9c). Output: eval/aps_curves.json."""
import json, math, os
HB = "/Users/mi11ion/Desktop/hackapertus/bern"
S9 = f"{HB}/ideation2/spikes/s9-aps"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aps_curves.json")

def load(path):
    out = {}
    for l in open(path):
        r = json.loads(l); out[r["oid"]] = r
    return out

def geo2(pa, pb):  # s9lib.geo2 verbatim
    g = [math.exp((math.log(max(x, 1e-12)) + math.log(max(y, 1e-12))) / 2) for x, y in zip(pa, pb)]
    s = sum(g); return [v / s for v in g]

def wilson(k, n, z=1.96):  # s1lib.wilson verbatim
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 3), round(c + h, 3)]

def pav(xs, ys):  # S9c calib.py verbatim
    pts = sorted(zip(xs, ys)); blocks = []
    for x, y in pts:
        blocks.append([x, x, y, 1])
        while len(blocks) > 1 and blocks[-2][2] / blocks[-2][3] > blocks[-1][2] / blocks[-1][3]:
            b = blocks.pop(); blocks[-1][1] = b[1]; blocks[-1][2] += b[2]; blocks[-1][3] += b[3]
    return [(b[0], b[1], b[2] / b[3]) for b in blocks]

def apply(f, x):
    for lo, hi, v in f:
        if x <= hi: return v
    return f[-1][2]

items = {it["oid"]: it for it in json.load(open(f"{S9}/data/items.json"))}
raw = {ph: load(f"{S9}/raw/{ph}.jsonl") for ph in ("d0a", "d0b", "d1", "d3m")}
order = lambda p: sorted(range(len(p)), key=lambda i: -p[i])

def d1(o):
    a, b = raw["d0a"][o]["p"], raw["d0b"][o]["p"]; PA = [(x + y) / 2 for x, y in zip(a, b)]
    r = raw["d1"][o]; sc = {(c, s): r["p"][i] * PA[c] for i, (c, s) in enumerate(r["opts"])}; tot = sum(sc.values()) or 1
    best = max(sc, key=sc.get); return best[0], sum(v for (c, s), v in sc.items() if c == best[0]) / tot

def d3(o):
    p = geo2(raw["d3m"][o]["p"], raw["d0b"][o]["p"]); k = order(p)[0]; return k, p[k]

def curve(fn):
    ids = sorted(o for o in items if o in raw["d0a"] and o in raw["d0b"] and o in raw["d1"] and o in raw["d3m"])
    pred = {o: fn(o) for o in ids}
    hit = {o: int(pred[o][0] == items[o]["chapter"]) for o in ids}
    f = pav([pred[o][1] for o in ids], [hit[o] for o in ids])
    srt = sorted(ids, key=lambda o: -pred[o][1])
    pts = []
    grid = sorted({round(x / 100, 2) for x in range(5, 101, 5)})
    for c in grid:
        k = max(1, round(c * len(srt))); sel = srt[:k]; h = sum(hit[o] for o in sel)
        thr = pred[sel[-1]][1]
        pts.append(dict(coverage=c, n=k, correct=h, precision=round(h / k, 4), ci=wilson(h, k),
                        p_raw_threshold=round(thr, 4), p_cal_insample=round(apply(f, thr), 3)))
    return dict(n=len(ids), points=pts)

out = dict(
    source=dict(items="ideation2/spikes/s9-aps/data/items.json", raw=["ideation2/spikes/s9-aps/raw/d0a.jsonl", "ideation2/spikes/s9-aps/raw/d0b.jsonl",
                "ideation2/spikes/s9-aps/raw/d1.jsonl", "ideation2/spikes/s9-aps/raw/d3m.jsonl"],
                rules="ideation2/spikes/s9-aps/scripts/analyze.py reliability(); ideation2/spikes/s9c-calibration/calib.py d1()/d3()/pav()"),
    build="vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840",
    aps_d3=curve(d3), aps_d1=curve(d1))
json.dump(out, open(OUT, "w"), indent=1)
for k in ("aps_d3", "aps_d1"):
    print(k, [(p["coverage"], p["n"], p["precision"], p["ci"]) for p in out[k]["points"] if p["coverage"] in (0.5, 0.7, 0.9, 1.0)])
