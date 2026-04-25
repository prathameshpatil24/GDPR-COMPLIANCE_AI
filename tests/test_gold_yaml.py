"""Gold file structure checks."""
from __future__ import annotations

from pathlib import Path

from gdpr_ai.evaluation import load_gold_scenarios

ROOT = Path(__file__).resolve().parents[1]


def test_load_gold_has_thirty_scenarios() -> None:
    rows = load_gold_scenarios(ROOT / "gold" / "test_scenarios.yaml")
    assert len(rows) == 30
    ids = {r["id"] for r in rows}
    assert ids == {f"SC-{i:03d}" for i in range(1, 31)}
