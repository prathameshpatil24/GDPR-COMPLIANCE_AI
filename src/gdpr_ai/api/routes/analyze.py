"""Violation and compliance analysis endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from gdpr_ai.api.schemas import (
    AnalysisGetResponse,
    AnalysisRunResponse,
    ComplianceAnalyzeRequest,
    ViolationAnalyzeRequest,
)
from gdpr_ai.compliance.orchestrator import run_compliance_assessment_logged
from gdpr_ai.logger import get_query
from gdpr_ai.pipeline import run_pipeline_logged

router = APIRouter()


@router.post("/analyze/violation", response_model=AnalysisRunResponse)
async def analyze_violation(body: ViolationAnalyzeRequest) -> AnalysisRunResponse:
    """Run v1 violation analysis (RAG pipeline)."""
    try:
        report, qid = await run_pipeline_logged(body.scenario)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return AnalysisRunResponse(
        analysis_id=qid,
        mode="violation_analysis",
        result=report.model_dump(),
    )


@router.post("/analyze/compliance", response_model=AnalysisRunResponse)
async def analyze_compliance(body: ComplianceAnalyzeRequest) -> AnalysisRunResponse:
    """Run v2 compliance assessment (intake → retrieve → assess)."""
    payload: dict | str
    if body.system_description is not None:
        payload = body.system_description.strip()
    else:
        payload = body.data_map or {}
    try:
        assessment, qid = await run_compliance_assessment_logged(payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return AnalysisRunResponse(
        analysis_id=qid,
        mode="compliance_assessment",
        result=assessment.model_dump(),
    )


@router.get("/analyze/{analysis_id}", response_model=AnalysisGetResponse)
def get_analysis(analysis_id: str) -> AnalysisGetResponse:
    """Fetch a stored analysis by query log id."""
    rec = get_query(analysis_id)
    if not rec or not rec.report_json:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return AnalysisGetResponse(
        analysis_id=rec.id,
        mode=rec.analysis_mode,
        result=rec.report_json,
        scenario_text=rec.scenario_text,
        created_at=rec.timestamp,
    )
