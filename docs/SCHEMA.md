# Output Schema Specification

This document provides the canonical field-level specification for all output data models produced by `universal-doc-parser`. All models are implemented using Pydantic v2 (`universal_parser/core/schema.py`).

---

## 1. Top-Level Models

### 1.1 `Document`

The root object returned by `parse(path)`.

| Field | Type | Required | Description |
|---|---|---|---|
| `schema_version` | `str` | Yes | Schema specification version. Always `"1.0"` in this release. |
| `doc_id` | `str` | Yes | Unique UUID v4 identifier generated at parse time. |
| `metadata` | `DocumentMetadata` | Yes | Document-level metadata (filename, detected format, page count). |
| `content_tree` | `list[Element]` | Yes | Ordered sequence of extracted document elements in natural reading order. |

```json
{
  "schema_version": "1.0",
  "doc_id": "c8cdb60a-fc20-4e79-bb30-37218c8dba8a",
  "metadata": {
    "file_name": "annual_report.pdf",
    "file_type": "pdf",
    "page_count": 42,
    "has_scanned_pages": false
  },
  "content_tree": [ ... ]
}
```

---

### 1.2 `DocumentMetadata`

Captures file container properties and parsing telemetry.

| Field | Type | Required | Description |
|---|---|---|---|
| `file_name` | `str` | Yes | Original filename including file extension. |
| `file_type` | `str` | Yes | Normalized format identifier: `pdf`, `docx`, `xlsx`, `pptx`, `html`, `epub`, `csv`, `tsv`, `parquet`, `json`, `xml`, `eml`, `msg`, `mbox`, `image`, `doc`, `xls`, `ppt`. |
| `page_count` | `int or None` | No | Total pages in paginated documents. `null` for non-paginated formats (e.g. CSV, Parquet, JSON). |
| `has_scanned_pages` | `bool` | Yes | `true` if any page in the document required CPU OCR fallback processing. |

---

## 2. Element Models

### 2.1 `Element`

The atomic unit of extracted content within `content_tree`.

| Field | Type | Required | Null Semantics / Invariants |
|---|---|---|---|
| `element_id` | `str` | Yes | Unique UUID v4 assigned to this specific element. |
| `type` | `str` | Yes | One of: `"heading"`, `"paragraph"`, `"table"`, `"figure"`, `"list_item"`, `"code_block"`. |
| `level` | `int or None` | No | Heading hierarchy depth ($1 \le \text{level} \le 6$). `null` for all non-heading elements. |
| `text` | `str or None` | No | Plain text content. `null` for pure table elements. |
| `page` | `int or None` | No | 1-indexed page number where the element appears. `null` for non-paginated files. |
| `bbox` | `BBox or None` | No | Spatial coordinates in standard PDF points (72 pt = 1 inch). `null` for non-spatial files. |
| `parent_id` | `str or None` | No | `element_id` of the nearest ancestor heading above this element. `null` for root-level items. |
| `data` | `TableData or None` | No | Structured grid data (`headers`, `rows`). Populated **only** when `type == "table"`. |
| `markdown_repr` | `str or None` | No | Pre-rendered GitHub-Flavored Markdown representation of the element. |
| `confidence` | `float or None` | No | Extraction confidence score in $[0.0, 1.0]$. Populated for OCR text and tables; `null` for digital text. |
| `vlm_description` | `str or None` | No | Optional visual description for images/figures. Reserved for multimodal extensions. |

---

### 2.2 `BBox` (Bounding Box)

Spatial coordinates for layout-aware document elements.

| Field | Type | Required | Description |
|---|---|---|---|
| `x0` | `float` | Yes | Left horizontal coordinate in PDF points from top-left origin. |
| `y0` | `float` | Yes | Top vertical coordinate in PDF points from top-left origin. |
| `x1` | `float` | Yes | Right horizontal coordinate in PDF points from top-left origin. |
| `y1` | `float` | Yes | Bottom vertical coordinate in PDF points from top-left origin. |

---

### 2.3 `TableData`

Structured tabular representation.

| Field | Type | Required | Description |
|---|---|---|---|
| `headers` | `list[str]` | Yes | Ordered list of table column header strings. |
| `rows` | `list[list[str]]` | Yes | 2D list of row cell values normalized to string representations. |

```json
{
  "headers": ["Quarter", "Revenue (USD)", "Operating Margin"],
  "rows": [
    ["Q1", "$1.2B", "24.5%"],
    ["Q2", "$1.4B", "26.1%"]
  ]
}
```

---

## 3. Element Type Examples

### 3.1 Heading Element (H1)
```json
{
  "element_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "type": "heading",
  "level": 1,
  "text": "1. Executive Summary",
  "page": 1,
  "bbox": { "x0": 72.0, "y0": 100.0, "x1": 540.0, "y1": 124.0 },
  "parent_id": null,
  "data": null,
  "markdown_repr": "# 1. Executive Summary",
  "confidence": null,
  "vlm_description": null
}
```

### 3.2 Paragraph Element (Child of H1)
```json
{
  "element_id": "f2e3d4c5-b6a7-4890-1234-567890abcdef",
  "type": "paragraph",
  "level": null,
  "text": "Operating cash flow reached record highs across all European business units.",
  "page": 1,
  "bbox": { "x0": 72.0, "y0": 135.0, "x1": 540.0, "y1": 160.0 },
  "parent_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "data": null,
  "markdown_repr": "Operating cash flow reached record highs across all European business units.",
  "confidence": null,
  "vlm_description": null
}
```

### 3.3 Table Element
```json
{
  "element_id": "99887766-5544-3322-1100-aabbccddeeff",
  "type": "table",
  "level": null,
  "text": null,
  "page": 2,
  "bbox": { "x0": 72.0, "y0": 200.0, "x1": 540.0, "y1": 350.0 },
  "parent_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "data": {
    "headers": ["Region", "YoY Growth"],
    "rows": [["APAC", "+18%"], ["EMEA", "+12%"]]
  },
  "markdown_repr": "| Region | YoY Growth |\n|---|---|\n| APAC | +18% |\n| EMEA | +12% |",
  "confidence": 0.98,
  "vlm_description": null
}
```

---

## 4. Export Models

### 4.1 `Chunk` (Produced by `to_chunks()`)

| Field | Type | Description |
|---|---|---|
| `chunk_id` | `str` | Unique chunk identifier formatted as `{doc_id}-chunk-{index}`. |
| `text` | `str` | Full chunk text prepended with heading ancestry breadcrumbs: `Context: H1 > H2\n\n{text}`. |
| `headings` | `list[str]` | Ordered list of ancestor heading titles from root to nearest section. |
| `element_types` | `list[str]` | Deduplicated list of element types contained within this chunk. |
| `page_numbers` | `list[int]` | Sorted list of page numbers spanned by the chunk. |
| `estimated_tokens` | `int` | Approximate token count (estimated at ~4 characters per token). |

---

### 4.2 `KnowledgeGraph` (Produced by `to_graph()`)

| Field | Type | Description |
|---|---|---|
| `nodes` | `list[GraphNode]` | Graph vertices representing the document root, sections, and content elements. |
| `edges` | `list[GraphEdge]` | Directed relationship edges: `CONTAINS_SECTION`, `CONTAINS`, `FOLLOWS`. |