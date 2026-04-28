"""Aggregate statistics from the query log (same source as ``gdpr-check stats``)."""

from __future__ import annotations

from fastapi import APIRouter

from gdpr_ai.api.schemas import StatsResponse
from gdpr_ai.logger import get_stats_dashboard

router = APIRouter()


@router.get("/stats", response_model=StatsResponse)
async def stats() -> StatsResponse:
    """Return aggregate counters, averages, and daily breakdowns for all logged queries."""
    return StatsResponse.model_validate(get_stats_dashboard())
