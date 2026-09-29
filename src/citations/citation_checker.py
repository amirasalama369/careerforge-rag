"""
Citation verification layer.

Parses [Source: <doc title>, Page N] / [Source: <doc title>, Pages N-M]
citations out of an LLM answer's text (the exact format required by
generation.prompts.SYSTEM_PROMPT) and checks each one against the
RetrievalResult list that was actually sent as context, so we can tell
a grounded citation from a hallucinated one.

A citation is considered VALID only if both the document title AND the
page number match a chunk that was genuinely in the context -- a
plausible-looking but wrong page number is still flagged invalid.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from retrieval.vector_retriever import RetrievalResult

_CITATION_RE = re.compile(
    r"\[Source:\s*(?P<title>[^,]+),\s*Pages?\s*(?P<start>\d+)(?:-(?P<end>\d+))?\]"
)


@dataclass
class CitationCheck:
    raw_text: str
    doc_title: str
    page_start: int
    page_end: int
    is_valid: bool


def extract_citations(answer_text: str) -> List[dict]:
    """Pull every [Source: ..., Page(s) ...] citation out of the answer text."""
    citations = []
    for match in _CITATION_RE.finditer(answer_text):
        start = int(match.group("start"))
        end = int(match.group("end")) if match.group("end") else start
        citations.append(
            {
                "raw_text": match.group(0),
                "doc_title": match.group("title").strip(),
                "page_start": start,
                "page_end": end,
            }
        )
    return citations


def _citation_matches_result(citation: dict, result: RetrievalResult) -> bool:
    same_title = citation["doc_title"].lower() == result.doc_title.lower()
    # valid if the cited page range overlaps the chunk's actual page range at all
    overlaps = citation["page_start"] <= result.page_number_end and citation["page_end"] >= result.page_number_start
    return same_title and overlaps


def verify_citations(answer_text: str, context_results: List[RetrievalResult]) -> List[CitationCheck]:
    """Return a CitationCheck for every citation found in answer_text,
    marking is_valid=True only if it matches a chunk genuinely present
    in context_results."""
    checks = []
    for citation in extract_citations(answer_text):
        is_valid = any(_citation_matches_result(citation, r) for r in context_results)
        checks.append(
            CitationCheck(
                raw_text=citation["raw_text"],
                doc_title=citation["doc_title"],
                page_start=citation["page_start"],
                page_end=citation["page_end"],
                is_valid=is_valid,
            )
        )
    return checks


def all_citations_valid(checks: List[CitationCheck]) -> bool:
    return all(c.is_valid for c in checks)
