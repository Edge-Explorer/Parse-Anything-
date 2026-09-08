# universal_parser.extractors.office

The `office` sub-package provides structured extraction for the full range of Microsoft Office document formats, spanning both the modern Open XML formats (`.docx`, `.pptx`, `.xlsx`) and the legacy binary OLE2 compound formats (`.doc`, `.ppt`, `.xls`). It exists as a distinct sub-package because Office documents share a common semantic model — headings, body paragraphs, list items, and tables — but each format stores that information using entirely different on-disk representations that require different parsing libraries.

All four extractors in this package inherit from `BaseExtractor` and are decorated with `@register`, making them automatically available to the central router without any manual mapping. The package covers the most common productivity document formats encountered in enterprise document processing pipelines.

---

## Files

| Filename | Purpose | Key Exported Class / Function |
|---|---|---|
| `__init__.py` | Package marker | — |
| `docx_extractor.py` | Extracts text and tables from Word Open XML documents | `DocxExtractor` |
| `pptx_extractor.py` | Extracts slides, bullet points, and tables from PowerPoint presentations | `PPTXExtractor` |
| `xlsx_extractor.py` | Extracts worksheets from Excel workbooks as table elements | `XlsxExtractor` |
| `legacy_extractor.py` | Extracts content from legacy binary Office formats via olefile and xlrd | `LegacyOfficeExtractor` |

---

## Technical Details

### DocxExtractor (`docx_extractor.py`)

`DocxExtractor` handles `FileType.DOCX` using `python-docx`. Its most important design decision is how it traverses the document body.

#### Body Traversal and Reading Order

`python-docx` exposes two convenience attributes: `doc.paragraphs` and `doc.tables`. These are pre-filtered lists containing only their respective element types. Using them to extract content would yield all paragraphs first and all tables second, completely destroying the interleaved order in which they actually appear in the document body — a table that appears between two paragraphs would be relocated to after all paragraphs.

`DocxExtractor` avoids this by iterating over `doc.element.body` directly, which is the raw XML element tree of the document body. Each child element has an XML tag accessible via `child.tag`. The extractor checks this against `qn("w:p")` (paragraph) and `qn("w:tbl")` (table), where `qn` is the qualified-name resolver from `docx.oxml.ns`. Python-docx wrapper objects (`Paragraph`, `Table`) are constructed on the fly from these raw elements and the document reference, preserving the original document order.

#### Heading Detection

Heading detection is performed by looking up the paragraph's style name (converted to lowercase) in the `_HEADING_STYLE_MAP` dictionary. This dictionary maps Word's built-in style names — `"heading 1"` through `"heading 6"`, `"title"`, and `"subtitle"` — to integer heading levels 1–6. Word's `"Title"` style is treated as H1 and `"Subtitle"` as H2, which matches the semantic role these styles play in practice.

Empty paragraphs (after stripping whitespace) are silently skipped to avoid generating `Element` objects with no informational content.

#### List Detection

List items are detected by checking whether the paragraph's style name contains the substring `"list"`. This is a broad match that captures Word's various built-in list styles (`"List Bullet"`, `"List Number"`, `"List Paragraph"`, etc.) without requiring an exhaustive enumeration of every possible list style name.

#### Table Processing

Tables are converted by iterating `table.rows`, extracting `cell.text.strip()` for each cell. The first row is promoted to `headers` and all subsequent rows become `data_rows`. A `TableData` object is constructed and a Markdown pipe-table representation is generated for use in RAG prompts. Cells within merged regions may repeat the same text (this is a behavior of the underlying `python-docx` API for merged cells) — the extractor does not de-duplicate these at this stage.

---

### PPTXExtractor (`pptx_extractor.py`)

`PPTXExtractor` handles `FileType.PPTX` using the `python-pptx` library. It models a presentation as a sequence of slides, each of which produces a heading element followed by shape-level content elements.

#### Slide Title Extraction

Every slide is processed by first checking `slide.shapes.title`. If the title shape exists and has non-empty text, it is yielded as a `heading` element at level 1 with the text `"Slide N: <title>"`. If the title shape is absent (a slide with no title placeholder), a bare `"Slide N"` heading is still yielded, ensuring that RAG chunk boundaries align with slide transitions regardless of whether the designer used a title.

The `page` field of every element from a slide is set to the 1-based slide number, providing provenance information for downstream retrieval systems.

#### Shape Content Extraction

After the title, all other shapes on the slide are iterated. The extractor handles two shape types:

**Tables** (`shape.has_table == True`): PowerPoint tables are extracted by iterating `table.rows` and collecting `cell.text.strip()` for each cell. Completely empty rows are skipped. The first row is used as `headers`, subsequent rows as `data_rows`. A Markdown pipe-table representation is built and the element's `text` field is set to `"Slide N Table"` for identification purposes.

**Text frames** (`shape.has_text_frame == True`): Each paragraph within the text frame is inspected. `paragraph.level` indicates its nesting depth in the bullet hierarchy: level 0 is a top-level paragraph (emitted as `"paragraph"`), while levels 1 and above are sub-bullets (emitted as `"list_item"`). The `markdown_repr` for list items is prefixed with `"  " * level + "- "` to represent bullet depth in plain Markdown.

---

### XlsxExtractor (`xlsx_extractor.py`)

`XlsxExtractor` handles `FileType.XLSX` using `openpyxl`. Its key feature is memory-safe streaming of large workbooks.

#### Memory-Safe Loading

The workbook is opened with `load_workbook(path, read_only=True, data_only=True)`. The `read_only=True` flag instructs openpyxl to use its streaming reader, which yields one row at a time rather than loading the entire worksheet into memory. This is critical for large Excel files (millions of rows) where the in-memory representation of the full workbook could exhaust available RAM. The `data_only=True` flag evaluates all formula cells and returns their computed values rather than the formula strings themselves, making the extracted data immediately usable without a spreadsheet engine.

#### Multi-Sheet Handling

Each worksheet in the workbook is processed independently and yields one `table` element. The element's `text` field is set to `"Sheet: <sheet_name>"` and the `markdown_repr` includes a `### Sheet: <sheet_name>` prefix, allowing downstream systems to identify which sheet each table originated from.

#### Merged Header Handling

The first row of each sheet is treated as the header row. Because Excel's cell merging does not duplicate the merge label into all covered cells — merged cells appear as empty strings in the extracted data — the extractor applies a forward-fill pass over the header row. If a header cell is empty and a previous non-empty header exists, the cell is renamed to `"<previous_header>_col<column_index>"`. Cells where no prior non-empty header exists at all are named `"Column_<index>"`. This ensures that every column in the output `TableData` has a unique, non-empty header even when the source spreadsheet uses merged header cells for visual grouping.

---

### LegacyOfficeExtractor (`legacy_extractor.py`)

`LegacyOfficeExtractor` handles the legacy binary Microsoft Office formats: `FileType.DOC`, `FileType.XLS`, and `FileType.PPT`. It dispatches to one of two internal methods based on file extension.

#### XLS Extraction (`_stream_xls`)

Legacy Excel workbooks are read using `xlrd`. Unlike openpyxl's streaming reader, xlrd loads the entire workbook into memory (this is a limitation of the XLS format's binary structure). For each sheet, `sheet.cell_value(row_idx, col_idx)` is called for every cell — xlrd returns native Python types (float, str, datetime, etc.) — and these are coerced to strings with `str()`. Empty rows are skipped, the first row is promoted to headers, and the sheet is yielded as a `table` element with a Markdown representation, matching the output format of `XlsxExtractor`.

#### DOC and PPT Text Extraction (`_stream_ole_text`)

Legacy `.doc` and `.ppt` files are OLE2 compound documents — a Windows-specific hierarchical container format that stores multiple named streams (binary data sequences) within a single file, analogous to a filesystem-in-a-file. `olefile.OleFileIO` opens the container and `ole.listdir()` enumerates all named streams.

The extractor reads each stream's raw bytes and applies `re.findall(rb"[\x20-\x7E]{4,}", stream_data)` — a regex that matches sequences of four or more printable ASCII characters. This approach bypasses the complexity of the full binary DOC/PPT format specifications: rather than parsing the Word Binary Format or PowerPoint binary record structures, it performs a heuristic extraction of embedded printable strings. Strings are decoded as ASCII and filtered: chunks shorter than 4 characters and strings starting with `"Microsoft"` (internal metadata markers) are discarded. Each retained string is yielded as a `paragraph` element with a confidence of `0.8`, reflecting that this extraction method may pick up metadata fragments and internal identifiers alongside genuine document text.

---

## Code Examples

### Extracting a DOCX file

```python
from universal_parser.extractors.office.docx_extractor import DocxExtractor

extractor = DocxExtractor()
for element in extractor.stream("quarterly_report.docx"):
    if element.type == "heading":
        print(f"{'#' * element.level} {element.text}")
    elif element.type == "table":
        print(element.markdown_repr)
    else:
        print(element.text)
```

### Extracting a PowerPoint file

```python
from universal_parser.extractors.office.pptx_extractor import PPTXExtractor

extractor = PPTXExtractor()
for element in extractor.stream("presentation.pptx"):
    print(f"[Slide {element.page}] [{element.type}] {element.text[:80]}")
```

### Extracting an Excel workbook (all sheets)

```python
from universal_parser.extractors.office.xlsx_extractor import XlsxExtractor

extractor = XlsxExtractor()
for element in extractor.stream("data.xlsx"):
    print(f"Sheet table: {element.text}")
    print(f"Columns: {element.data.headers}")
    print(f"Row count: {len(element.data.rows)}")
```

### Extracting a legacy .doc file

```python
from universal_parser.extractors.office.legacy_extractor import LegacyOfficeExtractor

extractor = LegacyOfficeExtractor()
for element in extractor.stream("old_report.doc"):
    print(f"[{element.confidence:.2f}] {element.text[:100]}")
```

### Via the engine (format-transparent)

```python
from universal_parser.core.engine import parse

# Works identically for .docx, .pptx, .xlsx, .doc, .xls, .ppt
doc = parse("any_office_file.xlsx")
for element in doc.content_tree:
    print(element.type, element.text)
```

---

## Dependencies

| Library | Format | Role |
|---|---|---|
| `python-docx` | DOCX | Paragraph, heading, and table extraction with style metadata |
| `python-pptx` | PPTX | Slide shape iteration, text frame and table access |
| `openpyxl` | XLSX | Streaming workbook reader with formula evaluation |
| `xlrd` | XLS | Legacy binary Excel workbook reading |
| `olefile` | DOC, PPT | OLE2 compound document container access |
