"""S29 (eval/PREREG-BUILD.md): Ticino Gran Consiglio lead department (OPD leading_department, position 1) vs the
ti-dipartimenti scheme file, Italian. No model calls. Reads runs/s29 and eval/s29/items.jsonl -> eval/s29/results.json
Point values truncated (never rounded up) to 4 decimals; Wilson 95% bounds rounded outward (floor/ceil) to 4 decimals."""
import collections, gzip, json, math, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt import prompts as P  # noqa: E402
from querschnitt.compose import read_run  # noqa: E402
from querschnitt.scheme import named  # noqa: E402

BUILD = "vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840"
S = named("ti-dipartimenti")
NAMES = [o["name"]["it"] for o in S["options"]] + [S["none"]["name"]["it"]]
DEPTS = set(NAMES[1:6])
n = len(NAMES)
lock, rows = read_run(ROOT / "runs/s29")
assert lock["fp"] == BUILD, lock
ITEMS = [json.loads(l) for l in open(HERE / "items.jsonl")]
IDS = {r["id"] for r in ITEMS}
X = {}
with gzip.open(ROOT.parent / "data/inputs.jsonl.gz", "rt") as f:
    for line in f:
        x = json.loads(line)
        if x["id"] in IDS:
            X[x["id"]] = x
KW = json.loads((HERE / "keywords_frozen.json").read_text())["stems"]


def tr(v, d=4):
    return math.floor(v * 10 ** d) / 10 ** d


def wilson(k, m, z=1.96):
    if not m:
        return [0.0, 1.0]
    p = k / m; dd = 1 + z * z / m; c = p + z * z / (2 * m); h = z * ((p * (1 - p) / m + z * z / (4 * m * m)) ** 0.5)
    return [math.floor((c - h) / dd * 1e4) / 1e4, math.ceil((c + h) / dd * 1e4) / 1e4]


def prop(k, m):
    return dict(k=k, n=m, acc=tr(k / m) if m else None, ci=wilson(k, m))


res, missing, other_build = [], 0, 0
for it in ITEMS:
    x = X[it["id"]]
    assert x["input_hash"] == it["input_hash"], it["id"]
    ra = rows.get(P.pid(*P.named_prompt(S, x)[:2]))
    if not ra:
        missing += 1; continue
    rb = None
    if max(ra["p"]) < 0.9:
        rb = rows.get(P.pid(*P.named_prompt(S, x, P.named_perm(n))[:2]))
        if not rb:
            missing += 1; continue
    if any(r["meta"]["fp"] != BUILD for r in (ra, rb) if r):
        other_build += 1; continue
    pm = [(a + b) / 2 for a, b in zip(ra["p"], rb["p"])] if rb else ra["p"]
    rk = sorted(range(n), key=lambda i: -pm[i])
    lane = "please_check" if (rb and max(range(n), key=lambda i: ra["p"][i]) != max(range(n), key=lambda i: rb["p"][i])) else "readings_agree"
    res.append(dict(it, pred=NAMES[rk[0]], top=[NAMES[i] for i in rk[:3]], p=pm[rk[0]], lane=lane, title=x["title"],
                    mass=[r["meta"].get("mass") for r in (ra, rb) if r]))


def kw_pred(title, forder):
    t = title.lower(); sc = {u: sum(s in t for s in st) for u, st in KW.items()}
    best = max(sc.values())
    return forder[0] if best == 0 else next(u for u in forder if sc.get(u, 0) == best)


def block(sub, seed=2026):
    N = len(sub)
    freq = collections.Counter(r["gold"] for r in sub)
    forder = [g for g, _ in freq.most_common()] + [u for u in NAMES if u not in freq]
    k1 = sum(r["pred"] == r["gold"] for r in sub)
    k2 = sum(r["gold"] in r["top"][:2] for r in sub); k3 = sum(r["gold"] in r["top"][:3] for r in sub)
    kws = [kw_pred(r["title"], forder) for r in sub]
    kk = sum(k == r["gold"] for k, r in zip(kws, sub)); km = freq[forder[0]]
    out = dict(n=N, top1=prop(k1, N), top2=prop(k2, N), top3=prop(k3, N),
               majority=dict(label=forder[0], **prop(km, N)), keyword=prop(kk, N),
               gold_dist=dict(freq.most_common()), pred_dist=dict(collections.Counter(r["pred"] for r in sub).most_common()))
    va = [int(r["pred"] == r["gold"]) for r in sub]; vb = [int(k == r["gold"]) for k, r in zip(kws, sub)]
    rng = random.Random(seed); ds = []
    for _ in range(2000):
        s = [rng.randrange(N) for _ in range(N)]; ds.append(sum(va[i] - vb[i] for i in s) / N)
    ds.sort()
    out["minus_keyword"] = dict(diff=tr((sum(va) - sum(vb)) / N), ci=[math.floor(ds[50] * 1e4) / 1e4, math.ceil(ds[1949] * 1e4) / 1e4],
                                note="paired bootstrap 2,000, percentile, random.Random(2026); bounds rounded outward")
    for ln in ("readings_agree", "please_check"):
        s = [r for r in sub if r["lane"] == ln]
        out[f"lane_{ln}"] = dict(share=tr(len(s) / N) if N else None, **prop(sum(r["pred"] == r["gold"] for r in s), len(s)))
    out["by_type"] = {t: prop(sum(r["pred"] == r["gold"] for r in sub if r["type"] == t), c)
                      for t, c in collections.Counter(r["type"] for r in sub).most_common()}
    out["by_gold"] = {g: prop(sum(r["pred"] == g for r in sub if r["gold"] == g), c) for g, c in freq.most_common()}
    conf = collections.defaultdict(collections.Counter)
    for r in sub:
        conf[r["gold"]][r["pred"]] += 1
    out["confusion_gold_to_pred"] = {g: dict(c.most_common()) for g, c in conf.items()}
    return out


prim = [r for r in res if not r["named_in_input"]]
R = dict(test="S29", build=lock["fp"], model=lock["model"], scheme="ti-dipartimenti", options=n,
         n_items=len(ITEMS), n_scored=len(res), missing=missing, other_build=other_build,
         n_primary_items=sum(not r["named_in_input"] for r in ITEMS),
         primary=block(prim),
         secondary_all_items=block(res),
         secondary_gold_in_5_departments=block([r for r in prim if r["gold"] in DEPTS]),
         second_order_share=tr(sum(len(r["mass"]) == 2 for r in res) / len(res)) if res else None,
         note="primary = items whose input block names none of the six units (eval/s29/items.py); point values truncated, "
              "Wilson 95% bounds rounded outward, 4 decimals")
(HERE / "results.json").write_text(json.dumps(R, indent=1, ensure_ascii=False) + "\n")
p = R["primary"]
print(json.dumps(dict(n=p["n"], top1=p["top1"], top2=p["top2"], top3=p["top3"], majority=p["majority"], keyword=p["keyword"],
                      minus_keyword=p["minus_keyword"], all_items_top1=R["secondary_all_items"]["top1"],
                      depts5_top1=R["secondary_gold_in_5_departments"]["top1"], missing=missing, other_build=other_build,
                      lanes={k: p[k] for k in p if k.startswith("lane_")}), indent=1, ensure_ascii=False))
