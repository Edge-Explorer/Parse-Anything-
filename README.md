# universal-parser

A document ingestion engine for RAG pipelines. Parses PDFs, spreadsheets, Word documents, emails, web pages, scanned images, and more into a single consistent output format — without requiring a GPU or any paid API.

[![CI](https://github.com/your-username/Parse-Anything-/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/Parse-Anything-/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/universal-parser)](https://pypi.org/project/universal-parser/)
[![Python](https://img.shields.io/pypi/pyversions/universal-parser)](https://pypi.org/project/universal-parser/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## The Problem

Feeding real-world documents into an AI pipeline is messier than it looks. A PDF is not a text file — reading order breaks on multi-column layouts, tables come out as garbage, and scanned pages return nothing at all. Every file format needs a different library, and those libraries return different data structures, making it difficult to build a consistent downstream pipeline.

Most solutions either require a paid API, need a GPU, or only handle one or two formats cleanly. This project handles all of them from a single call, free to run, on CPU.

---

## What It Does

- Parses a document from any supported format into a validated, consistent JSON structure
- Preserves reading order across single-column, multi-column, and mixed layouts
- Extracts tables with both bordered and borderless detection, including merged cells
- Routes scanned pages through OCR with deskew and orientation correction
- Unpacks embedded assets in Office files and routes them back through the pipeline recursively
- Streams large files page-by-page — does not load the full document into memory
- Output schema is versioned; downstream integrations do not break between releases

---

## Installation

Requires Python 3.11 or later.

```bash
pip install universal-parser
```

For OCR support (scanned PDFs and images):

```bash
pip install "universal-parser[ocr]"
```

For development:

```bash
pip install "universal-parser[dev]"
```

Using `uv`:

```bash
uv add universal-parser
uv add "universal-parser[ocr]"
```

---

## Quickstart

```python
from universal_parser.core.engine import parse

doc = parse("path/to/your/file.pdf")

print(doc.metadata.file_type)
print(doc.metadata.page_count)

for element in doc.content_tree:
    print(element.type, element.text)
```

The returned `Document` object is a Pydantic model. Serialize it to JSON:

```python
print(doc.model_dump_json(indent=2))
```

---

## Output Schema

Every supported format produces the same output structure:

```json
{
  "schema_version": "1.0",
  "doc_id": "abc123",
  "metadata": {
    "file_name": "report.pdf",
    "file_type": "pdf",
    "page_count": 12,
    "has_scanned_pages": false
  },
  "content_tree": [
    {
      "element_id": "e1",
      "type": "heading",
      "level": 1,
      "text": "Introduction",
      "page": 1,
      "bbox": { "x0": 72.0, "y0": 100.0, "x1": 300.0, "y1": 120.0 }
    },
    {
      "element_id": "e2",
      "type": "table",
      "page": 2,
      "data": {
        "headers": ["Name", "Value"],
        "rows": [["Item A", "100"], ["Item B", "200"]]
      },
      "markdown_repr": "| Name | Value |\n|---|---|\n| Item A | 100 |"
    }
  ]
}
```

Full schema reference: [docs/SCHEMA.md](docs/SCHEMA.md)

---

## Supported Formats

| Format | Extension(s) | Status | Notes |
|---|---|---|---|
| PDF (native text) | `.pdf` | v0.1.0 | Multi-column reading order, header hierarchy |
| Word Document | `.docx` | v0.1.0 | Paragraphs, headings, tables |
| Excel Spreadsheet | `.xlsx` | v0.1.0 | Streaming mode, merged cells |
| PDF (tables) | `.pdf` | v0.2.0 | Lattice + stream detection, confidence scores |
| HTML / XHTML | `.html`, `.xhtml` | v0.3.0 | selectolax-based, bs4 fallback |
| EPUB | `.epub` | v0.3.0 | |
| CSV / TSV | `.csv`, `.tsv` | v0.3.0 | Auto-dialect detection |
| Parquet | `.parquet` | v0.3.0 | pyarrow streaming |
| JSON / XML | `.json`, `.xml` | v0.3.0 | |
| Scanned images | `.tiff`, `.bmp`, `.webp` | v0.4.0 | OCR + deskew, requires `[ocr]` |
| Scanned PDF | `.pdf` | v0.4.0 | Per-page detection, requires `[ocr]` |
| Email | `.eml`, `.mbox`, `.msg` | v0.5.0 | Recursive attachment parsing |
| PowerPoint | `.pptx` | v0.6.0 | |
| Legacy Office | `.doc`, `.xls`, `.ppt` | v0.6.0 | OLE compound file format via olefile |

---

## Architecture

```
Input File
    |
    v
Sniffer  (magic-byte + extension detection)
    |
    v
Router   (FileType -> Extractor registry)
    |
    v
Extractor  (format-specific, yields Element objects)
    |
    v
Schema Normalizer  (Pydantic validation)
    |
    v
Document  (versioned output)
```

Every extractor implements one method:

```python
def stream(self, path: str) -> Iterator[Element]:
    ...
```

Adding a new format means creating one new file in `extractors/` and one entry in `router.py`. Nothing else changes. Details: [docs/ADDING_A_FORMAT.md](docs/ADDING_A_FORMAT.md)

Full architecture notes: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Roadmap

| Phase | What Ships | Version |
|---|---|---|
| 0 | Repo scaffold, schema, sniffer | — |
| 1 | PDF (native), DOCX, XLSX | v0.1.0 |
| 2 | Table extraction (lattice + stream) | v0.2.0 |
| 3 | HTML, EPUB, CSV, TSV, Parquet, JSON, XML | v0.3.0 |
| 4 | Scanned documents and images (OCR) | v0.4.0 |
| 5 | Email parsing with recursive attachments | v0.5.0 |
| 6 | OLE / embedded asset recursion | v0.6.0 |
| 7 | Memory and streaming hardening | v0.7.0 |
| 8 | Markdown / chunk / graph export layer | v0.8.0 |
| 9 | MCP server interface | v0.9.0 |
| 10 | Template fingerprinting and auto-tuning | v0.10.0 |
| 11 | Observability and drift dashboard | v1.0.0 |

---

## Contributing

Contributions are welcome. Before opening a pull request:

1. Read [docs/ADDING_A_FORMAT.md](docs/ADDING_A_FORMAT.md) if you are adding format support.
2. Add fixture files in `tests/fixtures/<format>/` — at least three real samples, including one deliberately messy one.
3. Write tests in `tests/test_<format>.py` asserting schema validity and at least one content-correctness check.
4. Add a `CHANGELOG.md` entry.
5. Run `pytest tests/` and `python benchmarks/memory_profile.py` — both must pass.

Pull requests without fixture files and tests will not be merged. "Supports .epub" must mean something verifiable, not just a file that imports without crashing.

---

## License

MIT. See [LICENSE](LICENSE).

Note: `PyMuPDF` (used for PDF text extraction) is licensed under AGPL-3.0. This is compatible with open-source use. If you are building a closed-source commercial product on top of this library, replace the PDF text extraction layer with `pdfplumber` (MIT). The swap requires changing only `extractors/pdf/native.py`.
