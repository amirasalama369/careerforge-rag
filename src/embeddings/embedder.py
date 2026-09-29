"""
Embedding layer.

Wraps a sentence-transformers model behind a small interface so the
rest of the pipeline (vector store, retrieval) never talks to the
embedding library directly -- swapping models later means editing
only this file.

Model: BAAI/bge-small-en-v1.5 -- chosen because this corpus is
English-only and small, so a larger or multilingual model would add
cost with no real benefit here.
"""
from __future__ import annotations

from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

DEFAULT_MODEL_NAME = "BAAI/bge-small-en-v1.5"

# BGE models are trained to expect this instruction prefixed to QUERIES
# (not to the passages/chunks being searched) -- it measurably improves
# retrieval quality for this model family.
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


class Embedder:
    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        self.dimension = self._model.get_sentence_embedding_dimension()

    def embed_texts(self, texts: List[str], batch_size: int = 16) -> np.ndarray:
        """Embed a list of chunk texts (no instruction prefix)."""
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return embeddings.astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single search query (with the BGE instruction prefix)."""
        prefixed = QUERY_INSTRUCTION + query
        return self.embed_texts([prefixed])[0]
