"""
Query rewriting layer for multi-turn conversations.

A follow-up question like "what's it good for?" is meaningless to the
embedding model on its own -- it needs the prior conversation turn to
know what "it" refers to. This module uses a lightweight LLM call to
rewrite the latest user question into a self-contained, standalone
question BEFORE it reaches retrieval. Retrieval and generation
themselves are unchanged by this -- they still just receive a plain
question string.

If there is no conversation history yet (first turn), the question is
returned unchanged -- no LLM call needed.
"""
from __future__ import annotations

from typing import List, Tuple

from generation.generator import Generator

REWRITE_SYSTEM_PROMPT = """You rewrite a user's follow-up question into a standalone question that \
makes sense with no prior context, based on the conversation history given to you.

Rules:
1. If the question is already standalone and doesn't depend on prior turns, return it UNCHANGED.
2. Preserve the original meaning and intent exactly -- do not add new assumptions or answer the question.
3. Output ONLY the rewritten question, nothing else -- no explanation, no quotes."""


def _format_history(history: List[Tuple[str, str]]) -> str:
    lines = []
    for question, answer in history:
        lines.append(f"User: {question}")
        lines.append(f"Assistant: {answer}")
    return "\n".join(lines)


def rewrite_query(
    question: str,
    history: List[Tuple[str, str]],
    generator: Generator,
) -> str:
    """Rewrite `question` into a standalone form using `history`
    ([(question, answer), ...] from earlier turns). Returns the
    question unchanged if history is empty."""
    if not history:
        return question

    messages = [
        {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Conversation history:\n{_format_history(history)}\n\n"
            f"Follow-up question: {question}\n\n"
            f"Standalone question:",
        },
    ]
    rewritten = generator.generate(messages, temperature=0.0, max_tokens=100)
    return rewritten.strip()
