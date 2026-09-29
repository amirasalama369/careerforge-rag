"""
Shared line-classification and block-building logic.

Both pdf_extractor.py (production) and fixture_adapter.py (dev/test) end
up with a page reduced to a plain list of text lines (tables are handled
separately by each). This module turns that line list into typed
ContentBlocks the same way in both places, so "what counts as a
heading" or "what counts as a bullet" can't silently drift between the
two extraction paths.

Heuristic used (deliberately simple, tuned to this corpus's style but
not overfit to it):
  - A line like "3. Some Heading" -> heading
  - A line starting with a bullet/checkbox glyph -> bullet
  - Anything else -> prose

Extracted PDF text is hard-wrapped: a single bullet or paragraph in the
source document arrives as several physical lines, and only the FIRST
line of a bullet carries the bullet glyph. So a plain line with no
heading/bullet marker is treated as a CONTINUATION of whatever group is
currently open -- it does not start a new prose fragment by itself.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .schema import ContentBlock, ContentType, ExtractionSource

HEADING_RE = re.compile(r"^\d+\.\s+\S")
BULLET_RE = re.compile(r"^[•\-\*■]\s+")


@dataclass
class SectionState:
    """Carries the "current section heading" across page boundaries so a
    block whose section starts on page N and continues onto page N+1
    still gets tagged with the right section_heading on both pages."""
    current: Optional[str] = None


def group_lines(lines: List[str]) -> List[Tuple[str, str]]:
    """Collapse raw lines into (kind, merged_text) groups.

    A continuation line only starts a fresh prose group when nothing is
    open yet, or the last thing that closed was a heading. Otherwise it
    attaches to whatever group (bullet or prose) is currently open.
    Blank lines are dropped.
    """
    groups: List[List[object]] = []  # each item: [kind, [line, line, ...]]
    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            continue
        if HEADING_RE.match(stripped):
            groups.append(["heading", [stripped]])
        elif BULLET_RE.match(stripped):
            groups.append(["bullet", [stripped]])
        elif groups and groups[-1][0] != "heading":
            groups[-1][1].append(stripped)  # continuation of the open bullet/prose group
        else:
            groups.append(["prose", [stripped]])
    return [(kind, "\n".join(text_lines)) for kind, text_lines in groups]


_CONTENT_TYPE_BY_KIND = {
    "heading": ContentType.HEADING,
    "bullet": ContentType.BULLET_LIST,
    "prose": ContentType.PROSE,
}


def build_blocks_for_page(
    doc_id: str,
    page_number: int,
    lines: List[str],
    section_state: SectionState,
    extraction_source: ExtractionSource,
    block_counter: int,
) -> Tuple[List[ContentBlock], int]:
    """Turn one page's text lines into ContentBlocks, mutating
    section_state.current as headings are encountered. Returns the new
    blocks plus the updated block_counter (callers pass it back in on
    the next page so block IDs stay unique across the whole document)."""
    blocks: List[ContentBlock] = []
    cursor = 0
    for kind, text in group_lines(lines):
        block_counter += 1
        content_type = _CONTENT_TYPE_BY_KIND[kind]

        if kind == "heading":
            section_state.current = text

        blocks.append(
            ContentBlock(
                block_id=f"{doc_id}_p{page_number}_b{block_counter}",
                doc_id=doc_id,
                page_number=page_number,
                page_number_end=page_number,
                section_heading=section_state.current,
                content_type=content_type,
                raw_text=text,
                char_start=cursor,
                char_end=cursor + len(text),
                extraction_source=extraction_source,
            )
        )
        cursor += len(text) + 1
    return blocks, block_counter
