"""Local embedding model wrapper (sentence-transformers)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import numpy as np


@lru_cache(maxsize=4)
def _model(model_name: str) -> Any:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def embed_texts(model_name: str, texts: list[str], batch_size: int = 16) -> list[list[float]]:
    """Embed texts with the configured sentence-transformers model."""
    model = _model(model_name)
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return [row.astype(float).tolist() for row in np.asarray(vectors)]
