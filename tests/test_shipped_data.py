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
