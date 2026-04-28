"""Tests for gold eval scoring (recital filtering, precision)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
_TESTS = ROOT / "tests"
if str(_TESTS) not in sys.path:
    sys.path.insert(0, str(_TESTS))

from eval_scoring import (  # noqa: E402
    article_recall_precision_violation,
    compliance_article_metrics,
    finding_area_coverage,
)

from gdpr_ai.compliance.schemas import ComplianceStatus, Finding  # noqa: E402


def test_compliance_precision_excludes_recitals_from_denominator() -> None:
    findings = [
        Finding(
            area="consent",
            status=ComplianceStatus.AT_RISK,
            relevant_articles=["Art. 6", "Recital 47"],
            description="x",
            remediation=None,
        ),
    ]
    expected = ["6"]
    rec, prec, *_rest = compliance_article_metrics(expected, findings)
    assert rec == 1.0
    assert prec == 1.0


def test_finding_area_coverage_matches_lawful_basis_wording() -> None:
    """Match gold consent when findings use lawful-basis wording without saying consent."""
    specs = [{"area": "consent", "min_status": "at_risk"}]
    findings = [
        Finding(
            area="Marketing lists — lawful basis",
            status=ComplianceStatus.AT_RISK,
            relevant_articles=["6"],
            description="Lawful basis for the newsletter is not clearly documented.",
            remediation=None,
        )
    ]
    assert finding_area_coverage(specs, findings) == 1.0


def test_violation_precision_excludes_recital_extras() -> None:
    """Unexpected normalized keys that are recitals must not lower precision."""
    violations = [
        SimpleNamespace(article_reference="Art. 6 GDPR"),
        SimpleNamespace(article_reference="Recital 42"),
    ]
    expected = ["Art. 6 GDPR"]
    acceptable: list[str] = []
    rec, prec = article_recall_precision_violation(expected, acceptable, violations)
    assert rec == 1.0
    assert prec == 1.0
