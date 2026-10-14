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
