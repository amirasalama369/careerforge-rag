"""
Text cleaning and normalization layer.

Takes ExtractedDocument objects (from EITHER pdf_extractor.py production
extraction or fixture_adapter.py dev/test extraction -- this module does
not care which) and produces cleaned versions: each ContentBlock gets a
new cleaned_text field (the original raw_text is left untouched for
traceability/citations), and known repeated boilerplate (the closing
disclaimer paragraph, near-identical across all 7 CareerForge documents)
is flagged via is_boilerplate rather than silently treated as normal
retrievable content.
"""
from __future__ import annotations

import re
from dataclasses import replace
from typing import List

from ingestion.schema import ContentBlock, ExtractedDocument

# "P&L ownership" appears in the source text as "P&L; ownership" -- a
# stray semicolon. A narrow, specific fix for a known artifact, not a
# general HTML-entity decoder.
_ENCODING_FIXES = [
    (re.compile(r"P&L;"), "P&L"),
]

# Bullet/checkbox glyphs get normalized to one canonical marker in
# CLEANED text only; raw_text keeps the original glyph untouched.
_BULLET_GLYPH_RE = re.compile(r"^[\u2022\u25a0]\s+")

# The closing disclaimer paragraph is near-identical, verbatim, across all
# 7 documents. Detected by two anchor phrases rather than an exact string
# match, so small wording variance doesn't slip past detection.
_BOILERPLATE_ANCHORS = (
    "widely-observed hiring practices",
    "not a guarantee of interview or offer outcomes",
)


def fix_encoding_artifacts(text: str) -> str:
    for pattern, replacement in _ENCODING_FIXES:
        text = pattern.sub(replacement, text)
    return text


def normalize_bullet_marker(text: str) -> str:
    return _BULLET_GLYPH_RE.sub("- ", text)


def normalize_whitespace(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(lines)


def clean_text(raw_text: str) -> str:
    text = fix_encoding_artifacts(raw_text)
    text = normalize_bullet_marker(text)
    text = normalize_whitespace(text)
    return text


def is_disclaimer_boilerplate(raw_text: str) -> bool:
    return all(anchor in raw_text for anchor in _BOILERPLATE_ANCHORS)


def clean_block(block: ContentBlock) -> ContentBlock:
    """Return a NEW ContentBlock with cleaned_text and is_boilerplate set;
    the original block (and its raw_text) is left untouched."""
    cleaned = clean_text(block.raw_text)
    boilerplate = is_disclaimer_boilerplate(block.raw_text)
    return replace(block, cleaned_text=cleaned, is_boilerplate=boilerplate)


def clean_document(doc: ExtractedDocument) -> ExtractedDocument:
    """Return a NEW ExtractedDocument whose blocks all have cleaned_text
    and is_boilerplate populated. Does not mutate the input document."""
    cleaned_blocks: List[ContentBlock] = [clean_block(b) for b in doc.blocks]
    return replace(doc, blocks=cleaned_blocks)
