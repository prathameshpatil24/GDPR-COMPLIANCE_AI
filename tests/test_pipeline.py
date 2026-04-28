"""Pipeline tests with mocked LLM and retrieval."""

from __future__ import annotations

import pytest

from gdpr_ai.exceptions import HallucinationDetected
from gdpr_ai.llm.client import LLMResult
from gdpr_ai.models import (
    AnalysisReport,
    ArticleViolation,
    ClassifiedTopics,
    ExtractedEntities,
    RetrievedChunk,
)
from gdpr_ai.pipeline import _grounding_check, classify_topics, extract_entities


@pytest.mark.asyncio
async def test_extract_entities_parses_json(monkeypatch) -> None:
    async def fake_complete_text(**kwargs):  # noqa: ANN003, ANN201
        return LLMResult(
            text='{"actors":["controller"],"data_types":["email"],"processing_activities":["marketing"],'
            '"legal_bases_mentioned":[],"jurisdiction":"EU","special_categories_present":false,'
            '"summary":"Marketing without consent."}',
            model="x",
            input_tokens=1,
            output_tokens=1,
            latency_ms=1,
            cost_eur=0.0,
        )

    monkeypatch.setattr("gdpr_ai.pipeline.complete_text", fake_complete_text)
    entities, meta = await extract_entities("scenario text here")
    assert entities.actors == ["controller"]
    assert meta.input_tokens == 1


@pytest.mark.asyncio
async def test_classify_topics_filters_unknown(monkeypatch) -> None:
    async def fake_complete_text(**kwargs):  # noqa: ANN003, ANN201
        return LLMResult(
            text='{"topics":["consent","not-a-real-topic"],"rationale":"because"}',
            model="x",
            input_tokens=1,
            output_tokens=1,
            latency_ms=1,
            cost_eur=0.0,
        )

    monkeypatch.setattr("gdpr_ai.pipeline.complete_text", fake_complete_text)
    entities = ExtractedEntities(summary="s")
    topics, _meta = await classify_topics("scenario", entities)
    assert topics.topics == ["consent"]


def test_grounding_check_rejects_unknown_url() -> None:
    chunks = [
        RetrievedChunk(
            chunk_id="1",
            text="t",
            metadata={"source_url": "https://ok.example"},
            similarity_score=1.0,
        )
    ]
    report = AnalysisReport(
        scenario_summary="s",
        extracted_entities=ExtractedEntities(summary="s"),
        classified_topics=ClassifiedTopics(topics=["gdpr"]),
        violations=[
            ArticleViolation(
                article_reference="Art. 5 GDPR",
                description="d",
                confidence=0.5,
                supporting_chunk_ids=["1"],
                source_url="https://bad.example",
            )
        ],
    )
    with pytest.raises(HallucinationDetected):
        _grounding_check(report, chunks)
