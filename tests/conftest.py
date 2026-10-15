"""Shared fixtures: a SQLite store loaded with the sample (80 real OPD affairs, synthetic topic rows marked
model=fixture), a fake OpenAI-compatible endpoint, and an API client wired to both. No real model call is made."""
import os
import pathlib

import pytest

from querschnitt.client import Client, Endpoint
from querschnitt.fake_endpoint import FakeEndpoint
from querschnitt.store import Store

FIX = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _measured_mode(monkeypatch):
    """Every test starts in the measured design, whatever the shell exports (QS_PREFILL=0 is tested explicitly)."""
    for k in ("QS_PREFILL", "QS_NO_LOGPROBS"):
        monkeypatch.delenv(k, raising=False)


@pytest.fixture
def store(tmp_path):
    """SQLite per test; with QS_TEST_ALL_PG=1 and QS_TEST_PG_DSN, the same tests on Postgres (tables emptied first)."""
    if os.environ.get("QS_TEST_ALL_PG") and os.environ.get("QS_TEST_PG_DSN"):
        s = Store(dsn=os.environ["QS_TEST_PG_DSN"])
        s.ex("TRUNCATE topics, qs_affairs, qs_runs RESTART IDENTITY"); s.commit()
    else:
        s = Store(path=str(tmp_path / "t.sqlite"), dsn="")
    s.load_affairs(FIX / "inputs_sample.jsonl")
    s.load_topics(FIX / "topics_sample.jsonl")
    yield s
    s.close()


@pytest.fixture
def fake():
    with FakeEndpoint() as f:
        yield f


def fake_client(fake, tmp_path) -> Client:
    ep = Endpoint(name="fake", base_url=fake.url, key_file=str(tmp_path / "nokey"), key_env="QS_TEST_NO_KEY", max_rate=200, conc=3)
    c = Client(ep, ledger=str(tmp_path / "ledger.jsonl"), cap_usd=1.0, tag="test")
    c.guard.rate = 200.0                     # the guard starts at 1 req/s; tests need no pacing
    return c


@pytest.fixture
def api(store, fake, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from querschnitt.adhoc import Adhoc
    from querschnitt.api import create_app
    monkeypatch.setenv("QS_ADHOC_DIR", str(tmp_path / "adhoc_yaml"))
    monkeypatch.delenv("QS_WRITE_TOKEN", raising=False)        # writes open unless a test sets a token (test_write_token)
    ah = Adhoc(store, fake_client(fake, tmp_path), out=tmp_path / "adhoc_runs")
    app = create_app(store, ah, app_dir=tmp_path / "noapp")
    with TestClient(app) as c:
        c.ah = ah
        yield c
    ah.shutdown()                          # (also run by the app's lifespan) no job outlives its fake endpoint
