"""Tests for Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from gdpr_ai.models import (
    AnalysisReport,
    ArticleViolation,
    ClassifiedTopics,
    ExtractedEntities,
    RetrievedChunk,
    Scenario,
)


def test_scenario_roundtrip() -> None:
    s = Scenario(text="A controller processes health data without consent.")
    assert s.source == "cli"


def test_extracted_entities_defaults() -> None:
    e = ExtractedEntities(summary="Health profiling without consent.")
    assert e.actors == []


def test_article_violation_confidence_bounds() -> None:
    with pytest.raises(ValidationError):
        ArticleViolation(
            article_reference="Art. 5 GDPR",
            description="d",
            confidence=1.5,
            source_url="https://example.com",
        )


def test_analysis_report_serialization() -> None:
    entities = ExtractedEntities(summary="s")
    topics = ClassifiedTopics(topics=["consent"], rationale="r")
    v = ArticleViolation(
        article_reference="Art. 9 GDPR",
        description="Special categories without a lawful basis.",
        confidence=0.8,
        supporting_chunk_ids=["abc"],
        source_url="https://example.com",
    )
    report = AnalysisReport(
        scenario_summary="summary",
        extracted_entities=entities,
        classified_topics=topics,
        violations=[v],
        severity_level="high",
        recommendations=["notify DPA"],
        citations=["EUR-Lex"],
    )
    data = report.model_dump()
    restored = AnalysisReport.model_validate(data)
    assert restored.violations[0].article_reference == "Art. 9 GDPR"


def test_retrieved_chunk_metadata_strings() -> None:
    ch = RetrievedChunk(
        chunk_id="1",
        text="text",
        metadata={"source": "gdpr", "article_number": "Art. 6"},
        similarity_score=0.42,
    )
    assert ch.metadata["source"] == "gdpr"
