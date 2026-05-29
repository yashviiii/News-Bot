"""BGE embedding model loader and batch embedding.

Loads the sentence-transformers model lazily on first use so that import
time stays fast (matters for the API process startup and tests).
"""

from __future__ import annotations

import logging
import threading
from typing import Sequence

import numpy as np

from ..config import EMBED_DIM, EMBED_MODEL_NAME


logger = logging.getLogger(__name__)

_model = None
_model_lock = threading.Lock()


def _load_model():
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        from sentence_transformers import SentenceTransformer

        logger.info("Loading embedding model: %s", EMBED_MODEL_NAME)
        _model = SentenceTransformer(EMBED_MODEL_NAME)
    return _model


def embed_texts(texts: Sequence[str], *, batch_size: int = 32) -> np.ndarray:
    """Encode a sequence of texts. Returns float32 (N, EMBED_DIM) array, L2-normalized."""
    if not texts:
        return np.zeros((0, EMBED_DIM), dtype=np.float32)
    model = _load_model()
    vectors = model.encode(
        list(texts),
        batch_size=batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    vectors = np.asarray(vectors, dtype=np.float32)
    if vectors.shape[1] != EMBED_DIM:
        raise ValueError(
            f"Embedding dim mismatch: model produced {vectors.shape[1]}, expected {EMBED_DIM}"
        )
    return vectors


def embed_one(text: str) -> np.ndarray:
    """Encode a single text. Returns float32 (EMBED_DIM,) array, L2-normalized."""
    return embed_texts([text])[0]


def serialize(vector: np.ndarray) -> bytes:
    """Serialize a single float32 vector for BLOB storage."""
    arr = np.asarray(vector, dtype=np.float32)
    return arr.tobytes()


def deserialize(blob: bytes) -> np.ndarray:
    """Deserialize a BLOB back to a float32 vector."""
    return np.frombuffer(blob, dtype=np.float32)
