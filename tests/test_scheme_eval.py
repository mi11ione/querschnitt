"""`make scheme-eval`: reading a partner's CSV/XLSX, the id / business-number join, label detection, the generated scheme
file, the frozen keyword stems, the sample, and one end-to-end run on the fake endpoint (no model call, no network)."""
import builtins
import gzip
import json
import pathlib

import pytest
import yaml

from querschnitt import prompts as P
from querschnitt import scheme as SCH
from querschnitt import scheme_eval as SE

FIX = pathlib.Path(__file__).parent / "fixtures"
ROOT = pathlib.Path(__file__).resolve().parents[1]


def _inputs(rows):
    return SE.Inputs([dict(id=i, body=b, number=n, lang=l, title=t, date=d) for i, b, n, l, t, d in rows])


IDX = [(101, "CHE", "24.4266", "de", "Motion Digitalisierung der Verwaltung", "2024-12-01"),
       (102, "CHE", "24.4300", "de", "Postulat Velowege", "2024-12-02"),
       (103, "AG", "24.4300", "de", "Interpellation Velowege im Aargau", "2024-11-02"),
       (201, "GE", "PL 9402", "fr", "Projet de loi sur les transports", "2025-01-01"),
       (301, "BS", "24.5077", "de", "Interpellation Notrufe", "2024-03-06"),
       (302, "BS", "24.5076", "de", "Anzug Wahlen", "2024-03-06")]


# ------------------------------------------------------------------ reading
def test_read_csv_semicolon_bom_title_line(tmp_path):
    p = tmp_path / "export.csv"
    p.write_bytes("POLITmonitor Export 18.10.2026;;\nGeschäftsnummer;Titel;Kategorie\n24.4266;Digital;Digitalisierung\n"
                  "24.4300;Velo;Verkehr\n".encode("utf-8-sig"))
    header, rows, meta = SE.read_table(p)
    assert header == ["Geschäftsnummer", "Titel", "Kategorie"] and meta["delimiter"] == ";" and meta["header_row"] == 2
    assert rows == [["24.4266", "Digital", "Digitalisierung"], ["24.4300", "Velo", "Verkehr"]]


def test_read_csv_latin1_and_tab(tmp_path):
    p = tmp_path / "x.csv"
    p.write_bytes("id\tThème\n101\tFinances publiques\n102\tSanté\n".encode("latin-1"))
    header, rows, meta = SE.read_table(p)
    assert header == ["id", "Thème"] and rows[1] == ["102", "Santé"] and meta["encoding"] in ("cp1252", "latin-1")
    assert meta["delimiter"] == "\t"


def test_read_xlsx_without_openpyxl_asks_for_csv(tmp_path, monkeypatch):
    p = tmp_path / "x.xlsx"; p.write_bytes(b"PK")
    real = builtins.__import__
    monkeypatch.setattr(builtins, "__import__", lambda name, *a, **k: (_ for _ in ()).throw(ImportError(name))
                        if name == "openpyxl" else real(name, *a, **k))
    with pytest.raises(SystemExit) as e:
        SE.read_table(p)
    assert "openpyxl" in str(e.value) and "CSV UTF-8" in str(e.value)


def test_read_xlsx(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook(); ws = wb.active
    for r in (["Liste der Geschäfte"], ["OPD-ID", "Titel", "Thema"], [101, "Digital", "Digitalisierung"], [102.0, "Velo", "Verkehr"]):
        ws.append(r)
    wb.save(tmp_path / "x.xlsx")
    header, rows, meta = SE.read_table(tmp_path / "x.xlsx")
    assert header == ["OPD-ID", "Titel", "Thema"] and rows == [["101", "Digital", "Digitalisierung"], ["102", "Velo", "Verkehr"]]
    assert meta["format"] == "xlsx"


# ------------------------------------------------------------------ key and label columns, join
def test_detect_key_id_vs_number():
    idx = _inputs(IDX)
    (j, kind, rate), = SE.detect_key(["opd", "label"], [["101", "a"], ["301", "b"]], idx)[0][:1]
    assert (j, kind, rate) == (0, "id", 1.0)
    keys, _ = SE.detect_key(["Titel", "Nr.", "Datum"], [["x", "24.4266", "2024-12-01"], ["y", "PL 9402", "2025-01-01"]], idx)
    assert keys[0][:2] == (1, "number") and all(k[0] != 2 for k in keys)   # a date column is never a key
    with pytest.raises(SystemExit, match="no column joins"):
        SE.detect_key(["a", "b"], [["x", "y"]], idx)


def test_join_numbers_bodies_duplicates_and_reasons():
    idx = _inputs(IDX)
    header = ["Nummer", "Kanton", "Kategorie"]
    rows = [["24.4266", "", "Digitalisierung"],       # unique number
            ["24.4300", "CH", "Verkehr"],              # in CHE and AG: the body column decides (CH -> CHE)
            ["PL9402", "", "Verkehr"],                 # whitespace-insensitive
            ["24.4266", "", "Verwaltung"],             # listed twice: merged, first label first
            ["99.9999", "", "Verkehr"],                # not in the inputs
            ["24.5077", "", ""]]                       # no label
    body_col = SE.detect_body_col(header, rows[1:2], idx.bodies, {0})
    assert body_col == 1
    items, rep = SE.join(header, rows, idx, [(0, "number", 1.0)], [2], None, body_col)
    by = {x["id"]: x for x in items}
    assert sorted(by) == [101, 102, 201] and by[101]["labels"] == ["Digitalisierung", "Verwaltung"] and by[101]["rows"] == 2
    assert rep["merged_rows"] == 1 and rep["not_joined"] == {"number not in the inputs": 1, "no label": 1}
    assert rep["examples"]["number not in the inputs"] == ["99.9999"]


def test_join_ambiguous_number_resolved_by_majority_body_or_reported():
    idx = _inputs(IDX)
    items, rep = SE.join(["nr", "l"], [["24.4266", "a"], ["24.4300", "b"]], idx, [(0, "number", 1.0)], [1], None)
    assert [x["id"] for x in items] == [101, 102]          # 24.4300 -> CHE, the body of every other joined row
    assert any("from the other rows" in k for k in rep["joined_by"])
    items, rep = SE.join(["nr", "l"], [["24.4300", "b"], ["PL 9402", "c"], ["24.5077", "d"]], idx, [(0, "number", 1.0)], [1], None)
    assert 102 not in {x["id"] for x in items} and 103 not in {x["id"] for x in items}
    assert rep["not_joined"] == {"number in several parliaments (pass BODY= or a body column)": 1}
    items, _ = SE.join(["nr", "l"], [["24.4300", "b"]], idx, [(0, "number", 1.0)], [1], None, body="AG")
    assert [x["id"] for x in items] == [103]


def test_join_id_with_number_fallback():
    idx = _inputs(IDX)
    rows = [["101", "", "a"], ["999999", "24.5077", "b"], ["", "PL 9402", "c"]]
    items, rep = SE.join(["id", "nr", "l"], rows, idx, [(0, "id", 0.5), (1, "number", 0.6)], [2], None)
    assert [x["id"] for x in items] == [101, 201, 301] and rep["joined_by"] == {"id": 1, "number": 2}


def test_label_columns_and_separators():
    header = ["Signatur", "Titel", "Thema 1", "Thema 2", "Status"]
    rows = [["1", "x", "Kinder, Jugendliche & Familien", "Wohnen", "A"], ["2", "y", "Wohnen", "", "B"]]
    assert SE.detect_label(header, rows, None, {0}) == [2, 3]
    assert SE.detect_label(header, rows, "Thema 2+Thema 1", {0}) == [3, 2]
    cells = ["Kinder, Jugendliche & Familien", "Wohnen", "Arbeit, Wirtschaft"]
    assert SE.choose_sep(cells) is None                                   # commas inside names stay
    assert SE.choose_sep(["Umwelt; Verkehr", "Umwelt", "Verkehr", "Bildung"]) == ";"
    assert SE.choose_sep(["Umwelt, Verkehr", "Umwelt", "Verkehr"]) == ","
    assert SE.choose_sep(["Umwelt|Verkehr", "Bildung|Umwelt"]) == "|"   # no single cell: | still splits
    assert SE.choose_sep(["a;b"], "none") is None
    assert SE.labels_of(["Umwelt; Verkehr", " umwelt ", "–"], ";") == ["Umwelt", "Verkehr", "umwelt"]
    # no hinted name: the text column with the fewest distinct values (not numbers, dates or links)
    h = ["nr", "titel", "x", "datum"]
    r = [[str(i), f"Titel {i}", ["Umwelt", "Verkehr"][i % 2], "2024-01-01"] for i in range(20)]
    assert SE.detect_label(h, r, None, {0}) == [2]


# ------------------------------------------------------------------ scheme file, keywords, sample
def test_scheme_file_and_prompt(tmp_path, monkeypatch):
    names = sorted(["Öffentlicher Verkehr", "Abfall & Recycling", "Bildung", "Bildung!"])
    doc = SE.build_scheme("partner-x", names, "de", ["BS"], "src", "Titel")
    assert doc["kind"] == "named" and doc["status"] == "test" and doc["body"] == "BS"
    assert [o["name"]["de"] for o in doc["options"]] == names                       # verbatim, alphabetical
    codes = [o["code"] for o in doc["options"]]
    assert len(set(codes)) == len(codes) and codes[1:3] == ["x:bildung", "x:bildung-2"]
    u, pre, cs = P.named_prompt(doc, dict(title="Tram", title_long="", text=""))
    assert "A = Abfall & Recycling" in u and f"{cs[-1]} = Keines dieser Themen" in u and pre == '{"thema": "'
    fr = SE.build_scheme("partner-y", ["Santé", "Transports"], "fr", ["GE", "VD"], "src", "Titre")
    assert "body" not in fr and fr["bodies"] == ["GE", "VD"] and fr["frame"]["de"] == fr["frame"]["fr"]
    assert P.named_prompt(fr, dict(title="t", title_long="", text=""))[1] == '{"theme": "'
    # status: test keeps the file out of compose / export, named() still reads it
    for f in ("bs-themen.yaml", "aps.yaml"):
        (tmp_path / f).write_text((SCH.HERE / f).read_text())
    (tmp_path / "partner-x.yaml").write_text(SE.scheme_yaml(doc))
    monkeypatch.setattr(SCH, "HERE", tmp_path); SCH.flat.cache_clear(); SCH._named_schemes.cache_clear()
    try:
        assert [s["id"] for s in SCH.named_schemes()] == ["bs-themen"]
        assert SCH.named("partner-x")["options"] == doc["options"]
    finally:
        SCH.flat.cache_clear(); SCH._named_schemes.cache_clear()


def test_keyword_stems_reproduce_s20():
    frozen = json.loads((ROOT / "eval/s20/keywords_frozen.json").read_text())["stems"]
    assert SE.keyword_stems(list(frozen)) == {k: sorted(v) for k, v in frozen.items()}
    st = SE.keyword_stems(["Dipartimento del territorio", "Dipartimento delle istituzioni", "Cancelleria dello Stato"])
    assert st["Dipartimento del territorio"] == ["dipar", "terri"]   # 'Dipartimento' is not in every name here
    forder = ["Verkehr", "Umwelt"]
    assert SE.kw_predict("Mehr Umweltschutz", {"Umwelt": ["umwel"], "Verkehr": ["verke"]}, forder) == "Umwelt"
    assert SE.kw_predict("nichts", {"Umwelt": ["umwel"], "Verkehr": ["verke"]}, forder) == "Verkehr"


def test_choose_labels_caps_at_51():
    items = [dict(id=i, labels=[f"L{i % 60:02d}"]) for i in range(600)] + [dict(id=999, labels=["L00", "Rare"])]
    kept, dropped = SE.choose_labels(items)
    assert len(kept) == 51 and kept == sorted(kept) and "L00" in kept and "Rare" in dropped


def test_stratified_sample_is_proportional_and_deterministic():
    items = [dict(id=i, labels=["A" if i < 600 else "B" if i < 900 else "C"]) for i in range(1000)]
    s1, how = SE.stratified_sample(items, 100)
    s2, _ = SE.stratified_sample(list(reversed(items)), 100)
    assert [x["id"] for x in s1] == [x["id"] for x in s2] and len(s1) == 100 and "proportional" in how
    c = {l: sum(x["labels"][0] == l for x in s1) for l in "ABC"}
    assert c == {"A": 60, "B": 30, "C": 10}
    assert SE.stratified_sample(items[:5], 10)[0] == items[:5]


def test_boot_diff_and_score_arm():
    d = SE.boot_diff([1, 1, 1, 0], [0, 1, 0, 0])
    assert d["diff"] == 0.5 and d["ci"][0] <= 0.5 <= d["ci"][1]
    names = ["A", "B", "none"]
    res = [dict(id=1, labels=["A"], rank=[0, 1, 2], lane="readings_agree"), dict(id=2, labels=["B", "A"], rank=[0, 1, 2], lane="please_check")]
    m, k1 = SE.score_arm(res, names)
    assert k1 == [1, 0] and m["top1"]["value"] == 0.5 and m["any_top1"]["value"] == 1.0 and m["top3"]["value"] == 1.0
    assert m["lanes"]["please_check"]["top1"]["k"] == 0 and m["per_label"]["A"]["recall"]["value"] == 1.0


# ------------------------------------------------------------------ end to end on the fake endpoint
def test_end_to_end_fake_endpoint(tmp_path, monkeypatch, fake):
    from querschnitt import client as C
    X = [json.loads(l) for l in open(FIX / "inputs_sample.jsonl")]
    labs = ["Umwelt", "Verkehr", "Bildung"]
    che = [dict(x, title=f"{['Umweltschutz', 'Verkehrspolitik', 'Bildungswesen'][i % 3]} und Klimaschutz im Kanton {i}")
           for i, x in enumerate(x for x in X if x["body"] == "CHE")][:12]          # shared words: BM25 finds neighbours
    inp = tmp_path / "inputs.jsonl.gz"
    with gzip.open(inp, "wt") as f:
        for x in che + [x for x in X if x["body"] != "CHE"]:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    gold = tmp_path / "Partner Liste.csv"
    gold.write_text("Geschäftsnummer;Titel;Kategorie\n" + "".join(
        f"{x['number']};{x['title'][:30].replace(';', ',')};\"{labs[i % 3]}{'; Umwelt' if i == 1 else ''}\"\n" for i, x in enumerate(che))
        + "99.9999;nicht da;Umwelt\n", encoding="utf-8")
    monkeypatch.setattr(SCH, "HERE", tmp_path / "schemes"); (tmp_path / "schemes").mkdir()
    SCH.flat.cache_clear()
    monkeypatch.setattr(SE, "BATCH_IN_PROCESS", True)
    monkeypatch.setenv("QS_BASE_URL", fake.url); monkeypatch.setenv("QS_API_KEY", "x"); monkeypatch.setenv("QS_NAME", "fake")
    orig = C.Guard.__init__
    monkeypatch.setattr(C.Guard, "__init__", lambda self, conc, max_rate, start=1.0, floor=0.15: orig(self, conc, max_rate, max_rate, floor))
    seen = {}
    real_prereg = SE.prereg

    def prereg(mode, out, title, body):
        seen["requests_before"] = len(fake.requests); seen["body"] = body
        return real_prereg(mode, out, title, body)
    monkeypatch.setattr(SE, "prereg", prereg)
    out = tmp_path / "run"
    try:
        SE.main([str(gold), "--n", "9", "--examples", "2", "--cap", "0.5", "--inputs", str(inp), "--out", str(out),
                 "--build", "first", "--prereg", "local", "--max-rate", "100", "--conc", "3"])
    finally:
        SCH.flat.cache_clear()
    assert seen["requests_before"] == 0 and "Primary: top-1" in seen["body"]           # registered before any call
    assert (out / "PREREG.md").read_text().count("make scheme-eval partner-partner-liste") == 1
    assert (out / "PREREG.sha256").exists()
    sch = yaml.safe_load((tmp_path / "schemes/partner-partner-liste.yaml").read_text())
    assert [o["name"]["de"] for o in sch["options"]] == sorted(labs) and sch["body"] == "CHE" and sch["status"] == "test"
    kw = json.loads((out / "keywords_frozen.json").read_text())
    assert kw["stems"]["Umwelt"] == ["umwel"]
    R = json.loads((out / "report.json").read_text())
    assert R["n_joined"] == 12 and R["join"]["not_joined"] == {"number not in the inputs": 1}
    assert R["arms"]["names"]["n"] == 9 and R["arms"]["names"]["not_scored"] == 0
    assert R["arms"]["examples"]["n"] == 9 and R["arms"]["examples_minus_names"]["n"] == 9
    assert R["build"] == "fp_fake_1" and R["usd"] > 0
    assert R["arms"]["names"]["any_top1"]["k"] >= R["arms"]["names"]["top1"]["k"]
    msgs = [r["messages"] for r in fake.requests]
    assert all(m[0]["role"] == "user" and m[-1]["role"] == "assistant" for m in msgs)    # no system message, prefill
    assert sum(P.EX_HEAD in m[0]["content"] for m in msgs) == 9                       # one examples reading per affair
    # rerun: everything cached, no new call, no second pre-registration
    n = len(fake.requests)
    SCH.flat.cache_clear()
    SE.main([str(gold), "--n", "9", "--examples", "2", "--cap", "0.5", "--inputs", str(inp), "--out", str(out),
             "--build", "first", "--prereg", "local", "--max-rate", "100", "--conc", "3"])
    SCH.flat.cache_clear()
    assert len(fake.requests) == n and (out / "PREREG.md").read_text().count("## ") == 1


def test_pin_build(tmp_path):
    lock = SE.pin_build(tmp_path / "r", "vllm-x-tp8-abcd1234", "swiss-ai/apertus-v1.5-8b")
    assert lock["fp"] == "vllm-x-tp8-abcd1234" and lock["key"].startswith("abcd1234-") and (tmp_path / "r" / lock["key"]).is_dir()
    assert SE.pin_build(tmp_path / "r", "other", "m") == lock                     # an existing lock is never replaced
    assert SE.pin_build(tmp_path / "s", "first", "m") is None and not (tmp_path / "s/state.json").exists()
