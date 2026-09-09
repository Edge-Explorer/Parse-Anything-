<p align="center">
  <img src="https://raw.githubusercontent.com/Edge-Explorer/Parse-Anything-/main/assets/banner.png" alt="Universal Document Parser Banner" width="800" />
</p>

# UNIVERSAL PARSER

[![CI](https://github.com/Edge-Explorer/Parse-Anything-/actions/workflows/ci.yml/badge.svg)](https://github.com/Edge-Explorer/Parse-Anything-/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/badge/PyPI-v1.0.1-blue.svg)](https://pypi.org/project/universal-doc-parser/)
[![Hugging Face Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Live%20Demo-yellow.svg)](https://huggingface.co/spaces/Karan6124/universal-doc-parser)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue.svg)](https://pypi.org/project/universal-doc-parser/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Memory: <250MB](https://img.shields.io/badge/Memory_Limit-%3C250MB_RSS-success.svg)](#memory-and-performance)

A CPU-only document ingestion engine for RAG pipelines and AI agents. Parses 15+ file formats into a unified Pydantic schema with hierarchical chunking, adaptive layout fingerprinting, and a FastMCP server interface.

**[Try the Live Interactive Demo on Hugging Face Spaces](https://huggingface.co/spaces/Karan6124/universal-doc-parser)**

No GPU. No paid API. No recurring cost.

---

## Table of Contents

- [Problem and Scope](#problem-and-scope)
- [Related Work](#related-work)
- [The One Original Contribution](#the-one-original-contribution)
- [Supported Formats](#supported-formats)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Output Schema](#output-schema)
- [API Reference](#api-reference)
- [Architecture](#architecture)
- [Adaptive Layout Fingerprinting](#adaptive-layout-fingerprinting)
- [FastMCP Server](#fastmcp-server)
- [Memory and Performance](#memory-and-performance)
- [Benchmarks](#benchmarks)
- [Limitations](#limitations)
- [Contributing](#contributing)
- [License](#license)

---

## Problem and Scope

Feeding real-world documents into a RAG pipeline is harder than it looks.

A PDF is a stream of positioned drawing commands. Reading order breaks on multi-column layouts. Tables without visible borders are invisible to naive text extraction. Scanned pages have no machine-readable text. Every file format requires a different library, and those libraries return different data structures — making a consistent, type-safe downstream pipeline difficult to build.

This library handles the extraction and normalization layer: MIME sniffing, format routing, multi-column reading order reconstruction, two-pass table detection, OCR fallback, and output to a single validated Pydantic schema — for 15+ file formats, from a single `parse(path)` call, running entirely on CPU.

It does **not** do layout model inference, deep learning-based element classification, or PDF reconstruction at the visual rendering layer. For those capabilities, see Docling.

---

## Related Work

Honest comparison with the tools a practitioner would actually evaluate before using this one.

**[Docling](https://github.com/DS4SD/docling)** (IBM Research / Linux Foundation, MIT-adjacent license)
Docling ships a trained document layout analysis model and a PDF table structure recognition model. Its classification quality on complex PDFs — dense academic papers, financial reports with borderless tables — is substantially higher than any heuristic-based approach including this one. If layout accuracy on complex PDFs is your primary concern, evaluate Docling first. It is CPU-capable and actively maintained by a funded team.

**[Marker](https://github.com/VikParuchuri/marker)** (Apache-2.0)
Marker uses a fine-tuned Surya OCR model and a layout segmentation model. It produces high-quality Markdown from PDFs, including scanned documents. Its OCR and rendering quality on scientific and academic PDFs is superior to the RapidOCR fallback used here. If your pipeline is primarily scientific PDFs, evaluate Marker first.

**[Unstructured](https://github.com/Unstructured-IO/unstructured)** (Apache-2.0, managed API available)
Unstructured supports the broadest format coverage in the space (40+ formats) with optional hi-res partition mode and a managed API. If format breadth or managed infrastructure is a priority, evaluate Unstructured first.

**Where this library differs:**

| Criterion | Docling | Marker | Unstructured | Universal Parser |
|---|---|---|---|---|
| Layout model inference | Yes (trained model) | Yes (Surya) | Optional (hi-res mode) | No (heuristics only) |
| Table structure recognition | Trained model | Limited | Optional | Heuristic (lattice + stream) |
| OCR quality | Good | Excellent | Good | Adequate (RapidOCR) |
| Format coverage | PDF, DOCX, XLSX, PPTX, HTML | PDF, images | 40+ formats | 15+ formats |
| Python version | 3.9+ | 3.9+ | 3.9+ | 3.11+ |
| Memory footprint | Moderate (model weights) | Higher (model weights) | Varies | <250 MB RSS (no model weights) |
| Per-template auto-tuning | No | No | No | Yes (see below) |
| MCP server interface | No | No | No | Yes |

The heuristic approach used here extracts less accurately on complex layouts than Docling or Marker. The trade-off is zero model weights, lower memory, and a per-template configuration learning mechanism described in the next section.

---

## The One Original Contribution

The piece of this library that does not exist in the same form in Docling, Marker, or Unstructured is the **adaptive layout fingerprinting and per-template auto-tuner**.

Many real RAG pipelines process the same document template repeatedly — the same invoice format thousands of times, the same SEC 10-K filing structure across years, the same internal report template across departments. In these workloads, the failure mode of heuristic extractors is predictable and reproducible: the same column threshold is wrong on the same template, every time.

The fingerprinter computes a content-agnostic 10x10 spatial occupancy grid from element bounding boxes, hashes it with SHA-256, and uses it as a stable template identity. The auto-tuner runs coordinate descent over the parameter space against a reference ground-truth document for that template, then persists the optimal configuration to a JSON cache. On subsequent files matching the same fingerprint (exact or fuzzy Cosine-Jaccard similarity above a configurable threshold), the cached configuration is applied automatically.

This is a focused, narrow contribution: it does not make the base extraction better than Docling on arbitrary documents. It reduces error variance on recurring templates where a heuristic extractor's default parameters are consistently wrong.

The ablation study validating this claim on a real document set is [planned and tracked here](#benchmarks).

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
| Email | EML / MBOX | `.eml`, `.mbox` | `email` stdlib with recursive embedded attachment routing |
| Email | MSG (Outlook) | `.msg` | `extract-msg` (GPL-3.0 — see license section) with recursive attachment routing |

---

## Installation

Requires Python 3.11 or later.

```bash
pip install universal-doc-parser
```

With OCR support for scanned PDFs and raster images:

```bash
pip install "universal-doc-parser[ocr]"
```

With development tooling:

```bash
pip install "universal-doc-parser[dev]"
```

Using uv:

```bash
uv add universal-doc-parser
uv add "universal-doc-parser[ocr]"
```

System dependencies on Linux (for magic-byte MIME detection — optional, falls back to extension sniffing if absent):

```bash
# Ubuntu / Debian Bookworm (Python 3.10 era containers)
sudo apt-get install -y libmagic1t64

# Ubuntu / Debian Bullseye and earlier
sudo apt-get install -y libmagic1

# Fedora / RHEL
sudo dnf install -y file-libs
```

On macOS and Windows, MIME detection is handled through the Python package layer automatically.

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

Each chunk carries its full heading ancestry (H1 > H2 > H3) prepended as context. Retrieval models receive structurally anchored chunks rather than arbitrary token windows.

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
| `level` | `int or null` | Heading depth 1-6. `null` for non-heading elements. |
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

Raises `FileNotFoundError` if the path does not exist. Raises `ValueError` for corrupt, unreadable, or unrecognized files. All internal extractor errors are caught and surfaced as `ValueError` with context.

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
- `max_tokens` - Maximum estimated tokens per chunk. Default: `512`. Estimated at approximately 4 characters per token.
- `overlap_tokens` - Reserved for future sliding window chunking.

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

**Pass 1 - Table Detection** (`extractors/pdf/tables.py`)

Two strategies are attempted in sequence:

- **Lattice:** Detects tables with visible border lines. Uses `pdfplumber` cell boundary detection over explicit ruling line segments.
- **Stream:** Detects borderless tables using whitespace column alignment. A cell word-density heuristic (`avg_words_per_cell <= 2.5`) and a table height ratio constraint (`table_h <= 0.40 * page_h`) suppress false positives on paragraph-heavy pages.

Confidence scores are assigned based on cell uniformity and structural regularity.

**Pass 2 - Text and Heading Extraction** (`extractors/pdf/native.py`)

- Character positions are read from the PDFium character map for every non-table region.
- Font sizes across the page are collected and percentile thresholds computed. Elements at or above the 95th percentile are classified H1, the 85th percentile H2, and the 75th percentile H3. All remaining text is classified as paragraphs.
- Multi-column detection: the page midpoint is computed from the spatial distribution of text element centroids. Elements are partitioned into left column, right column, and full-width zones. Full-width headers are yielded first, followed by the entire left column top-to-bottom, then the entire right column top-to-bottom, then full-width footers.
- Pages with zero extractable characters fall back to RapidOCR.

---

## Adaptive Layout Fingerprinting

Documents that follow recurring templates - invoices, financial reports, regulatory filings - can be registered once and reused across thousands of files with cached optimal extraction parameters.

**Fingerprinting** (`adaptive/fingerprint.py`)

Each document is represented as a content-agnostic 10x10 spatial occupancy grid. Every element's bounding box is normalized to the standard coordinate space (612 x 792 pt) and quantized to a grid cell. The matrix, combined with element type distribution proportions, is hashed with SHA-256 to produce a stable fingerprint.

```python
from universal_parser.adaptive import compute_fingerprint

doc = parse("invoice_template.pdf")
fp = compute_fingerprint(doc)
print(fp.hash_digest)  # SHA-256 hex string
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

The ablation study measuring extraction accuracy with auto-tuning on vs off across a real set of recurring templates is in progress and will be published here when complete with methodology and sample sizes disclosed.

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
    "universal-doc-parser": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "universal-doc-parser",
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

The numbers below are from the memory benchmark suite (`benchmarks/memory_profile.py`) running on an Intel Core i7, 16 GB RAM, no GPU. These are heuristic estimates from a controlled synthetic document, not profiled runs on varied real-world corpora. Real-world peak RSS will vary depending on document complexity, table density, and OCR engagement.

| Document Size | Peak RSS Memory | Processing Time |
|---|---|---|
| 100 pages | ~150 MB | ~5 seconds |
| 500 pages | ~165 MB | ~24 seconds |
| 1,000 pages | ~180 MB | ~49 seconds |

The 250 MB RSS hard limit is asserted in the benchmark suite on every CI push:

```bash
uv run python benchmarks/memory_profile.py
```

---

## Benchmarks

### What exists today

The benchmark suite at `benchmarks/run_llm_benchmark.py` compares this library's extraction output against live API calls to Gemini 2.5 Flash, GPT-4o, DeepSeek V3, Qwen 2.5 72B, Llama 3.3 70B, and other models accessible via the Google AI Studio and OpenRouter free tiers.

14 of the 15 rows in the original benchmark table were live API results. The two Claude rows (Claude 3.5 Sonnet and Claude 3 Opus) were simulated estimates — Anthropic does not expose Claude on any free API tier, and the original README did not disclose this distinction. Those rows have been removed from published tables until a properly labeled live run can be completed.

Run the benchmark suite yourself:

```bash
# Offline mode — simulates responses, zero cost, no API keys required
uv run python benchmarks/run_llm_benchmark.py

# Live mode — runs real API calls against Gemini and OpenRouter models
GEMINI_API_KEY=your_key OPENROUTER_API_KEY=your_key \
  uv run python benchmarks/run_llm_benchmark.py --live
```

### What is planned

The benchmark work that would make this project defensible — and which does not yet exist — is:

1. **Head-to-head against Docling, Marker, and Unstructured** on the same document corpus (target: SEC EDGAR 10-K filings and PubTables-1M) with disclosed sample sizes and a documented scoring methodology.

2. **Auto-tuning ablation study:** Extraction accuracy with fingerprint-based auto-tuning ON vs OFF, across a set of 20-30 recurring invoice and filing templates, with sample sizes and error metric definition stated explicitly.

These are the two experiments that would either validate or invalidate the claims this project is making. Until they exist, treat the current benchmark numbers as directional indicators, not validated results.

---

## Limitations

These are known failure modes, not edge cases.

- **Complex PDF layouts:** On multi-column academic papers and dense financial reports with borderless tables, Docling's trained layout model will outperform the heuristic approach used here. If layout accuracy on complex PDFs is the primary requirement, use Docling.
- **Scanned document quality:** The RapidOCR fallback performs adequately on clean scans. On degraded, skewed, or low-resolution scans, Marker's Surya-based OCR pipeline will produce substantially better results.
- **Python version requirement:** This library requires Python 3.11+, which excludes some deployment environments. Docling, Marker, and Unstructured support Python 3.9+.
- **MSG parsing license:** The `extract-msg` dependency carries a GPL-3.0 license. MSG parsing is therefore subject to GPL-3.0 copyleft terms — see the license section for the full implication.
- **Memory numbers are heuristic estimates:** The memory table above was produced from a controlled synthetic document. Real-world peak RSS will vary.
- **Benchmark numbers are not externally validated:** No one outside of the author has run the full benchmark suite on the full dataset yet. Treat published numbers accordingly.

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
7. Add a `docs/CHANGELOG.md` entry

Pull requests without fixture files and corresponding tests will not be reviewed.

Code standards:
- Pass `uv run ruff check .` with zero errors
- Format with `uv run ruff format .`
- No new AGPL-licensed dependencies. All additions must carry MIT, Apache-2.0, or BSD licenses

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

**License note on MSG support:** The `extract-msg` dependency used for Outlook `.msg` parsing is licensed under **GPL-3.0**. If you parse `.msg` files in a closed-source product, the GPL-3.0 copyleft terms apply to that use. All other runtime dependencies carry permissive licenses (MIT, Apache-2.0, BSD, LGPL-3.0). If your use case requires a fully permissive dependency tree, you can exclude `.msg` parsing by not calling `parse()` on `.msg` files and removing `extract-msg` from your installation.

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
| `extract-msg` | **GPL-3.0** | Outlook MSG email parsing -- see note above |
| `beautifulsoup4` | MIT | HTML fallback parser |
| `mcp` | MIT | FastMCP server interface |

The previous dependency on `PyMuPDF` / `fitz` (AGPL-3.0) was removed in v0.1.0 and replaced with `pypdfium2` (Apache-2.0).