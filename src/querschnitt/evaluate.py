"""`make eval GOLD=file.csv`: score any labelled list against the stored topic rows.

Gold CSV (header row; `,` or `;` or tab):
  affair_id                       a list of positives (a DVS / POLITmonitor export) for one binary topic (--scheme,
                                  default adhoc/digitalisierung): recall, and the misses by level
  affair_id,label                 label 1/0, yes/no, ja/nein, true/false → binary (accuracy, precision, recall, F1);
                                  label = a code (`1.7.2.`, `aps:1.7.2.`, `aps:kw:…`, chapter index 0–24) → multi-class
  affair_id,scheme,code           multi-class per scheme (adhoc `…:yes/no` codes are scored as binary)
Prediction = the latest machine row (provenance inferred) at rank 1 of that scheme and level; editor rows are never
scored as predictions. Gold affairs without a machine row are counted as `not scored` and left out of every rate.
Proportions carry Wilson 95% intervals; F1 a percentile bootstrap (1,000 resamples of the scored items, seed 7).
Breakdowns per parliament level, language and body come from the loaded affair summaries."""
from __future__ import annotations

import argparse
import collections
import csv
import io
import json
import math
import random
import sys
from pathlib import Path

from .scheme import APS
from .store import Store

TRUE = {"1", "yes", "y", "ja", "j", "true", "t", "oui", "si", "sì", "x", "+"}
FALSE = {"0", "no", "n", "nein", "false", "f", "non", "-", ""}
ID_COLS = ("affair_id", "id", "oid", "affair", "geschaeft_id", "opd_id")


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float] | tuple[None, None]:
    """Wilson score interval for k successes in n."""
    if n == 0:
        return None, None
    ph = k / n; d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def _down(v: float, d: int) -> float:
    return math.floor(v * 10 ** d + 1e-9) / 10 ** d


def _up(v: float, d: int) -> float:
    return math.ceil(v * 10 ** d - 1e-9) / 10 ** d


def prop(k: int, n: int) -> dict:
    """Point truncated, interval rounded outward (never rounded up / inward): the docs' rule, so `make eval` prints what
    the README says."""
    lo, hi = wilson(k, n)
    return dict(k=k, n=n, value=_down(k / n, 4) if n else None, ci=[_down(lo, 4), _up(hi, 4)] if n else None)


def read_gold(path: str | Path) -> tuple[list[str], list[dict]]:
    text = Path(path).read_text(encoding="utf-8-sig")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.DictReader(io.StringIO(text), dialect=dialect))
    cols = [c.strip().lower() for c in (rows[0].keys() if rows else [])]
    out = []
    for r in rows:
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        idc = next((c for c in ID_COLS if c in r), None)
        if idc is None:
            raise SystemExit(f"{path}: no affair id column (one of {', '.join(ID_COLS)}); columns: {cols}")
        if not r[idc].isdigit():
            continue
        r["affair_id"] = int(r[idc])
        out.append(r)
    return cols, out


def norm_code(scheme: str, v: str) -> str:
    v = v.strip()
    if scheme == "aps":
        if v.isdigit() and int(v) < 25:
            return APS.codes[int(v)]
        return v if v.startswith("aps:") else f"aps:{v}"
    if scheme.startswith("adhoc/"):
        lv = v.lower().rsplit(":", 1)[-1]
        return f"{scheme}:{'yes' if lv in TRUE else 'no' if lv in FALSE else lv}"
    return v


def predictions(store: Store, scheme: str, level: int, ids: list[int], ranks: int = 3) -> dict[int, list[dict]]:
    """affair → latest machine rows of (scheme, level) by rank (current rows first, else the latest closed ones)."""
    out: dict[int, dict[int, dict]] = collections.defaultdict(dict)
    for i in range(0, len(ids), 900):
        part = ids[i:i + 900]
        q = (f"SELECT affair_id, code, rank, p, p_raw, lane, valid_to, row_id FROM topics WHERE provenance = 'inferred' "
             f"AND scheme = ? AND level = ? AND rank <= ? AND affair_id IN ({', '.join('?' * len(part))})")
        for r in store.all(q, [scheme, level, ranks] + part):
            cur = out[r["affair_id"]].get(r["rank"])
            key = (r["valid_to"] is None, r["row_id"])
            if cur is None or key > (cur["valid_to"] is None, cur["row_id"]):
                out[r["affair_id"]][r["rank"]] = r
    return {a: [d[k] for k in sorted(d)] for a, d in out.items()}


def f1_boot(items: list[tuple[bool, bool]], n: int = 1000, seed: int = 7) -> list[float] | None:
    if not items:
        return None
    rng = random.Random(seed); vals = []
    for _ in range(n):
        s = [items[rng.randrange(len(items))] for _ in items]
        tp = sum(g and p for g, p in s); fp = sum(p and not g for g, p in s); fn = sum(g and not p for g, p in s)
        vals.append(2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0)
    vals.sort()
    return [_down(vals[int(0.025 * n)], 4), _up(vals[int(0.975 * n) - 1], 4)]


def binary(items: list[tuple[bool, bool]], has_neg: bool) -> dict:
    tp = sum(g and p for g, p in items); fp = sum(p and not g for g, p in items)
    fn = sum(g and not p for g, p in items); tn = sum(not g and not p for g, p in items)
    out = dict(n=len(items), tp=tp, fp=fp, fn=fn, tn=tn, recall=prop(tp, tp + fn))
    if has_neg:
        f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else None
        out.update(accuracy=prop(tp + tn, len(items)), precision=prop(tp, tp + fp),
                   f1=dict(value=_down(f1, 4) if f1 is not None else None, ci=f1_boot(items)))
    return out


def multiclass(items: list[tuple[str, str, list[str]]]) -> dict:
    """items: (gold, predicted rank 1, predicted ranks 1–3)."""
    n = len(items)
    ok = sum(g == p for g, p, _ in items)
    top3 = sum(g in r for g, _, r in items)
    classes = sorted({g for g, _, _ in items} | {p for _, p, _ in items})
    per = {}
    for c in classes:
        tp = sum(g == c and p == c for g, p, _ in items); fp = sum(p == c and g != c for g, p, _ in items)
        fn = sum(g == c and p != c for g, p, _ in items)
        pr = tp / (tp + fp) if tp + fp else None; rc = tp / (tp + fn) if tp + fn else None
        f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else None
        per[c] = dict(support=tp + fn, precision=pr and _down(pr, 4), recall=rc and _down(rc, 4), f1=f1 and _down(f1, 4),
                      precision_ci=(lambda w: [_down(w[0], 4), _up(w[1], 4)])(wilson(tp, tp + fp)) if tp + fp else None,
                      recall_ci=(lambda w: [_down(w[0], 4), _up(w[1], 4)])(wilson(tp, tp + fn)) if tp + fn else None)
    sup = [c for c in classes if per[c]["support"]]
    macro = lambda k: _down(sum(per[c][k] or 0 for c in sup) / len(sup), 4) if sup else None
    return dict(n=n, accuracy=prop(ok, n), top3=prop(top3, n), macro_precision=macro("precision"),
                macro_recall=macro("recall"), macro_f1=macro("f1"), per_class=per)


def evaluate(gold: str | Path, store: Store, scheme: str | None = None, max_misses: int = 200) -> dict:
    cols, rows = read_gold(gold)
    res: dict = dict(gold=str(gold), n_gold=len(rows), schemes={})
    groups: dict[str, list[dict]] = collections.defaultdict(list)
    for r in rows:
        if "code" in r and r["code"]:
            s = r.get("scheme") or scheme or ("aps" if not r["code"].startswith("adhoc/") else r["code"].rsplit(":", 1)[0])
            groups[s].append(dict(affair_id=r["affair_id"], value=r["code"]))
        elif "label" in r or "gold" in r:
            groups[r.get("scheme") or scheme or "adhoc/digitalisierung"].append(dict(affair_id=r["affair_id"], value=r.get("label", r.get("gold", ""))))
        else:
            groups[r.get("scheme") or scheme or "adhoc/digitalisierung"].append(dict(affair_id=r["affair_id"], value="1"))
    for s, items in groups.items():
        ids = sorted({x["affair_id"] for x in items})
        aff = store.affairs(ids)
        vals = [x["value"].strip().lower() for x in items]
        is_bin = s.startswith("adhoc/") or (s != "aps" and all(v in TRUE | FALSE for v in vals))
        if is_bin:
            gold_of = {x["affair_id"]: (norm_code(s, x["value"]).endswith(":yes") if s.startswith("adhoc/") else x["value"].strip().lower() in TRUE)
                       for x in items}
            has_neg = not all(gold_of.values())
            pred = predictions(store, s, 1, ids, 1)
            scored = [a for a in ids if a in pred]
            pairs = {a: (gold_of[a], pred[a][0]["code"].endswith(":yes")) for a in scored}
            out = dict(kind="binary" if has_neg else "positives_only", n_gold=len(ids), not_scored=len(ids) - len(scored),
                       overall=binary(list(pairs.values()), has_neg), by={})
            for dim in ("level", "lang", "body_key"):
                g = collections.defaultdict(list)
                for a, v in pairs.items():
                    g[(aff.get(a) or {}).get(dim) or "unknown"].append(v)
                out["by"][dim] = {k: binary(v, has_neg) for k, v in sorted(g.items(), key=lambda kv: -len(kv[1]))}
            miss = [a for a, (g_, p_) in pairs.items() if g_ != p_]
            out["misses"] = [dict(affair_id=a, gold="yes" if pairs[a][0] else "no", predicted=pred[a][0]["code"].rsplit(":", 1)[-1],
                                  p=pred[a][0]["p"], **{k: (aff.get(a) or {}).get(k) for k in ("level", "body_key", "lang", "date", "title")})
                             for a in sorted(miss, key=lambda a: ((aff.get(a) or {}).get("level") or "", a))][:max_misses]
            out["not_scored_ids"] = [a for a in ids if a not in pred][:max_misses]
        else:
            gold_of = {x["affair_id"]: norm_code(s, x["value"]) for x in items}
            lvl = 2 if all(":kw:" in v for v in gold_of.values()) else 1
            pred = predictions(store, s, lvl, ids, 3)
            scored = [a for a in ids if a in pred]
            trip = {a: (gold_of[a], pred[a][0]["code"], [r["code"] for r in pred[a]]) for a in scored}
            out = dict(kind="multiclass", level=lvl, n_gold=len(ids), not_scored=len(ids) - len(scored),
                       overall=multiclass(list(trip.values())), by={})
            for dim in ("level", "lang", "body_key"):
                g = collections.defaultdict(list)
                for a, v in trip.items():
                    g[(aff.get(a) or {}).get(dim) or "unknown"].append(v)
                out["by"][dim] = {k: {kk: vv for kk, vv in multiclass(v).items() if kk != "per_class"}
                                  for k, v in sorted(g.items(), key=lambda kv: -len(kv[1]))}
            out["misses"] = [dict(affair_id=a, gold=trip[a][0], predicted=trip[a][1], p=pred[a][0]["p"] or pred[a][0]["p_raw"],
                                  in_top3=trip[a][0] in trip[a][2], **{k: (aff.get(a) or {}).get(k) for k in ("level", "body_key", "lang", "date", "title")})
                             for a in scored if trip[a][0] != trip[a][1]][:max_misses]
        res["schemes"][s] = out
    return res


def fmt_p(d: dict | None) -> str:
    if not d or d.get("value") is None:
        return "–"
    return f"{_down(d['value'], 3):.3f} [{_down(d['ci'][0], 3):.3f}, {_up(d['ci'][1], 3):.3f}] ({d['k']}/{d['n']})"


def report(res: dict) -> str:
    L = [f"gold {res['gold']} · {res['n_gold']} rows"]
    for s, o in res["schemes"].items():
        ov = o["overall"]
        L.append(f"\n{s} · {o['kind']} · gold affairs {o['n_gold']} · not scored {o['not_scored']}")
        if o["kind"] == "multiclass":
            L.append(f"  accuracy {fmt_p(ov['accuracy'])} · top-3 {fmt_p(ov['top3'])} · macro P/R/F1 "
                     f"{ov['macro_precision']}/{ov['macro_recall']}/{ov['macro_f1']}")
        else:
            L.append(f"  recall {fmt_p(ov['recall'])}")
            if "precision" in ov:
                f1 = ov["f1"]
                L.append(f"  precision {fmt_p(ov['precision'])} · accuracy {fmt_p(ov['accuracy'])} · F1 {f1['value']} {f1['ci']}")
        for dim, g in o["by"].items():
            key = "accuracy" if o["kind"] == "multiclass" else "recall"
            L.append(f"  by {dim}: " + " · ".join(f"{k} {fmt_p(v.get(key))}" for k, v in list(g.items())[:12]))
        if o["misses"]:
            L.append(f"  misses ({len(o['misses'])}):")
            for m in o["misses"][:25]:
                L.append(f"    {m['affair_id']:>7} {m.get('level') or '?':9} {m.get('body_key') or '?':5} {m.get('lang') or '?'} "
                         f"{m['gold']} → {m['predicted']} p={m['p']}  {(m.get('title') or '')[:80]}")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="querschnitt eval", description=__doc__.split("\n\n")[0])
    ap.add_argument("gold")
    ap.add_argument("--scheme", help="for a positives list or a 0/1 label column (default adhoc/digitalisierung)")
    ap.add_argument("--out", help="write the full result as JSON")
    a = ap.parse_args(argv)
    st = Store()
    res = evaluate(a.gold, st, a.scheme)
    print(report(res))
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1))
        print(f"\n→ {a.out}")


if __name__ == "__main__":
    sys.exit(main())
