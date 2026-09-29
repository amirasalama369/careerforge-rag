"""
Shared data model for extracted document content.

Both extraction paths in this project produce objects of these exact
types:

  * pdf_extractor.py   -> the PRODUCTION pipeline, run on real PDF files
  * fixture_adapter.py -> a LOCAL DEV/TEST fixture, run on hand-prepared
                           text (used only during development)

Everything downstream (cleaning, chunking, embedding, retrieval) is
written against this schema only, and never needs to know or care which
extractor produced a given ExtractedDocument.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ContentType(str, Enum):
    HEADING = "heading"
    PROSE = "prose"
    BULLET_LIST = "bullet_list"
    TABLE = "table"
    # Used when a block's text is known to be unreliable (e.g. a
    # flattened table we can't cleanly separate from surrounding prose).
    OTHER = "other"


class ExtractionSource(str, Enum):
    PDF_PLUMBER = "pdfplumber_production"
    FIXTURE_ADAPTER = "fixture_adapter"


@dataclass
class ContentBlock:
    block_id: str
    doc_id: str
    page_number: int
    page_number_end: int
    section_heading: Optional[str]
    content_type: ContentType
    raw_text: str
    table_data: Optional[List[List[str]]] = None
    char_start: int = 0
    char_end: int = 0
    extraction_source: ExtractionSource = ExtractionSource.PDF_PLUMBER
    extraction_notes: Optional[str] = None
    # -- cleaning layer fields --
    cleaned_text: Optional[str] = None
    is_boilerplate: bool = False


@dataclass
class DocumentMetadata:
    doc_id: str
    filename: str
    title: str
    volume: Optional[int]
    num_pages: int
    extraction_source: ExtractionSource


@dataclass
class ExtractedDocument:
    metadata: DocumentMetadata
    blocks: List[ContentBlock] = field(default_factory=list)


def to_serializable(doc: ExtractedDocument) -> Dict[str, Any]:
    """JSON-serializable dict form of an ExtractedDocument (Enums -> their .value)."""

    def convert(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [convert(v) for v in obj]
        if isinstance(obj, Enum):
            return obj.value
        return obj

    return convert(asdict(doc))
