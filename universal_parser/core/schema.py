from __future__ import annotations

from typing import Literal
import uuid

from pydantic import BaseModel, Field

class BBox(BaseModel):
    """Bounding box of an element on a page. Coordinates in points (PDF units)."""
    x0: float
    y0: float
    x1: float
    y1: float
    
class TableData(BaseModel):
    """Structured representation of a table."""
    headers: list[str]
    rows: list[list[str]]
    
class Element(BaseModel):
    """A single unit of content extracted from a document."""
    element_id: str= Field(default_factory= lambda: str(uuid.uuid4()))
    type: Literal["heading", "paragraph", "table", "figure", "list_item", "code_block"]
    level: int | None= None  # heading level: 1, 2, 3 etc. None for non-headings
    text: str | None= None
    page: int | None= None   # 1-indexed page number
    bbox: BBox | None= None
    parent_id: str | None= None   # links to a parent element (e.g. heading this paragraph belongs to)
    data: TableData | None= None  # only for type="table"
    markdown_repr: str | None= None  # pre-rendered markdown string of this element
    confidence: float | None= None   # 0.0 to 1.0, used for tables and OCR output
    vlm_description: str | None= None  # Phase 8 — optional VLM-generated caption for figures
    
class DocumentMetadata(BaseModel):
    """Facts about the source file — not its content."""
    file_name: str
    file_type: str
    page_count: int | None= None
    has_scanned_pages: bool= False
    
class Document(BaseModel):
    """The top-level output object. This is what parse() returns."""
    schema_version: str= "1.0"
    doc_id: str= Field(default_factory=lambda: str(uuid.uuid4()))
    metadata: DocumentMetadata
    content_tree: list[Element]= Field(default_factory=list)