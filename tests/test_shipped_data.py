"""The export committed in app/data (what the live site and `make data` serve) covers its period: a half-scored export —
e.g. one written while a re-score was in progress — must not ship. Skipped when app/data holds no export."""
import json
from pathlib import Path

import pytest

META = Path(__file__).resolve().parents[1] / "app/data/meta.json"


@pytest.mark.skipif(not META.exists(), reason="no export in app/data")
def test_shipped_export_is_scored():
    m = json.loads(META.read_text())
    assert m["scored_share"] >= 0.95, f"app/data: only {m['scored']:,} of {m['affairs']:,} affairs scored (share {m['scored_share']})"


AFFAIRS = META.parent / "affairs.json"


@pytest.mark.skipif(not (META.exists() and AFFAIRS.exists()), reason="no full export in app/data (affairs.json is not in git)")
def test_shipped_affairs_match_meta():
    """meta.json alone can look complete while affairs.json is a half-scored export (a partial restore): count the
    chapters the app actually reads."""
    m = json.loads(META.read_text()); c = json.loads(AFFAIRS.read_text())["cols"]
    inper = [i for i, d in enumerate(c["date"]) if m["since"] <= d <= m["until"]]
    have = sum(c["ch"][i] is not None for i in inper)
    assert have >= 0.95 * len(inper), f"affairs.json: chapters for {have:,} of {len(inper):,} affairs (meta says {m['scored']:,})"
