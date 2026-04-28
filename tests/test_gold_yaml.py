"""Gold file structure checks."""

from __future__ import annotations

from pathlib import Path

from gdpr_ai.evaluation import load_gold_scenarios

ROOT = Path(__file__).resolve().parents[1]


def test_load_gold_unified_fifty_scenarios() -> None:
    rows = load_gold_scenarios(ROOT / "gold" / "test_scenarios.yaml")
    assert len(rows) == 50
    v_ids = {str(r["id"]) for r in rows if r.get("mode") == "violation_analysis"}
    c_ids = {str(r["id"]) for r in rows if r.get("mode") == "compliance_assessment"}
    assert len(v_ids) == 30
    assert len(c_ids) == 20
    assert {f"SC-V-{i:03d}" for i in range(1, 31)} == v_ids
    assert {f"SC-C-{i:03d}" for i in range(1, 21)} == c_ids
