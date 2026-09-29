"""
Vector store layer, backed by ChromaDB running in embedded (local,
file-persisted) mode -- no separate server needed.

Chosen over a managed vector DB (Pinecone, Qdrant Cloud) because this
corpus is small: a hosted service would add real operational overhead
with no benefit at this scale. Data persists on disk, so it survives
runtime restarts.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import chromadb
import numpy as np

from processing.chunker import Chunk

DEFAULT_COLLECTION_NAME = "career_rag_chunks"


class ChromaStore:
    def __init__(self, persist_dir: str, collection_name: str = DEFAULT_COLLECTION_NAME):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self.persist_dir))
        self._collection = self._client.get_or_create_collection(name=collection_name)

    def add_chunks(self, chunks: List[Chunk], vectors: np.ndarray) -> None:
        """Add chunks and their pre-computed vectors to the collection.
        Metadata (doc_id, page numbers, section heading...) is stored
        alongside each vector, so search results carry full citation info."""
        if len(chunks) != len(vectors):
            raise ValueError(f"chunks ({len(chunks)}) and vectors ({len(vectors)}) length mismatch")
        if not chunks:
            return

        self._collection.add(
            ids=[c.chunk_id for c in chunks],
            embeddings=vectors.tolist(),
            documents=[c.text for c in chunks],
            metadatas=[
                {
                    "doc_id": c.doc_id,
                    "doc_title": c.doc_title,
                    "volume": c.volume if c.volume is not None else -1,
                    "section_heading": c.section_heading or "",
                    "page_number_start": c.page_number_start,
                    "page_number_end": c.page_number_end,
                    "content_type": c.content_type,
                }
                for c in chunks
            ],
        )

    def count(self) -> int:
        return self._collection.count()

    def query(self, query_vector: np.ndarray, top_k: int = 5) -> dict:
        """Return the top_k most similar chunks to query_vector, with
        their text, metadata, and distance (lower = more similar)."""
        return self._collection.query(
            query_embeddings=[query_vector.tolist()],
            n_results=top_k,
        )

    def reset(self) -> None:
        """Delete all data in this collection. Used for re-running
        ingestion from scratch during development."""
        self._client.delete_collection(self._collection.name)
        self._collection = self._client.get_or_create_collection(name=self._collection.name)
