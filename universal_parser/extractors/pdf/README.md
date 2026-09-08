# universal_parser.extractors.pdf

The `pdf` sub-package provides complete extraction coverage for PDF documents, handling both text-native PDFs and fully scanned (image-only) pages within the same pipeline. It exists as a dedicated sub-package because PDF extraction is inherently more complex than other formats: a single PDF file may mix typeset text, bordered and borderless tables, multi-column layouts, and scanned page images — all of which require different parsing strategies that must be orchestrated in a defined sequence to produce an accurate, ordered stream of `Element` objects.

The package uses two external PDF libraries in tandem: `pdfplumber` for word-level coordinate extraction and table detection, and `pypdfium2` for high-fidelity page rendering when OCR is needed. This dual-library approach avoids the limitations of relying on a single library, which typically excels at either text extraction or rendering but not both.

---

## Files

| Filename | Purpose | Key Exported Class / Function |
|---|---|---|
| `__init__.py` | Package marker | — |
| `native.py` | Primary PDF extractor: text, tables, multi-column layout, OCR fallback | `NativePDFExtractor` |
| `tables.py` | Bordered and borderless table detection and extraction logic | `PDFTableExtractor` |
| `visual_onnx.py` | Reserved for future visual-model (ONNX layout detection) integration | — (empty placeholder) |

---

## Technical Details

### NativePDFExtractor (`native.py`)

`NativePDFExtractor` is the `@register`-decorated concrete extractor that handles `FileType.PDF`. It is the orchestrator: it opens the document, collects font metadata, and then iterates page by page, delegating to `PDFTableExtractor` for table regions and to its own OCR fallback path for scanned pages.

#### Initialization

The constructor instantiates a `RapidOCR` engine from `rapidocr_onnxruntime`. This object loads ONNX model weights into memory once per `NativePDFExtractor` instance. Keeping it as an instance attribute means the weights survive across multiple `stream()` calls on the same extractor instance, avoiding repeated model loading overhead.

#### Font-Size-Based Header Hierarchy

Before page-by-page iteration begins, `_collect_font_sizes()` samples up to the first 10 pages of the document and accumulates all word-level `size` attributes produced by `pdfplumber.extract_words(extra_attrs=["size"])`. This produces a distribution of font sizes representative of the document's overall typography.

`_compute_header_thresholds()` then computes three heading level thresholds from this distribution using `numpy.percentile`:

- **H1 threshold**: the 95th percentile, or the median plus 3.0 points, whichever is larger.
- **H2 threshold**: the 85th percentile, or the median plus 1.5 points, whichever is larger.
- **H3 threshold**: the 75th percentile, or the median plus 0.5 points, whichever is larger.

The percentile-plus-floor approach ensures that headings are always meaningfully larger than the body text even in documents with a narrow font-size range (e.g., a document that uses only 10pt and 12pt fonts). Without the floor, a 75th-percentile threshold on such a document would classify the majority of text as H3, producing a nonsensical hierarchy.

#### Per-Page Extraction Pipeline

For each page, the extractor runs the following steps in sequence:

**Step A — Table extraction**: A `PDFTableExtractor` is instantiated for the page and `extract_tables()` is called. This returns a list of table dictionaries, each containing a `TableData` object, a bounding box tuple `(x0, y0, x1, y1)`, and a confidence score. The bounding boxes are retained separately as `table_bboxes`.

**Step B — Word grouping**: `pdfplumber.page.extract_words(extra_attrs=["size"])` returns every discrete word on the page with its spatial coordinates and font size. Words that fall inside any `table_bbox` (with a 2-point tolerance on all sides, checked by `_is_inside_any_bbox()`) are suppressed — this prevents table cell text from appearing twice in the output.

The remaining words are grouped into "spans" (phrase-level text blocks) using a simple greedy pass: two consecutive words are merged into the same span if their top coordinates differ by fewer than 4 points (same baseline) and the horizontal gap between them is fewer than 12 points. When a word breaks either condition, the current span is finalized and a new one begins. Each span records the text, the font size of its first word, and a tight bounding box covering all words in it.

**Step C — Merging tables and spans**: Table dictionaries (with `is_table=True`) are appended to the spans list so that all content — both text and table regions — is represented in a single flat list before reading-order sorting.

**Step D — OCR fallback**: If the combined spans list is empty after Steps A–C (meaning the page contains no detectable text or tables), the page is treated as scanned. `_ocr_scanned_page()` is called with the corresponding `pypdfium2.PdfPage` object.

#### Reading Order Sorting (`_sort_reading_order`)

Sorting is not a simple top-to-bottom sort by Y coordinate because that would interleave left-column and right-column content on two-column pages.

The algorithm partitions elements into three groups based on their horizontal extent relative to the page midpoint (`page_width / 2.0`):

- **Full-width elements**: spans whose bounding box crosses the midpoint (extending past it on both sides, within a 15-point tolerance).
- **Left column elements**: spans whose `x1` falls at or left of `midpoint + 15`.
- **Right column elements**: spans whose `x0` falls at or right of `midpoint - 15`.

If both left and right columns contain at least two elements (confirming a genuine two-column layout), the algorithm further partitions the full-width elements into those that appear above the column region, those that appear within it, and those that appear below it. The final order is:

```
top full-width -> mid full-width -> left column (sorted by Y) -> right column (sorted by Y) -> bottom full-width
```

This exactly replicates the reading order a human would follow through a two-column academic or business document.

For pages with fewer than five elements, the algorithm falls back to a plain `(y, x)` sort without column detection.

#### OCR Scanned Pages (`_ocr_scanned_page`)

When a page has no native text, `pypdfium2.PdfPage.render(scale=200.0/72.0)` renders the page to a bitmap at approximately 200 DPI (a resolution high enough for reliable character recognition without excessive memory use). The bitmap is converted to a Pillow `RGB` image, then to a `numpy` array suitable for RapidOCR.

`RapidOCR.__call__(img_np)` returns a list of `(dt_boxes, text, score)` tuples, where `dt_boxes` is a quadrilateral of four pixel corner coordinates around the detected text region. The extractor computes `x0, y0, x1, y1` as the min/max of these corner coordinates scaled back from pixel space to PDF coordinate space using `scale_x = page_width / image_pixel_width` and `scale_y = page_height / image_pixel_height`. Each result is yielded as a `paragraph` element with its OCR confidence score attached.

---

### PDFTableExtractor (`tables.py`)

`PDFTableExtractor` handles the two fundamentally different table structures found in PDFs.

#### Lattice (Bordered) Table Extraction (`_extract_lattice`)

Bordered tables — where visible horizontal and vertical lines define cell boundaries — are detected by configuring `pdfplumber`'s `find_tables()` with `vertical_strategy="lines"` and `horizontal_strategy="lines"`, plus a `snap_tolerance` and `join_tolerance` of 3 points to account for minor rendering imprecision in line coordinates.

When `pdfplumber` detects a table under these settings, it has traced the actual vector lines in the PDF's graphics stream and mapped them to a coordinate grid. Cell extraction from such tables is deterministic: the text within each cell boundary is extracted by `table.extract()`, `None` values (merged cells) are coerced to empty strings, and the first row is promoted to `headers`. Confidence is assigned `0.98` if all data rows have the same column count as the header row, and `0.90` otherwise.

#### Stream (Borderless) Table Extraction (`_extract_stream`)

Borderless tables — where columns are aligned by whitespace rather than drawn lines — are detected with `vertical_strategy="text"` and `horizontal_strategy="text"`. This strategy infers column positions from the horizontal alignment of text runs and row positions from the vertical spacing of text lines. The settings `min_words_vertical=3` and `min_words_horizontal=2` require a minimum number of text tokens in each direction before a region is treated as a table candidate.

Because this strategy is inherently heuristic, several rejection filters are applied before accepting a candidate table:

1. **Minimum density**: The candidate must have at least 2 non-empty rows and 4 non-empty cells total.
2. **Average word count per cell**: If the mean number of words per non-empty cell exceeds 2.5, the candidate is rejected. This threshold distinguishes genuine tabular data (short labels, numbers, codes) from multi-column body text, which also appears as a grid under the stream strategy but contains sentence-length content in each cell.
3. **Page height fraction**: If the candidate table spans more than 40% of the page height, it is rejected. This eliminates false positives from two-column text pages that the stream strategy misidentifies as a single wide table.
4. **Minimum columns**: Candidates with fewer than 2 detected columns are rejected.

Accepted stream tables receive a fixed confidence of `0.85`, reflecting the inherently probabilistic nature of borderless table detection.

---

### visual_onnx.py

This file is currently an empty placeholder. It is reserved for a future ONNX-based visual layout model that would analyze the rendered page image to detect table regions, figure regions, and column boundaries using a neural document layout architecture. When implemented, it will be called before `PDFTableExtractor` and its output will provide spatial priors that improve both table and column detection accuracy on complex layouts.

---

## Code Examples

### Streaming a PDF document

```python
from pathlib import Path
from universal_parser.extractors.pdf.native import NativePDFExtractor

extractor = NativePDFExtractor()
for element in extractor.stream(Path("annual_report.pdf")):
    if element.type == "heading":
        print(f"H{element.level}: {element.text}")
    elif element.type == "table":
        print(f"Table ({len(element.data.rows)} rows):")
        print(element.markdown_repr)
    elif element.type == "paragraph":
        print(f"  {element.text[:100]}")
```

### Using the engine (recommended)

```python
from universal_parser.core.engine import parse
from universal_parser.exports.to_markdown import to_markdown

doc = parse("scanned_contract.pdf")
print(to_markdown(doc))
```

### Checking per-element OCR confidence

```python
from universal_parser.extractors.pdf.native import NativePDFExtractor

extractor = NativePDFExtractor()
for element in extractor.stream("scan.pdf"):
    if element.confidence is not None and element.confidence < 0.7:
        print(f"Low-confidence segment: '{element.text}' ({element.confidence:.2f})")
```

### Using PDFTableExtractor directly

```python
import pdfplumber
from universal_parser.extractors.pdf.tables import PDFTableExtractor

with pdfplumber.open("financial_tables.pdf") as doc:
    for page in doc.pages:
        te = PDFTableExtractor(page)
        for table in te.extract_tables():
            print("Headers:", table["data"].headers)
            print("Rows:", len(table["data"].rows))
            print("Confidence:", table["confidence"])
```

---

## Dependencies

| Library | Role |
|---|---|
| `pdfplumber` | Word extraction with spatial coordinates, lattice and stream table detection |
| `pypdfium2` | High-fidelity page rendering to bitmap for scanned pages |
| `rapidocr_onnxruntime` | CPU-only ONNX OCR engine for scanned page text recovery |
| `numpy` | Font-size percentile computation, bounding box coordinate scaling |
| `Pillow` | Image format conversion from pypdfium2 bitmap to numpy array |
