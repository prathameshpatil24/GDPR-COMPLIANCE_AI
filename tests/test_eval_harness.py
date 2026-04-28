"""Tests for unified gold eval harness (load, filter, validation, scoring)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_TESTS = ROOT / "tests"
if str(_TESTS) not in sys.path:
    sys.path.insert(0, str(_TESTS))

from eval_models import EvalReport, ScenarioResult  # noqa: E402
from eval_scoring import outcome_label  # noqa: E402

from gdpr_ai.evaluation import load_gold_scenarios, normalize_article_ref  # noqa: E402

GOLD = ROOT / "gold" / "test_scenarios.yaml"


def _import_run_eval():
    """Import run_eval module (tests/ is on sys.path)."""
    import run_eval as re  # noqa: PLC0415

    return re


def test_load_scenarios_fifty_total() -> None:
    re = _import_run_eval()
    rows = re.load_scenarios(GOLD)
    assert len(rows) == 50
    v = [r for r in rows if r.get("mode") == "violation_analysis"]
    c = [r for r in rows if r.get("mode") == "compliance_assessment"]
    assert len(v) == 30
    assert len(c) == 20


def test_filter_mode_violation_only() -> None:
    re = _import_run_eval()
    rows = re.load_scenarios(GOLD)
    f = re.filter_scenarios(rows, mode="violation_analysis")
    assert len(f) == 30
    assert all(r["mode"] == "violation_analysis" for r in f)


def test_filter_mode_compliance_only() -> None:
    re = _import_run_eval()
    rows = re.load_scenarios(GOLD)
    f = re.filter_scenarios(rows, mode="compliance_assessment")
    assert len(f) == 20
    assert all(r["mode"] == "compliance_assessment" for r in f)


def test_filter_ids_two_specific() -> None:
    re = _import_run_eval()
    rows = re.load_scenarios(GOLD)
    f = re.filter_scenarios(rows, ids=["SC-V-001", "SC-C-001"])
    assert len(f) == 2
    got = {str(r["id"]) for r in f}
    assert got == {"SC-V-001", "SC-C-001"}


def test_filter_difficulty_hard_only() -> None:
    re = _import_run_eval()
    rows = re.load_scenarios(GOLD)
    f = re.filter_scenarios(rows, difficulty="hard")
    assert f
    assert all(str(r.get("difficulty", "")) == "hard" for r in f)


def test_filter_category_consent() -> None:
    re = _import_run_eval()
    rows = re.load_scenarios(GOLD)
    f = re.filter_scenarios(rows, category="consent")
    assert f
    assert all(str(r.get("category", "")) == "consent" for r in f)


def test_dry_run_subprocess_all_parse() -> None:
    cmd = [sys.executable, str(ROOT / "tests" / "run_eval.py"), "--dry-run"]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_dry_run_subprocess_filtered() -> None:
    cmd = [
        sys.executable,
        str(ROOT / "tests" / "run_eval.py"),
        "--dry-run",
        "--scenarios",
        "SC-V-001,SC-C-001,SC-C-002",
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_all_scenario_ids_unique() -> None:
    rows = load_gold_scenarios(GOLD)
    ids = [str(r["id"]) for r in rows]
    assert len(ids) == len(set(ids))


def test_v1_rows_have_required_fields() -> None:
    rows = load_gold_scenarios(GOLD)
    for r in rows:
        if r.get("mode") != "violation_analysis":
            continue
        assert "scenario" in r and str(r["scenario"]).strip()
        assert "expected_articles" in r
        assert isinstance(r["expected_articles"], list)


def test_v2_rows_have_required_fields() -> None:
    rows = load_gold_scenarios(GOLD)
    for r in rows:
        if r.get("mode") != "compliance_assessment":
            continue
        assert "system_description" in r and str(r["system_description"]).strip()
        assert "expected_findings" in r
        assert "expected_documents" in r
        assert isinstance(r["expected_findings"], list)
        assert isinstance(r["expected_documents"], list)


def test_scenario_result_eval_report_roundtrip() -> None:
    sr = ScenarioResult(
        id="SC-V-001",
        mode="violation_analysis",
        title="t",
        status="pass",
        article_recall=0.9,
        article_precision=0.85,
        law_recall=1.0,
        expected_articles=["6"],
        found_article_keys=["6"],
    )
    raw = sr.model_dump()
    sr2 = ScenarioResult.model_validate(raw)
    assert sr2.article_recall == 0.9

    rep = EvalReport(
        total_scenarios=1,
        passed=1,
        scenarios=[sr],
        violation_analysis_summary={"count": 1, "avg_article_recall": 0.9},
    )
    j = rep.model_dump_json()
    rep2 = EvalReport.model_validate_json(j)
    assert rep2.total_scenarios == 1
    assert rep2.scenarios[0].id == "SC-V-001"


def test_outcome_label_pass_warn_fail() -> None:
    assert outcome_label(article_recall=0.9, article_precision=0.9, finding_coverage=None) == "pass"
    assert outcome_label(article_recall=0.8, article_precision=0.5, finding_coverage=0.9) == "pass"
    assert outcome_label(article_recall=0.65, article_precision=0.3, finding_coverage=0.3) == "warn"
    assert outcome_label(article_recall=0.5, article_precision=0.9, finding_coverage=0.5) == "fail"


def test_article_recall_precision_normalized_keys() -> None:
    """Precision/recall for overlapping normalized article keys."""
    exp = ["Art. 6 GDPR", "Art. 7 GDPR"]
    act = {"6", "7", "99"}
    exp_s = {normalize_article_ref(x) for x in exp}
    act_s = {normalize_article_ref(x) for x in act}
    inter = exp_s & act_s
    recall = len(inter) / len(exp_s)
    precision = len(inter) / len(act_s)
    assert recall == 1.0
    assert 0 < precision < 1.0


def test_baseline_json_is_valid() -> None:
    path = ROOT / "gold" / "baseline.json"
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "violation_analysis" in data
    assert "compliance_assessment" in data
