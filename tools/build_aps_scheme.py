"""Build src/querschnitt/schemes/aps.yaml from the APS chapter/subtopic list (R1 taxonomies, ids from anneepolitique.swiss)
and the prompt names used in the measured spikes (S1/S5/S9), so the engine's prompts stay byte-identical to the measured ones.
Usage: python tools/build_aps_scheme.py <path to R1-parts/taxonomies.md> <path to ideation s1lib.py dir>"""
import re, sys, types, pathlib, yaml
tax, s1dir = sys.argv[1], sys.argv[2]
sys.modules.setdefault("gw", types.ModuleType("gw")); sys.path.insert(0, s1dir)
import urllib.request; _o = urllib.request.urlopen
import s1lib; urllib.request.urlopen = _o
rows = [l.strip()[2:] for l in open(tax) if re.match(r"\s+- \d\.\d\.(\d\.)? ", l)]
assert len(rows) == 24, len(rows)
chapters = []
for i, r in enumerate(rows):
    code, rest = r.split(" ", 1); name, subs = rest.split(": ", 1)
    assert name == s1lib.CH_DE[i], (name, s1lib.CH_DE[i])
    parsed = re.findall(r"(.+?) \((\d+)\)(?:; |$)", subs)
    assert len(parsed) == len(s1lib.SUBS[i]), (code, len(parsed))
    sub = []
    for (nm, kid), pn in zip(parsed, s1lib.SUBS[i]):
        assert " ".join(nm.split()) == pn, (nm, pn)
        sub.append({"code": f"aps:kw:{kid}", "name": {"de": pn}})
    chapters.append({"code": f"aps:{code}", "name": {"de": s1lib.CH_DE[i], "fr": s1lib.CH_FR[i], "it": s1lib.CH_IT[i]},
                     "subtopics": sub})
none = {"code": "aps:none", "name": {k: v for k, v in s1lib.NONE.items()}}
doc = {"id": "aps", "title": {"de": "Année Politique Suisse: 24 Kapitel, 190 Unterthemen", "fr": "Année Politique Suisse : 24 chapitres, 190 sous-thèmes"},
       "source": "https://anneepolitique.swiss (chapter codes and keyword ids as published; Italian names are an unofficial translation)",
       "levels": 2, "chapters": chapters, "none": none}
out = pathlib.Path(__file__).resolve().parents[1] / "src/querschnitt/schemes/aps.yaml"
out.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=200))
print(out, sum(len(c["subtopics"]) for c in chapters))
