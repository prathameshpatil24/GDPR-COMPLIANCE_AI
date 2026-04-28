"""Split GDPR article plain text into embed-friendly pieces with stable headings."""

from __future__ import annotations

import re
from typing import Any

from gdpr_ai.knowledge.chunk_split import chunk_text_by_tokens


def citation_title(article_number: str, raw_title: str) -> str:
    """Strip a leading \"Art. N GDPR\" prefix from mirror titles when present."""
    num = article_number.strip()
    t = (raw_title or "").strip()
    m = re.match(rf"^Art\.\s*{re.escape(num)}\s*GDPR\s*[–-]?\s*(.+)$", t, flags=re.I)
    if m:
        return m.group(1).strip()
    m2 = re.match(r"^Art\.\s*\d+\s*GDPR\s*[–-]?\s*(.+)$", t, flags=re.I)
    return m2.group(1).strip() if m2 else t


def paragraphs_from_gdpr_article_text(text: str) -> list[str]:
    """Split consolidated article text into numbered paragraphs where possible.

    EUR-Lex plain text typically uses lines starting with \"1. \", \"2. \", etc.
    Falls back to a single segment when no numbered paragraphs are detected.
    """
    stripped = (text or "").strip()
    if not stripped:
        return []
    parts = re.split(r"(?m)(?=^\d+\.\s+)", stripped)
    cleaned = [p.strip() for p in parts if p.strip()]
    if len(cleaned) <= 1 and "\n\n" in stripped:
        alt = [p.strip() for p in re.split(r"\n\s*\n", stripped) if p.strip()]
        if len(alt) > 1:
            return alt
    return cleaned if cleaned else [stripped]


def text_pieces_for_gdpr_article(
    article: dict[str, Any],
    embedding_model: str,
    max_tokens: int = 512,
    overlap_tokens: int = 64,
) -> list[tuple[str, str]]:
    """Return (paragraph_label, text_with_header) pairs for one GDPR article.

    Each piece is prefixed with the article title for embedding quality. Long
    paragraphs are further split with ``chunk_text_by_tokens``.
    """
    num = str(article.get("article_number", "")).strip()
    title = citation_title(num, str(article.get("title", "")))
    header = f"Art. {num} GDPR — {title}" if title else f"Art. {num} GDPR"
    body = str(article.get("text", ""))
    paras = paragraphs_from_gdpr_article_text(body)
    out: list[tuple[str, str]] = []
    for pi, para in enumerate(paras):
        label = str(pi + 1) if len(paras) > 1 else "1"
        subpieces = chunk_text_by_tokens(
            para,
            embedding_model,
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
        )
        for si, chunk in enumerate(subpieces):
            suffix = ""
            if len(paras) > 1:
                suffix = f" — paragraph {label}"
            if len(subpieces) > 1:
                suffix += f" — part {si + 1}/{len(subpieces)}"
            prefixed = f"{header}{suffix}\n\n{chunk}"
            out.append((label if len(subpieces) == 1 else f"{label}.{si}", prefixed))
    return out
