"""HTTP API tests (FastAPI TestClient)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from gdpr_ai.api.app import app
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
from gdpr_ai.db.database import DEFAULT_PROJECT_ID
from gdpr_ai.db.repository import AppRepository
from gdpr_ai.logger import QueryLogRecord
from gdpr_ai.models import AnalysisReport, ClassifiedTopics, ExtractedEntities


@pytest.fixture
def app_db_path(tmp_path: Path) -> Path:
    return tmp_path / "api.sqlite"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, app_db_path: Path) -> TestClient:
    monkeypatch.setattr("gdpr_ai.config.settings.sqlite_path", app_db_path)
    with TestClient(app) as tc:
        yield tc


def _minimal_report() -> AnalysisReport:
    return AnalysisReport(
        scenario_summary="Marketing without consent",
        extracted_entities=ExtractedEntities(summary="test"),
        classified_topics=ClassifiedTopics(topics=["consent"]),
        violations=[],
        severity_level="medium",
    )


def _minimal_assessment() -> ComplianceAssessment:
    dm = DataMap(
        system_name="S",
        system_description="Newsletter tool",
        data_categories=[
            DataCategory(
                name="email",
                sensitivity=Sensitivity.STANDARD,
                volume=Volume.LOW,
                subjects=["users"],
            )
        ],
        processing_purposes=[
            ProcessingPurpose(
                purpose="emailing",
                legal_basis_claimed="consent",
                data_categories=["email"],
            )
        ],
        data_flows=[],
        third_parties=[],
        storage=[],
    )
    return ComplianceAssessment(
        system_name="S",
        overall_risk_level="low",
        findings=[
            Finding(
                area="consent",
                status=ComplianceStatus.AT_RISK,
                relevant_articles=["Art. 7 GDPR"],
                description="Check consent records.",
            )
        ],
        summary="Ok",
        data_map=dm,
    )


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_analyze_violation_mocked(client: TestClient) -> None:
    with patch(
        "gdpr_ai.api.routes.analyze.run_pipeline_logged",
        new_callable=AsyncMock,
        return_value=(_minimal_report(), "log-id-1"),
    ):
        r = client.post("/api/v1/analyze/violation", json={"scenario": "x" * 12})
    assert r.status_code == 200
    body = r.json()
    assert body["analysis_id"] == "log-id-1"
    assert body["mode"] == "violation_analysis"
    assert body["result"]["scenario_summary"] == "Marketing without consent"


def test_analyze_compliance_mocked(client: TestClient) -> None:
    with patch(
        "gdpr_ai.api.routes.analyze.run_compliance_assessment_logged",
        new_callable=AsyncMock,
        return_value=(_minimal_assessment(), "log-id-2"),
    ):
        r = client.post(
            "/api/v1/analyze/compliance",
            json={"system_description": "We run a newsletter for EU users with double opt-in."},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["analysis_id"] == "log-id-2"
    assert body["mode"] == "compliance_assessment"
    assert body["result"]["overall_risk_level"] == "low"


def test_analyze_compliance_structured_mocked(client: TestClient) -> None:
    assessment = _minimal_assessment()
    with patch(
        "gdpr_ai.api.routes.analyze.run_compliance_assessment_logged",
        new_callable=AsyncMock,
        return_value=(assessment, "log-id-3"),
    ):
        r = client.post(
            "/api/v1/analyze/compliance",
            json={"data_map": assessment.data_map.model_dump()},
        )
    assert r.status_code == 200
    assert r.json()["analysis_id"] == "log-id-3"


def test_analyze_compliance_validation_error(client: TestClient) -> None:
    r = client.post("/api/v1/analyze/compliance", json={})
    assert r.status_code == 422


def test_get_analysis_not_found(client: TestClient) -> None:
    r = client.get("/api/v1/analyze/does-not-exist")
    assert r.status_code == 404


def test_get_analysis_mocked(client: TestClient) -> None:
    rep = _minimal_report()
    rec = QueryLogRecord(
        id="abc",
        timestamp="2026-01-01T00:00:00+00:00",
        scenario_text="scenario",
        extracted_entities=None,
        classified_topics=None,
        retrieved_chunks_count=0,
        retrieved_articles=None,
        report_json=rep.model_dump(),
        violations_count=0,
        severity="medium",
        latency_total_ms=1,
        latency_extract_ms=0,
        latency_classify_ms=0,
        latency_retrieve_ms=0,
        latency_reason_ms=0,
        latency_validate_ms=0,
        input_tokens=0,
        output_tokens=0,
        total_tokens=0,
        estimated_cost_eur=0.0,
        model_reasoning=None,
        feedback=None,
        analysis_mode="violation_analysis",
    )
    with patch("gdpr_ai.api.routes.analyze.get_query", return_value=rec):
        r = client.get("/api/v1/analyze/abc")
    assert r.status_code == 200
    assert r.json()["analysis_id"] == "abc"


async def _seed_compliance_analysis(db_path: Path, assessment: ComplianceAssessment) -> None:
    repo = AppRepository(db_path)
    await repo.create_analysis(
        analysis_id="doc-run",
        project_id=DEFAULT_PROJECT_ID,
        mode="compliance_assessment",
        input_text="x",
        result=assessment.model_dump(),
        llm_cost_usd=0.0,
        duration_seconds=0.0,
    )


def test_documents_generate_mocked(client: TestClient, app_db_path: Path) -> None:
    assessment = _minimal_assessment()
    asyncio.run(_seed_compliance_analysis(app_db_path, assessment))
    rec = QueryLogRecord(
        id="doc-run",
        timestamp="2026-01-01T00:00:00+00:00",
        scenario_text="x",
        extracted_entities=None,
        classified_topics=None,
        retrieved_chunks_count=0,
        retrieved_articles=None,
        report_json=assessment.model_dump(),
        violations_count=1,
        severity="low",
        latency_total_ms=1,
        latency_extract_ms=0,
        latency_classify_ms=0,
        latency_retrieve_ms=0,
        latency_reason_ms=0,
        latency_validate_ms=0,
        input_tokens=0,
        output_tokens=0,
        total_tokens=0,
        estimated_cost_eur=0.0,
        model_reasoning=None,
        feedback=None,
        analysis_mode="compliance_assessment",
    )
    with patch("gdpr_ai.api.routes.documents.get_query", return_value=rec):
        r = client.post(
            "/api/v1/documents/generate",
            json={"analysis_id": "doc-run", "doc_types": ["checklist"]},
        )
    assert r.status_code == 200
    payload = r.json()
    assert len(payload["documents"]) == 1
    doc_id = payload["documents"][0]["document_id"]
    gr = client.get(f"/api/v1/documents/{doc_id}")
    assert gr.status_code == 200
    assert "DISCLAIMER" in gr.json()["content"] or "Automated draft" in gr.json()["content"]


def test_documents_generate_wrong_mode(client: TestClient) -> None:
    rep = _minimal_report()
    rec = QueryLogRecord(
        id="v",
        timestamp="2026-01-01T00:00:00+00:00",
        scenario_text="x",
        extracted_entities=None,
        classified_topics=None,
        retrieved_chunks_count=0,
        retrieved_articles=None,
        report_json=rep.model_dump(),
        violations_count=0,
        severity="low",
        latency_total_ms=1,
        latency_extract_ms=0,
        latency_classify_ms=0,
        latency_retrieve_ms=0,
        latency_reason_ms=0,
        latency_validate_ms=0,
        input_tokens=0,
        output_tokens=0,
        total_tokens=0,
        estimated_cost_eur=0.0,
        model_reasoning=None,
        feedback=None,
        analysis_mode="violation_analysis",
    )
    with patch("gdpr_ai.api.routes.documents.get_query", return_value=rec):
        r = client.post(
            "/api/v1/documents/generate",
            json={"analysis_id": "v", "doc_types": ["dpia"]},
        )
    assert r.status_code == 400


def test_projects_crud(client: TestClient) -> None:
    c = client.post(
        "/api/v1/projects",
        json={"name": "P1", "system_description": "Does things with personal data"},
    )
    assert c.status_code == 200
    pid = c.json()["id"]
    lst = client.get("/api/v1/projects")
    assert lst.status_code == 200
    assert len(lst.json()["projects"]) >= 1
    one = client.get(f"/api/v1/projects/{pid}")
    assert one.json()["name"] == "P1"
    up = client.put(
        f"/api/v1/projects/{pid}",
        json={"name": "P2"},
    )
    assert up.status_code == 200
    assert up.json()["name"] == "P2"


def test_projects_404(client: TestClient) -> None:
    assert client.get("/api/v1/projects/nope").status_code == 404
