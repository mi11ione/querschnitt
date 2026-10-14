"""Task E: run the BFH omikuji-bonsai DE baseline on <=500 clean-pool DE affairs; score 28 Hauptthemen vs Curia tags.
Run with the x86_64 venv:  arch -x86_64 .venv-bfh/bin/python -I scripts/e_bfh_run.py
"""
import collections
import gzip
import html
import json
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e_safe_load  # noqa: E402
import omikuji  # noqa: E402

D = "/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s2-oracles/data"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 500
REN = {"Medien / Kommunikation": "Medien und Kommunikation", "Wissenschaft / Forschung": "Wissenschaft und Forschung",
       "Rechte und Freiheiten": "Menschenrechte"}

tags = {t["TagName"]: t["ID"] for t in json.load(open(f"{D}/curia_tags.json"))["DE"]}
id2label = json.load(open(f"{D}/bfh/id2label.json"))
haupt = {}
for k, v in id2label.items():
    if v.startswith("Hauptthema: "):
        name = REN.get(v[12:], v[12:])
        haupt[int(k)] = tags[name]
assert len(haupt) == 28 and len(set(haupt.values())) == 28

oracle = {}
for line in gzip.open(f"{D}/oracle_curia.jsonl.gz", "rt"):
    o = json.loads(line)
    if o["clean_pool"] and o["tags"]:
        oracle[o["curia_id"]] = o


def clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return " ".join(html.unescape(s).split())


docs = []
for line in gzip.open(f"{D}/curia_cleanpool_texts_de.jsonl.gz", "rt"):
    r = json.loads(line)
    if r["ID"] not in oracle:
        continue
    body = clean(r.get("SubmittedText")) or clean(r.get("InitialSituation")) or clean(r.get("Description"))
    reason = clean(r.get("ReasonText"))
    text = "\n".join(x for x in (clean(r["Title"]), body, reason) if x)
    w = re.findall(r"\w+", text.lower())
    de = sum(x in ("der", "die", "und", "das", "nicht", "ist", "zu", "den", "mit") for x in w)
    fr = sum(x in ("le", "la", "les", "et", "des", "est", "du", "une", "pour") for x in w)
    it_ = sum(x in ("il", "che", "di", "della", "per", "una", "sono", "gli", "non") for x in w)
    if de <= max(fr, it_):
        continue  # BFH routes by language id; keep German-text docs for the DE model
    docs.append({"curia_id": r["ID"], "text": text, "has_body": bool(body), "gold": oracle[r["ID"]]["tags"],
                 "type": oracle[r["ID"]]["type"]})
print("clean-pool DE docs with tags+text row", len(docs), "with body", sum(d["has_body"] for d in docs))
random.Random(20261013).shuffle(docs)
docs = docs[:N]

t0 = time.time()
vec = e_safe_load.load(f"{D}/bfh/raw/de/vectorizer")
model = omikuji.Model.load(f"{D}/bfh/raw/de/omikuji-model")
print(f"load {time.time() - t0:.1f}s", flush=True)
t1 = time.time()
X = vec.transform([d["text"] for d in docs])
print(f"vectorize {len(docs)} docs {time.time() - t1:.1f}s", flush=True)
t2 = time.time()
for d, row in zip(docs, X):
    fv = [(int(c), float(row[0, c])) for c in row.nonzero()[1]]
    pred = model.predict(fv, top_k=1000) if fv else []
    d["scores"] = {haupt[i]: round(s, 4) for i, s in pred if i in haupt}
    d["sub_scores"] = {id2label[str(i)]: round(s, 4) for i, s in pred if i not in haupt and s >= 0.05}
print(f"predict {time.time() - t2:.1f}s", flush=True)

ALL = sorted(set(tags.values()))


def f1(pairs):
    tp = collections.Counter(); fp = collections.Counter(); fn = collections.Counter()
    for gold, pred in pairs:
        for t in pred:
            (tp if t in gold else fp)[t] += 1
        for t in gold:
            if t not in pred:
                fn[t] += 1
    TP, FP, FN = sum(tp.values()), sum(fp.values()), sum(fn.values())
    micro = 2 * TP / (2 * TP + FP + FN) if TP else 0.0
    per = []
    for t in ALL:
        if tp[t] + fn[t] == 0:
            continue  # label absent from gold in this sample
        per.append(2 * tp[t] / (2 * tp[t] + fp[t] + fn[t]) if tp[t] else 0.0)
    return round(micro, 4), round(sum(per) / len(per), 4), round(TP / (TP + FP), 4) if TP + FP else 0, round(TP / (TP + FN), 4)


dev, test = docs[:150], docs[150:]
res = {}
for th in (0.2, 0.3, 0.4, 0.5):
    res[f"thr{th}_all"] = f1([(set(d["gold"]), {t for t, s in d["scores"].items() if s >= th}) for d in docs])
best = max((f1([(set(d["gold"]), {t for t, s in d["scores"].items() if s >= th}) for d in dev])[0], th)
           for th in [x / 100 for x in range(5, 80, 5)])
res[f"dev_tuned_thr{best[1]}_on_test(n={len(test)})"] = f1(
    [(set(d["gold"]), {t for t, s in d["scores"].items() if s >= best[1]}) for d in test])
for k in (1, 2, 3):
    res[f"top{k}_all"] = f1([(set(d["gold"]), set(sorted(d["scores"], key=d["scores"].get, reverse=True)[:k])) for d in docs])
res["topK_oracle_k(=gold count)_all"] = f1(
    [(set(d["gold"]), set(sorted(d["scores"], key=d["scores"].get, reverse=True)[:len(d["gold"])])) for d in docs])
res["thr0.3_with_body_only"] = f1([(set(d["gold"]), {t for t, s in d["scores"].items() if s >= 0.3}) for d in docs if d["has_body"]])
print("metric = (micro-F1, macro-F1, micro-P, micro-R)")
for k, v in res.items():
    print(f"  {k}: {v}")
json.dump({"n": len(docs), "results": res, "timing_s": {"load": round(t1 - t0, 1), "vectorize": round(t2 - t1, 1),
           "predict": round(time.time() - t2, 1)}}, open(f"{D}/bfh/baseline_results.json", "w"), indent=1)
with gzip.open(f"{D}/bfh/baseline_predictions_de.jsonl.gz", "wt") as f:
    for d in docs:
        f.write(json.dumps({k: d[k] for k in ("curia_id", "type", "has_body", "gold", "scores", "sub_scores")},
                           ensure_ascii=False) + "\n")
