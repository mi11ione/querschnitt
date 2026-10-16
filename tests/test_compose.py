"""Decision rules (VISION §4.1): read-back chapter, lanes, ad-hoc flags."""
from querschnitt import prompts as P
from querschnitt.compose import chapter_decision, yn_decision


def vec(top, p=0.8, n=25):
    v = [(1 - p) / (n - 1)] * n
    v[top] = p
    return v


def test_readback_picks_subtopic_chapter():
    r1 = dict(p=vec(16, 0.6)); r2 = dict(p=vec(17, 0.5))
    chs = P.subtopic_chapters([(a + b) / 2 for a, b in zip(r1["p"], r2["p"])])
    opts = P.subtopic_options(chs)
    ps = [0.0] * (len(opts) + 1)
    k = next(i for i, (c, j) in enumerate(opts) if c == 17)
    ps[k] = 0.9; ps[0] = 0.1
    d = chapter_decision(r1, r2, dict(chs=chs, p=ps))
    assert d["ch"] == 17 and d["lane"] == "please_check" and d["readback"]


def test_single_confident_reading_agrees():
    d = chapter_decision(dict(p=vec(9, 0.95)), None, None)
    assert d["ch"] == 9 and d["lane"] == "readings_agree" and d["n_readings"] == 1


def test_none_is_shipped_when_top():
    d = chapter_decision(dict(p=vec(24, 0.7)), dict(p=vec(24, 0.7)), dict(chs=[0, 1], p=[1.0] + [0.0] * 20))
    assert d["ch"] == 24


def test_yesno_lanes():
    assert yn_decision(dict(p_yes=0.95), None)["lane"] == "readings_agree"
    d = yn_decision(dict(p_yes=0.6), dict(p_yes=0.3))
    assert d["lane"] == "please_check" and not d["flag"]
    assert yn_decision(dict(p_yes=0.8), dict(p_yes=0.9))["flag"]


def test_examples_format_matches_loop():
    t = dict(question={"de": "Q?"}, answer_yes={"de": "Ja"})
    u, _ = P.yesno_prompt(t, "de", "Titel X", "", "a", [("Beispiel eins", True), ("Beispiel zwei", False)])
    assert "Beispiele, von einer Redaktorin entschieden:\n- Titel: Beispiel eins → A\n- Titel: Beispiel zwei → B\n\nGeschäft:" in u


def test_topic_examples_nearest_and_stable():
    from querschnitt.examples import topic_examples
    t = dict(id="adhoc/x", question={"de": "Q?"}, answer_yes={"de": "Ja"},
             examples=[dict(affair_id=1, title="Rechenzentren im Kanton", match=True),
                       dict(affair_id=2, title="Velowege in der Stadt", match=False),
                       dict(affair_id=3, title="Digitale Verwaltung und Rechenzentren", match=True)])
    a = dict(id=9, title="Neue Rechenzentren bauen", title_long="", lang="de")
    ex = topic_examples(t, a)
    assert ex and ex[0][1] is True and all(isinstance(m, bool) for _, m in ex)
    assert topic_examples(t, a) == ex                       # same examples → same prompt id in batch and compose
    assert topic_examples(dict(id="adhoc/y", question={}, answer_yes={}), a) is None


def test_example_neighbours_same_in_every_process():
    """BM25 neighbours must not depend on the per-process hash seed (else a restarted run asks other prompts)."""
    import os, subprocess, sys
    code = ("import sys; sys.path.insert(0, 'src'); from querschnitt.examples import ExamplePool; "
            "p = ExamplePool([dict(oid=i, title=t, chapter=0) for i, t in enumerate(['Asyl Gesetz Revision', 'Gesetz Asyl', "
            "'Revision Asyl Gesetz', 'Asyl Revision', 'Gesetz Revision Asyl Verfahren', 'Asyl', 'Revision Gesetz'])], k=5); "
            "print([e['oid'] for e in p.neighbours(dict(id=-1, title='Asyl Gesetz Revision Verfahren', text=''))])")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    outs = {subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True,
                           env={**os.environ, "PYTHONHASHSEED": str(s)}).stdout for s in range(12)}
    assert len(outs) == 1, outs


def test_verify_rows_in_compose_match_batch_and_adhoc():
    """S27 in compose: the verify readings are part of the decision's prompt ids (as Neues Thema's saved rows, so the
    nightly row of the same decision is not a new version), and a verify reading that needs its order b counts only with
    it (the batch and Neues Thema always ask both; a run stopped in between must not decide on order a alone)."""
    from querschnitt.compose import decide
    t = dict(id="adhoc/t", names={"de": "Wolf"}, question={"de": "Betrifft es «Wolf»?"}, answer_yes={"de": "Ja, Wolf"},
             cutoff=0.5, verify=True)
    a = dict(id=7, body="CHE", lang="de", title="Wolfsbestand regulieren", title_long="", text="")

    def row(u_p, py):
        return dict(pid=P.pid(*u_p), p_yes=py, meta={"fp": "x"})

    ya = row(P.yesno_prompt(t, "de", a["title"], "", "a"), 0.95)
    va = row(P.verify_prompt(t, "de", a["title"], "", "a"), 0.45)          # 0.1 < p < 0.9: order b is asked too
    vb = row(P.verify_prompt(t, "de", a["title"], "", "b"), 0.75)
    rows = {r["pid"]: r for r in (ya, va, vb)}
    d = decide(a, rows, lambda a: ("", "", None), [t])[t["id"]]
    assert d["verified"] is True and d["lane"] == "readings_agree" and d["pids"] == [ya["pid"], va["pid"], vb["pid"]]
    del rows[vb["pid"]]                                                       # stopped between the two verify readings
    d = decide(a, rows, lambda a: ("", "", None), [t])[t["id"]]
    assert "verified" not in d and d["lane"] == "readings_agree" and d["pids"] == [ya["pid"]]


def chapter_affair(fp):
    """A federal affair with one confident chapter reading of build `fp` (no subtopic row yet)."""
    a = dict(id=8, body="CHE", lang="de", title="Bahnausbau", title_long="", text="", input_hash="h")
    u, p = "kapitel", "{"
    rows = {P.pid(u, p): dict(pid=P.pid(u, p), p=vec(9, 0.95), meta={"fp": fp})}
    return a, rows, lambda a: (u, p, None)


def test_calibration_only_for_its_build(monkeypatch, caplog):
    """eval/calibration.json is applied only to rows of the build it was fitted on; `cutoffs_id` names that build. Rows of
    another build: p null, the readings lane, no cutoffs_id, and one warning however many rows."""
    from querschnitt import compose as C
    from querschnitt.calibrate import Calibration
    from querschnitt.store import ROOT
    cal = Calibration.load(ROOT / "eval/calibration.json")
    assert cal.build == "vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840"
    monkeypatch.setattr(C, "_WARNED", set())
    a, rows, ch1 = chapter_affair(cal.build)
    d = C.decide(a, rows, ch1, [])
    pc = cal.apply("aps", 0.95)
    assert d["aps"]["p_cal"] == pc and d["aps"]["lane"] == ("please_check" if pc < C.LANE_TAU else "pass")
    r1 = C.topic_rows(a, d, dict(model="m", fp=cal.build), cal)[0]
    assert r1["p"] == round(pc, 4) and r1["p_raw"] == 0.95 and r1["cutoffs_id"] == "aps@dd237840"
    caplog.set_level("WARNING", logger="querschnitt.compose")
    a, rows, ch1 = chapter_affair("vllm-other-build-12345678")
    for _ in range(2):
        d = C.decide(a, rows, ch1, [])
        assert d["aps"]["p_cal"] is None and d["aps"]["lane"] == "pass"           # readings agree → pass, as without a file
        r1 = C.topic_rows(a, d, dict(model="m", fp="vllm-other-build-12345678"), cal)[0]
        assert r1["p"] is None and r1["p_raw"] == 0.95 and r1["cutoffs_id"] is None and r1["lane"] == "pass"
    warned = [r for r in caplog.records if r.name == "querschnitt.compose"]
    assert len(warned) == 1 and "dd237840" in warned[0].getMessage() and "12345678" in warned[0].getMessage()


def test_be_directorates_rows():
    """Bern's directorates (flat scheme, decided for body BE) are written as topic rows: one level-1, rank-1 row per
    affair with the code of the reading in the affair's language, raw p, the readings lane and both prompt ids; every
    code is one the OPD seed carries (upstream/opd/tools/gen_seed.py seeds every scheme file)."""
    import importlib.util
    from querschnitt.compose import decide, topic_rows
    from querschnitt.scheme import flat
    from querschnitt.store import ROOT
    sch = flat("be-directorates"); n = len(sch["options"]) + 1
    a = dict(id=9, body="BE", lang="de", title="Steuergesetz Revision", title_long="", text="", input_hash="h",
             title_alt="Révision de la loi sur les impôts", alt_lang="fr", bilingual=True)

    def reading(title, lang, top, p):
        u, pr = P.flat_prompt(sch, title, lang)[:2]
        v = [(1 - p) / (n - 1)] * n; v[top] = p
        return dict(pid=P.pid(u, pr), p=v, meta={"fp": "x"})

    de = reading(a["title"], "de", 3, 0.8)
    lock = dict(model="m", fp="x")
    for fr_top, lane in ((3, "readings_agree"), (1, "please_check")):
        fr = reading(a["title_alt"], "fr", fr_top, 0.6)
        d = decide(a, {de["pid"]: de, fr["pid"]: fr}, lambda a: ("", "", None), [])
        rs = [r for r in topic_rows(a, d, lock, None, "2026-10-15T00:00:00Z") if r["scheme"] == "be-directorates"]
        assert len(rs) == 1
        r = rs[0]
        assert (r["level"], r["rank"], r["code"], r["p_raw"], r["p"], r["lane"]) == (1, 1, sch["options"][3]["code"], 0.8, None, lane)
        assert r["prompt_id"] == f"{de['pid']},{fr['pid']}" and r["valid_from"] == "2026-10-15T00:00:00Z" and r["body_key"] == "BE"
    # the Grand Council's own field names a directorate: it is the value, the reading stays beside it, no inferred row
    fr = reading(a["title_alt"], "fr", 3, 0.6)
    d = decide(dict(a, dept="FIN\xa0Finanzdirektion"), {de["pid"]: de, fr["pid"]: fr}, lambda a: ("", "", None), [])
    assert (d["be-directorates"]["field"], d["be-directorates"]["inferred"]) == ("be:FIN", sch["options"][3]["code"])
    assert not [r for r in topic_rows(a, d, lock, None, "") if r["scheme"] == "be-directorates"]
    d = decide(dict(a, dept="Ratssekretariat"), {de["pid"]: de, fr["pid"]: fr}, lambda a: ("", "", None), [])
    assert "field" not in d["be-directorates"]   # a field that names no directorate leaves the reading as the value
    spec = importlib.util.spec_from_file_location("gen_seed", ROOT / "upstream/opd/tools/gen_seed.py")
    gs = importlib.util.module_from_spec(spec); spec.loader.exec_module(gs)
    seeded = {c["code"] for s, cs in gs.schemes(strict=False) if s["scheme_key"] == "be-directorates" for c in cs}
    assert {o["code"] for o in sch["options"]} | {sch["none"]["code"]} <= seeded


def test_scope_check_rows_in_compose():
    """S30 in compose: a topic with include / exclude lists is verified only when the S27 check and the scope check both
    say yes, with both checks' readings present; their prompt ids are part of the decision's ids."""
    from querschnitt.compose import decide
    t = dict(id="adhoc/t", names={"de": "Wolf"}, question={"de": "Betrifft es «Wolf»?"}, answer_yes={"de": "Ja, Wolf"},
             cutoff=0.5, verify=True, include={"de": "Wolf, Herdenschutz"}, exclude={"de": "Jagd allgemein"})
    a = dict(id=7, body="CHE", lang="de", title="Wolfsbestand regulieren", title_long="", text="")

    def row(u_p, py):
        return dict(pid=P.pid(*u_p), p_yes=py, meta={"fp": "x"})

    ya = row(P.yesno_prompt(t, "de", a["title"], "", "a"), 0.95)
    va = row(P.verify_prompt(t, "de", a["title"], "", "a"), 0.95)
    sa = row(P.scope_check_prompt(t, "de", a["title"], "", "a"), 0.45)        # 0.1 < p < 0.9: order b too
    sb = row(P.scope_check_prompt(t, "de", a["title"], "", "b"), 0.35)
    rows = {r["pid"]: r for r in (ya, va, sa, sb)}
    d = decide(a, rows, lambda a: ("", "", None), [t])[t["id"]]
    assert d["verified"] is False and d["lane"] == "please_check" and d["flag"] is True
    assert d["pids"] == [ya["pid"], va["pid"], sa["pid"], sb["pid"]]
    sb["p_yes"] = 0.75                                                         # mean 0.6: both checks say yes
    d = decide(a, rows, lambda a: ("", "", None), [t])[t["id"]]
    assert d["verified"] is True and d["lane"] == "readings_agree"
    del rows[sb["pid"]]                                                       # stopped between the two scope readings
    d = decide(a, rows, lambda a: ("", "", None), [t])[t["id"]]
    assert "verified" not in d and d["pids"] == [ya["pid"]]


def test_batch_asks_the_scope_check_on_flags(tmp_path, monkeypatch):
    """The nightly batch asks the S30 scope check on flags of a topic with include / exclude (and only there), with the
    prompt ids compose looks up; Digitalisierung asks no scope check."""
    import gzip, json as _json
    from querschnitt import batch
    from querschnitt.client import Guard
    from querschnitt.compose import read_run
    from querschnitt.fake_endpoint import FakeEndpoint
    from querschnitt.scheme import adhoc as real_adhoc
    from querschnitt.store import ROOT
    inp, run = tmp_path / "inputs.jsonl.gz", tmp_path / "run"
    lines = [l for l in open(ROOT / "tests/fixtures/inputs_sample.jsonl")]
    lines = [l for l in lines if "digital" in l.lower()][:4] + [l for l in lines if "digital" not in l.lower()][:4]
    with gzip.open(inp, "wt") as fh:
        fh.writelines(lines)
    t = dict(real_adhoc("digitalisierung"), id="adhoc/digi-scope", verify=True,
             include={"de": "Verwaltung, Daten"}, exclude={"de": "Telefonie"})
    monkeypatch.setattr(batch, "adhoc", lambda s: t if s == "digi-scope" else real_adhoc(s))
    monkeypatch.setattr(Guard.__init__, "__defaults__", (50.0, 0.15))
    with FakeEndpoint() as f:
        for k, v in dict(QS_BASE_URL=f.url, QS_API_KEY="test", QS_KEY_FILE=str(tmp_path / "nokey")).items():
            monkeypatch.setenv(k, v)
        batch.main(["run", "--inputs", str(inp), "--out", str(run), "--since", "0000", "--no-examples", "--max-rate", "50",
                    "--steps", "yn", "--topics", "digitalisierung", "digi-scope"])
    _, rows = read_run(run)
    steps = [r["step"] for r in rows.values()]
    assert any(s.startswith("sc:adhoc/digi-scope") for s in steps) and not any(s.startswith("sc:adhoc/digitalisierung") for s in steps)
    for line in lines:
        a = _json.loads(line); a = dict(a, title_long=a.get("title_long") or "", lang=a.get("lang") or "de")
        ra = rows.get(P.pid(*P.yesno_prompt(t, a["lang"], a["title"], a["title_long"], "a")))
        if ra is None:
            continue
        rb = rows.get(P.pid(*P.yesno_prompt(t, a["lang"], a["title"], a["title_long"], "b")))
        pm = (ra["p_yes"] + rb["p_yes"]) / 2 if rb else ra["p_yes"]
        has = P.pid(*P.scope_check_prompt(t, a["lang"], a["title"], a["title_long"], "a")) in rows
        assert has is (pm >= 0.5), a["title"]
