"""
PRODUCTION PDF ingestion/extraction layer.

This is the pipeline the deployed system runs on real, user-uploaded PDF
files. It uses pdfplumber directly against actual PDF bytes on disk.

Design:
  - Tables are located and extracted first (page.find_tables /
    extract_tables), and their character content is excluded from the
    plain-text extraction pass so a table's cells never leak into a
    prose block as garbled run-on text.
  - Each table is attached to the heading genuinely positioned above it
    on the page (by vertical position), not to whichever heading the
    block-processing loop last saw -- otherwise a table late on a page
    could be mis-attributed to a heading that actually comes after it.
  - A table split across a page boundary (pdfplumber processes each
    page independently) is detected by an exact match on the header
    row between the last table seen and a new table on the very next
    page, and merged into one logical table block.
  - The remaining text is split into lines and handed to
    block_parser.build_blocks_for_page, shared with the fixture adapter
    so "what counts as a heading" can't drift between extraction paths.
  - One malformed page logs a warning and is skipped rather than
    failing the whole document; a file that can't be opened at all
    raises PDFExtractionError so the caller can decide how to handle it.
"""
from __future__ import annotations

import logging
import re
from dataclasses import replace
from pathlib import Path
from typing import List, Optional, Tuple

import pdfplumber

from .block_parser import HEADING_RE, SectionState, build_blocks_for_page
from .schema import (
    ContentBlock,
    ContentType,
    DocumentMetadata,
    ExtractedDocument,
    ExtractionSource,
)

logger = logging.getLogger(__name__)

VOLUME_RE = re.compile(r"Volume\s+(\d+)", re.IGNORECASE)


class PDFExtractionError(Exception):
    """Raised when a PDF file cannot be opened / is too malformed to read at all."""


def _make_doc_id(pdf_path: Path) -> str:
    return pdf_path.stem


def _extract_title_and_volume(first_page_text: str) -> Tuple[str, Optional[int]]:
    lines = [line.strip() for line in first_page_text.splitlines() if line.strip()]
    title = lines[0] if lines else "Untitled"
    volume = None
    for line in lines[:5]:
        match = VOLUME_RE.search(line)
        if match:
            volume = int(match.group(1))
            break
    return title, volume


def _table_bboxes(page) -> List[Tuple[float, float, float, float]]:
    try:
        return [t.bbox for t in page.find_tables()]
    except Exception as e:
        logger.warning("Table detection failed on page %s: %s", page.page_number, e)
        return []


def _char_inside_any_bbox(char, bboxes) -> bool:
    for (x0, top, x1, bottom) in bboxes:
        if char["x0"] >= x0 - 1 and char["x1"] <= x1 + 1 and char["top"] >= top - 1 and char["bottom"] <= bottom + 1:
            return True
    return False


def _extract_page_text_excluding_tables(page, table_bboxes) -> str:
    if not table_bboxes:
        return page.extract_text() or ""
    filtered_page = page.filter(
        lambda obj: obj.get("object_type") != "char" or not _char_inside_any_bbox(obj, table_bboxes)
    )
    return filtered_page.extract_text() or ""


def _table_to_text(table: List[List[Optional[str]]]) -> str:
    rows = [" | ".join((cell or "").strip() for cell in row) for row in table]
    return "\n".join(rows)


def _heading_positions(page) -> List[Tuple[float, str]]:
    """Return (top, heading_text) for each heading-like line on the page,
    by position -- used to attach a table to the heading genuinely above
    it, rather than to whichever heading the block-processing loop last
    saw. Headings never fall inside a table's own bounding box, so this
    is safe to compute on the ORIGINAL (unfiltered) page."""
    positions = []
    try:
        for line in page.extract_text_lines():
            text = (line.get("text") or "").strip()
            if text and HEADING_RE.match(text):
                positions.append((line["top"], text))
    except Exception as e:
        logger.warning("Heading position detection failed on page %s: %s", page.page_number, e)
    return positions


def _section_heading_for_table(
    table_top: float,
    heading_positions: List[Tuple[float, str]],
    fallback: Optional[str],
) -> Optional[str]:
    """Pick the heading whose position is immediately above table_top.
    Falls back to `fallback` (the heading carried in from earlier pages)
    if no heading appears above the table on this page at all."""
    candidates = [(top, text) for top, text in heading_positions if top < table_top]
    if not candidates:
        return fallback
    return max(candidates, key=lambda pair: pair[0])[1]


def _merge_split_tables(blocks: List[ContentBlock]) -> List[ContentBlock]:
    """A table split across a page boundary (pdfplumber sees each page
    independently, so it becomes two separate TABLE blocks) is detected
    by an exact match on the first row (the header) between the most
    recent TABLE block seen so far and a new table on the very next
    page, and merged into one block IN PLACE at the earlier block's
    position -- other, non-table blocks (headings/prose from the page
    in between) are left exactly where they are. This is a narrow,
    specific check -- it will not merge two genuinely different tables
    that happen to be nearby."""
    merged: List[ContentBlock] = []
    last_table_index: Optional[int] = None

    for block in blocks:
        if (
            block.content_type == ContentType.TABLE
            and last_table_index is not None
            and merged[last_table_index].page_number_end == block.page_number - 1
            and merged[last_table_index].table_data
            and block.table_data
            and merged[last_table_index].table_data[0] == block.table_data[0]
        ):
            previous = merged[last_table_index]
            combined_rows = previous.table_data + block.table_data[1:]  # drop repeated header
            combined_text = "\n".join(" | ".join(row) for row in combined_rows)
            merged[last_table_index] = replace(
                previous,
                page_number_end=block.page_number,
                table_data=combined_rows,
                raw_text=combined_text,
                char_end=len(combined_text),
            )
            # do NOT append `block` -- it has been folded into merged[last_table_index]
        else:
            merged.append(block)
            if block.content_type == ContentType.TABLE:
                last_table_index = len(merged) - 1
    return merged


def extract_pdf(pdf_path: Path) -> ExtractedDocument:
    """Extract a single real PDF file into an ExtractedDocument.

    Raises PDFExtractionError if the file can't be opened at all. A page
    that fails individually is logged and skipped so one bad page
    doesn't take down extraction for the rest of the document.
    """
    pdf_path = Path(pdf_path)
    doc_id = _make_doc_id(pdf_path)

    try:
        pdf = pdfplumber.open(str(pdf_path))
    except Exception as e:
        raise PDFExtractionError(f"Could not open '{pdf_path.name}': {e}") from e

    section_state = SectionState()
    blocks: List[ContentBlock] = []
    block_counter = 0
    title, volume = "Untitled", None

    with pdf:
        num_pages = len(pdf.pages)
        for page_index, page in enumerate(pdf.pages):
            page_number = page_index + 1
            try:
                table_bboxes = _table_bboxes(page)
                tables = page.extract_tables() if table_bboxes else []

                text = _extract_page_text_excluding_tables(page, table_bboxes)
                lines = text.splitlines() if text else []

                if page_number == 1:
                    title, volume = _extract_title_and_volume(text)

                page_blocks, block_counter = build_blocks_for_page(
                    doc_id=doc_id,
                    page_number=page_number,
                    lines=lines,
                    section_state=section_state,
                    extraction_source=ExtractionSource.PDF_PLUMBER,
                    block_counter=block_counter,
                )
                blocks.extend(page_blocks)

                if tables:
                    heading_positions = _heading_positions(page)
                    table_objects = page.find_tables()
                    for table_obj, table in zip(table_objects, tables):
                        block_counter += 1
                        table_text = _table_to_text(table)
                        table_top = table_obj.bbox[1]
                        table_section = _section_heading_for_table(
                            table_top, heading_positions, fallback=section_state.current
                        )
                        blocks.append(
                            ContentBlock(
                                block_id=f"{doc_id}_p{page_number}_b{block_counter}",
                                doc_id=doc_id,
                                page_number=page_number,
                                page_number_end=page_number,
                                section_heading=table_section,
                                content_type=ContentType.TABLE,
                                raw_text=table_text,
                                table_data=[[cell or "" for cell in row] for row in table],
                                char_start=0,
                                char_end=len(table_text),
                                extraction_source=ExtractionSource.PDF_PLUMBER,
                            )
                        )
            except Exception as e:
                logger.warning("Failed to extract page %d of '%s': %s", page_number, pdf_path.name, e)
                continue

    metadata = DocumentMetadata(
        doc_id=doc_id,
        filename=pdf_path.name,
        title=title,
        volume=volume,
        num_pages=num_pages,
        extraction_source=ExtractionSource.PDF_PLUMBER,
    )
    return ExtractedDocument(metadata=metadata, blocks=_merge_split_tables(blocks))


def extract_pdf_directory(directory: Path) -> List[ExtractedDocument]:
    """Extract every *.pdf in a directory. Files that fail to open are
    logged and skipped rather than aborting the whole batch."""
    directory = Path(directory)
    documents: List[ExtractedDocument] = []
    for pdf_path in sorted(directory.glob("*.pdf")):
        try:
            documents.append(extract_pdf(pdf_path))
        except PDFExtractionError as e:
            logger.error(str(e))
    return documents
