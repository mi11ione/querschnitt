"""upstream/opd/export/to_opd.py reads the topics file gzipped or plain (.jsonl / .ndjson) and writes the same export."""
import gzip
import importlib.util
import shutil

from conftest import FIX
from querschnitt.store import ROOT


def to_opd():
    spec = importlib.util.spec_from_file_location("to_opd", ROOT / "upstream/opd/export/to_opd.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def test_plain_and_gzipped_inputs_agree(tmp_path):
    m = to_opd()
    gz = tmp_path / "topics.jsonl.gz"
    with open(FIX / "topics_sample.jsonl", "rb") as f, gzip.open(gz, "wb") as g:
        shutil.copyfileobj(f, g)
    out = {}
    for name, src in (("plain", FIX / "topics_sample.jsonl"), ("gz", gz)):
        assert m.main(["--topics", str(src), "--out", str(tmp_path / name)]) == 0
        out[name] = gzip.open(tmp_path / name / "topics.ndjson.gz", "rt").read()
    assert out["plain"] == out["gz"] and out["plain"].count("\n") == 504 - 216   # APS subtopics held back by default
