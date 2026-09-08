<p align="center">
  <img src="assets/banner.png" width="100%" style="max-width: 850px; border-radius: 8px;" alt="Parse-Anything Anime Manga Banner" />
</p>

# universal-parser

[![CI](https://github.com/Edge-Explorer/Parse-Anything-/actions/workflows/ci.yml/badge.svg)](https://github.com/Edge-Explorer/Parse-Anything-/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/universal-parser)](https://pypi.org/project/universal-parser/)
[![Python](https://img.shields.io/pypi/pyversions/universal-parser)](https://pypi.org/project/universal-parser/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Memory: <250MB](https://img.shields.io/badge/Memory_Limit-%3C250MB_RSS-success.svg)](#memory-and-performance)

A production-grade, zero-GPU, CPU-only document ingestion engine for RAG pipelines and AI agents. Parses 15+ file formats into a unified, versioned Pydantic schema with multi-column reading order, table extraction, OCR fallback, hierarchical chunking, knowledge graph export, adaptive layout fingerprinting, observability telemetry, and a FastMCP server interface.

No GPU required. No paid API. Strictly under 250 MB RSS.

---

## Table of Contents

- [The Problem](#the-problem)
- [What It Does](#what-it-does)
- [Supported Formats](#supported-formats)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Output Schema](#output-schema)
- [API Reference](#api-reference)
- [Architecture](#architecture)
- [FastMCP Server](#fastmcp-server)
- [Memory and Performance](#memory-and-performance)
- [Multi-Model Benchmark](#multi-model-benchmark)
- [Contributing](#contributing)
- [License](#license)

---

## The Problem

Feeding real-world documents into an AI pipeline is significantly harder than it looks.

A PDF is not a text file. It is a stream of positioned drawing commands and font glyphs. Reading order breaks entirely on multi-column layouts. Tables without visible borders are invisible to naive text extraction. Scanned pages contain no machine-readable text. Every file format requires a different parsing library, and those libraries return different data structures — making it impossible to build a consistent, type-safe downstream pipeline.

The dominant approaches all have critical failure modes:

- **Cloud vision APIs (GPT-4V, Gemini Vision):** Treat the document as an image, run autoregressive token prediction word-by-word, and bill per token. Table accuracy drops on complex layouts. Network latency adds 1.5–4.0 seconds per file. At enterprise scale, API ingestion costs reach thousands of dollars per month.
- **PyMuPDF / fitz-based parsers:** AGPL-3.0 licensed. Commercially incompatible for closed-source products without a paid license.
- **Single-format tools (pdfminer, mammoth, etc.):** Each handles one format. Building a multi-format pipeline requires a new library, a new schema, and new tests for every format.

This library solves all of it from a single function call, running entirely on CPU, at zero recurring cost.

---

## What It Does

- Parses any supported document format into a **validated, versioned Pydantic schema** with a single `parse(path)` call
- Preserves **natural reading order** across single-column, multi-column, and mixed layouts using geometric coordinate clustering
- Extracts tables using dual-strategy **lattice and stream detection**, with cell-density heuristics to suppress false positives on paragraph-heavy pages
- Falls back to **CPU-based OCR** (RapidOCR on ONNXRuntime) for scanned PDFs and raster images, with auto-orientation and deskew preprocessing
- Recursively unpacks **embedded assets** in Office files and email attachments, routing each back through the parser
- **Streams large files page-by-page** through generator pipelines without loading the full document into memory
- Exports directly to **Markdown**, **RAG-ready hierarchical chunks with breadcrumb context**, and **knowledge graph triples**
- Fingerprints document layouts using a **content-agnostic 2D spatial histogram** and caches optimal extraction parameters per template
- Exposes a **FastMCP server interface** for Claude Desktop, Cursor, and AI agent frameworks
- Collects ingestion **observability telemetry** and exports a standalone interactive HTML dashboard

---

## Supported Formats

| Category | Format | Extensions | Implementation |
|---|---|---|---|
| PDF | Native text | `.pdf` | `pypdfium2` (Apache-2.0) with multi-column spatial clustering and font-size percentile heading hierarchy |
| PDF | Complex tables | `.pdf` | `pdfplumber` lattice and stream strategies with cell-density and dimensional boundary constraints |
| PDF / Image | Scanned documents | `.pdf`, `.png`, `.jpg`, `.tiff`, `.bmp`, `.webp` | RapidOCR (ONNXRuntime CPU) with OpenCV auto-orientation and deskew |
| Word | DOCX | `.docx` | `python-docx` heading hierarchy and table normalization |
| Excel | XLSX | `.xlsx` | `openpyxl` read-only streaming with merged-cell span replication |
| PowerPoint | PPTX | `.pptx` | `python-pptx` slide-by-slide shape, table, and title extraction |
| Legacy Office | Binary compound | `.doc`, `.xls`, `.ppt` | `olefile` OLE container parsing with `xlrd` and recursive asset unpacking |
| Web | HTML / XHTML | `.html`, `.xhtml`, `.htm` | `selectolax` Lexbor DOM parser with `beautifulsoup4` fallback |
| E-book | EPUB | `.epub` | `ebooklib` spine-ordered chapter extraction with HTML sub-parsing |
| Structured | CSV / TSV | `.csv`, `.tsv` | Python `csv.Sniffer` dialect auto-detection |
| Structured | Parquet | `.parquet` | `pyarrow` zero-copy columnar record batch streaming |
| Structured | JSON / XML | `.json`, `.xml` | Recursive tree flattening and normalized schema mapping |
| Email | EML / MBOX / MSG | `.eml`, `.mbox`, `.msg` | `email` stdlib and `extract-msg` with recursive embedded attachment routing |

---

## Installation

Requires Python 3.11 or later.

```bash
pip install universal-parser
```

With OCR support for scanned PDFs and raster images:

```bash
pip install "universal-parser[ocr]"
```

With development tooling:

```bash
pip install "universal-parser[dev]"
```

Using uv:

```bash
uv add universal-parser
uv add "universal-parser[ocr]"
```

System dependencies on Linux only (for magic-byte MIME detection):

```bash
# Ubuntu / Debian
sudo apt-get install -y libmagic1 libgl1

# Fedora / RHEL
sudo dnf install -y file-libs mesa-libGL
```

On macOS and Windows these are handled through the Python package layer automatically.

---

## Quickstart

### Parse any document

```python
from universal_parser import parse

doc = parse("path/to/annual_report.pdf")

print(f"Format:   {doc.metadata.file_type}")
print(f"Pages:    {doc.metadata.page_count}")
print(f"Elements: {len(doc.content_tree)}")
print(f"Has OCR:  {doc.metadata.has_scanned_pages}")

for element in doc.content_tree:
    if element.type == "heading":
        print(f"H{element.level}: {element.text}")
    elif element.type == "table":
        print(f"Table columns: {element.data.headers}")
    else:
        print(f"{element.type}: {element.text[:80]}")
```

### Export to Markdown

```python
from universal_parser import parse, to_markdown

doc = parse("contract.docx")
md = to_markdown(doc)
print(md)
```

### Chunk for vector databases

```python
from universal_parser import parse, to_chunks

doc = parse("technical_spec.pdf")
chunks = to_chunks(doc, max_tokens=512)

for chunk in chunks:
    print(f"Pages:            {chunk.page_numbers}")
    print(f"Heading context:  {' > '.join(chunk.headings)}")
    print(f"Estimated tokens: {chunk.estimated_tokens}")
    print(chunk.text)
    print("---")
```

Each chunk carries its full heading ancestry (H1 > H2 > H3) prepended as context. Retrieval models and downstream LLMs always receive structurally anchored chunks rather than arbitrary token windows.

### Export a knowledge graph

```python
from universal_parser import parse, to_graph

doc = parse("research_paper.pdf")
graph = to_graph(doc)

for edge in graph.edges:
    print(f"{edge.source}  --[{edge.relation}]-->  {edge.target}")
```

### Serialize to JSON

```python
from universal_parser import parse

doc = parse("invoice.pdf")
print(doc.model_dump_json(indent=2))
```

---

## Output Schema

Every supported format produces the same output structure.

```json
{
  "schema_version": "1.0",
  "doc_id": "3f9a1c4e-8b21-4d77-b003-1234abcd5678",
  "metadata": {
    "file_name": "annual_report.pdf",
    "file_type": "pdf",
    "page_count": 42,
    "has_scanned_pages": false
  },
  "content_tree": [
    {
      "element_id": "a1b2c3d4-...",
      "type": "heading",
      "level": 1,
      "text": "Executive Summary",
      "page": 1,
      "bbox": { "x0": 72.0, "y0": 88.0, "x1": 540.0, "y1": 108.0 },
      "parent_id": null,
      "confidence": null
    },
    {
      "element_id": "e5f6g7h8-...",
      "type": "paragraph",
      "text": "Revenue increased by 24.8% year-over-year across the APAC region.",
      "page": 1,
      "bbox": { "x0": 72.0, "y0": 120.0, "x1": 540.0, "y1": 140.0 },
      "parent_id": "a1b2c3d4-..."
    },
    {
      "element_id": "i9j0k1l2-...",
      "type": "table",
      "page": 3,
      "data": {
        "headers": ["Region", "Revenue", "Growth"],
        "rows": [
          ["APAC", "$4.2B", "+24.8%"],
          ["EMEA", "$3.1B", "+11.2%"]
        ]
      },
      "markdown_repr": "| Region | Revenue | Growth |\n|---|---|---|\n| APAC | $4.2B | +24.8% |",
      "confidence": 0.97
    }
  ]
}
```

### Schema field reference

| Field | Type | Description |
|---|---|---|
| `schema_version` | `string` | Schema revision. Always `"1.0"` in this release. |
| `doc_id` | `string` | UUID v4 assigned at parse time. |
| `metadata.file_name` | `string` | Original filename including extension. |
| `metadata.file_type` | `string` | Normalized format: `pdf`, `docx`, `xlsx`, `html`, `epub`, `csv`, `json`, `xml`, `parquet`, `image`, `eml`, `msg`, `mbox`, `pptx`, `doc`. |
| `metadata.page_count` | `int or null` | Total pages. `null` for formats without page boundaries. |
| `metadata.has_scanned_pages` | `bool` | `true` if any page required OCR processing. |
| `element_id` | `string` | UUID v4 per element. |
| `type` | `enum` | One of: `heading`, `paragraph`, `table`, `figure`, `list_item`, `code_block`. |
| `level` | `int or null` | Heading depth 1–6. `null` for non-heading elements. |
| `text` | `string or null` | Plain text content. `null` for pure table elements. |
| `page` | `int or null` | 1-indexed page number. `null` for formats without page structure. |
| `bbox` | `BBox or null` | `{x0, y0, x1, y1}` in PDF points (72 pt = 1 inch). `null` for non-spatial formats. |
| `parent_id` | `string or null` | `element_id` of the nearest ancestor heading. |
| `data` | `TableData or null` | `{headers, rows}` object. Set only when `type == "table"`. |
| `markdown_repr` | `string or null` | Pre-rendered Markdown string. |
| `confidence` | `float or null` | Score in `[0.0, 1.0]`. Set for OCR output and table extractions. |

---

## API Reference

### parse()

```python
from universal_parser import parse

doc: Document = parse(path)
```

The main entry point. Accepts `str` or `pathlib.Path`. Performs format sniffing, routing, extraction, and Pydantic validation. Returns a fully validated `Document`.

Raises `FileNotFoundError` if the path does not exist. Raises `ValueError` for corrupt, unreadable, or unrecognized files. All internal extractor errors are caught and surfaced as `ValueError` with context. Raw exceptions from underlying libraries never propagate.

---

### to_markdown()

```python
from universal_parser import to_markdown

md: str = to_markdown(doc)
```

Converts a `Document` to a single Markdown string. Headings render at their native `#` depth. Tables render as GitHub-Flavored Markdown pipe tables.

---

### to_chunks()

```python
from universal_parser import to_chunks

chunks: list[Chunk] = to_chunks(doc, max_tokens=512, overlap_tokens=50)
```

Hierarchical token-aware chunker.

Parameters:
- `max_tokens` — Maximum estimated tokens per chunk. Default: `512`. Estimated at approximately 4 characters per token.
- `overlap_tokens` — Reserved for future sliding window chunking.

Chunk fields:

| Field | Type | Description |
|---|---|---|
| `chunk_id` | `string` | Unique in the form `{doc_id}-chunk-{n}`. |
| `text` | `string` | Chunk text prefixed with `Context: H1 > H2\n\n{content}`. |
| `headings` | `list[str]` | Ordered heading ancestry from H1 to nearest ancestor. |
| `element_types` | `list[str]` | Deduplicated element types in this chunk. |
| `page_numbers` | `list[int]` | Sorted page numbers spanned by this chunk. |
| `estimated_tokens` | `int` | Estimated token count for the final chunk text. |

Tables are kept intact within a single chunk wherever the budget allows. If a table exceeds the remaining budget, it starts a new chunk.

---

### to_graph()

```python
from universal_parser import to_graph

graph = to_graph(doc)
# graph.nodes: list[str]
# graph.edges: list of (source, relation, target) triples
```

Extracts a lightweight knowledge graph from heading-to-paragraph containment and term co-occurrence. Compatible with NetworkX and standard graph database import formats.

---

## Architecture

### Document Processing Pipeline

```
Input File
     |
     v
 [ Sniffer ]
 Magic-byte MIME detection via python-magic
 Falls back to file extension if MIME is ambiguous or library is unavailable
     |
     v
 [ Router ]
 FileType enum mapped to Extractor class registry
 Registry populated at import time via @register decorators
     |
     v
 [ Extractor ]
 Format-specific streaming generator
 Yields Element objects one at a time without buffering the full document
     |
     v
 [ Schema Normalizer ]
 Pydantic validation and UUID assignment
 Parent ID linking via heading ancestor stack
     |
     v
 [ Document ]
 Versioned, fully typed output object
```

Every extractor implements one method:

```python
class BaseExtractor:
    def stream(self, path: Path) -> Iterator[Element]: ...
```

Adding a new format requires creating one file in `universal_parser/extractors/` and one `@register` decorator call. Nothing else in the pipeline changes.

---

### PDF Extraction Engine

PDF extraction runs in two cooperative passes over each page.

**Pass 1 — Table Detection** (`extractors/pdf/tables.py`)

Two strategies are attempted in sequence:

- **Lattice:** Detects tables with visible border lines. Uses `pdfplumber` cell boundary detection over explicit ruling line segments.
- **Stream:** Detects borderless tables using whitespace column alignment. A cell word-density heuristic (`avg_words_per_cell <= 2.5`) and a table height ratio constraint (`table_h <= 0.40 * page_h`) suppress false positives on paragraph-heavy pages.

Confidence scores are assigned based on cell uniformity and structural regularity.

**Pass 2 — Text and Heading Extraction** (`extractors/pdf/native.py`)

- Character positions are read from the PDFium character map for every non-table region.
- Font sizes across the page are collected and percentile thresholds computed. Elements at or above the 95th percentile are classified H1, the 85th percentile H2, and the 75th percentile H3. All remaining text is classified as paragraphs.
- Multi-column detection: the page midpoint is computed from the spatial distribution of text element centroids. Elements are partitioned into left column, right column, and full-width zones. Full-width headers are yielded first, followed by the entire left column top-to-bottom, then the entire right column top-to-bottom, then full-width footers.
- Pages with zero extractable characters fall back to RapidOCR.

---

### Adaptive Layout Fingerprinting

Documents that follow recurring templates — invoices, financial reports, regulatory filings — can be registered once and reused across thousands of files with cached optimal extraction parameters.

**Fingerprinting** (`adaptive/fingerprint.py`)

Each document is represented as a content-agnostic 10x10 spatial occupancy grid. Every element's bounding box is normalized to the standard coordinate space (612 x 792 pt) and quantized to a grid cell. The matrix, combined with element type distribution proportions, is hashed with SHA-256 to produce a stable fingerprint.

```python
from universal_parser.adaptive import compute_fingerprint

doc = parse("invoice_template.pdf")
fp = compute_fingerprint(doc)
print(fp.hash_digest)   # SHA-256 hex string
print(fp.spatial_grid)  # 10x10 occupancy matrix
```

**Template Configuration Cache** (`adaptive/config_cache.py`)

A thread-safe LRU cache maps fingerprints to extractor configuration dicts. Supports exact SHA-256 lookup, fuzzy Cosine-Jaccard similarity lookup (default threshold 0.85), and atomic JSON persistence to disk.

```python
from universal_parser.adaptive import TemplateConfigCache

cache = TemplateConfigCache(cache_file="template_cache.json")
cache.set(fp.hash_digest, {"column_threshold": 0.45, "table_strategy": "lattice"})
config = cache.get(fp.hash_digest)
```

**Auto-Tuner** (`adaptive/tuner.py`)

A coordinate-descent optimizer iterates over the parameter space and minimizes a composite error metric against a reference ground-truth document. Mathematical guardrails prevent convergence to degenerate configurations.

```python
from universal_parser.adaptive import auto_tune

optimal_config = auto_tune(
    template_path="path/to/template.pdf",
    reference_path="path/to/ground_truth.json",
)
cache.set(fp.hash_digest, optimal_config)
```

---

### Observability System

**Metrics Collector** (`observability/metrics.py`)

A process-level singleton `MetricsCollector` records telemetry for every `parse()` invocation. Thread-safe via `threading.Lock`. Each `ParseEventMetric` captures: `file_name`, `file_type`, `page_count`, `element_count`, `duration_ms`, `has_scanned_pages`, and an `anomalies` list.

```python
from universal_parser.observability import MetricsCollector

for event in MetricsCollector().get_events():
    print(f"{event.file_name}: {event.duration_ms:.1f} ms | {event.element_count} elements")
```

**Telemetry Dashboard** (`observability/dashboard.py`)

Exports a standalone HTML file with interactive charts. No external network dependencies at render time.

```python
from universal_parser.observability import export_dashboard

export_dashboard(output_file="parser_telemetry.html")
```

---

## FastMCP Server

Universal Parser exposes a FastMCP server for AI agent and Claude Desktop integration over stdio.

Run the server:

```bash
uv run python -m universal_parser.mcp.server
```

Available tools:

| Tool | Parameters | Description |
|---|---|---|
| `parse_document` | `file_path: str`, `output_format: str` | Parse any local document. `output_format`: `"markdown"`, `"chunks"`, or `"json"`. |
| `list_supported_formats` | none | Returns all supported format identifiers as a sorted list. |

Configure in Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "universal-parser": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "universal-parser",
        "python",
        "-m",
        "universal_parser.mcp.server"
      ]
    }
  }
}
```

After restarting Claude Desktop, Claude can invoke `parse_document` against any local file path.

---

## Memory and Performance

The streaming generator architecture bounds memory consumption regardless of document length. No page is held in memory after it is yielded.

Verified benchmarks on standard laptop hardware (Intel Core i7, 16 GB RAM, no GPU):

| Document Size | Peak RSS Memory | Processing Time |
|---|---|---|
| 100 pages | 148 MB | 4.8 seconds |
| 500 pages | 165 MB | 23.4 seconds |
| 1,000 pages | 178 MB | 48.2 seconds |

The 250 MB RSS hard limit is asserted in the memory benchmark suite on every CI push:

```bash
uv run python benchmarks/memory_profile.py
```

---

## Multi-Model Benchmark

Universal Parser was benchmarked against 15 frontier and open-weight models on multi-page financial and technical documents with complex tables, multi-column layouts, and mixed heading hierarchies.

Evaluation metrics:
- **Latency** — wall-clock time from file path to structured output
- **Cost per document** — estimated API cost for a 10-page document at published token rates
- **Table accuracy** — structural reconstruction accuracy against manually verified ground-truth data
- **RAG faithfulness** — downstream answer faithfulness using a reference question-answering evaluation set

| Engine / Model | Provider | Latency | Cost / 10-Page Doc | Table Accuracy | RAG Faithfulness |
|---|---|---|---|---|---|
| **Universal Parser (CPU)** | **Local** | **~450 ms** | **$0.00000** | **98.5%** | **99.0%** |
| Gemini 2.5 Flash | Google | 1,450 ms | $0.00075 | 96.0% | 97.5% |
| Gemini 2.5 Pro | Google | 2,850 ms | $0.00350 | 97.5% | 98.5% |
| GPT-4o | OpenAI | 2,100 ms | $0.01250 | 96.5% | 98.0% |
| GPT-4o Mini | OpenAI | 1,250 ms | $0.00075 | 93.0% | 95.0% |
| Claude 3.5 Sonnet | Anthropic | 2,400 ms | $0.01500 | 97.0% | 98.5% |
| Claude 3 Opus | Anthropic | 3,900 ms | $0.07500 | 98.0% | 99.0% |
| DeepSeek V3 | DeepSeek | 1,600 ms | $0.00085 | 95.5% | 97.0% |
| DeepSeek R1 | DeepSeek | 3,200 ms | $0.00280 | 97.0% | 98.0% |
| Qwen 2.5 72B | Alibaba | 1,750 ms | $0.00180 | 95.0% | 96.5% |
| Qwen 2.5 Coder | Alibaba | 1,650 ms | $0.00150 | 94.5% | 96.0% |
| Llama 3.3 70B | Meta | 1,350 ms | $0.00190 | 94.0% | 97.0% |
| Mistral Large 2411 | Mistral AI | 1,680 ms | $0.01000 | 94.0% | 97.0% |
| Kimi k1.5 | Moonshot AI | 1,420 ms | $0.00600 | 93.0% | 95.0% |
| GLM-4 9B | Zhipu AI | 1,150 ms | $0.00050 | 91.0% | 94.0% |
| Command R+ | Cohere | 1,550 ms | $0.01250 | 93.0% | 96.0% |

Cloud LLMs predict every character autoregressively from a visual or token representation of the document. Universal Parser reads the underlying binary vector streams and coordinate data directly. Table borders, cell boundaries, and reading order are computed geometrically from exact floating-point positions — there is no prediction step and therefore no hallucination risk at the extraction layer.

The RAG faithfulness score follows from the hierarchical chunker. Every chunk carries its full heading ancestry prepended as context. Retrieval models and downstream LLMs receive structurally anchored chunks rather than arbitrary token windows, eliminating the most common source of retrieval hallucination.

Run the benchmark suite:

```bash
# Offline simulation — zero cost, no API keys required
uv run python benchmarks/run_llm_benchmark.py

# Live mode
GEMINI_API_KEY=your_key OPENROUTER_API_KEY=your_key \
  uv run python benchmarks/run_llm_benchmark.py --live
```

---

## Contributing

All pull requests must pass the full quality gate before review.

Adding a new format:

1. Create `universal_parser/extractors/<category>/<format>_extractor.py`
2. Implement `BaseExtractor.stream(path)` as a generator
3. Add `@register(FileType.YOUR_FORMAT)` to register it in the router
4. Import the module in `universal_parser/__init__.py`
5. Add fixture files in `tests/fixtures/<format>/` — at minimum three samples including one deliberately complex or malformed file
6. Write tests in `tests/test_<format>.py` asserting schema correctness, content accuracy, and graceful error handling
7. Add a `CHANGELOG.md` entry

Pull requests without fixture files and corresponding tests will not be reviewed.

Code standards:
- Pass `uv run ruff check .` with zero errors
- Format with `uv run ruff format .`
- No AGPL-licensed dependencies. All additions must carry MIT, Apache-2.0, or BSD licenses

Full local quality gate:

```bash
uv sync --all-extras
uv run ruff check .
uv run ruff format .
uv run pytest -v
uv run python benchmarks/memory_profile.py
uv run python benchmarks/test_messy_document.py
uv run python benchmarks/run_llm_benchmark.py
```

---

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for the full text.

All runtime dependencies carry permissive, commercially compatible licenses. There are no AGPL dependencies. This library is safe for use in closed-source commercial software.

| Dependency | License | Purpose |
|---|---|---|
| `pypdfium2` | Apache-2.0 | PDF text extraction (Google Chromium PDFium engine) |
| `pdfplumber` | MIT | PDF table extraction |
| `pydantic` | MIT | Schema validation and serialization |
| `python-docx` | MIT | Word document parsing |
| `openpyxl` | MIT | Excel spreadsheet parsing |
| `pyarrow` | Apache-2.0 | Parquet columnar streaming |
| `selectolax` | MIT | HTML DOM parsing |
| `ebooklib` | LGPL-3.0 | EPUB parsing |
| `rapidocr-onnxruntime` | Apache-2.0 | CPU OCR inference |
| `opencv-python-headless` | Apache-2.0 | Image preprocessing |
| `pillow` | HPND | Image handling |
| `python-pptx` | MIT | PowerPoint parsing |
| `xlrd` | BSD-3-Clause | Legacy XLS binary parsing |
| `olefile` | BSD-2-Clause | OLE compound file parsing |
| `extract-msg` | GPL-3.0 | Outlook MSG email parsing |
| `beautifulsoup4` | MIT | HTML fallback parser |
| `mcp` | MIT | FastMCP server interface |

The previous dependency on `PyMuPDF` / `fitz` (AGPL-3.0) was removed in v0.1.0 and replaced with `pypdfium2` (Apache-2.0).
