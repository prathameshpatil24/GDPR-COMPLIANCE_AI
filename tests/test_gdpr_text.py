"""Unit tests for GDPR chunk text helpers."""

from __future__ import annotations

from gdpr_ai.knowledge.gdpr_text import citation_title, paragraphs_from_gdpr_article_text


def test_citation_title_strips_mirror_prefix() -> None:
    assert citation_title("6", "Art. 6 GDPR Lawfulness of processing") == "Lawfulness of processing"
    assert citation_title("6", "Art. 6 GDPR – Lawfulness") == "Lawfulness"


def test_paragraphs_split_numbered_lines() -> None:
    text = "1. First para.\n\n2. Second para."
    parts = paragraphs_from_gdpr_article_text(text)
    assert len(parts) == 2
    assert parts[0].startswith("1.")
