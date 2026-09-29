"""
Conversation orchestration layer.

Ties together every earlier piece (query rewriting, retrieval, prompt
construction, generation, citation checking) behind one simple
interface: Conversation.ask(question) -> ConversationTurn. The
Conversation object owns its own history, so a caller just asks
questions one after another without managing history manually.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from citations.citation_checker import CitationCheck, verify_citations
from generation.generator import Generator
from generation.prompts import build_messages
from generation.query_rewriter import rewrite_query
from retrieval.vector_retriever import RetrievalResult, VectorRetriever


@dataclass
class ConversationTurn:
    original_question: str
    standalone_question: str
    results: List[RetrievalResult]
    answer: str
    citation_checks: List[CitationCheck]


class Conversation:
    def __init__(self, retriever: VectorRetriever, generator: Generator, top_k: int = 3):
        self.retriever = retriever
        self.generator = generator
        self.top_k = top_k
        self._history: List[Tuple[str, str]] = []  # [(question, answer), ...]
        self.turns: List[ConversationTurn] = []

    def ask(self, question: str) -> ConversationTurn:
        """Rewrite the question using conversation history, retrieve
        context, generate a grounded answer, verify its citations, and
        record this turn in the conversation history for future turns."""
        standalone_question = rewrite_query(question, self._history, self.generator)

        results = self.retriever.retrieve(standalone_question, top_k=self.top_k)
        messages = build_messages(standalone_question, results)
        answer = self.generator.generate(messages)
        checks = verify_citations(answer, results)

        turn = ConversationTurn(
            original_question=question,
            standalone_question=standalone_question,
            results=results,
            answer=answer,
            citation_checks=checks,
        )
        self.turns.append(turn)
        self._history.append((question, answer))
        return turn

    def reset(self) -> None:
        """Clear conversation history -- start a fresh conversation."""
        self._history = []
        self.turns = []
