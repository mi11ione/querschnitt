"""Shared fixtures: a SQLite store loaded with the sample (80 real OPD affairs, synthetic topic rows marked
model=fixture), a fake OpenAI-compatible endpoint, and an API client wired to both. No real model call is made."""
import os
import pathlib

import pytest

from querschnitt.client import Client, Endpoint
from querschnitt.fake_endpoint import FakeEndpoint
from querschnitt.store import Store

FIX = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture
def store(tmp_path):
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
    ah = Adhoc(store, fake_client(fake, tmp_path), out=tmp_path / "adhoc_runs")
    app = create_app(store, ah, app_dir=tmp_path / "noapp")
    with TestClient(app) as c:
        c.ah = ah
        yield c
