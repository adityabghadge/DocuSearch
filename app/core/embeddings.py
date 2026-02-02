from __future__ import annotations

import threading
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import settings

_lock = threading.Lock()
_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                _model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    return _model


def embed_texts(texts: List[str]) -> np.ndarray:
    model = get_model()
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(vectors, dtype=np.float32)


def embedding_dim() -> int:
    model = get_model()
    return int(model.get_sentence_embedding_dimension())