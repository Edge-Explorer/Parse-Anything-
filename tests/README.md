# tests

This directory contains the complete test suite for the universal-doc-parser library. Every extractor, schema component, export utility, adaptive layer, observability system, MCP server interface, and benchmark provider family is covered by dedicated test modules. The test suite is executed on every push and pull request in the GitHub Actions CI/CD matrix across Ubuntu, macOS, and Windows on Python 3.11 and 3.12.

---

## Testing Framework and Configuration

The project uses `pytest` as the test runner. Test configuration is defined in `pyproject.toml` under `[tool.pytest.ini_options]`, which suppresses known harmless deprecation warnings from `openpyxl` and third-party libraries to keep the test output readable.

Run the full test suite locally:

```bash
uv run pytest -v
```

Run a single test module:

```bash
uv run pytest tests/test_pdf.py -v
```

Run with coverage reporting:

```bash
uv run pytest --cov=universal_parser --cov-report=term-missing
```

---

## Test Modules

| File | What It Tests |
|---|---|
| `test_pdf.py` | Native PDF text extraction, multi-column reading order, heading hierarchy, table detection, and scanned PDF OCR fallback. |
| `test_docx.py` | Word document heading hierarchy, table extraction, paragraph ordering, and schema correctness. |
| `test_xlsx.py` | Excel spreadsheet row and column extraction, merged cell replication, and schema normalization. |
| `test_pptx.py` | PowerPoint slide shape ordering, table elements, and title hierarchy extraction. |
| `test_legacy.py` | Legacy OLE binary compound document parsing for `.doc`, `.xls`, and `.ppt` formats. |
| `test_csv.py` | CSV and TSV parsing with automatic dialect detection for varied delimiter and quote character combinations. |
| `test_parquet.py` | Apache Parquet columnar streaming extraction and schema normalization. |
| `test_json_xml.py` | JSON recursive tree flattening and XML element traversal and schema mapping. |
| `test_html.py` | HTML and XHTML DOM parsing, heading hierarchy reconstruction, and malformed markup resilience. |
| `test_epub.py` | EPUB spine-ordered chapter extraction and per-chapter HTML sub-parsing. |
| `test_image.py` | Raster image OCR extraction through the RapidOCR pipeline for PNG, JPEG, and other supported image formats. |
| `test_mail.py` | EML, MBOX, and MSG email header extraction, body decoding, and recursive attachment routing. |
| `test_mcp.py` | FastMCP server tool registration, `parse_document` invocation, and `list_supported_formats` correctness. |
| `test_exports.py` | Markdown export fidelity, hierarchical chunk structure with heading breadcrumb injection, and knowledge graph edge correctness. |
| `test_adaptive.py` | Layout fingerprint computation reproducibility, SHA-256 hash stability, cache exact lookup, fuzzy similarity matching, cache persistence across load/save cycles, and auto-tuner parameter bounds. |
| `test_observability.py` | Metrics collector singleton behavior, thread-safe event recording, anomaly signal emission, and dashboard HTML export structure. |
| `test_benchmark_providers.py` | Dry-run validation of all 15 benchmark provider classes verifying that each provider returns a well-formed result dictionary without requiring API connectivity. |

---

## Fixtures

All test fixture files are located in `tests/fixtures/` and are committed to the repository so that all CI runners have access to them without downloading from external sources.

```
tests/fixtures/
    csv/
    docx/
    html/
    json/
    pdf/
    xlsx/
    xml/
```

### Fixture Standards

When contributing a new format extractor, the following fixture requirements must be met before the pull request will be reviewed:

1. At least three fixture files in `tests/fixtures/<format>/`.
2. One fixture must be a deliberately simple, well-structured document to verify basic extraction.
3. One fixture must be a complex document with mixed layouts, tables, or nested structures to verify production robustness.
4. One fixture must be a deliberately malformed or edge-case document to verify that the extractor degrades gracefully rather than raising an unhandled exception.

---

## Writing a New Test Module

Every test module must satisfy the following contract:

1. Import the `parse()` function directly and test against the `Document` schema, not against internal extractor methods.
2. Assert that `doc.metadata.file_type` is set to the correct format identifier string.
3. Assert that `doc.content_tree` is non-empty and contains elements of the correct types.
4. Assert that at least one element has non-empty `text` or `data` (for tables).
5. Assert that the extractor does not raise unhandled exceptions on the malformed fixture.

Example structure for a new format test:

```python
import pytest
from pathlib import Path
from universal_parser import parse

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "myformat"


def test_basic_extraction():
    doc = parse(FIXTURE_DIR / "simple.myformat")
    assert doc.metadata.file_type == "myformat"
    assert len(doc.content_tree) > 0
    assert any(e.text for e in doc.content_tree)


def test_complex_document():
    doc = parse(FIXTURE_DIR / "complex.myformat")
    headings = [e for e in doc.content_tree if e.type == "heading"]
    assert len(headings) > 0


def test_malformed_does_not_crash():
    doc = parse(FIXTURE_DIR / "malformed.myformat")
    # Must not raise — may return empty content_tree
    assert doc is not None
```
