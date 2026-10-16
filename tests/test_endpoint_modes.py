"""Endpoint capabilities (fake endpoint only): the measured design needs assistant prefill and top_logprobs. An endpoint
that refuses or ignores prefill stops with an error naming the capability and QS_PREFILL=0; QS_PREFILL=0 is a separate,
fallback mode measured in S28 (one user message, own prompt ids, `mode` in meta and lock); the default path is unchanged."""
import gzip
import importlib.util
import json
from pathlib import Path

import pytest

from querschnitt import client as C
from querschnitt import prompts as P
from querschnitt.client import CapabilityError, Client, Endpoint, capability_error
from querschnitt.engine import Engine
from querschnitt.fake_endpoint import FakeEndpoint
from querschnitt.scheme import adhoc

ROOT = Path(__file__).resolve().parents[1]
A = dict(id=1, title="Digitalisierung der Verwaltung im Kanton Bern",
         title_long="Wie weit ist die Digitalisierung der kantonalen Verwaltung? Der Regierungsrat soll berichten.",
         text="Der Kanton Bern soll seine Verwaltung digitalisieren. Die Bevölkerung soll Gesuche online einreichen können.",
         lang="de", level="cantonal", body="BE")
PRE = {"continue_final_message", "add_generation_prompt"}


def client(f: FakeEndpoint, tmp_path, prefill: bool = True, logprobs: bool = True) -> Client:
    ep = Endpoint(name="fake", base_url=f.url, key_file=str(tmp_path / "nokey"), key_env="QS_TEST_NO_KEY", max_rate=200,
                  conc=3, prefill=prefill, logprobs=logprobs)
    c = Client(ep, ledger=str(tmp_path / "ledger.jsonl"), cap_usd=1.0, tag="test")
    c.guard.rate = 200.0
    return c


def steps(e: Engine) -> list[dict]:
    t = adhoc("digitalisierung")
    return [e.ch1(A), e.ch2(A), e.sub(A, [16, 17, 2]), e.yn(t, A, "a"), e.yn(t, A, "b"),
            e.verify(t, A, "a"), e.evidence(A, "Digitalisierung")]


# ------------------------------------------------------------------ an endpoint without prefill: a clear error, no retry
def test_endpoint_rejecting_prefill_raises_named_error(tmp_path):
    with FakeEndpoint(mode="noprefill") as f:
        e = Engine(client(f, tmp_path))
        with pytest.raises(CapabilityError) as ex:
            e.ch1(A)
        assert len(f.requests) == 1                               # not retried, not silently re-sent without prefill
    msg = str(ex.value)
    assert ex.value.capability == "prefill"
    assert "QS_PREFILL=0" in msg and "continue_final_message" in msg and "measured on the held-out set (S28)" in msg
    assert "unmeasured" not in msg


def test_endpoint_ignoring_prefill_raises(tmp_path):
    """A server that drops unknown fields answers a new turn (`{"kapitel": …`): stopped, not stored as an empty row."""
    with FakeEndpoint(mode="ignoreprefill") as f:
        with pytest.raises(CapabilityError) as ex:
            Engine(client(f, tmp_path)).ch1(A)
    assert ex.value.capability == "prefill" and "QS_PREFILL=0" in str(ex.value)


@pytest.mark.parametrize("code,body,cap", [
    (400, '{"error": {"message": "Unrecognized request argument supplied: continue_final_message"}}', "prefill"),   # OpenAI
    (422, "Failed to deserialize the JSON body into the target type: unknown field `add_generation_prompt`", "prefill"),  # TGI
    (400, '{"detail": [{"type": "extra_forbidden", "loc": ["body", "continue_final_message"], '
          '"msg": "Extra inputs are not permitted"}]}', "prefill"),                                                   # pydantic
    (400, "litellm.UnsupportedParamsError: does not support parameters: ['continue_final_message']", "prefill"),
    (400, "Expected last role User or Tool (or Assistant with prefix True) for serving but got assistant", "prefill"),
    (400, '{"error": "bad request"}', "prefill"),                    # bare 400 to a prefill request: prefill is the likely cause
    (400, "This model's maximum context length is 4096 tokens", None),
    (401, '{"error": "invalid api key"}', None),
    (404, '{"error": "model not found"}', None),
    (400, '{"error": "logprobs are not supported for this model"}', "logprobs"),
])
def test_capability_error_phrasings(code, body, cap):
    payload = dict(messages=[], continue_final_message=True, add_generation_prompt=False, logprobs=True, top_logprobs=20)
    e = capability_error(code, body, payload, "x")
    assert (e.capability if e else None) == cap
    assert e is None or e.certain == (body != '{"error": "bad request"}')   # a bare 400 is likely, not certain
    if e:
        assert ("QS_PREFILL=0" if cap == "prefill" else "QS_NO_LOGPROBS=1") in str(e)


def test_plain_request_4xx_is_not_blamed_on_prefill():
    assert capability_error(400, '{"error": "bad request"}', dict(messages=[]), "x") is None


# ------------------------------------------------------------------ QS_PREFILL=0: the no-prefill fallback (measured, S28)
@pytest.mark.parametrize("mode", ["noprefill", "nologprobs"])
def test_no_prefill_mode(tmp_path, monkeypatch, mode):
    with FakeEndpoint() as f:                                     # the measured design on an endpoint with prefill
        ref = steps(Engine(client(f, tmp_path)))
    monkeypatch.setenv("QS_PREFILL", "0")
    with FakeEndpoint(mode=mode) as f:                            # refuses prefill fields / returns no logprobs
        rows = steps(Engine(client(f, tmp_path, prefill=False, logprobs=mode != "nologprobs")))
        reqs = list(f.requests)
    assert reqs and all(r["messages"][-1]["role"] == "user" and len(r["messages"]) == 1 for r in reqs)
    assert not any(PRE & set(r) for r in reqs)                    # no assistant message, no vLLM prefill fields
    assert all("Beginne deine Antwort genau mit `{" in r["messages"][0]["content"] for r in reqs)
    for r, m in zip(rows, ref):
        assert r["meta"]["mode"] == "no-prefill" and "mode" not in m["meta"]
        assert r["pid"] != m["pid"]                               # never the id of a measured row
        assert r["step"] == m["step"]
        if "codes" in r:                                          # the same code is read, from logprobs or from the text
            assert max(r["codes"], key=r["codes"].get) == max(m["codes"], key=m["codes"].get)
            assert (r["meta"]["mass"] > 0.5) if mode == "noprefill" else (r["codes"] == {max(m["codes"], key=m["codes"].get): 0.0})
        else:
            assert r["ok"] and r["quote"] == m["quote"]
    # the pid of a no-prefill row is the hash of the message actually sent, and differs from the prefill pid
    u, p = P.chapter_prompt(A, list(range(25)))
    assert rows[0]["pid"] == P.pid(u, p) == P.pid(u, p, prefill_mode=False) != P.pid(u, p, prefill_mode=True) == ref[0]["pid"]


def test_mode_and_endpoint_must_agree(tmp_path, monkeypatch):
    with FakeEndpoint() as f:
        monkeypatch.setenv("QS_PREFILL", "0")
        with pytest.raises(ValueError, match="QS_PREFILL"):
            Engine(client(f, tmp_path))                           # prefill endpoint, no-prefill prompts: refused
        monkeypatch.setenv("QS_PREFILL", "1")
        with pytest.raises(CapabilityError):                      # an endpoint without prefill never gets an assistant turn
            client(f, tmp_path, prefill=False).chat([{"role": "user", "content": "x"}, {"role": "assistant", "content": "{"}])
    monkeypatch.setenv("QS_PREFILL", "0")
    assert Endpoint.from_env().prefill is False
    monkeypatch.delenv("QS_PREFILL")
    assert Endpoint.from_env().prefill is True


# ------------------------------------------------------------------ the default path is the measured one, unchanged
def test_default_path_unchanged(tmp_path, monkeypatch):
    monkeypatch.delenv("QS_PREFILL", raising=False)
    with FakeEndpoint() as f:
        rows = steps(Engine(client(f, tmp_path)))
        reqs = list(f.requests)
    u, p = P.chapter_prompt(A, list(range(25)))
    assert reqs[0]["messages"] == [{"role": "user", "content": u}, {"role": "assistant", "content": p}]
    assert reqs[0]["continue_final_message"] is True and reqs[0]["add_generation_prompt"] is False
    assert reqs[0]["max_tokens"] == 1 and reqs[0]["logprobs"] is True and reqs[0]["top_logprobs"] == 20
    assert all(r["messages"][-1]["role"] == "assistant" for r in reqs)
    import hashlib
    assert rows[0]["pid"] == hashlib.sha256((u + "\x00" + p).encode()).hexdigest()[:12]
    assert all("mode" not in r["meta"] for r in rows)


# ------------------------------------------------------------------ batch + compose: separate lock, never mixed
def _inputs(tmp_path) -> Path:
    inp = tmp_path / "inputs.jsonl.gz"
    with gzip.open(inp, "wt") as fh:
        for line in list(open(ROOT / "tests/fixtures/inputs_sample.jsonl"))[:2]:
            fh.write(line)
    return inp


def _env(f, tmp_path, monkeypatch):
    monkeypatch.setattr(C.Guard.__init__, "__defaults__", (50.0, 0.15))
    for k, v in dict(QS_BASE_URL=f.url, QS_API_KEY="test", QS_KEY_FILE=str(tmp_path / "nokey")).items():
        monkeypatch.setenv(k, v)


def test_batch_no_prefill_lock_and_compose(tmp_path, monkeypatch):
    from querschnitt import batch
    from querschnitt.compose import read_run, run_build
    inp, run = _inputs(tmp_path), tmp_path / "run"
    monkeypatch.setenv("QS_PREFILL", "0")
    with FakeEndpoint(mode="noprefill") as f:
        _env(f, tmp_path, monkeypatch)
        batch.main(["run", "--inputs", str(inp), "--out", str(run), "--since", "0000", "--no-examples", "--max-rate", "50"])
    assert not (run / "STOP.md").exists()
    lock = json.loads((run / "state.json").read_text())["lock"]
    assert lock["mode"] == "no-prefill" and lock["key"].endswith("-no-prefill")
    assert "no-prefill" in (run / "PROGRESS.md").read_text()
    lk, rows = read_run(run)
    assert rows and all(r["meta"]["mode"] == "no-prefill" for r in rows.values())
    assert run_build(lk) == lk["fp"] + "+no-prefill"
    monkeypatch.delenv("QS_PREFILL")                              # composing / resuming in the measured mode: refused
    with pytest.raises(ValueError, match="QS_PREFILL"):
        read_run(run)
    with pytest.raises(SystemExit, match="never mix"):
        batch.main(["run", "--inputs", str(inp), "--out", str(run), "--since", "0000", "--no-examples", "--max-rate", "50"])


def test_batch_stops_on_prefill_rejection(tmp_path, monkeypatch):
    from querschnitt import batch
    inp, run = _inputs(tmp_path), tmp_path / "run"
    monkeypatch.delenv("QS_PREFILL", raising=False)
    with FakeEndpoint(mode="noprefill") as f:
        _env(f, tmp_path, monkeypatch)
        batch.main(["run", "--inputs", str(inp), "--out", str(run), "--since", "0000", "--no-examples", "--max-rate", "50"])
    stop = (run / "STOP.md").read_text()
    assert stop.startswith("# Endpoint capability: prefill") and "QS_PREFILL=0" in stop
    assert not (run / "state.json").exists()                      # nothing locked, nothing written


def test_no_calibration_for_no_prefill_rows():
    from querschnitt.compose import calibration_for

    class Cal:
        build = "fp_x"
    assert calibration_for(Cal, "fp_x") is Cal and calibration_for(Cal, "fp_x", "no-prefill") is None


# ------------------------------------------------------------------ the probe: prefill reported, env and verdict printed
def _probe_mod():
    spec = importlib.util.spec_from_file_location("probe_endpoint", ROOT / "tools/probe_endpoint.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


@pytest.mark.parametrize("mode,prefill,env,measured", [
    ("logprobs", "honoured", {}, "MEASURED"),
    ("noprefill", "rejected", {"QS_PREFILL": "0"}, "FALLBACK"),        # S28: the no-prefill fallback is measured
    ("ignoreprefill", "ignored", {"QS_PREFILL": "0"}, "FALLBACK"),
    ("nologprobs", "honoured", {"QS_NO_LOGPROBS": "1"}, "UNMEASURED"),
])
def test_probe_reports_prefill_and_settings(tmp_path, mode, prefill, env, measured):
    pr = _probe_mod()
    with FakeEndpoint(mode=mode) as f:
        R = pr.probe(client(f, tmp_path), [1, 2])
    assert R["prefill"] == prefill
    if prefill != "honoured":
        assert R["noprefill_ok"] is True
    for k, v in env.items():
        assert R["env"][k] == v
    for k in {"QS_PREFILL", "QS_NO_LOGPROBS"} - set(env):
        assert k not in R["env"]
    assert "QS_MAX_RATE" in R["env"] and R["batch_args"].startswith("--conc ")
    assert R["verdict"] == pr.MEASURED if measured == "MEASURED" else R["verdict"].startswith(getattr(pr, measured))


def _tok(token, lp, alts):
    return dict(token=token, logprob=lp, top_logprobs=[dict(token=k, logprob=v) for k, v in alts.items()])


def test_no_prefill_reads_the_code_token_not_the_quote():
    """S28 smoke run: Apertus writes the opening quote as its own token (` "`), whose alternatives include rare merged
    tokens (` "B` at -15); the code distribution is on the next token. A merged ` "B` token is read where it is generated."""
    pre = '{"kapitel": "'
    split = dict(logprobs=dict(content=[_tok('{"', -0.01, {'{"': -0.01}), _tok("kap", 0, {"kap": 0}), _tok("itel", 0, {"itel": 0}),
                                        _tok('":', 0, {'":': 0}), _tok(' "', 0, {' "': 0, ' "B': -15.5, ' "C': -25.9}),
                                        _tok("B", -0.1, {"B": -0.1, "C": -2.4, "x": -9}), _tok('"}', 0, {'"}': 0})]))
    d = C.read_codes_after(split, P.CODES, pre)
    assert d == {"B": -0.1, "C": -2.4}
    merged = dict(logprobs=dict(content=[_tok('{"kapitel":', -0.01, {}), _tok(' "C', -0.2, {' "C': -0.2, ' "B': -1.7, ' "': -3}),
                                         _tok('"}', 0, {})]))
    assert C.read_codes_after(merged, P.CODES, pre) == {"C": -0.2, "B": -1.7}
