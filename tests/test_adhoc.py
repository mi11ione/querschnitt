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
    assert list(doc)[:9] == ["id", "names", "question", "answer_yes", "cutoff", "verify", "include", "exclude", "examples"]
    assert doc["verify"] is True and set(doc["include"]) == set(doc["exclude"]) == {"de", "fr", "it"}   # S30 scope lists
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


def test_first_calls_work_without_a_runs_dir(store, fake, tmp_path, monkeypatch):
    """The client's ledger lives in the runs dir; it must exist before the first generation call (dogfood: FileNotFoundError)."""
    from querschnitt import client as C
    from querschnitt.adhoc import Adhoc
    monkeypatch.setattr(C.Guard.__init__, "__defaults__", (50.0, 0.15))
    for k, v in dict(QS_BASE_URL=fake.url, QS_API_KEY="t", QS_KEY_FILE=str(tmp_path / "nokey")).items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("QS_ADHOC_LEDGER", raising=False)
    ah = Adhoc(store, out=tmp_path / "does" / "not" / "exist")
    job = ah.start("Wolf und Herdenschutz", "de", limit=2)
    job.thread.join(20)
    assert job.topic["generated"] is True and any(job.terms.values())
    assert job.info["terms_generation"].get("error") is None and job.stop_reason == "done"
    ah.shutdown()


def test_cap_is_explicit_and_continue_reads_on(api):
    api.ah.max_calls = 6
    r = api.post("/adhoc", json={"sentence": "Digitale Verwaltung", "lang": "de", "period": "2026-09-01..2026-10-31"}).json()
    st = wait(api, r["slug"])
    assert st["stop"] == "cap" and st["summary"]["stop"] == "cap" and st["error"] is None
    assert 0 < st["summary"]["read"] <= 6 and st["summary"]["unread"] > 0
    ev = sse(api.get(f"/adhoc/{r['slug']}/stream").text)
    done = ev[-1]
    assert done[0] == "done" and done[1]["stop"] == "cap" and done[1]["period"] == ["2026-09-01", "2026-10-31"]
    assert all(d["period"] == ["2026-09-01", "2026-10-31"] for k, d in ev if k == "progress")
    read1 = st["summary"]["read"]
    api.ah.max_calls = None
    c = api.post(f"/adhoc/{r['slug']}/continue")
    assert c.status_code == 200 and c.json()["unread"] == st["summary"]["unread"]
    st2 = wait(api, r["slug"])
    assert st2["stop"] == "done" and st2["summary"]["unread"] == 0 and st2["summary"]["read"] > read1
    assert len({d["id"] for d in st2["decisions"]}) == st2["summary"]["read"]           # nothing read twice
    assert api.post(f"/adhoc/{r['slug']}/continue").status_code == 409


def test_named_periods_and_estimate(api):
    r = api.post("/adhoc", json={"sentence": "Wolf", "lang": "de", "period": "last_month", "limit": 1}).json()
    f, t = r["period"]
    import datetime as dt
    assert (dt.date.fromisoformat(t) - dt.date.fromisoformat(f)).days == 29 and r["period_name"] == "last_month"
    assert r["estimate"]["affairs"] >= 1 and r["estimate"]["mode"] == "all" and r["estimate"]["seconds"] >= 0
    wait(api, r["slug"])
    s = api.post("/adhoc", json={"sentence": "Wolf", "lang": "de", "period": "scored", "limit": 1}).json()
    assert s["period"][0] == "2025-01-01" and s["period_name"] == "scored"
    wait(api, s["slug"])
    d = api.post("/adhoc", json={"sentence": "Wolf", "lang": "de", "from": "2026-10-01", "to": "2026-10-05", "limit": 1}).json()
    assert d["period"] == ["2026-10-01", "2026-10-05"]
    wait(api, d["slug"])
    assert api.post("/adhoc", json={"sentence": "Wolf", "period": "last_century"}).status_code == 422


def test_user_stop_is_reported(api, fake):
    fake.latency = 0.05
    r = api.post("/adhoc", json={"sentence": "Digitale Verwaltung", "lang": "de", "period": "scored"}).json()
    time.sleep(0.3)
    api.post(f"/adhoc/{r['slug']}/stop")
    st = wait(api, r["slug"])
    fake.latency = 0.0
    assert st["stop"] == "stopped" and st["summary"]["unread"] > 0


def test_flags_are_verified(api, fake):
    """S27 rule: each flag gets the stricter second question; an unverified flag stays a flag but goes to please_check."""
    fake.central_words = ["digitalisierung"]          # the fake says «central» only for these; «digital…» alone is a flag
    r = api.post("/adhoc", json={"sentence": "Digitalisierung der Verwaltung", "lang": "de", "period": "2026-09-01..2026-10-31"}).json()
    assert r["topic"]["verify"] is True
    st = wait(api, r["slug"])
    flags = [d for d in st["decisions"] if d["flag"]]
    assert flags and all(d["verified"] is None for d in st["decisions"] if not d["flag"])
    for d in flags:
        a = api.app.state.store.affair(d["id"])
        central = "digitalisierung" in (a["title"] + " " + (a["title_long"] or "")).lower()
        assert d["verified"] is central, (d, a["title"])
        if not central:
            assert d["lane"] == "please_check"
    s = st["summary"]
    assert s["flagged"] == len(flags) and s["verified"] == sum(d["verified"] is True for d in flags)
    assert s["please_check"] == sum(d["lane"] == "please_check" for d in st["decisions"]) and s["verified"] < s["flagged"]
    ev = sse(api.get(f"/adhoc/{r['slug']}/stream").text)
    one = next(d for k, d in ev if k == "decision" and d["flag"])
    assert {"id", "p", "flag", "verified", "lane"} <= set(one)
    from querschnitt.fake_endpoint import VERIFY_Q
    vq = [b for b in fake.requests if b["messages"][-1]["role"] == "assistant" and VERIFY_Q.search(b["messages"][0]["content"])]
    assert len(vq) >= len(flags)                      # one verify per flag (order b where 0.1 < p < 0.9)
    out = api.post(f"/adhoc/{r['slug']}/save", json={"by": "t"}).json()
    assert "verify: true" in out["yaml"]
    fake.central_words = None


def test_verify_can_be_switched_off(api, fake):
    r = api.post("/adhoc", json={"sentence": "Digitalisierung", "lang": "de", "period": "2026-09-01..2026-10-31", "verify": False}).json()
    st = wait(api, r["slug"])
    assert r["topic"]["verify"] is False and all(d["verified"] is None for d in st["decisions"])
    from querschnitt.fake_endpoint import VERIFY_Q
    assert not any(VERIFY_Q.search(b["messages"][0]["content"]) for b in fake.requests)


def test_examples_build_the_batch_prompt(api, fake):
    """Neues Thema asks with the examples the nightly batch and compose use for the same topic (examples.topic_examples:
    the 4 most similar, never the affair itself), so a saved run's rows carry the prompt ids the nightly computes."""
    from querschnitt.examples import topic_examples
    ex = [{"title": "Hitzeschutz für Arbeitnehmende", "match": True},                 # an affair of the period itself
          {"title": "Hitzeschutz in Schulen", "match": True}, {"title": "Hitzeschutz und Arbeitszeiten", "match": True},
          {"title": "Schutz vor Hitze am Arbeitsplatz", "match": True}, {"title": "Hitzeschutz im Spital", "match": False},
          {"title": "Velowege im Kanton", "match": False}]
    r = api.post("/adhoc", json={"sentence": "Hitzeschutz", "lang": "de", "period": "2026-10-02..2026-10-02", "examples": ex}).json()
    st = wait(api, r["slug"])
    t = dict(st["topic"], examples=ex)
    assert st["decisions"]
    for d in st["decisions"]:
        a = api.app.state.store.affair(d["id"])
        a = dict(a, title_long=a["title_long"] or "")
        u, p = P.yesno_prompt(st["topic"], d["lang"], a["title"], a["title_long"], "a", topic_examples(t, a))
        assert d["prompt_id"].split(",")[0] == P.pid(u, p), a["title"]
        if a["title"] == "Hitzeschutz für Arbeitnehmende":
            assert "Hitzeschutz für Arbeitnehmende →" not in u                          # not its own example


def test_continue_twice_at_once_reads_once(api):
    """Two `continue` requests at the same moment (a double click) start one reader, not two."""
    import threading
    api.ah.max_calls = 2
    r = api.post("/adhoc", json={"sentence": "Digitale Verwaltung", "lang": "de", "period": "2026-09-01..2026-10-31"}).json()
    st = wait(api, r["slug"])
    assert st["stop"] == "cap"
    api.ah.max_calls = None
    slow = api.ah.check_daily
    api.ah.check_daily = lambda: (time.sleep(0.3), slow())[1]
    codes = []
    th = [threading.Thread(target=lambda: codes.append(api.post(f"/adhoc/{r['slug']}/continue").status_code)) for _ in range(2)]
    [x.start() for x in th]; [x.join() for x in th]
    api.ah.check_daily = slow
    assert sorted(codes) == [200, 409]
    wait(api, r["slug"])


def test_same_sentence_at_once_gets_two_slugs(api, monkeypatch):
    """Two runs of the same sentence started at the same moment get their own slug (and run dir)."""
    import threading
    est = api.ah.estimate
    monkeypatch.setattr(api.ah, "estimate", lambda f, t: (time.sleep(0.3), est(f, t))[1])
    out = []
    th = [threading.Thread(target=lambda: out.append(api.post("/adhoc", json={"sentence": "Wolf", "lang": "de", "limit": 1}).json()))
          for _ in range(2)]
    [x.start() for x in th]; [x.join() for x in th]
    assert len({o["slug"] for o in out}) == 2
    for o in out:
        wait(api, o["slug"])


def test_decision_usd_counts_every_call(api, fake):
    """A decision's `usd` is what its calls cost, the verify readings included."""
    r = api.post("/adhoc", json={"sentence": "Digitalisierung", "lang": "de", "period": "2026-09-01..2026-10-31"}).json()
    st = wait(api, r["slug"])
    d = next(d for d in st["decisions"] if d["verified"] is not None)
    by_pid = {}
    for b in fake.requests:
        if b["messages"][-1]["role"] == "assistant":
            u = b["messages"][0]["content"]
            by_pid[P.pid(u, b["messages"][1]["content"])] = round((len(u) // 4 * 0.10 + 1 * 0.20) / 1e6, 7)
    assert len(d["prompt_id"].split(",")) >= 2
    assert abs(d["usd"] - sum(by_pid[x] for x in d["prompt_id"].split(","))) < 1e-9


def test_dead_endpoint_refuses_in_seconds(api, monkeypatch):
    """No connection to the endpoint (Wi-Fi off, unroutable host): POST /adhoc answers 503 within the probe timeout instead of
    waiting out the client's retries; nothing is started and nothing is counted (the app then offers the recording)."""
    import socket
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()     # a port nobody listens on
    api.ah.client.endpoint.base_url = f"http://127.0.0.1:{port}/v1"
    monkeypatch.setenv("QS_ADHOC_PROBE_S", "1")
    t0 = time.time()
    r = api.post("/adhoc", json={"sentence": "Wolf", "lang": "de", "limit": 2})
    assert r.status_code == 503 and "not reachable" in r.json()["detail"]
    assert time.time() - t0 < 5 and not api.ah.jobs and api.ah.calls == 0


def test_slow_topic_request_falls_back_on_time(api, monkeypatch):
    """An endpoint that accepts connections but does not answer: the topic request gives up after QS_ADHOC_GEN_S and the run
    starts on the fallback frame (the sentence in every language)."""
    import contextlib
    import socket
    import threading
    srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(8); port = srv.getsockname()[1]
    held = []

    def hold():                                   # accept and never answer
        with contextlib.suppress(OSError):
            while True:
                held.append(srv.accept())
    threading.Thread(target=hold, daemon=True).start()
    api.ah.client.endpoint.base_url = f"http://127.0.0.1:{port}/v1"
    monkeypatch.setenv("QS_ADHOC_GEN_S", "1")
    t0 = time.time()
    r = api.post("/adhoc", json={"sentence": "Wolf und Herdenschutz", "lang": "de", "limit": 1})
    assert r.status_code == 200 and time.time() - t0 < 4
    assert r.json()["topic"]["names"]["fr"] == "Wolf und Herdenschutz"
    api.post(f"/adhoc/{r.json()['slug']}/stop")
    for c, _ in held:
        c.close()
    srv.close()


def test_flags_get_the_scope_check(api, fake):
    """S30: Neues Thema generates include / exclude lists (one more plain request, user message only) and asks the scope
    check on every flag next to the S27 check; a flag is verified only if both say yes, otherwise it goes to please_check."""
    from querschnitt.fake_endpoint import SCOPE_Q
    fake.scope_words = ["verwaltung", "administration", "amministrazione"]   # the fake's scope check: «belongs» only for these
    r = api.post("/adhoc", json={"sentence": "Digitalisierung", "lang": "de", "period": "2026-09-01..2026-10-31"}).json()
    t = r["topic"]
    assert t["include"]["de"] and t["exclude"]["fr"] and P.has_scope_check(t)
    gen = [b for b in fake.requests if b["messages"][-1]["role"] == "user" and '"include"' in b["messages"][0]["content"]]
    assert len(gen) == 1 and len(gen[0]["messages"]) == 1 and "logprobs" not in gen[0]
    st = wait(api, r["slug"])
    flags = [d for d in st["decisions"] if d["flag"]]
    assert flags and all(d["p_scope"] is None for d in st["decisions"] if not d["flag"])
    for d in flags:
        a = api.app.state.store.affair(d["id"])
        a = dict(a, title_long=a["title_long"] or "")
        in_scope = any(w in (a["title"] + " " + a["title_long"][:400]).lower() for w in fake.scope_words)
        assert (d["p_scope"] >= 0.5) is in_scope and d["verified"] is (d["p_verify"] >= 0.5 and in_scope), (d, a["title"])
        if not d["verified"]:
            assert d["lane"] == "please_check" and d["flag"] is True                  # the flag stays; a person decides
        u, p = P.scope_check_prompt(st["topic"], d["lang"], a["title"], a["title_long"], "a")
        assert P.pid(u, p) in d["prompt_id"].split(",")
    sq = [b for b in fake.requests if b["messages"][-1]["role"] == "assistant" and SCOPE_Q.search(b["messages"][0]["content"])]
    assert len(sq) >= len(flags)
    out = api.post(f"/adhoc/{r['slug']}/save", json={"by": "t"}).json()
    doc = yaml.safe_load(out["yaml"])
    assert doc["include"] == t["include"] and doc["exclude"] == t["exclude"]
    fake.scope_words = None


def test_no_scope_check_without_generation_or_verify(api, fake):
    from querschnitt.fake_endpoint import SCOPE_Q
    for body in ({"generate": False}, {"verify": False}):
        n0 = len(fake.requests)
        r = api.post("/adhoc", json=dict(sentence="Digitalisierung", lang="de", period="2026-09-01..2026-10-31", **body)).json()
        st = wait(api, r["slug"])
        assert "include" not in r["topic"] and not P.has_scope_check(r["topic"])
        assert all(d.get("p_scope") is None for d in st["decisions"])
        assert not any(SCOPE_Q.search(b["messages"][0]["content"]) or '"include"' in b["messages"][0]["content"]
                       for b in fake.requests[n0:])


def _subtopic_row(store, affair_id, code):
    a = store.affair(affair_id)
    return dict(affair_id=affair_id, body_key=a["body_key"], status="suggested", provenance="inferred", model="fixture",
                build="fixture-00000000", input_hash=a.get("input_hash"), valid_to=None, version="0.6.0", scheme="aps",
                level=2, code=code, rank=1, p_raw=0.7, p=None, lane=None, cutoffs_id="aps@00000000",
                prompt_id="fixture-sub", evidence=None)


def test_capped_run_reads_candidates_first(api, monkeypatch):
    """J3 r8: under a cap, term hits and stored-subtopic hits are read before the newest rest, and the run says so."""
    from querschnitt.adhoc import SUBS
    monkeypatch.setenv("QS_TERM_BROAD", "1")              # 80 fixture titles: every term would count as broad
    store = api.app.state.store
    store.load_topics([_subtopic_row(store, 341356, SUBS[9][0])])     # the fake names subtopics 10 and 11
    per = "2026-09-01..2026-10-31"
    r = api.post("/adhoc", json={"sentence": "Wolf und Herdenschutz", "lang": "de", "period": per, "limit": 5}).json()
    st = wait(api, r["slug"])
    items = [(a["id"], a["sample"]) for a in api.ah.jobs[r["slug"]].items]
    newest = [x["id"] for x in store.all("SELECT id FROM qs_affairs WHERE date >= '2026-09-01' AND date <= '2026-10-31' "
                                         "ORDER BY date DESC, id DESC")]
    # 341356 (7 Oct, stored subtopic) and 340424 (30 Sep, «Wolf» in the title), newest first, then the newest rest
    assert items[:2] == [(341356, "candidate"), (340424, "candidate")]
    assert [i for i, _ in items[2:]] == [i for i in newest if i not in (341356, 340424)][:3]
    assert {s for _, s in items[2:]} == {"rest"}
    assert 340424 not in newest[:5]                       # the old order would not have read the wolf affair at all
    s = st["summary"]
    assert s["order"] == "candidates first" and s["census"] is False and "not a census" in s["note"]
    c = s["candidates_first"]
    assert (c["n"], c["terms"], c["subtopics"], c["read"]) == (2, 1, 1, 2)
    assert c["flagged"] == sum(d["flag"] for d in st["decisions"] if d["id"] in (341356, 340424)) == 1
    assert {d["id"] for d in st["decisions"]} == {i for i, _ in items} and s["read"] == 5
    ev = sse(api.get(f"/adhoc/{r['slug']}/stream").text)
    prog = [d for k, d in ev if k == "progress"]
    assert prog and all(p["order"] == "candidates first" for p in prog)
    assert "candidates first: 2 of 2 candidates read, 1 flagged" in prog[-1]["line"]
    done = ev[-1][1]
    assert ev[-1][0] == "done" and done["order"] == "candidates first" and done["candidates_first"]["read"] == 2


def test_uncapped_run_reads_what_it_read_before(api, fake, monkeypatch):
    """Without a cap the order is unchanged: every affair of the period, newest first, no candidate step in the slice."""
    from querschnitt.adhoc import SUBS
    monkeypatch.setenv("QS_TERM_BROAD", "1")
    store = api.app.state.store
    store.load_topics([_subtopic_row(store, 341356, SUBS[9][0])])
    r = api.post("/adhoc", json={"sentence": "Wolf und Herdenschutz", "lang": "de", "period": "2026-09-01..2026-10-31"}).json()
    st = wait(api, r["slug"])
    items = [(a["id"], a["sample"]) for a in api.ah.jobs[r["slug"]].items]
    newest = [x["id"] for x in store.all("SELECT id FROM qs_affairs WHERE date >= '2026-09-01' AND date <= '2026-10-31' "
                                         "ORDER BY date DESC, id DESC")]
    assert items == [(i, "all") for i in newest]
    s = st["summary"]
    assert "order" not in s and "candidates_first" not in s and "census" not in s and "note" not in s
    assert "subtopics" not in st["topic"]                 # no subtopic request inside the scored slice
    assert not any('"subtopics"' in m["content"] for b in fake.requests for m in b["messages"])
