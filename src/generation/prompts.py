"""
Prompt construction layer.

Turns a list of RetrievalResult (from retrieval.vector_retriever) into
the system + user prompt sent to the LLM. Kept separate from the actual
LLM call (generator.py) so the prompt can be built and inspected with
zero API cost, and so prompt wording changes happen in exactly one place.
"""
from __future__ import annotations

from typing import List

from retrieval.vector_retriever import RetrievalResult

SYSTEM_PROMPT = """You are a knowledgeable career-advice assistant for the CareerForge knowledge base, talking directly to someone who wants practical help with their career.

Answer in a natural, conversational tone -- the way a helpful mentor would explain something to a colleague, not like a formal report. Avoid robotic phrasing, avoid restating the question, and don't pad the answer with disclaimers unless truly necessary.

Rules you must still follow, no matter how natural the tone is:
1. Answer ONLY using the information in the provided context. Do not use outside knowledge.
2. If the context does not contain enough information to answer, say so plainly and naturally instead of guessing (e.g. "I don't see anything in the knowledge base about that" rather than a generic refusal template).
3. Every factual claim in your answer must be traceable to the context. When you state something from the context, cite it using this exact format: [Source: <document title>, Page <page number>].
4. Keep the answer concise and directly useful -- do not pad with generic advice not found in the context.
"""


def format_context(results: List[RetrievalResult]) -> str:
    """Render retrieved chunks as labeled, citeable source blocks."""
    if not results:
        return "(no relevant context was found)"

    blocks = []
    for i, r in enumerate(results, start=1):
        pages = (
            f"Page {r.page_number_start}"
            if r.page_number_start == r.page_number_end
            else f"Pages {r.page_number_start}-{r.page_number_end}"
        )
        header = f"[Source {i}: {r.doc_title}, {pages}]"
        blocks.append(f"{header}\n{r.text}")
    return "\n\n".join(blocks)


def build_user_prompt(query: str, results: List[RetrievalResult]) -> str:
    context = format_context(results)
    return f"""Context:
{context}

Question: {query}

Answer the question using only the context above, citing sources as instructed."""


def build_messages(query: str, results: List[RetrievalResult]) -> List[dict]:
    """Return a chat-style messages list ready to send to an LLM API."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(query, results)},
    ]
