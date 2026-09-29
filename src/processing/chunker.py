"""
Structure-aware chunking layer.

Turns a cleaned ExtractedDocument's flat list of ContentBlocks into
retrieval-ready Chunks. Chunking groups by section (a heading plus its
prose/bullets) rather than fixed-size token windows, since this corpus
is small and highly structured, and a fixed window would frequently cut
mid-bullet or mid-table. Each table always becomes its own standalone
chunk, never merged with prose.

OTHER-typed blocks (the flattened, unreliable duplicate of a table's
text) are excluded entirely: the clean table content is already
represented as its own TABLE chunk.

Blocks flagged is_boilerplate (the repeated closing disclaimer -- see
cleaner.py) have just that disclaimer LINE stripped out before being
added to a chunk, so any real content merged into the same block (e.g.
a checklist item that happened to share a block with the disclaimer)
is preserved, without the disclaimer paragraph being duplicated across
every document's chunks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ingestion.schema import ContentBlock, ContentType, ExtractedDocument

_BOILERPLATE_ANCHORS = (
    "widely-observed hiring practices",
    "not a guarantee of interview or offer outcomes",
)


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    doc_title: str
    volume: Optional[int]
    section_heading: Optional[str]
    page_number_start: int
    page_number_end: int
    content_type: str  # "section" or "table"
    text: str
    source_block_ids: List[str] = field(default_factory=list)
    char_count: int = 0


def _strip_boilerplate_lines(text: str) -> str:
    """Drop any line that IS the repeated disclaimer paragraph, keeping
    any other line that happened to be merged into the same block."""
    kept_lines = [
        line for line in text.split("\n")
        if not all(anchor in line for anchor in _BOILERPLATE_ANCHORS)
    ]
    return "\n".join(kept_lines).strip()


def _block_text_for_chunk(block: ContentBlock) -> str:
    text = block.cleaned_text if block.cleaned_text is not None else block.raw_text
    if block.is_boilerplate:
        text = _strip_boilerplate_lines(text)
    return text


def chunk_document(doc: ExtractedDocument) -> List[Chunk]:
    """Group a document's blocks into section-level chunks. Tables always
    become their own chunk. OTHER blocks are dropped entirely."""
    chunks: List[Chunk] = []
    current_texts: List[str] = []
    current_block_ids: List[str] = []
    current_section: Optional[str] = None
    current_page_start: Optional[int] = None
    current_page_end: Optional[int] = None
    chunk_counter = 0
    section_started = False

    def flush() -> None:
        nonlocal current_texts, current_block_ids, chunk_counter
        combined = "\n".join(t for t in current_texts if t.strip())
        if combined.strip():
            chunk_counter += 1
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.metadata.doc_id}_c{chunk_counter}",
                    doc_id=doc.metadata.doc_id,
                    doc_title=doc.metadata.title,
                    volume=doc.metadata.volume,
                    section_heading=current_section,
                    page_number_start=current_page_start,
                    page_number_end=current_page_end,
                    content_type="section",
                    text=combined.strip(),
                    source_block_ids=list(current_block_ids),
                    char_count=len(combined.strip()),
                )
            )
        current_texts = []
        current_block_ids = []

    for block in doc.blocks:
        if block.content_type == ContentType.OTHER:
            continue  # unreliable flattened-table duplicate -- never chunked

        if block.content_type == ContentType.TABLE:
            flush()
            chunk_counter += 1
            table_text = block.cleaned_text if block.cleaned_text is not None else block.raw_text
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.metadata.doc_id}_c{chunk_counter}",
                    doc_id=doc.metadata.doc_id,
                    doc_title=doc.metadata.title,
                    volume=doc.metadata.volume,
                    section_heading=block.section_heading,
                    page_number_start=block.page_number,
                    page_number_end=block.page_number_end,
                    content_type="table",
                    text=table_text,
                    source_block_ids=[block.block_id],
                    char_count=len(table_text),
                )
            )
            continue

        text = _block_text_for_chunk(block)
        if not text.strip():
            continue

        # `not section_started` handles the very first block of the
        # document (its section_heading is None, same as the initial
        # current_section -- without this flag that "change" would be
        # invisible and the block's real page number would be lost).
        if not section_started or block.section_heading != current_section:
            flush()
            current_section = block.section_heading
            current_page_start = block.page_number
            section_started = True

        current_texts.append(text)
        current_block_ids.append(block.block_id)
        current_page_end = block.page_number_end

    flush()
    return chunks


def chunk_documents(docs: List[ExtractedDocument]) -> List[Chunk]:
    all_chunks: List[Chunk] = []
    for doc in docs:
        all_chunks.extend(chunk_document(doc))
    return all_chunks
