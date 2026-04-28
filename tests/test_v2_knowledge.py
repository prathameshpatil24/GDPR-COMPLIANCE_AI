"""Tests for v2 knowledge ingestion helpers and multi-collection retrieval."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import chromadb
import pytest

from gdpr_ai.config import settings
from gdpr_ai.knowledge.v2_chunk_builders import load_v2_rows_from_raw
from gdpr_ai.models import ClassifiedTopics, ExtractedEntities
from gdpr_ai.retriever import retrieve, retrieve_multi_collection

FIXTURES_RAW = Path(__file__).resolve().parent / "fixtures" / "v2_raw"


def test_load_v2_rows_all_collections_non_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "gdpr_ai.knowledge.v2_chunk_builders.chunk_text_by_tokens",
        lambda text, model, **kwargs: [text] if (text or "").strip() else [""],
    )
    bundles = load_v2_rows_from_raw(FIXTURES_RAW)
    assert set(bundles.keys()) == {
        settings.chroma_collection_dpia,
        settings.chroma_collection_ropa,
        settings.chroma_collection_tom,
        settings.chroma_collection_consent,
        settings.chroma_collection_ai_act,
    }
    for name, rows in bundles.items():
        assert len(rows) > 0, f"empty bundle {name}"


def test_retrieve_multi_collection_merges(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Two v2 collections with one doc each; merged ranking returns both."""
    chroma_path = tmp_path / "chroma"
    monkeypatch.setattr("gdpr_ai.retriever.settings.chroma_path", chroma_path)
    dim = 8
    monkeypatch.setattr(
        "gdpr_ai.retriever.embed_texts",
        lambda _model, texts, batch_size=16: [[0.01] * dim for _ in texts],
    )

    client = chromadb.PersistentClient(path=str(chroma_path))
    for name, doc in (
        (settings.chroma_collection_dpia, "DPIA Article 35 high risk assessment"),
        (settings.chroma_collection_consent, "Consent Article 7 conditions"),
    ):
        coll = client.create_collection(name=name, metadata={"hnsw:space": "cosine"})
        coll.add(
            ids=["id-1"],
            documents=[doc],
            embeddings=[[0.01] * dim],
            metadatas=[
                {
                    "source": "test",
                    "article_number": "test",
                    "topic_tags": "gdpr",
                    "source_url": "https://example.invalid",
                }
            ],
        )

    out = retrieve_multi_collection(
        "consent and DPIA requirements",
        collection_names=[
            settings.chroma_collection_dpia,
            settings.chroma_collection_consent,
        ],
        top_k_per_collection=4,
        top_k=10,
    )
    assert len(out) == 2
    cols = {c.metadata.get("chroma_collection") for c in out}
    assert cols == {settings.chroma_collection_dpia, settings.chroma_collection_consent}


def test_retrieve_v1_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: single-collection retrieve still works with mocked Chroma."""
    chroma_path = MagicMock()
    chroma_path.exists.return_value = True
    bm25_path = MagicMock()
    bm25_path.exists.return_value = False
    monkeypatch.setattr("gdpr_ai.retriever.settings.chroma_path", chroma_path)
    monkeypatch.setattr("gdpr_ai.retriever.settings.bm25_index_path", bm25_path)
    monkeypatch.setattr(
        "gdpr_ai.retriever.embed_texts",
        lambda model_name, texts, batch_size=16: [[0.0, 0.0, 0.0]] * len(texts),
    )

    class FakeColl:
        def query(self, **kwargs):  # noqa: ANN003, ANN201
            return {
                "ids": [["a"]],
                "documents": [["GDPR consent marketing"]],
                "metadatas": [
                    [{"source": "gdpr", "topic_tags": "consent,gdpr", "source_url": "u1"}],
                ],
                "distances": [[0.1]],
            }

        def count(self) -> int:
            return 1

    class FakeClient:
        def get_collection(self, name: str) -> FakeColl:  # noqa: ARG002
            return FakeColl()

    monkeypatch.setattr("gdpr_ai.retriever.chromadb.PersistentClient", lambda path: FakeClient())
    topics = ClassifiedTopics(topics=["consent"], rationale="")
    entities = ExtractedEntities(jurisdiction="Germany")
    out = retrieve("email marketing", topics, entities, top_k=3)
    assert len(out) == 1
    assert "consent" in out[0].text.lower()
