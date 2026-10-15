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
             profile="full", plan=False, fetch=False, model=True, max_affairs=None, conc=3, max_rate=50.0, full_rebuild=False, last=None)
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
    assert log["steps"] == ["ch", "sub", "yn", "bi", "ev"]                      # the nightly default, not the batch's
    line = capsys.readouterr().out.strip().splitlines()[-1]
    assert line.startswith("affairs 3 · wall ") and "list-price USD" in line and "pending 0" in line
    st = Store()
    t = {r["affair_id"]: r for r in st.all("SELECT * FROM qs_topics WHERE scheme = 'adhoc/digitalisierung'")}
    assert t[1001]["code"].endswith(":yes") and t[1003]["code"].endswith(":no")
    assert st.all("SELECT COUNT(*) AS n FROM qs_topics WHERE scheme = 'aps' AND level = 1 AND rank = 1")[0]["n"] == 3
    assert all(r["build"] == "fp_fake_1" for r in st.all("SELECT build FROM qs_topics"))
    assert t[1001]["evidence"] and t[1003]["evidence"] is None          # the ev step ran: the flag quotes its title
    assert not any(m["role"] == "system" for b in fake.requests for m in b["messages"])
    n_req = len(fake.requests)
    # second night, nothing changed: nothing scored, nothing sent
    log2 = delta(args(tmp_path))
    assert log2["todo"] == 0 and len(fake.requests) == n_req
    # an affair's title changes: only it is re-scored, its old rows closed
    export(tmp_path / "opd", title3="Velowege und digitale Verkehrsdaten im Kanton Bern")
    log3 = delta(args(tmp_path))
    assert log3["todo"] == 1
    cur = st.all("SELECT code FROM qs_topics WHERE affair_id = 1003 AND scheme = 'adhoc/digitalisierung' AND valid_to IS NULL")
    assert [r["code"] for r in cur] == ["adhoc/digitalisierung:yes"]
    assert st.all("SELECT COUNT(*) AS n FROM qs_topics WHERE affair_id = 1003 AND valid_to IS NOT NULL")[0]["n"] > 0
    runs = st.runs("delta")
    assert len(runs) == 3 and runs[0]["affairs"] == 1 and runs[0]["usd"] > 0


def test_delta_lite_chapter_and_subtopic(tmp_path, fake, monkeypatch):
    """lite = `ch sub`: the chapter as measured (read back from the subtopic), no ad-hoc topics, no quote."""
    from querschnitt.cli import delta
    from querschnitt.store import Store
    monkeypatch.setattr(C.Guard.__init__, "__defaults__", (50.0, 0.15))
    for k, v in dict(QS_DB=str(tmp_path / "s.sqlite"), QS_BASE_URL=fake.url, QS_API_KEY="test", QS_KEY_FILE=str(tmp_path / "nokey")).items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("QS_PROFILE", "lite")
    monkeypatch.setenv("QS_TOPICS_OUT", str(tmp_path / "out" / "topics.jsonl.gz"))
    export(tmp_path / "opd")
    log = delta(args(tmp_path))
    st = Store()
    assert log["steps"] == ["ch", "sub"]
    assert {r["scheme"] for r in st.all("SELECT scheme FROM qs_topics")} == {"aps"}
    assert st.all("SELECT COUNT(*) AS n FROM qs_topics WHERE level = 2")[0]["n"] > 0
    # the night ends with the topics file for OPD's Hop loader: every current machine row of the store
    f = log["topics_file"]
    assert f["path"] == str(tmp_path / "out" / "topics.jsonl.gz")
    with gzip.open(f["path"], "rt") as fh:
        rows = [json.loads(l) for l in fh]
    assert f["rows"] == len(rows) == st.one("SELECT COUNT(*) AS n FROM qs_topics WHERE valid_to IS NULL")["n"] > 0
    assert {r["affair_id"] for r in rows} == {1001, 1002, 1003} and all(r["valid_from"].endswith("Z") for r in rows)


def test_delta_full_writes_no_topics_file_unless_asked(tmp_path, fake, monkeypatch):
    from querschnitt.cli import delta
    monkeypatch.setattr(C.Guard.__init__, "__defaults__", (50.0, 0.15))
    for k, v in dict(QS_DB=str(tmp_path / "s.sqlite"), QS_BASE_URL=fake.url, QS_API_KEY="test", QS_KEY_FILE=str(tmp_path / "nokey")).items():
        monkeypatch.setenv(k, v)
    for k in ("QS_PROFILE", "QS_TOPICS_OUT", "QS_EXPORT_DIR", "QS_INPUTS", "QS_RUN_DIR"):
        monkeypatch.delenv(k, raising=False)
    export(tmp_path / "opd")
    assert "topics_file" not in delta(args(tmp_path, model=False))
    out = tmp_path / "asked.jsonl.gz"
    assert delta(args(tmp_path, model=False, topics_out=str(out)))["topics_file"]["path"] == str(out) and out.exists()


def add_affairs(d, extra, title3=None):
    """Re-write the mini export with extra affairs (and optionally a changed title for 1003)."""
    export(d, **({"title3": title3} if title3 else {}))
    with gzip.open(d / "affairs.ndjson.gz", "rt") as f:
        A = [json.loads(l) for l in f]
    gz(d / "affairs.ndjson.gz", A + extra)


def new_affair(i, title, day="2026-10-13"):
    return dict(id=i, body_key="BE", number=f"M {i}", title_de=title, begin_date=f"{day}T00:00:00", type_name_de="Motion",
                type_harmonized_de="Motion", updated_at=f"{day}T10:00:00")


def env(tmp_path, fake, monkeypatch):
    monkeypatch.setattr(C.Guard.__init__, "__defaults__", (50.0, 0.15))
    for k, v in dict(QS_DB=str(tmp_path / "s.sqlite"), QS_BASE_URL=fake.url, QS_API_KEY="test", QS_KEY_FILE=str(tmp_path / "nokey")).items():
        monkeypatch.setenv(k, v)
    for k in ("QS_EXPORT_DIR", "QS_INPUTS", "QS_RUN_DIR", "QS_PROFILE", "QS_STEPS"):
        monkeypatch.delenv(k, raising=False)


def test_cut_then_drain(tmp_path, fake, monkeypatch, capsys):
    """Pass 1 without the endpoint queues new and changed affairs; pass 2 scores exactly the queue, whatever --since says."""
    from querschnitt.cli import delta
    from querschnitt.store import Store
    env(tmp_path, fake, monkeypatch)
    export(tmp_path / "opd")
    (tmp_path / "opd" / "index.json").write_text(json.dumps({"generated_at": "2026-10-14T06:35:00Z", "files": []}))
    delta(args(tmp_path))                                                   # night 0: 3 affairs scored
    st = Store()
    assert st.metrics()["pending"] == 0
    add_affairs(tmp_path / "opd", [new_affair(1010, "Digitale Signatur im Grossen Rat"), new_affair(1011, "Schulweg Sicherheit")],
                title3="Velowege und digitale Verkehrsdaten im Kanton Bern")
    last = tmp_path / "last.json"
    n0 = len(fake.requests)
    cut = delta(args(tmp_path, model=False, since="2026-10-13", last=str(last)))
    assert len(fake.requests) == n0                                          # the endpoint is cut: no call
    m = st.metrics()
    assert m["pending"] == 3 and cut["new_affairs"] == 2 and cut["queued"] == 3
    assert {r["affair_id"] for r in st.all("SELECT affair_id FROM qs_queue")} == {1010, 1011, 1003}
    assert "pending 3" in capsys.readouterr().out
    drain = delta(args(tmp_path, since="2030-01-01", last=str(last)))       # a --since that matches nothing
    assert drain["scored"] == 3 and len(fake.requests) > n0
    m = st.metrics()
    assert m["pending"] == 0 and st.all("SELECT COUNT(*) AS n FROM qs_queue")[0]["n"] == 0
    cur = {r["affair_id"]: r["code"] for r in st.all("SELECT affair_id, code FROM qs_topics WHERE scheme = 'adhoc/digitalisierung' AND valid_to IS NULL")}
    assert cur[1010].endswith(":yes") and cur[1011].endswith(":no") and cur[1003].endswith(":yes")
    L = json.loads(last.read_text())
    assert L["date"] and L["opd_export_generated"] == "2026-10-14T06:35:00Z" and L["new_affairs"] == 2
    assert L["pending_after_cut"] == 3 and L["pending_after_drain"] == 0 and L["scored"] == 3
    assert L["drain_minutes"] is not None and L["usd"] > 0
    run = st.runs("delta", 1)[0]
    note = json.loads(run["note"])
    assert note["pending_before"] == 3 and note["pending_after"] == 0 and note["drain_s"] >= 0
    # a failed drain keeps the queue: the next model pass picks it up
    add_affairs(tmp_path / "opd", [new_affair(1012, "Digitale Archive")], title3="Velowege und digitale Verkehrsdaten im Kanton Bern")
    fake.mode = "bad"                                     # the endpoint answers 400: every call of the drain fails
    delta(args(tmp_path))
    fake.mode = "logprobs"
    assert Store().metrics()["pending"] == 1
    delta(args(tmp_path, since="2030-01-01"))
    assert Store().metrics()["pending"] == 0


def test_pending_is_the_queue_not_the_backlog(tmp_path, fake, monkeypatch):
    """Affairs in scope without rows that the nightly never queued (the corpus run's backlog) are `unscored_in_scope`."""
    from querschnitt.cli import delta
    from querschnitt.store import Store
    env(tmp_path, fake, monkeypatch)
    export(tmp_path / "opd")
    delta(args(tmp_path, model=False))                    # first night without the endpoint: 3 new affairs queued
    st = Store()
    assert st.metrics()["pending"] == 3
    st.ex("DELETE FROM qs_queue"); st.commit()            # the corpus run owns them (backlog), not the nightly
    m = st.metrics()
    assert m["pending"] == 0 and m["unscored_in_scope"] == 3
    # affairs loaded from the static export (no input hash) that already carry rows are not re-queued
    delta(args(tmp_path))                                 # nothing new or changed: nothing to score
    assert Store().metrics()["pending"] == 0 and Store().runs("delta", 1)[0]["affairs"] == 0


def test_static_export_load_keeps_input_hashes(tmp_path, fake, monkeypatch):
    """ops/nightly.sh loads app/data before the delta; that must not erase the hashes the delta compares against."""
    from querschnitt.cli import delta
    from querschnitt.store import Store
    env(tmp_path, fake, monkeypatch)
    export(tmp_path / "opd")
    delta(args(tmp_path))
    st = Store()
    before = {r["id"]: r["input_hash"] for r in st.all("SELECT id, input_hash FROM qs_affairs")}
    d = tmp_path / "appdata"; d.mkdir()
    (d / "affairs.json").write_text(json.dumps(dict(n=3, cols=dict(id=[1001, 1002, 1003], body=["CHE", "BE", "BE"],
                                                                   date=["2026-10-12", "2026-10-11", "2026-10-10"], title=["a", "b", "c"]))))
    st.load_affairs_export(d)
    assert {r["id"]: r["input_hash"] for r in st.all("SELECT id, input_hash FROM qs_affairs")} == before
    n = len(fake.requests)
    delta(args(tmp_path))
    assert len(fake.requests) == n and Store().metrics()["pending"] == 0


def test_budget_stop_is_not_an_outage(tmp_path, fake, monkeypatch):
    """A run that reached its list-price cap stops with a `Budget` STOP.md: ops/pipeline.py and ops/watchdog.sh resume
    `# Errors` stops (an endpoint outage) by themselves once the endpoint answers, which for a spent budget would restart
    the run forever."""
    from querschnitt import batch
    env(tmp_path, fake, monkeypatch)
    inp = tmp_path / "inputs.jsonl.gz"
    gz(inp, [json.loads(l) for l in open("tests/fixtures/inputs_sample.jsonl")][:2])
    run = tmp_path / "run"; run.mkdir()
    (run / "ledger.jsonl").write_text(json.dumps(dict(ts=0, tag="batch", usd=5.0)) + "\n")
    batch.main(["run", "--inputs", str(inp), "--out", str(run), "--since", "0000", "--cap", "1", "--no-examples", "--max-rate", "50"])
    stop = (run / "STOP.md").read_text()
    assert "BUDGET" in stop and stop.startswith("# Budget") and not stop.startswith("# Errors")


def test_endpoint_ok_before_the_first_lock(tmp_path, fake, monkeypatch):
    """ops/endpoint_ok.py: a run stopped on errors before its first answer has no lock (no state.json); the endpoint
    answering at all is then enough. With a lock, the build must be the locked one."""
    import importlib.util
    import pathlib
    env(tmp_path, fake, monkeypatch)
    spec = importlib.util.spec_from_file_location("endpoint_ok", pathlib.Path(__file__).parents[1] / "ops/endpoint_ok.py")
    E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)
    run = tmp_path / "run"; run.mkdir()
    assert E.ok(run)
    (run / "state.json").write_text(json.dumps(dict(lock=dict(model=fake.model, fp="fp_other", key="x"))))
    assert not E.ok(run)
    (run / "state.json").write_text(json.dumps(dict(lock=dict(model=fake.model, fp=fake.fp, key="x"))))
    assert E.ok(run)
    fake.mode = "error"
    assert not E.ok(run)
    fake.mode = "logprobs"
