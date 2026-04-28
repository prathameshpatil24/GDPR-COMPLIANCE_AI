"""BM25 tokenisation shared between indexing and retrieval."""

from __future__ import annotations

import re


def bm25_tokenize(text: str) -> list[str]:
    """Tokenise text for BM25Okapi (consistent build/query tokenisation)."""
    return re.findall(r"[a-zA-Z0-9_]+", text.lower())
