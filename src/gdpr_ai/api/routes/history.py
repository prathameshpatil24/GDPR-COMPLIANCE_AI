"""History and analysis detail endpoints (app database + query log fallback)."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from gdpr_ai.api.deps import get_repository
from gdpr_ai.api.schemas import HistoryDetailResponse, HistoryListResponse, HistorySummaryItem
from gdpr_ai.db.repository import AppRepository
from gdpr_ai.logger import get_query

logger = logging.getLogger(__name__)

router = APIRouter()


def _severity_from_result(mode: str, result: dict) -> str | None:
    if mode == "violation_analysis":
        raw = result.get("severity_level")
        return str(raw) if raw is not None else None
    if mode == "compliance_assessment":
        raw = result.get("overall_risk_level")
        return str(raw) if raw is not None else None
    return None


@router.get("/history", response_model=HistoryListResponse)
async def list_history(
    limit: int = Query(50, ge=1, le=500),
    mode: str | None = Query(
        None,
        description="Filter: violation_analysis or compliance_assessment",
    ),
    repo: AppRepository = Depends(get_repository),
) -> HistoryListResponse:
    """List past analyses from the application database (newest first)."""
    if mode is not None and mode not in ("violation_analysis", "compliance_assessment"):
        raise HTTPException(
            status_code=422,
            detail="mode must be violation_analysis or compliance_assessment",
        )
    rows = await repo.list_analyses(limit=limit, mode=mode)
    items: list[HistorySummaryItem] = []
    for row in rows:
        try:
            result = json.loads(row.result_json)
        except json.JSONDecodeError:
            logger.warning("Skipping analysis %s: invalid result_json", row.id)
            continue
        items.append(
            HistorySummaryItem(
                id=row.id,
                mode=row.mode,
                scenario_system_description=row.input_text or "",
                severity=_severity_from_result(row.mode, result),
                created_at=row.created_at,
                latency_ms=(
                    (row.duration_seconds * 1000.0) if row.duration_seconds is not None else None
                ),
                cost_eur=row.llm_cost_usd,
            )
        )
    return HistoryListResponse(analyses=items)


@router.get("/history/{analysis_id}", response_model=HistoryDetailResponse)
async def get_history_detail(
    analysis_id: str,
    repo: AppRepository = Depends(get_repository),
) -> HistoryDetailResponse:
    """Return full analysis JSON for one id (app DB first, then query log)."""
    row = await repo.get_analysis(analysis_id)
    if row:
        try:
            result = json.loads(row.result_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=500, detail="Stored analysis JSON is invalid") from exc
        return HistoryDetailResponse(
            analysis_id=row.id,
            mode=row.mode,
            result=result,
            scenario_text=row.input_text or "",
            created_at=row.created_at,
            latency_ms=(
                (row.duration_seconds * 1000.0) if row.duration_seconds is not None else None
            ),
            cost_eur=row.llm_cost_usd,
        )
    rec = get_query(analysis_id)
    if not rec or not rec.report_json:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return HistoryDetailResponse(
        analysis_id=rec.id,
        mode=rec.analysis_mode,
        result=rec.report_json,
        scenario_text=rec.scenario_text,
        created_at=rec.timestamp,
        latency_ms=float(rec.latency_total_ms) if rec.latency_total_ms else None,
        cost_eur=rec.estimated_cost_eur,
    )
