"""Tests for retrieval helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from gdpr_ai.knowledge.bm25_tokens import bm25_tokenize
from gdpr_ai.models import ClassifiedTopics, ExtractedEntities, RetrievedChunk
from gdpr_ai.retriever import _dense_query_text, retrieve


def test_dense_query_text_adds_transfer_and_security_hints() -> None:
    topics = ClassifiedTopics(
        topics=["gdpr", "transfers", "security-and-breaches", "security-of-processing"],
        rationale="",
    )
    out = _dense_query_text("vendor subprocessors US region", topics)
    assert "Articles 44" in out or "Article 44" in out
    assert "Article 32" in out


def test_dense_query_text_adds_consent_and_information_hints() -> None:
    topics = ClassifiedTopics(
        topics=["gdpr", "consent", "information", "data-subject-rights"],
        rationale="",
    )
    out = _dense_query_text("newsletter signup", topics)
    assert "Article 5" in out
    assert "Article 7" in out
    assert "Articles 12 and 13" in out


def test_bm25_tokenize_splits_words() -> None:
    assert bm25_tokenize("Article 6(1)(a) GDPR; consent!") == [
        "article",
        "6",
        "1",
        "a",
        "gdpr",
        "consent",
    ]


def test_retrieve_deduplicates_identical_text_prefixes(monkeypatch) -> None:
    chroma_path = MagicMock()
    chroma_path.exists.return_value = True
    bm25_path = MagicMock()
    bm25_path.exists.return_value = False
    monkeypatch.setattr("gdpr_ai.retriever.settings.chroma_path", chroma_path)
    monkeypatch.setattr("gdpr_ai.retriever.settings.bm25_index_path", bm25_path)

    fake_chunks = [
        RetrievedChunk(
            chunk_id="a",
            text="same text prefix " * 5,
            metadata={"source": "gdpr", "topic_tags": "consent,gdpr", "source_url": "u1"},
            similarity_score=1.0,
            dense_score=1.0,
            bm25_score=0.0,
        ),
        RetrievedChunk(
            chunk_id="b",
            text="same text prefix " * 5,
            metadata={"source": "gdpr", "topic_tags": "consent,gdpr", "source_url": "u2"},
            similarity_score=0.9,
            dense_score=0.9,
            bm25_score=0.0,
        ),
    ]

    monkeypatch.setattr(
        "gdpr_ai.retriever.embed_texts",
        lambda model_name, texts, batch_size=16: [[0.0, 0.0, 0.0]] * len(texts),
    )

    class FakeColl:
        def query(self, **kwargs):  # noqa: ANN003, ANN201
            return {
                "ids": [[c.chunk_id for c in fake_chunks]],
                "documents": [[c.text for c in fake_chunks]],
                "metadatas": [[c.metadata for c in fake_chunks]],
                "distances": [[0.1, 0.2]],
            }

        def count(self) -> int:
            return 2

    class FakeClient:
        def get_collection(self, name: str) -> FakeColl:  # noqa: ARG002
            return FakeColl()

    monkeypatch.setattr("gdpr_ai.retriever.chromadb.PersistentClient", lambda path: FakeClient())

    topics = ClassifiedTopics(topics=["consent"], rationale="")
    entities = ExtractedEntities(jurisdiction="Germany")
    out = retrieve("marketing consent email", topics, entities, top_k=5)
    assert len(out) == 1
