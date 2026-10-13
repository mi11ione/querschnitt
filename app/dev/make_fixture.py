"""Dev fixture for the app: CONTRACT §3 files built from real inputs only, written to app/data-fixture/ (never deployed).

Sources (read-only):
- affairs: bern/data/inputs.jsonl.gz if present (built by src/querschnitt/data.py), else the OPD bulk exports in
  bern/data/opd-new/ (affairs, bodies, contributors, texts) through the same data.py functions;
- "Digitalisierung" decisions: the real S8 census rows (ideation2/spikes/s8-dvs/raw/a.jsonl + b.jsonl, build dd237840),
  p = mean of the two readings where both exist; flag at the topic's cut-off (0.5); please_check where the two readings
  disagree or 0.3 <= p < 0.7 (S8 rule); keyword hit from S8's frozen keyword column (items_cache.json);
- APS scheme: src/querschnitt/schemes/aps.yaml; Prüfstand rows: VISION-topics-v2 §6.1 as measured, plus the S9
  coverage–precision curve recomputed from S9's raw rows (no model calls).
Chapter fields stay empty: no chapter run exists yet. Evidence stays empty: S8 stored no quotes.

Usage: querschnitt/.venv/bin/python app/dev/make_fixture.py"""
from __future__ import annotations

import collections
import datetime as dt
import gzip
import json
import math
import os
import re
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
REPO = APP.parent
BERN = REPO.parent
OUT = APP / "data-fixture"
OPD = BERN / "data" / "opd-new"
INPUTS = BERN / "data" / "inputs.jsonl.gz"
S8 = BERN / "ideation2" / "spikes" / "s8-dvs"
S9 = BERN / "ideation2" / "spikes" / "s9-aps"
sys.path.insert(0, str(REPO / "src"))
from querschnitt import data as D  # noqa: E402

TOPIC = dict(id="adhoc/digitalisierung", names=dict(de="Digitalisierung", fr="numérique", it="digitalizzazione"),
             aliases=["Digitalisierung", "numérique", "digitalisation", "digitalizzazione", "digital", "Digitalisation"], cutoff=0.5)


def jl(p):
    with open(p) as f:
        return [json.loads(l) for l in f if l.strip()]


def write(name, obj):
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
    return p.stat().st_size


def s8_rows():
    a = {r["id"]: r for r in jl(S8 / "raw" / "a.jsonl")}
    b = {r["id"]: r for r in jl(S8 / "raw" / "b.jsonl")}
    items = {x["id"]: x for x in json.load(open(S8 / "items_cache.json"))}
    out = {}
    for i, ra in a.items():
        pa = ra["p_yes"]; pb = (b.get(i) or {}).get("p_yes")
        p = (pa + pb) / 2 if pb is not None else pa
        disagree = pb is not None and ((pa >= .5) != (pb >= .5))
        out[i] = dict(p=p, p_a=pa, p_b=pb, flag=p >= TOPIC["cutoff"], check=disagree or (0.3 <= p < 0.7),
                      kw=bool((items.get(i) or {}).get("kw")), fp=ra["fp"], model=ra["served"], ts=ra["ts"], item=items.get(i))
    return out


def opd_inputs(ids: set[int], B: dict):
    """Same field choices as data.build, restricted to ids (texts only; documents are skipped for speed)."""
    A = {}
    period_n = collections.Counter()
    for a in D.rows(OPD / "affairs.ndjson.gz"):
        d = (a.get("begin_date") or "")[:10]
        if "2026-01-01" <= d <= "2026-12-31" and a["body_key"] in B:
            period_n[a["body_key"]] += 1
        if a["id"] in ids:
            A[a["id"]] = a
    print("affairs read", len(A), file=sys.stderr)
    S = D.submitters(OPD, ids)
    print("submitters", len(S), file=sys.stderr)
    T = D.texts_index(OPD)
    print("texts", len(T), file=sys.stderr)
    X = {}
    for i, a in A.items():
        lang, tl = D.pick_lang(a, B)
        if not tl:
            continue
        title = D.clean(a.get(f"title_{tl}")); tlong = D.clean(a.get(f"title_long_{tl}"))
        tr = D.pick_text_rows(T.get(i), tl, a["body_key"])
        sub = S.get(i) or {}
        X[i] = dict(id=i, body=a["body_key"], lang=lang, text_lang=tl, number=a.get("number"), date=(a.get("begin_date") or "")[:10],
                    title=title, title_long=tlong, text=tr[2][:1500] if tr else "", text_src=f"text:{tr[3]}" if tr else None,
                    type=a.get(f"type_name_{tl}") or a.get("type_name_de") or "", type_h=a.get("type_harmonized_de") or "",
                    type_h_fr=a.get("type_harmonized_fr") or "", state=a.get(f"state_name_{tl}") or a.get("state_name_de") or "",
                    url=a.get(f"url_external_{tl}") or a.get("url_external_de") or a.get("url_external_fr") or "",
                    submitter=sub.get("name", ""), party=sub.get("party", ""), party_fr=sub.get("party_fr", ""))
    return X, period_n


def from_inputs(ids: set[int]):
    X = {}
    with gzip.open(INPUTS, "rt") as f:
        for l in f:
            x = json.loads(l)
            if x["id"] in ids:
                X[x["id"]] = x
    period_n = collections.Counter()
    for a in D.rows(OPD / "affairs.ndjson.gz"):
        d = (a.get("begin_date") or "")[:10]
        if "2026-01-01" <= d <= "2026-12-31":
            period_n[a["body_key"]] += 1
    return X, period_n


def curve():
    """S9 D3 (five APS-labelled examples): coverage–precision over the 1,357 held-out items, ranked by confidence;
    operating point = the shipped lane `readings_agree` (the two code orders agree)."""
    sys.path.insert(0, str(S9 / "scripts"))
    try:
        from s9lib import geo2  # noqa
    except Exception as e:  # pragma: no cover
        print("s9lib unavailable:", e, file=sys.stderr)
        return None
    items = {it["oid"]: it for it in json.load(open(S9 / "data" / "items.json"))}
    raw = {ph: {r["oid"]: r for r in jl(S9 / "raw" / f"{ph}.jsonl")} for ph in ("d0a", "d0b", "d3m")}
    am = lambda p: max(range(len(p)), key=lambda i: p[i])
    rows = []
    for o, it in items.items():
        if not all(o in raw[ph] for ph in raw):
            continue
        p = geo2(raw["d3m"][o]["p"], raw["d0b"][o]["p"]); k = am(p)
        agree = am(raw["d0a"][o]["p"]) == am(raw["d0b"][o]["p"])
        rows.append((p[k], int(k == int(it["chapter"])), agree))
    rows.sort(key=lambda r: -r[0])
    n = len(rows); pts = []; hit = 0
    for i, (_, y, _) in enumerate(rows, 1):
        hit += y
        if i % 10 == 0 or i == n:
            pts.append([round(i / n, 4), round(hit / i, 4)])
    ag = [r for r in rows if r[2]]
    op = dict(coverage=round(len(ag) / n, 4), precision=round(sum(r[1] for r in ag) / len(ag), 4), n=len(ag),
              label_de="ausgeliefert: Lesarten einig", label_fr="livré : lectures concordantes")
    return dict(test="APS-Kapitel, 1'357 Bundesgeschäfte, fünf APS-Beispiele (D3)", test_fr="Chapitre APS, 1 357 objets fédéraux, cinq exemples APS (D3)",
                n=n, x="coverage", y="precision", points=pts, op=op, file="ideation2/spikes/s9-aps/results.json")


PRUEF = [
    # test (de, fr), gold, design, n, result, interval, baseline, split, file
    ("APS-Kapitel vs. APS-Redaktion, Bundesgeschäfte", "Chapitre APS vs rédaction APS, objets fédéraux", "human",
     [("fünf APS-Beispiele (D3)", "cinq exemples APS (D3)", 1357, "top-1 0.722 · top-3 0.875", [0.698, 0.745], "Listen-Prompt 0.655 · Stichwort 0.192 · Mehrheit 0.080"),
      ("Kapitel aus Unterthema (D1, ausgeliefert)", "chapitre déduit du sous-thème (D1, livré)", 1357, "top-1 0.704 · top-3 0.843", [0.679, 0.727], "Listen-Prompt 0.655"),
      ("Listen-Prompt, zwei Reihenfolgen (D0)", "liste, deux ordres (D0)", 1357, "top-1 0.655", [0.629, 0.680], "—"),
      ("DE + FR gemittelt (D2)", "DE + FR moyennés (D2)", 1357, "top-1 0.634", None, "Δ vs D0 −0.021 [−0.037, −0.004]"),
      ("Unterthema, durchgehend", "sous-thème, de bout en bout", 1221, "top-1 0.521 · top-3 0.677", None, "—")],
     "held-out, vorregistriert", "ideation2/spikes/s9-aps/results.md"),
    ("«Digitalisierung»: 30 handkuratierte DVS-Geschäfte (Recall)", "« numérique » : 30 objets DVS choisis à la main (rappel)", "human",
     [("Ja/Nein mit Umfangnotiz", "oui/non avec note de portée", 30, "27/30", None, "Stichwort 21/30 · KI-Richter 27/30")],
     "alle öffentlichen Einträge", "ideation2/spikes/s8-dvs/results.md"),
    ("Sachbereiche Bund vs. Curia-Tags", "Domaines fédéraux vs tags Curia", "human",
     [("fünf getaggte Beispiele + Ja/Nein Top 6", "cinq exemples + oui/non top 6", 200, "micro-F1 0.654", [0.62, 0.69], "BFH (trainiert, 15'007) 0.687 [0.65, 0.72]")],
     "nach BFH-Publikation eingereicht", "ideation/spikes/s5"),
    ("Bern, Leitdirektion (8), Titel, DE / FR", "Berne, direction responsable (8), titres, DE / FR", "human",
     [("Schema-Tausch", "changement de schéma", 200, "0.615 / 0.645", None, "Stichwort 0.520 / 0.495 · Mehrheit 0.175")],
     "Grossratsfeld", "ideation/spikes/s6"),
    ("«Digitalisierung» 2026, Schweizer Parlamente vs. KI-Richter", "« numérique » 2026, parlements suisses vs juge IA", "judge",
     [("Präzision", "précision", 14513, "0.914", [0.876, 0.952], "Stichwort 0.753 [0.714, 0.790]"),
      ("Recall", "rappel", 14513, "0.654", [0.486, 0.894], "Stichwort 0.605 [0.451, 0.827]")],
     "453 geprüft, gewichtet", "ideation2/spikes/s8-dvs/results.md"),
    ("Beleg stützt das Thema (blinder KI-Richter)", "L'extrait soutient le thème (juge IA aveugle)", "judge",
     [("zitierter Satz", "phrase citée", 120, "0.850 · Teilstring 120/120", [0.775, 0.903], "—")], "Stichprobe", "ideation2/spikes/s12-evidence"),
    ("APS-Kapitel, kantonal + kommunal vs. KI-Richter", "Chapitre APS, cantonal + communal vs juge IA", "judge",
     [("Kapitel", "chapitre", 153, "0.686 · kantonal 0.726 · kommunal 0.621", None, "—")], "zwei Läufe, κ 0.95", "ideation/spikes/s7"),
    ("Zweisprachige Kantone, Titel, DE vs. FR", "Cantons bilingues, titres, DE vs FR", "judge",
     [("Deutsch", "allemand", 210, "0.543", [0.475, 0.609], "—"), ("Französisch", "français", 210, "0.529", [0.461, 0.595], "Differenz +0.014 [−0.043, +0.076]")],
     "vorregistriert", "ideation2/spikes/s10-bilingual"),
    ("KI-Richter selbst vs. APS-Redaktion", "Le juge IA vs rédaction APS", "judge",
     [("Claude, blind, gleicher Input", "Claude, aveugle, même entrée", 200, "0.790", [0.728, 0.841], "Apertus 0.695 / 0.720")], "Stichprobe", "ideation2/spikes/s11-anchor"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    B = D.load_bodies(OPD)
    R = s8_rows()
    ids = set(R)
    X, period_n = (from_inputs(ids) if INPUTS.exists() else opd_inputs(ids, B))
    src = "inputs.jsonl.gz" if INPUTS.exists() else "opd-new bulk exports"
    keep = sorted((i for i in ids if i in X and X[i]["date"] >= "2026-01-01"), key=lambda i: (X[i]["date"], i), reverse=True)
    cols = {k: [] for k in ("id", "body", "date", "number", "type", "type_h", "type_h_fr", "state", "lang", "title", "party", "submitter",
                            "ch", "ch_p", "lane", "subs", "dig_p", "dig_flag", "dig_lane", "kw")}
    chunks = collections.defaultdict(dict)
    per = collections.defaultdict(lambda: collections.Counter())
    first = {}
    fp = model = None
    for i in keep:
        x, r = X[i], R[i]
        fp, model = r["fp"], r["model"]
        lane = 1 if r["check"] else 0
        for k, v in (("id", i), ("body", x["body"]), ("date", x["date"]), ("number", x.get("number") or ""), ("type", x.get("type") or ""), ("type_h", x.get("type_h") or ""),
                     ("type_h_fr", x.get("type_h_fr") or ""), ("state", x.get("state") or ""), ("lang", x["text_lang"] if x.get("text_lang") in ("de", "fr", "it", "rm") else x["lang"]),
                     ("title", x["title"]), ("party", x.get("party") or ""), ("submitter", x.get("submitter") or ""),
                     ("ch", None), ("ch_p", None), ("lane", None), ("subs", None), ("dig_p", round(r["p"], 4)), ("dig_flag", 1 if r["flag"] else 0),
                     ("dig_lane", lane), ("kw", 1 if r["kw"] else 0)):
            cols[k].append(v)
        chunks[i // 1000][str(i)] = dict(title_long=x.get("title_long") if x.get("title_long") != x["title"] else "", text=x.get("text") or "", number=x.get("number") or "",
                                         text_src=x.get("text_src"), url=x.get("url") or "", evidence=None, ch_rank=None, subs=None,
                                         aps=None, dig=dict(p=round(r["p"], 4), p_a=round(r["p_a"], 4), p_b=None if r["p_b"] is None else round(r["p_b"], 4),
                                                  lane="please_check" if r["check"] else "readings_agree", evidence=None),
                                         type=x.get("type") or "", build=r["fp"], model=r["model"], prompt_ids=[], scored_at=r["ts"])
        c = per[x["body"]]
        c["scored"] += 1; c["flag"] += r["flag"]; c["title_only"] += not x.get("text"); c["check"] += r["check"]
        y = x["date"][:4]
        if y.isdigit() and (x["body"] not in first or y < first[x["body"]]):
            first[x["body"]] = y
    # bodies
    bodies = []
    for k in sorted(set(per) | set(period_n)):
        b = B.get(k) or {}
        lvl = D.level(k, B)
        c = per.get(k, collections.Counter())
        nfr = {"CHE": "Assemblée fédérale", "LIE": "Landtag (Liechtenstein)"}.get(k) or D.parl_name(k, B, "fr")
        bodies.append(dict(key=k, name_de=D.parl_name(k, B, "de"), name_fr=nfr,
                           place_de=b.get("name_de") or b.get("name") or k, place_fr=b.get("name_fr") or b.get("name") or k,
                           level=lvl, canton=b.get("canton_key") or (k if lvl == "cantonal" else None), lang=(b.get("lang") or "").lower() or None,
                           n_affairs=period_n.get(k, 0), n_scored=0, n_dig=c["scored"], n_check=c["check"],
                           title_only_share=round(c["title_only"] / c["scored"], 4) if c["scored"] else None, covered_from=first.get(k)))
    pend = sum(1 for i in keep if R[i]["check"])
    n_pop = sum(period_n.values())
    meta = dict(build=fp, build_short=(fp or "")[-8:], model=model, since="2026-01-01", until=max(cols["date"]),
                affairs=n_pop, parliaments=len([b for b in bodies if b["n_dig"]]), scored=0, scored_share=0, dig_scored=len(keep),
                please_check=pend, calibration=False, generated_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                version="fixture", fixture=True, source=f"S8 census rows + {src}", nightly=None)
    sizes = dict(meta=write("meta.json", meta), bodies=write("bodies.json", bodies), affairs=write("affairs.json", dict(n=len(keep), cols=cols)))
    for k, v in chunks.items():
        write(f"detail/{k}.json", v)
    # scheme
    import yaml
    doc = yaml.safe_load((REPO / "src" / "querschnitt" / "schemes" / "aps.yaml").read_text())
    ch = [dict(i=i, code=c["code"], de=c["name"]["de"], fr=c["name"].get("fr"), it=c["name"].get("it")) for i, c in enumerate(doc["chapters"])]
    ch.append(dict(i=len(ch), code=doc["none"]["code"], de=doc["none"]["name"]["de"], fr=doc["none"]["name"]["fr"], it=doc["none"]["name"]["it"]))
    subs = {str(1000 * i + j): dict(code=st["code"], de=st["name"]["de"], ch=i) for i, c in enumerate(doc["chapters"]) for j, st in enumerate(c["subtopics"])}
    sizes["scheme"] = write("scheme_aps.json", dict(chapters=ch, subtopics=subs, topics=[TOPIC]))
    rows = []
    for test, test_fr, gold, designs, split, f in PRUEF:
        for de, fr, n, res, ci, base in designs:
            rows.append(dict(test=test, test_fr=test_fr, gold=gold, design=de, design_fr=fr, n=n, result=res, interval=ci,
                             baseline=base, split=split, file=f))
    sizes["pruefstand"] = write("pruefstand.json", dict(rows=rows, curve=curve(), build="dd237840",
                                                         source="VISION-topics-v2 §6.1 (measured rows as published); curve recomputed from S9 raw"))
    print(json.dumps(dict(affairs=len(keep), bodies=len(bodies), chunks=len(chunks), pending=pend, population=n_pop, sizes=sizes, source=src)))


if __name__ == "__main__":
    main()
