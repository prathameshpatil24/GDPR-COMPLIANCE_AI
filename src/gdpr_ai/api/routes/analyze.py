"""Violation and compliance analysis endpoints."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException

from gdpr_ai.api.deps import get_repository
from gdpr_ai.api.schemas import (
    AnalysisGetResponse,
    AnalysisRunResponse,
    ComplianceAnalyzeRequest,
    ViolationAnalyzeRequest,
)
from gdpr_ai.compliance.orchestrator import run_compliance_assessment_logged
from gdpr_ai.db.database import DEFAULT_PROJECT_ID
from gdpr_ai.db.repository import AppRepository
from gdpr_ai.logger import get_query
from gdpr_ai.pipeline import run_pipeline_logged

logger = logging.getLogger(__name__)

router = APIRouter()


def _resolve_project_id(raw: str | None) -> str:
    return raw if raw and raw.strip() else DEFAULT_PROJECT_ID


async def _persist_after_log(
    repo: AppRepository,
    *,
    analysis_id: str,
    project_id: str,
    mode: str,
    input_text: str | None,
    result: dict,
) -> None:
    log = get_query(analysis_id)
    cost = float(log.estimated_cost_eur) if log else None
    duration = (log.latency_total_ms / 1000.0) if log else None
    try:
        await repo.create_analysis(
            analysis_id=analysis_id,
            project_id=project_id,
            mode=mode,
            input_text=input_text,
            result=result,
            llm_cost_usd=cost,
            duration_seconds=duration,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Could not persist analysis %s to app database", analysis_id)


@router.post("/analyze/violation", response_model=AnalysisRunResponse)
async def analyze_violation(
    body: ViolationAnalyzeRequest,
    repo: AppRepository = Depends(get_repository),
) -> AnalysisRunResponse:
    """Run v1 violation analysis (RAG pipeline)."""
    pid = _resolve_project_id(body.project_id)
    if (await repo.get_project(pid)) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        report, qid = await run_pipeline_logged(body.scenario)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    await _persist_after_log(
        repo,
        analysis_id=qid,
        project_id=pid,
        mode="violation_analysis",
        input_text=body.scenario,
        result=report.model_dump(),
    )
    return AnalysisRunResponse(
        analysis_id=qid,
        mode="violation_analysis",
        result=report.model_dump(),
    )


@router.post("/analyze/compliance", response_model=AnalysisRunResponse)
async def analyze_compliance(
    body: ComplianceAnalyzeRequest,
    repo: AppRepository = Depends(get_repository),
) -> AnalysisRunResponse:
    """Run v2 compliance assessment (intake → retrieve → assess)."""
    pid = _resolve_project_id(body.project_id)
    if (await repo.get_project(pid)) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    payload: dict | str
    input_text: str | None
    if body.system_description is not None:
        payload = body.system_description.strip()
        input_text = payload
    else:
        payload = body.data_map or {}
        input_text = json.dumps(payload)[:8000]
    try:
        assessment, qid = await run_compliance_assessment_logged(payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    await _persist_after_log(
        repo,
        analysis_id=qid,
        project_id=pid,
        mode="compliance_assessment",
        input_text=input_text,
        result=assessment.model_dump(),
    )
    return AnalysisRunResponse(
        analysis_id=qid,
        mode="compliance_assessment",
        result=assessment.model_dump(),
    )


@router.get("/analyze/{analysis_id}", response_model=AnalysisGetResponse)
async def get_analysis(
    analysis_id: str,
    repo: AppRepository = Depends(get_repository),
) -> AnalysisGetResponse:
    """Fetch a stored analysis by id (app database, with fallback to the query log)."""
    row = await repo.get_analysis(analysis_id)
    if row:
        return AnalysisGetResponse(
            analysis_id=row.id,
            mode=row.mode,
            result=json.loads(row.result_json),
            scenario_text=row.input_text or "",
            created_at=row.created_at,
        )
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
