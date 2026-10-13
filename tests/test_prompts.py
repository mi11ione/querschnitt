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
