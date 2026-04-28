"""Token-aware text chunking for embedding (BGE tokenizer)."""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=4)
def _tokenizer(model_name: str):
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(model_name, use_fast=True)


def chunk_text_by_tokens(
    text: str,
    model_name: str,
    max_tokens: int = 512,
    overlap_tokens: int = 64,
) -> list[str]:
    """Split long text into overlapping chunks measured in tokenizer tokens."""
    tok = _tokenizer(model_name)
    ids = tok.encode(text, add_special_tokens=False)
    if not ids:
        return []
    if len(ids) <= max_tokens:
        return [tok.decode(ids, skip_special_tokens=True)]
    chunks: list[str] = []
    start = 0
    while start < len(ids):
        end = min(start + max_tokens, len(ids))
        piece = ids[start:end]
        chunks.append(tok.decode(piece, skip_special_tokens=True).strip())
        if end == len(ids):
            break
        start = max(0, end - overlap_tokens)
    return [c for c in chunks if c]
