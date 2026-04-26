"""Tests for compliance evaluation harness and gold file shape."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from gdpr_ai.evaluation import load_gold_scenarios

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "gold" / "compliance_scenarios.yaml"


def test_compliance_gold_loads_twenty_scenarios() -> None:
    rows = load_gold_scenarios(GOLD)
    assert len(rows) == 20
    ids = {str(r["id"]) for r in rows}
    assert "SC-C-001" in ids
    assert "SC-C-020" in ids


def test_compliance_eval_dry_run_subset() -> None:
    cmd = [
        sys.executable,
        str(ROOT / "tests" / "run_compliance_eval.py"),
        "--dry-run",
        "--scenarios",
        "SC-C-001,SC-C-002,SC-C-003",
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    out = ROOT / "logs" / "compliance_eval_results.json"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["mode"] == "dry_run"
    assert len(data["per_scenario"]) == 3


def test_article_recall_precision_math() -> None:
    """Precision/recall for overlapping normalized article keys."""
    exp = ["Art. 6 GDPR", "Art. 7 GDPR"]
    act = {"6", "7", "99"}
    from gdpr_ai.evaluation import normalize_article_ref

    exp_s = {normalize_article_ref(x) for x in exp}
    act_s = {normalize_article_ref(x) for x in act}
    inter = exp_s & act_s
    recall = len(inter) / len(exp_s)
    precision = len(inter) / len(act_s)
    assert recall == 1.0
    assert 0 < precision < 1.0
