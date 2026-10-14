"""The nightly delta on a three-affair export on disk (no download), the batch against the fake endpoint: inputs are
rebuilt, new and changed affairs (input hash) are scored, rows are loaded, and a second night with no change scores
nothing."""
import argparse
import gzip
import json

from querschnitt import client as C


def gz(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def export(d, title3="Velowege im Kanton Bern"):
    gz(d / "bodies.ndjson.gz", [dict(body_key="CHE", type="federal", lang="de", legislative_name_de="Bundesversammlung"),
                                dict(body_key="BE", type="canton", lang="de", canton_key="BE", legislative_name_de="Grosser Rat")])
    A = [dict(id=1001, body_key="CHE", number="26.4001", title_de="Digitalisierung der Bundesverwaltung beschleunigen",
              begin_date="2026-10-12T00:00:00", type_name_de="Motion", type_harmonized_de="Motion", updated_at="2026-10-12T10:00:00"),
         dict(id=1002, body_key="BE", number="M 101-2026", title_de="Wolfsbestand im Berner Oberland regulieren",
              begin_date="2026-10-11T00:00:00", type_name_de="Motion", type_harmonized_de="Motion", updated_at="2026-10-11T10:00:00"),
         dict(id=1003, body_key="BE", number="M 102-2026", title_de=title3,
              begin_date="2026-10-10T00:00:00", type_name_de="Interpellation", type_harmonized_de="Interpellation", updated_at="2026-10-13T10:00:00")]
    gz(d / "affairs.ndjson.gz", A)
    gz(d / "contributors.ndjson.gz", [dict(id=1, affair_id=1001, role_harmonized="author", fullname="A. Muster", type="person",
                                           party_harmonized_de="FDP")])
    (d / "texts").mkdir(exist_ok=True)


def args(tmp_path, **kw):
    a = dict(since="2026-10-01", export=str(tmp_path / "opd"), inputs=str(tmp_path / "inputs.jsonl.gz"), run_dir=str(tmp_path / "run"),
             profile="full", plan=False, fetch=False, model=True, max_affairs=None, conc=3, max_rate=50.0, full_rebuild=False)
    a.update(kw)
    return argparse.Namespace(**a)


def test_delta_end_to_end(tmp_path, fake, monkeypatch, capsys):
    from querschnitt.cli import delta
    from querschnitt.store import Store
    monkeypatch.setattr(C.Guard.__init__, "__defaults__", (50.0, 0.15))      # no 1 req/s warm-up in tests
    for k, v in dict(QS_DB=str(tmp_path / "s.sqlite"), QS_BASE_URL=fake.url, QS_API_KEY="test", QS_KEY_FILE=str(tmp_path / "nokey"),
                     QS_EXPORT_DIR="", QS_INPUTS="", QS_RUN_DIR="").items():
        monkeypatch.setenv(k, v) if v else monkeypatch.delenv(k, raising=False)
    export(tmp_path / "opd")
    log = delta(args(tmp_path))
    assert log["todo"] == 3 and log["load"]["inserted"] > 0
    line = capsys.readouterr().out.strip().splitlines()[-1]
    assert line.startswith("affairs 3 · wall ") and "list-price USD" in line and "pending 0" in line
    st = Store()
    t = {r["affair_id"]: r for r in st.all("SELECT * FROM topics WHERE scheme = 'adhoc/digitalisierung'")}
    assert t[1001]["code"].endswith(":yes") and t[1003]["code"].endswith(":no")
    assert st.all("SELECT COUNT(*) AS n FROM topics WHERE scheme = 'aps' AND level = 1 AND rank = 1")[0]["n"] == 3
    assert all(r["build"] == "fp_fake_1" for r in st.all("SELECT build FROM topics"))
    assert not any(m["role"] == "system" for b in fake.requests for m in b["messages"])
    n_req = len(fake.requests)
    # second night, nothing changed: nothing scored, nothing sent
    log2 = delta(args(tmp_path))
    assert log2["todo"] == 0 and len(fake.requests) == n_req
    # an affair's title changes: only it is re-scored, its old rows closed
    export(tmp_path / "opd", title3="Velowege und digitale Verkehrsdaten im Kanton Bern")
    log3 = delta(args(tmp_path))
    assert log3["todo"] == 1
    cur = st.all("SELECT code FROM topics WHERE affair_id = 1003 AND scheme = 'adhoc/digitalisierung' AND valid_to IS NULL")
    assert [r["code"] for r in cur] == ["adhoc/digitalisierung:yes"]
    assert st.all("SELECT COUNT(*) AS n FROM topics WHERE affair_id = 1003 AND valid_to IS NOT NULL")[0]["n"] > 0
    runs = st.runs("delta")
    assert len(runs) == 3 and runs[0]["affairs"] == 1 and runs[0]["usd"] > 0


def test_delta_lite_chapter_only(tmp_path, fake, monkeypatch):
    from querschnitt.cli import delta
    from querschnitt.store import Store
    monkeypatch.setattr(C.Guard.__init__, "__defaults__", (50.0, 0.15))
    for k, v in dict(QS_DB=str(tmp_path / "s.sqlite"), QS_BASE_URL=fake.url, QS_API_KEY="test", QS_KEY_FILE=str(tmp_path / "nokey")).items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("QS_PROFILE", "lite")
    export(tmp_path / "opd")
    delta(args(tmp_path))
    st = Store()
    assert {r["scheme"] for r in st.all("SELECT scheme FROM topics")} == {"aps"}
    assert st.all("SELECT COUNT(*) AS n FROM topics WHERE level = 2")[0]["n"] == 0
