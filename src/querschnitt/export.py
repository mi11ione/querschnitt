"""Static export for the app and the open data files (docs/CONTRACT.md §3):

    python -m querschnitt.export --run runs/main --inputs ../data/inputs.jsonl.gz --out app/data [--since 2025-01-01]

Writes meta.json, bodies.json, affairs.json (columnar), detail/<id // 1000>.json, scheme_aps.json and, for the open
topics file, topics.jsonl.gz (CONTRACT §1 rows). Only affairs whose steps are complete get topic values; the scored
share is reported per parliament."""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import re
import time
from pathlib import Path

from . import prompts as P
from .calibrate import Calibration
from .compose import VERSION, decide, read_run, topic_rows
from .data import load_bodies, level
from .engine import Engine
from .examples import ExamplePool
from .scheme import APS, adhoc

ROOT = Path(__file__).resolve().parents[2]
KW = re.compile(json.loads((ROOT / "eval/kw_digitalisierung.json").read_text())["kw"], re.I)


def kw_text(x):
    t, tl = x["title"], x["title_long"]
    return t[:400] + ("\n" + tl[:400] if tl and tl != t else "")


def jdump(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
    tmp.rename(p)


def run(args):
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    lock, rows = read_run(*[Path(r) for r in args.run.split(",")])
    eng = Engine(None, ExamplePool.load(ROOT / "data/eval/aps_pool.jsonl"))
    topics = [adhoc("digitalisierung")]
    calib = Calibration.load(ROOT / "eval/calibration.json") if (ROOT / "eval/calibration.json").exists() else None
    B = load_bodies(Path(args.opd))
    first_year = collections.defaultdict(lambda: "9999")
    X = []
    with gzip.open(args.inputs, "rt") as f:
        for line in f:
            x = json.loads(line)
            if x["date"]:
                first_year[x["body"]] = min(first_year[x["body"]], x["date"][:4])
            if x["date"] and args.since <= x["date"] <= args.until:
                X.append(x)
    X.sort(key=lambda x: (x["date"], x["id"]), reverse=True)
    cols = collections.defaultdict(list)
    detail = collections.defaultdict(dict)
    cov = collections.defaultdict(collections.Counter)
    tfile = gzip.open(out / "topics.jsonl.gz.tmp", "wt") if args.topics_file else None
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    n_dec = collections.Counter()
    for x in X:
        d = decide(x, rows, eng.ch1_prompt, topics)
        a = d.get("aps"); g = d.get("adhoc/digitalisierung")
        c = cov[x["body"]]
        c["n"] += 1; c["scored"] += bool(a); c["dig"] += bool(g); c["title_only"] += not x["text"]
        c["check"] += bool(a and a["lane"] == "please_check")
        if not (a or g):
            continue
        n_dec["aps"] += bool(a); n_dec["dig"] += bool(g)
        cal = calib.apply("aps-fed" if (a and a.get("examples")) else "aps", a["conf"]) if (a and calib) else None
        for k, v in (("id", x["id"]), ("body", x["body"]), ("date", x["date"]), ("type_h", x["type_h"] or x["type"]),
                     ("state", x["state"]), ("lang", x["text_lang"] or x["lang"]), ("title", x["title"]), ("party", x["party"]),
                     ("submitter", x["submitter"]), ("stype", x["submitter_type"]),
                     ("ch", a["ch"] if a else None), ("ch_p", round(cal if cal is not None else a["conf"], 3) if a else None),
                     ("lane", (a["lane"] == "please_check") * 1 if a else None),
                     ("subs", [1000 * APS.sub_index[s][0] + APS.sub_index[s][1] for s, _ in a["subs"]] if a else []),
                     ("dig_p", round(g["p"], 3) if g else None), ("dig_flag", int(g["flag"]) if g else None),
                     ("dig_lane", int(g["lane"] == "please_check") if g else None), ("kw", int(bool(KW.search(kw_text(x)))))):
            cols[k].append(v)
        detail[x["id"] // 1000][x["id"]] = dict(
            title_long=x["title_long"], text=x["text"][:1500], text_src=x["text_src"], url=x["url"], number=x["number"],
            n_signers=x["n_signers"], dept=x["dept"],
            aps=dict(rank=a["rank"], conf_raw=round(a["conf"], 4), p=[round(a["P"][i], 4) for i in a["rank"]], lane=a["lane"],
                     subs=[[s, round(p, 4)] for s, p in a["subs"]], readings=a["n_readings"], examples=a.get("examples"),
                     pids=a["pids"], evidence=a.get("evidence"), bilingual=a.get("bilingual")) if a else None,
            be=d.get("be-directorates"),
            dig=dict(p=round(g["p"], 4), p_a=round(g["p_a"], 4), p_b=None if g["p_b"] is None else round(g["p_b"], 4),
                     lane=g["lane"], evidence=g.get("evidence")) if g else None,
            build=lock["fp"], model=lock["model"])
        if tfile:
            for r in topic_rows(x, d, lock, (lambda s, v: calib.apply("aps-fed" if (a and a.get("examples")) else "aps", v)) if calib else None, now):
                tfile.write(json.dumps(r, ensure_ascii=False) + "\n")
    if tfile:
        tfile.close()
        (out / "topics.jsonl.gz.tmp").rename(out / "topics.jsonl.gz")
    jdump(out / "affairs.json", dict(n=len(cols["id"]), cols=cols))
    for k, v in detail.items():
        jdump(out / "detail" / f"{k}.json", v)
    bodies = []
    for key, c in sorted(cov.items(), key=lambda kv: -kv[1]["n"]):
        b = B.get(key) or {}
        bodies.append(dict(key=key, name_de=b.get("legislative_name_de") or b.get("name_de") or key,
                           name_fr=b.get("legislative_name_fr") or b.get("name_fr") or key, place_de=b.get("name_de"), place_fr=b.get("name_fr"),
                           level=level(key, B), canton=b.get("canton_key") or (key if len(key) == 2 else None), lang=b.get("lang"),
                           n_affairs=c["n"], n_scored=c["scored"], n_dig=c["dig"], n_check=c["check"],
                           title_only_share=round(c["title_only"] / c["n"], 3), covered_from=first_year[key]))
    jdump(out / "bodies.json", bodies)
    jdump(out / "scheme_aps.json", dict(
        chapters=[dict(i=i, code=APS.codes[i], de=APS.short(i, "de"), fr=APS.short(i, "fr"), it=APS.short(i, "it")) for i in range(25)],
        subtopics={str(1000 * i + j): dict(code=APS.sub_codes[i][j], de=APS.subs_de[i][j], ch=i) for i in range(24) for j in range(len(APS.subs_de[i]))},
        topics=[dict(id=t["id"], names=t["names"], aliases=t.get("aliases", [])) for t in topics]))
    tot = sum(c["n"] for c in cov.values())
    meta = dict(generated_at=now, version=VERSION, model=lock["model"], build=lock["fp"], build_short=lock["fp"][-8:],
                since=args.since, until=X[0]["date"] if X else None, affairs=tot, parliaments=len(cov),
                scored=n_dec["aps"], scored_share=round(n_dec["aps"] / tot, 4) if tot else 0, dig_scored=n_dec["dig"],
                please_check=sum(c["check"] for c in cov.values()), calibration=bool(calib))
    jdump(out / "meta.json", meta)
    print(json.dumps(meta, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=f"{ROOT / 'runs/main'},{ROOT / 'runs/side'}")
    ap.add_argument("--inputs", default=str(ROOT.parent / "data/inputs.jsonl.gz"))
    ap.add_argument("--opd", default=str(ROOT.parent / "data/opd-new"))
    ap.add_argument("--out", default=str(ROOT / "app/data"))
    ap.add_argument("--since", default="2025-01-01")
    ap.add_argument("--until", default="9999")
    ap.add_argument("--topics-file", action="store_true")
    run(ap.parse_args(argv))


if __name__ == "__main__":
    main()
