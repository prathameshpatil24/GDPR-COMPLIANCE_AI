"""Tests for compliance intake and article mapping."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from gdpr_ai.compliance.intake import parse_freetext_input, parse_structured_input
from gdpr_ai.compliance.mapper import map_articles
from gdpr_ai.compliance.schemas import ComplianceStatus, DataCategory, Sensitivity, Volume
from gdpr_ai.llm.client import LLMResult
from gdpr_ai.models import RetrievedChunk


def _minimal_datamap_dict() -> dict:
    return {
        "system_name": "Test SaaS",
        "system_description": "Collects emails for newsletters.",
        "data_categories": [
            {
                "name": "email",
                "sensitivity": "standard",
                "volume": "low",
                "subjects": ["customers"],
            }
        ],
        "processing_purposes": [
            {
                "purpose": "newsletter",
                "legal_basis_claimed": "consent",
                "data_categories": ["email"],
            }
        ],
        "data_flows": [],
        "third_parties": [],
        "storage": [],
        "has_automated_decision_making": False,
        "processes_children_data": False,
        "uses_ai_ml": False,
    }


def test_parse_structured_input_valid() -> None:
    dm = parse_structured_input(_minimal_datamap_dict())
    assert dm.system_name == "Test SaaS"
    assert dm.data_categories[0].name == "email"


def test_parse_structured_input_invalid() -> None:
    bad = _minimal_datamap_dict()
    bad["data_categories"][0]["sensitivity"] = "not_an_enum"
    with pytest.raises(ValidationError):
        parse_structured_input(bad)


def test_enum_serialization_roundtrip() -> None:
    cat = DataCategory(
        name="x",
        sensitivity=Sensitivity.SPECIAL_CATEGORY,
        volume=Volume.HIGH,
        subjects=["a"],
    )
    d = json.loads(cat.model_dump_json())
    assert d["sensitivity"] == "special_category"
    assert ComplianceStatus.AT_RISK.value == "at_risk"


@pytest.mark.asyncio
async def test_parse_freetext_mocked() -> None:
    payload = _minimal_datamap_dict()
    fake = LLMResult(
        text=json.dumps(payload),
        model="test",
        input_tokens=1,
        output_tokens=1,
        latency_ms=1,
        cost_eur=0.0,
    )
    with patch("gdpr_ai.compliance.intake.complete_text", new_callable=AsyncMock) as m:
        m.return_value = fake
        dm, res = await parse_freetext_input("We store emails for marketing.")
    assert dm.system_name == "Test SaaS"
    assert res.cost_eur == 0.0


def test_map_articles_non_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    dm = parse_structured_input(_minimal_datamap_dict())

    def fake_retrieve(*_a, **_k):
        return [
            RetrievedChunk(
                chunk_id="m1",
                text="Art. 6 GDPR lawfulness",
                metadata={"source": "gdpr", "topic_tags": "gdpr", "source_url": "u1"},
                similarity_score=1.0,
            )
        ]

    def fake_multi(*_a, **_k):
        return [
            RetrievedChunk(
                chunk_id="v1",
                text="DPIA guidance",
                metadata={"source": "dpia", "topic_tags": "dpia", "source_url": "u2"},
                similarity_score=0.9,
            )
        ]

    monkeypatch.setattr("gdpr_ai.compliance.mapper.retrieve", fake_retrieve)
    monkeypatch.setattr("gdpr_ai.compliance.mapper.retrieve_multi_collection", fake_multi)
    article_map = map_articles(dm)
    assert "category:email" in article_map
    assert len(article_map["category:email"]) >= 1
    ids = {c.chunk_id for c in article_map["category:email"]}
    assert "m1" in ids and "v1" in ids
