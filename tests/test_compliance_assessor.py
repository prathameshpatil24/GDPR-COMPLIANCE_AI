"""Tests for compliance assessment and orchestrator logging."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from gdpr_ai.compliance.assessor import _filter_findings, assess_compliance
from gdpr_ai.compliance.orchestrator import run_compliance_assessment
from gdpr_ai.compliance.schemas import (
    ComplianceAssessment,
    ComplianceStatus,
    DataCategory,
    DataMap,
    Finding,
    ProcessingPurpose,
    Sensitivity,
    Volume,
)
from gdpr_ai.llm.client import LLMResult
from gdpr_ai.models import RetrievedChunk


def _dm() -> DataMap:
    return DataMap(
        system_name="S",
        system_description="Newsletter",
        data_categories=[
            DataCategory(
                name="email",
                sensitivity=Sensitivity.STANDARD,
                volume=Volume.LOW,
                subjects=["u"],
            )
        ],
        processing_purposes=[
            ProcessingPurpose(
                purpose="newsletter",
                legal_basis_claimed="consent",
                data_categories=["email"],
            )
        ],
        data_flows=[],
        third_parties=[],
        storage=[],
    )


def test_filter_findings_strips_ungrounded_articles() -> None:
    chunks = [
        RetrievedChunk(
            chunk_id="c1",
            text="Article 6 GDPR lawfulness of processing",
            metadata={
                "article_number": "Art. 6",
                "full_citation": "Art. 6 GDPR",
                "source_url": "u",
            },
            similarity_score=1.0,
        )
    ]
    findings = [
        Finding(
            area="basis",
            status=ComplianceStatus.AT_RISK,
            relevant_articles=["Art. 6 GDPR", "Art. 999 GDPR"],
            description="x",
        )
    ]
    out = _filter_findings(findings, chunks)
    assert out[0].relevant_articles == ["Art. 6 GDPR"]


@pytest.mark.asyncio
async def test_assess_compliance_mocked_filters() -> None:
    dm = _dm()
    chunk = RetrievedChunk(
        chunk_id="c1",
        text="Conditions for consent Article 7 GDPR",
        metadata={
            "article_number": "Art. 7",
            "full_citation": "Art. 7 GDPR",
            "source_url": "u",
        },
        similarity_score=1.0,
    )
    assessment_dump = {
        "system_name": "S",
        "overall_risk_level": "medium",
        "findings": [
            {
                "area": "consent",
                "status": "at_risk",
                "relevant_articles": ["Art. 7 GDPR", "Art. 500 GDPR"],
                "description": "Need consent records",
                "remediation": "Implement UI",
                "technical_guidance": "Use TLS",
            }
        ],
        "summary": "Review consent flow.",
    }
    fake = LLMResult(
        text=json.dumps(assessment_dump),
        model="test",
        input_tokens=1,
        output_tokens=1,
        latency_ms=1,
        cost_eur=0.0,
    )
    with patch("gdpr_ai.compliance.assessor.complete_text", new_callable=AsyncMock) as m:
        m.return_value = fake
        ass, res = await assess_compliance(dm, {"k": [chunk]})
    assert res.cost_eur == 0.0
    arts = ass.findings[0].relevant_articles
    assert "Art. 7 GDPR" in arts
    assert "Art. 500 GDPR" not in arts


@pytest.mark.asyncio
async def test_run_compliance_assessment_logs_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    logged: dict = {}

    def capture_log(**kwargs):  # noqa: ANN003
        logged.update(kwargs)
        return "qid"

    dm = _dm()
    assessment = ComplianceAssessment(
        system_name="S",
        overall_risk_level="low",
        findings=[],
        summary="ok",
        data_map=dm,
    )
    monkeypatch.setattr("gdpr_ai.compliance.orchestrator.log_query", capture_log)
    monkeypatch.setattr("gdpr_ai.compliance.orchestrator.map_articles", lambda _dm: {"x": []})
    monkeypatch.setattr(
        "gdpr_ai.compliance.orchestrator.assess_compliance",
        AsyncMock(return_value=(assessment, LLMResult("", "m", 0, 0, 0, 0.0))),
    )

    out = await run_compliance_assessment(dm.model_dump())
    assert out.summary == "ok"
    assert logged.get("analysis_mode") == "compliance_assessment"
