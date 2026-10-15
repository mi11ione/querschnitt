"""A parliament's own labels in the export (export.OWN): Basel-Stadt's CSV by number, Ticino's S29 items by OPD id, the
scheme entries the app names them from, and the defaults ops/refresh-site.sh relies on (extra ranges, run dirs)."""
import json

from querschnitt import export as X
from querschnitt.scheme import named


def test_gold_readers(tmp_path):
    ti, bs = named("ti-dipartimenti"), named("bs-themen")
    items = tmp_path / "items.jsonl"
    items.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in (
        dict(id=11, number="I1.23", gold="Dipartimento del territorio"),
        dict(id=12, number="I1.23", gold=ti["none"]["name"]["it"]),          # a number can recur: keyed by id
    )), encoding="utf-8")
    assert X._gold_items(ti, items) == {11: ["DT", None], 12: ["none", None]}
    csv = tmp_path / "bs.csv"
    csv.write_text("﻿Signatur;Thema 1;Thema 2\n19.5001;Abfall & Recycling;\n19.5002;Arbeitsmarkt;Abfall & Recycling\n", encoding="utf-8")
    assert X._gold_bs(bs, csv) == {("BS", "19.5001"): ["abfall-recycling", None], ("BS", "19.5002"): ["arbeitsmarkt", "abfall-recycling"]}


def test_own_gold_skips_missing_files(tmp_path, monkeypatch):
    monkeypatch.setattr(X, "OWN", {k: dict(v, gold=(v["gold"][0], tmp_path / "missing")) for k, v in X.OWN.items()})
    assert X.own_gold() == {}


def test_scheme_entries():
    ti = X.scheme_entry(named("ti-dipartimenti"))
    assert ti["body"] == "TI" and ti["names"]["fr"] and ti["source"]["de"] == "Federführung laut OpenParlData (Gran Consiglio Ticino)"
    assert [o["abbr"]["de"] for o in ti["options"][:-1]] == [o["code"] for o in ti["options"][:-1]]
    assert ti["options"][-1]["code"] == "none" and "abbr" not in ti["options"][-1]
    bs = X.scheme_entry(named("bs-themen"))
    assert "names" not in bs and "abbr" not in bs["options"][0] and bs["source"]["de"].endswith("CC BY 4.0")


def test_defaults(monkeypatch):
    got = {}
    monkeypatch.setattr(X, "run", lambda a: got.update(vars(a)))
    X.main([])
    assert got["extra"] == ["BS:2019-01-01:2024-12-31", "TI:2023-01-01:2024-12-31"]
    assert ((X.ROOT / "runs/s29/state.json").exists()) == any(r.endswith("/runs/s29") for r in got["run"].split(","))
