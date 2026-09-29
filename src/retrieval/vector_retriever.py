"""
Baseline (vector-only) retrieval layer.

Wraps Embedder + ChromaStore behind one simple interface: retrieve(query,
top_k) -> List[RetrievalResult]. Nothing downstream (generation, citations,
evaluation) needs to know how the query was embedded or how ChromaDB's
raw response is shaped -- that complexity stays entirely inside this file.

This is "baseline" retrieval specifically: pure vector similarity search,
no keyword/BM25 hybrid and no reranking. Evaluation (Recall@3 = 1.0,
MRR ~0.97 on a 24-question hand-written eval set, both on the fixture
and on real PDF files) showed no measurable benefit from adding either
at this corpus size, so neither was added -- see evaluation/ for the
numbers behind that decision, and revisit if the corpus grows a lot.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from embeddings.embedder import Embedder
from vectorstore.chroma_store import ChromaStore


@dataclass
class RetrievalResult:
    chunk_id: str
    text: str
    doc_id: str
    doc_title: str
    volume: Optional[int]
    section_heading: Optional[str]
    page_number_start: int
    page_number_end: int
    content_type: str
    distance: float


class VectorRetriever:
    def __init__(self, embedder: Embedder, store: ChromaStore):
        self.embedder = embedder
        self.store = store

    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        """Embed the query and return the top_k most similar chunks as
        clean RetrievalResult objects, ordered most similar first."""
        query_vector = self.embedder.embed_query(query)
        raw = self.store.query(query_vector, top_k=top_k)

        results: List[RetrievalResult] = []
        ids = raw["ids"][0]
        documents = raw["documents"][0]
        metadatas = raw["metadatas"][0]
        distances = raw["distances"][0]

        for i in range(len(ids)):
            meta = metadatas[i]
            results.append(
                RetrievalResult(
                    chunk_id=ids[i],
                    text=documents[i],
                    doc_id=meta["doc_id"],
                    doc_title=meta["doc_title"],
                    volume=meta["volume"] if meta["volume"] != -1 else None,
                    section_heading=meta["section_heading"] or None,
                    page_number_start=meta["page_number_start"],
                    page_number_end=meta["page_number_end"],
                    content_type=meta["content_type"],
                    distance=distances[i],
                )
            )
        return results
