"""Eval maths (Wilson, F1, multi-class) and `querschnitt eval` on positives lists, 0/1 labels and APS codes."""
import pytest

from querschnitt.evaluate import binary, evaluate, multiclass, report, wilson


def test_wilson_known_values():
    lo, hi = wilson(8, 10)
    assert lo == pytest.approx(0.4902, abs=1e-4) and hi == pytest.approx(0.9433, abs=1e-4)
    lo, hi = wilson(0, 20)
    assert lo == 0.0 and hi == pytest.approx(0.1611, abs=1e-4)
    assert wilson(0, 0) == (None, None)


def test_binary_counts():
    items = [(True, True)] * 6 + [(True, False)] * 2 + [(False, True)] * 1 + [(False, False)] * 11
    b = binary(items, True)
    assert (b["tp"], b["fn"], b["fp"], b["tn"]) == (6, 2, 1, 11)
    assert b["recall"]["value"] == 0.75 and b["precision"]["value"] == pytest.approx(6 / 7, abs=1e-4)
    assert b["accuracy"]["value"] == 0.85 and b["f1"]["value"] == pytest.approx(12 / 15, abs=1e-4)
    lo, hi = b["f1"]["ci"]
    assert lo <= 0.8 <= hi
    assert "precision" not in binary([(True, True), (True, False)], False)


def test_multiclass():
    items = [("a", "a", ["a", "b"]), ("a", "b", ["b", "a"]), ("b", "b", ["b"]), ("c", "b", ["b", "a"])]
    m = multiclass(items)
    assert m["accuracy"]["value"] == 0.5 and m["top3"]["value"] == 0.75
    assert m["per_class"]["b"]["precision"] == pytest.approx(1 / 3, abs=1e-4) and m["per_class"]["a"]["recall"] == 0.5


def _yes_no(store):
    rows = store.all("SELECT affair_id, code FROM qs_topics WHERE scheme = 'adhoc/digitalisierung' AND valid_to IS NULL")
    return [r["affair_id"] for r in rows if r["code"].endswith(":yes")], [r["affair_id"] for r in rows if r["code"].endswith(":no")]


def test_positives_list(store, tmp_path):
    yes, no = _yes_no(store)
    p = tmp_path / "dvs.csv"
    p.write_text("affair_id\n" + "\n".join(map(str, yes + no[:2] + [999999999])) + "\n")
    r = evaluate(p, store)["schemes"]["adhoc/digitalisierung"]
    assert r["kind"] == "positives_only" and r["not_scored"] == 1
    assert r["overall"]["recall"]["k"] == len(yes) and r["overall"]["recall"]["n"] == len(yes) + 2
    assert len(r["misses"]) == 2 and {m["level"] for m in r["misses"]} <= {"federal", "cantonal", "communal", "other"}
    assert set(r["by"]["level"]) and "recall" in report(evaluate(p, store))


def test_binary_labels_semicolon(store, tmp_path):
    yes, no = _yes_no(store)
    p = tmp_path / "gold.csv"
    p.write_text("affair_id;label\n" + "".join(f"{a};ja\n" for a in yes) + "".join(f"{a};nein\n" for a in no[:5]) + f"{no[5]};ja\n")
    r = evaluate(p, store)["schemes"]["adhoc/digitalisierung"]
    o = r["overall"]
    assert r["kind"] == "binary" and o["tp"] == len(yes) and o["tn"] == 5 and o["fn"] == 1 and o["fp"] == 0


def test_aps_codes(store, tmp_path):
    rows = store.all("SELECT affair_id, code FROM qs_topics WHERE scheme = 'aps' AND level = 1 AND rank = 1 AND valid_to IS NULL ORDER BY affair_id")
    p = tmp_path / "aps.csv"
    lines = ["affair_id,scheme,code"] + [f"{r['affair_id']},aps,{r['code']}" for r in rows[:10]]
    lines += [f"{r['affair_id']},aps,{r['code'].replace('aps:', '')}" for r in rows[10:15]]
    lines += [f"{rows[15]['affair_id']},aps,aps:none"]
    p.write_text("\n".join(lines) + "\n")
    r = evaluate(p, store)["schemes"]["aps"]
    assert r["kind"] == "multiclass" and r["overall"]["accuracy"]["k"] == 15 and r["overall"]["accuracy"]["n"] == 16
    assert len(r["misses"]) == 1 and r["misses"][0]["gold"] == "aps:none"
    assert "federal" in r["by"]["level"] or "cantonal" in r["by"]["level"]


def test_eval_ignores_editor_rows(store, tmp_path):
    yes, _ = _yes_no(store)
    store.decide(yes[0], "adhoc/digitalisierung", "adhoc/digitalisierung:no", "confirm", "x")
    p = tmp_path / "g.csv"
    p.write_text("affair_id\n" + "\n".join(map(str, yes)) + "\n")
    r = evaluate(p, store)["schemes"]["adhoc/digitalisierung"]
    assert r["overall"]["recall"]["k"] == len(yes)        # the machine's yes, not the editor's no
