from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings

_model: SentenceTransformer | None = None


def get_embedder() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model, device=settings.embedding_device)
    return _model


def embed_text(text: str) -> np.ndarray:
    model = get_embedder()
    vector = model.encode(text, normalize_embeddings=True)
    return np.asarray(vector, dtype=np.float32)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))
