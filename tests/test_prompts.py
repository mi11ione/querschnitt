"""The engine's prompts are byte-identical to the ones measured in the spikes (hashes captured from s9lib / S8 common.py)."""
import hashlib, json, pathlib
from querschnitt import prompts as P
from querschnitt.scheme import APS, adhoc

FIX = json.loads((pathlib.Path(__file__).parent / "fixtures" / "prompt_hashes.json").read_text())
A = FIX["affair"]


def h(u, p):
    return hashlib.sha256(json.dumps([u, p], ensure_ascii=False).encode()).hexdigest()


def test_chapter_identity():
    assert h(*P.chapter_prompt(A, list(range(25)))) == FIX["q1_id"]


def test_chapter_perm():
    assert h(*P.chapter_prompt(A, P.S1PERM)) == FIX["q1_s1"]


def test_chapter_examples():
    ex = [(t, c) for t, c in FIX["examples"]]
    assert h(*P.chapter_prompt_examples(A, list(range(25)), ex)) == FIX["q1_mem"]


def test_subtopic():
    u, p, opts, codes = P.subtopic_prompt(A, [16, 17, 2])
    assert h(u, p) == FIX["q2"]


def test_yesno_digital():
    t = adhoc("digitalisierung")
    for lang in ("de", "fr", "it"):
        for o in ("a", "b"):
            assert h(*P.yesno_prompt(t, lang, A["title"], A["title_long"], o)) == FIX[f"e6_{lang}_{o}"]


def test_scheme_shape():
    assert len(APS.codes) == 25 and sum(len(v) for v in APS.subs_de.values()) == 190
    assert P.S1PERM[:5] == FIX["s1perm5"]


def test_flat_be_directorates():
    from querschnitt.scheme import flat
    fx = json.loads((pathlib.Path(__file__).parent / "fixtures" / "be_prompt_hashes.json").read_text())
    s = flat("be-directorates")
    for lang in ("de", "fr"):
        u, p, codes = P.flat_prompt(s, "Neubau Gymnasium Biel: Planungskredit", lang)
        assert h(u, p) == fx[lang] and codes[-1] == "I"


def test_language_frames_match_s6():
    fx = json.loads((pathlib.Path(__file__).parent / "fixtures" / "s6_prompt_hashes.json").read_text())
    for lang, v in fx.items():
        a = v["a"]
        assert h(*P.chapter_prompt(a, list(range(25)))) == v["l1_id"], lang
        assert h(*P.chapter_prompt(a, P.S1PERM)) == v["l1_s1"], lang
        assert h(*P.subtopic_prompt(a, [16, 17, 2])[:2]) == v["l2"], lang


# ---- S30 scope check: pinned, byte-identical to the measured eval/s30/common.scope_prompt, never asked without its fields
S30_TOPIC = dict(names={"de": "Wolf und Grossraubtiere", "fr": "loup et grands prédateurs", "it": "lupo e grandi predatori"},
                 include={"de": "Wolf, Bär, Luchs, Herdenschutz", "fr": "loup, ours, lynx, protection des troupeaux", "it": "lupo, orso, lince"},
                 exclude={"de": "Jagd allgemein, Raubfische", "fr": "chasse en général", "it": ""}, verify=True)
S30_HASHES = {"de_a": "a7b6b02ee53b825cfaeb706d60cbe5b1e741016837065529c21ccd4ecaa84ec0",
              "de_b": "f08158301a7c41ac5858d62fe9f54a2149b659d48cd6091fb086627e2b417695",
              "fr_a": "510042654c5901fdcceb348e7432dfef6edba889860a3a8e236fb1ea4d70c6f2",
              "fr_b": "885096451a372e657614cbff82298c10e16f14a5058ca5955f1871be90997e26",
              "it_a": "3bde10f74b542b2d521de34f3a106efd1ce331edf6bc2add345059e0989c3853",
              "it_b": "bc11ed008f858c88d39f1df84c86fe556f190ab48abb281437c13a0b5becc7af"}


def test_scope_check_pinned():
    for lang in ("de", "fr", "it"):
        for o in ("a", "b"):
            assert h(*P.scope_check_prompt(S30_TOPIC, lang, A["title"], A["title_long"], o)) == S30_HASHES[f"{lang}_{o}"]


def test_scope_generation_pinned():
    from querschnitt.adhoc import SCOPE_PROMPT
    assert hashlib.sha256(SCOPE_PROMPT.encode()).hexdigest() == "fa7e5c5c1f1ab20f62d3cbdb7ce094075ea3488fa58da60f28b801d6879a13dd"


def test_scope_check_is_the_measured_prompt():
    """The product prompt and generation request are the ones S30 measured (eval/s30/common.py)."""
    import importlib.util, sys
    root = pathlib.Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("s30_common", root / "eval/s30/common.py")
    if spec is None or not (root / "eval/s30/common.py").exists():
        import pytest; pytest.skip("eval/s30 not in this checkout")
    m = importlib.util.module_from_spec(spec); sys.modules["s30_common"] = m; spec.loader.exec_module(m)
    from querschnitt.adhoc import SCOPE_PROMPT
    assert SCOPE_PROMPT == m.SCOPE_PROMPT
    sc = dict(include=S30_TOPIC["include"], exclude=S30_TOPIC["exclude"])
    for lang in ("de", "fr", "it"):
        for o in ("a", "b"):
            for tl in ("", A["title_long"], A["title"]):
                assert P.scope_check_prompt(S30_TOPIC, lang, A["title"], tl, o) == m.scope_prompt(S30_TOPIC["names"], sc, lang, A["title"], tl, order=o)


def test_shipped_topic_files_ask_no_scope_check():
    """Digitalisierung (no verify) and the S19 files (verify, no include/exclude) keep their prompts and steps."""
    for slug in ("digitalisierung", "wolf", "hitze", "ki-schule"):
        t = adhoc(slug)
        assert not P.has_scope_check(t) and "include" not in t and "exclude" not in t
    assert P.has_scope_check(S30_TOPIC) and not P.has_scope_check(dict(S30_TOPIC, verify=False))
