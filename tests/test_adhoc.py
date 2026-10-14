"""Neues Thema against the fake endpoint: topic generation (and its fallback), corpus-checked terms, streamed decisions
newest first with a running line, the candidate step before the scored slice, and the saved topic file."""
import json
import time

import yaml

from querschnitt import prompts as P
from querschnitt.adhoc import build_topic, parse_json, parse_terms, slugify


def sse(text):
    out = []
    for block in text.strip().split("\n\n"):
        ev = dict(l.split(": ", 1) for l in block.splitlines() if not l.startswith(":") and ": " in l)
        if "data" in ev:
            out.append((ev.get("event"), json.loads(ev["data"])))
    return out


def wait(api, slug, s=20):
    t = time.time()
    while time.time() - t < s:
        st = api.get(f"/adhoc/{slug}").json()
        if st["done"]:
            return st
        time.sleep(0.05)
    raise AssertionError("ad-hoc run did not finish")


def test_new_topic_streams(api):
    r = api.post("/adhoc", json={"sentence": "Wölfe, Grossraubtiere und Herdenschutz", "lang": "de"}).json()
    slug, topic = r["slug"], r["topic"]
    assert slug.startswith("wolf") and topic["id"] == f"adhoc/{slug}"
    assert topic["question"]["de"].startswith("Betrifft das folgende parlamentarische Geschäft das Thema «Wolf und Herdenschutz» (")
    assert "Wölfe, Grossraubtiere und Herdenschutz" in topic["question"]["de"]       # the sentence is the scope note
    assert topic["question"]["fr"].startswith("L'objet parlementaire suivant concerne-t-il le thème « loup")
    st = wait(api, slug)
    # terms: kept only when they occur in corpus titles (fake proposes Wolf, Herdenschutz, Grossraubtier, loup, prédateur, lupo)
    assert set(st["terms"]) == {"de", "fr", "it"}
    for l, ts in st["terms"].items():
        for t in ts:
            assert t["hits"] > 0 and t["term"] != "xyzzy"
    assert st["summary"]["mode"] == "all" and st["summary"]["read"] == st["summary"]["total"] > 0
    ev = sse(api.get(f"/adhoc/{slug}/stream").text)
    kinds = [k for k, _ in ev]
    assert kinds[0] == "topic" and kinds[-1] == "done" and "decision" in kinds and "progress" in kinds and "terms" in kinds
    dec = [d for k, d in ev if k == "decision"]
    assert {"id", "p", "flag", "t"} <= set(dec[0])
    assert len(dec) == st["summary"]["read"]
    prog = [d for k, d in ev if k == "progress"][-1]
    assert prog["line"].startswith(f"read {len(dec)} / flagged ")
    # the newest week only, every affair in it read
    lo, hi = st["period"]
    assert all(lo <= d["date"] <= hi for d in dec)
    assert st["error"] is None


def test_no_system_message_and_prompt_frame(api, fake):
    r = api.post("/adhoc", json={"sentence": "Digitale Verwaltung", "lang": "de", "limit": 5}).json()
    st = wait(api, r["slug"])
    assert all(m["role"] != "system" for b in fake.requests for m in b["messages"])
    gen = [b for b in fake.requests if b["messages"][-1]["role"] == "user"]
    assert gen and "logprobs" not in gen[0] and gen[0]["max_tokens"] > 1
    yn = [b for b in fake.requests if b["messages"][-1]["role"] == "assistant"]
    d = st["decisions"][0]
    a = api.app.state.store.affair(d["id"])
    u, pre = P.yesno_prompt(st["topic"], a["lang"], a["title"], a["title_long"] or "", "a")
    assert any(b["messages"][0]["content"] == u and b["messages"][1]["content"] == pre for b in yn)


def test_flags_follow_the_item(api):
    r = api.post("/adhoc", json={"sentence": "Digitalisierung der Verwaltung", "lang": "de", "period": "2026-09-01..2026-10-31"}).json()
    st = wait(api, r["slug"])
    for d in st["decisions"]:
        a = api.app.state.store.affair(d["id"])
        txt = (a["title"] + " " + (a["title_long"] or "")).lower()
        hit = any(w in txt for w in ("digital", "numérique", "digitale", "wolf", "loup", "lupo"))
        assert d["flag"] == hit, (d, a["title"])
    assert st["summary"]["flagged"] > 0


def test_candidates_before_scored_slice(api):
    r = api.post("/adhoc", json={"sentence": "Wolf", "lang": "de", "period": "2019"}).json()
    st = wait(api, r["slug"])
    s = st["summary"]
    assert s["mode"] == "candidates" and s["period"] == ["2019-01-01", "2019-12-31"]
    assert s["outside"]["n"] == s["outside_n"] > 0 and s["outside"]["population"] == s["non_candidates"]
    assert s["outside"]["interval"][0] <= (s["outside"]["rate"] or 0) <= s["outside"]["interval"][1]
    assert {d["sample"] for d in st["decisions"]} <= {"candidate", "outside"}
    assert s["read"] == s["candidates"] + s["outside_n"]


def test_save_writes_topic_file_and_rows(api, tmp_path):
    r = api.post("/adhoc", json={"sentence": "Wolf und Herdenschutz", "lang": "de", "limit": 6,
                                 "examples": [{"title": "Wolfsregulierung im Wallis", "match": True}]}).json()
    wait(api, r["slug"])
    out = api.post(f"/adhoc/{r['slug']}/save", json={"by": "test", "examples": [{"id": 341382, "match": False}]}).json()
    text = (tmp_path / "adhoc_yaml" / f"{r['slug']}.yaml").read_text()
    assert "\nyes:" not in text and "\n  yes:" not in text
    doc = yaml.safe_load(text)
    assert list(doc)[:6] == ["id", "names", "question", "answer_yes", "cutoff", "examples"]
    assert doc["id"] == f"adhoc/{r['slug']}" and doc["cutoff"] == 0.5 and set(doc["question"]) == {"de", "fr", "it"}
    assert doc["examples"][0] == {"title": "Wolfsregulierung im Wallis", "match": True} and doc["examples"][1]["match"] is False
    assert out["rows"] == 6
    rows = api.get(f"/topics/adhoc/{r['slug']}/no/affairs").json()["total"] + \
        api.get(f"/topics/adhoc/{r['slug']}/yes/affairs").json()["total"]
    assert rows == 6


def test_fallback_and_parsing():
    t = build_topic("Hitzeschutz in Städten", "de", None, "hitze")
    assert t["names"] == {"de": "Hitzeschutz in Städten", "fr": "Hitzeschutz in Städten", "it": "Hitzeschutz in Städten"}
    assert t["question"]["de"] == "Betrifft das folgende parlamentarische Geschäft das Thema «Hitzeschutz in Städten»?"
    assert t["answer_yes"]["it"] == "Sì, l'oggetto riguarda il tema «Hitzeschutz in Städten»"
    assert parse_json("```json\n{\"a\": {\"b\": 1}}\n``` trailing") == {"a": {"b": 1}}
    assert parse_json("no json here") is None
    cut = '{"terms": {"de": ["Wolf", "Herdenschutz"], "fr": ["loup", "prédat'
    assert parse_terms(cut) == {"de": ["Wolf", "Herdenschutz"], "fr": ["loup"], "it": []}
    long = build_topic("Wölfe", "de", {"name": {"fr": "Loups"}, "scope": {"fr": "Une rédaction cherche des objets sur les loups et plus encore"}}, "w")
    assert long["question"]["fr"].endswith("« Loups » ?")
    assert slugify("Künstliche Intelligenz an Schulen!") == "kuenstliche-intelligenz-an-schulen"
    # the topic dict feeds the engine's prompt builder unchanged
    u, pre = P.yesno_prompt(t, "fr", "Titre", "", "b")
    assert u.startswith("L'objet parlementaire suivant") and "A = Non, autre thème" in u and pre == '{"reponse": "'


def test_generation_garbage_falls_back(api, fake):
    fake.gen_text = "Gerne! Das Thema heisst Lärmschutz."
    r = api.post("/adhoc", json={"sentence": "Lärmschutz an Autobahnen", "lang": "de", "limit": 2}).json()
    assert r["topic"]["names"]["fr"] == "Lärmschutz an Autobahnen" and r["topic"]["generated"] is False
    st = wait(api, r["slug"])
    fake.gen_text = None
    assert st["terms"] == {"de": [], "fr": [], "it": []}
    assert st["error"] is None and st["summary"]["read"] == 2


def test_terms_put_is_corpus_checked(api):
    r = api.post("/adhoc", json={"sentence": "Wolf", "lang": "de", "limit": 1}).json()
    t = api.put(f"/adhoc/{r['slug']}/terms", json={"terms": {"de": ["Wolf", "xyzzyqq"], "fr": ["loup"]}}).json()["terms"]
    assert [x["term"] for x in t["de"]] in (["Wolf"], [])
    assert all(x["term"] != "xyzzyqq" for x in t["de"])
