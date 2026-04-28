"""Pydantic models for unified gold evaluation reports."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ScenarioResult(BaseModel):
    """Metrics for one gold scenario after running the appropriate pipeline."""

    id: str
    mode: str
    title: str
    status: str = Field(description="pass | warn | fail | error")
    article_recall: float = 0.0
    article_precision: float = 0.0
    law_recall: float | None = Field(
        None,
        description="violation_analysis only when expected_laws non-empty",
    )
    finding_coverage: float | None = None
    finding_accuracy: float | None = None
    document_completeness: float | None = None
    expected_articles: list[str] = Field(default_factory=list)
    found_article_keys: list[str] = Field(default_factory=list)
    missing_article_keys: list[str] = Field(default_factory=list)
    extra_article_keys: list[str] = Field(default_factory=list)
    cost_eur: float = 0.0
    duration_seconds: float = 0.0
    error: str | None = None
    hallucinations: int | None = None


class EvalReport(BaseModel):
    """Full unified evaluation run."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    version: str = "2.0.0"
    total_scenarios: int = 0
    passed: int = 0
    warned: int = 0
    failed: int = 0
    errored: int = 0
    avg_article_recall: float = 0.0
    avg_article_precision: float = 0.0
    avg_finding_coverage: float | None = None
    avg_law_recall: float | None = None
    total_cost_eur: float = 0.0
    total_duration_seconds: float = 0.0
    scenarios: list[ScenarioResult] = Field(default_factory=list)
    violation_analysis_summary: dict[str, float | int] | None = None
    compliance_assessment_summary: dict[str, float | int] | None = None
