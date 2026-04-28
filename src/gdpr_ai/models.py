"""Pydantic models shared across the GDPR AI pipeline."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Scenario(BaseModel):
    """User-provided scenario input."""

    text: str
    source: Literal["cli", "file"] = "cli"
    reference: str | None = None


class ExtractedEntities(BaseModel):
    """Structured entities extracted from the scenario text."""

    actors: list[str] = Field(default_factory=list)
    data_types: list[str] = Field(default_factory=list)
    processing_activities: list[str] = Field(default_factory=list)
    legal_bases_mentioned: list[str] = Field(default_factory=list)
    jurisdiction: str = "unspecified"
    special_categories_present: bool = False
    summary: str = ""


class ClassifiedTopics(BaseModel):
    """GDPR topic labels used to scope retrieval."""

    topics: list[str] = Field(default_factory=list)
    rationale: str = ""


class RetrievedChunk(BaseModel):
    """Single retrieved knowledge chunk with hybrid scores."""

    chunk_id: str
    text: str
    metadata: dict[str, str]
    similarity_score: float = Field(description="Final fused relevance score")
    dense_score: float = 0.0
    bm25_score: float = 0.0


class ArticleViolation(BaseModel):
    """One cited GDPR-related violation hypothesis."""

    article_reference: str = Field(description='e.g. "Art. 6(1)(a) GDPR"')
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_chunk_ids: list[str] = Field(default_factory=list)
    source_url: str = ""


class AnalysisReport(BaseModel):
    """Final structured report returned to the CLI."""

    scenario_summary: str
    extracted_entities: ExtractedEntities
    classified_topics: ClassifiedTopics
    violations: list[ArticleViolation]
    severity_level: Literal["low", "medium", "high", "critical", "unknown"] = "unknown"
    severity_rationale: str = ""
    recommendations: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    similar_cases: list[dict[str, Any]] = Field(default_factory=list)
    unsupported_notes: list[str] = Field(
        default_factory=list,
        description="Articles/topics that seem relevant but were not grounded in chunks.",
    )
    disclaimer: str = ""
