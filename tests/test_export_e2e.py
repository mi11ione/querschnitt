"""Run (fake endpoint) → export → `load --auto` path → API: one `p` everywhere (the API row, the app's `ch_p` and the
detail panel all carry the calibrated value from eval/calibration.json, with the federal map when examples were shown),
the API's affair totals equal the export's, and the data release tarball holds what `make data` unpacks."""
import gzip
import json
import os
import subprocess
import tarfile
from pathlib import Path

import pytest

from querschnitt import client as C
from querschnitt.fake_endpoint import FakeEndpoint
from querschnitt.store import ROOT
from test_delta import args, export


@pytest.fixture
def fake():
    """The fake endpoint serves the build eval/calibration.json was fitted on (the calibration applies to its rows only)."""
    with FakeEndpoint(fingerprint=json.loads((ROOT / "eval/calibration.json").read_text())["build"]) as f:
        yield f


@pytest.fixture
def exported(tmp_path, fake, monkeypatch):
    from querschnitt import export as X
    from querschnitt.cli import delta
    monkeypatch.setattr(C.Guard.__init__, "__defaults__", (50.0, 0.15))
    for k, v in dict(QS_DB=str(tmp_path / "run.sqlite"), QS_BASE_URL=fake.url, QS_API_KEY="test", QS_KEY_FILE=str(tmp_path / "nokey")).items():
        monkeypatch.setenv(k, v)
    for k in ("QS_EXPORT_DIR", "QS_INPUTS", "QS_RUN_DIR", "QS_PROFILE", "QS_STEPS"):
        monkeypatch.delenv(k, raising=False)
    export(tmp_path / "opd")
    delta(args(tmp_path))
    # one slice affair the run never scored (the export lists it with ch = null) and one before the slice
    with gzip.open(tmp_path / "inputs.jsonl.gz", "rt") as f:
        X0 = [json.loads(l) for l in f]
    extra = [dict(X0[-1], id=1004, title="Noch nicht gelesen", date="2026-10-09", input_hash="x1"),
             dict(X0[-1], id=1005, title="Altes Geschäft", date="2019-03-01", input_hash="x2")]
    with gzip.open(tmp_path / "inputs.jsonl.gz", "wt") as f:
        for x in X0 + extra:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    out = tmp_path / "appdata"
    X.main(["--run", str(tmp_path / "run"), "--inputs", str(tmp_path / "inputs.jsonl.gz"), "--opd", str(tmp_path / "opd"),
            "--out", str(out), "--since", "2025-01-01", "--topics-file"])
    return tmp_path, out


def test_one_p_and_equal_totals(exported, tmp_path):
    from fastapi.testclient import TestClient
    from querschnitt.api import create_app
    from querschnitt.calibrate import Calibration
    from querschnitt.store import Store
    _, out = exported
    meta = json.loads((out / "meta.json").read_text())
    cols = json.loads((out / "affairs.json").read_text())["cols"]
    det = {}
    for p in (out / "detail").glob("*.json"):
        det.update({int(k): v for k, v in json.loads(p.read_text()).items()})
    st = Store(path=str(tmp_path / "api.sqlite"), dsn="")
    st.load_affairs_export(out)
    st.load_topics(out / "topics.jsonl.gz")
    cal = Calibration.load(ROOT / "eval/calibration.json")
    with TestClient(create_app(st, app_dir=tmp_path / "noapp")) as c:
        assert meta["affairs"] == 4 and len(cols["id"]) == 4
        assert c.get("/metrics").json()["affairs"] == meta["affairs"]
        assert sum(b["affairs"] for b in c.get("/coverage").json()["bodies"]) == meta["affairs"]
        assert sum(b["scored"] for b in c.get("/coverage").json()["bodies"]) == meta["scored"] == 3
        for i, aid in enumerate(cols["id"]):
            rows = [r for r in c.get(f"/affairs/{aid}/topics?scheme=aps").json()["topics"] if r["level"] == 1]
            if cols["ch"][i] is None:
                assert rows == [] and det[aid]["aps"] is None
                continue
            r1 = next(r for r in rows if r["rank"] == 1)
            assert cols["ch_p"][i] == round(r1["p"], 3)                       # app list value == API row
            assert det[aid]["aps"]["p"][0] == r1["p"]                         # app detail value == API row
            assert [det[aid]["aps"]["p_raw"][k] for k in range(len(rows))] == [r["p_raw"] for r in sorted(rows, key=lambda r: r["rank"])]
            key = "aps-fed" if det[aid]["aps"]["examples"] else "aps"
            assert r1["p"] == round(cal.apply(key, r1["p_raw"]), 4) and r1["cutoffs_id"] == f"aps@{cal.build[-8:]}"
        assert any(det[a]["aps"] and det[a]["aps"]["examples"] for a in det)   # the federal map is exercised


def test_release_tarball(exported, tmp_path):
    _, out = exported
    tgz = tmp_path / "dist" / "querschnitt-data.tar.gz"
    env = dict(os.environ, APP_DATA=str(out), INPUTS=str(tmp_path / "inputs.jsonl.gz"), OUT=str(tgz), SINCE="2025-01-01")
    r = subprocess.run(["sh", str(ROOT / "tools/make_data_release.sh")], env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr + r.stdout
    with tarfile.open(tgz) as t:
        names = set(t.getnames())
        assert {"app/data/affairs.json", "app/data/meta.json", "data/inputs.jsonl.gz", "data/topics.jsonl.gz"} <= names
        assert not any(n.startswith("/") or ".." in n for n in names)
        rows = [json.loads(l) for l in gzip.open(t.extractfile("data/inputs.jsonl.gz"), "rt")]
    assert sorted(x["id"] for x in rows) == [1001, 1002, 1003, 1004]                    # the slice only
    assert all(len(x["text"] or "") <= 1500 for x in rows)
    assert "affairs 4" in r.stdout
