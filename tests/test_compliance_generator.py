"""Tests for compliance document generation (Jinja2)."""

from __future__ import annotations

from pathlib import Path

from gdpr_ai.compliance.generator import generate_documents, save_documents
from gdpr_ai.compliance.schemas import (
    ComplianceAssessment,
    ComplianceStatus,
    DataCategory,
    DataFlow,
    DataMap,
    Finding,
    ProcessingPurpose,
    Sensitivity,
    StorageInfo,
    ThirdParty,
    ThirdPartyRole,
    Volume,
)


def _sample_assessment() -> ComplianceAssessment:
    return ComplianceAssessment(
        system_name='Test "Beta" — v1',
        overall_risk_level="medium",
        findings=[
            Finding(
                area="data_minimization",
                status=ComplianceStatus.AT_RISK,
                relevant_articles=["Art. 5(1)(c) GDPR"],
                description="Collect only what you need.",
                remediation="Trim fields in signup.",
                technical_guidance="Drop unused columns; TTL raw logs.",
            ),
            Finding(
                area="security",
                status=ComplianceStatus.INSUFFICIENT_INFO,
                relevant_articles=["Art. 32 GDPR"],
                description="Encryption posture unclear.",
                remediation=None,
                technical_guidance=None,
            ),
        ],
        summary="Overall: tighten minimization and document security controls.",
        data_map=DataMap(
            system_name='Test "Beta" — v1',
            system_description=(
                "Handles café loyalty: names, emails, visit timestamps. "
                "Unicode: café résumé 日本語."
            ),
            data_categories=[
                DataCategory(
                    name="email",
                    sensitivity=Sensitivity.STANDARD,
                    volume=Volume.MEDIUM,
                    subjects=["customers"],
                ),
                DataCategory(
                    name="health_notes",
                    sensitivity=Sensitivity.SPECIAL_CATEGORY,
                    volume=Volume.LOW,
                    subjects=["customers"],
                ),
            ],
            processing_purposes=[
                ProcessingPurpose(
                    purpose="loyalty_marketing",
                    legal_basis_claimed=None,
                    data_categories=["email"],
                ),
                ProcessingPurpose(
                    purpose="wellness_tips",
                    legal_basis_claimed="legitimate interests",
                    data_categories=["health_notes"],
                ),
            ],
            data_flows=[
                DataFlow(
                    source="mobile_app",
                    destination="vendor_US",
                    data_categories=["email"],
                    crosses_border=True,
                    destination_country="US",
                )
            ],
            third_parties=[
                ThirdParty(
                    name="Vendor US",
                    role=ThirdPartyRole.PROCESSOR,
                    purpose="analytics",
                    dpa_in_place=None,
                    country="US",
                )
            ],
            storage=[
                StorageInfo(
                    location="Postgres EU",
                    country="DE",
                    encryption_at_rest=None,
                    encryption_in_transit=True,
                    retention_period=None,
                )
            ],
            has_automated_decision_making=False,
            processes_children_data=False,
            uses_ai_ml=False,
        ),
    )


def test_generate_documents_all_keys_and_disclaimer() -> None:
    docs = generate_documents(_sample_assessment(), generated_date="2026-04-26")
    assert set(docs.keys()) == {
        "dpia",
        "ropa",
        "checklist",
        "consent_flow",
        "retention_policy",
    }
    for content in docs.values():
        assert "DISCLAIMER" in content or "Automated draft" in content


def test_generate_documents_warns_on_missing_fields() -> None:
    docs = generate_documents(_sample_assessment())
    assert "NOT SPECIFIED ⚠️" in docs["dpia"] or "⚠️ NOT SPECIFIED" in docs["ropa"]
    assert "⚠️ NOT DEFINED" in docs["retention_policy"]


def test_save_documents_writes_files(tmp_path: Path) -> None:
    docs = generate_documents(_sample_assessment(), generated_date="2026-01-01")
    paths = save_documents(docs, tmp_path)
    assert len(paths) == 5
    for p in paths:
        assert p.exists()
        assert p.suffix == ".md"
    assert (tmp_path / "dpia.md").read_text(encoding="utf-8") == docs["dpia"]


def test_templates_render_without_jinja_syntax_in_user_text() -> None:
    """User text with braces should not be interpreted as Jinja (single braces are literal)."""
    a = _sample_assessment()
    a.data_map.system_description = "Template-like text: {single} and also } odd { braces ok"
    docs = generate_documents(a)
    assert "{single}" in docs["dpia"]
