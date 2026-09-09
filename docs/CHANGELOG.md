# Changelog

All notable changes to this project are documented in this file. Entries are organized by release version and follow Semantic Versioning (https://semver.org/spec/v2.0.0.html). No dates are recorded per entry — version identifiers are the canonical references.

---

## [1.0.2]

### Release Context

Documentation and metadata release adding live Hugging Face Spaces integration links, project URLs, and comprehensive architecture specifications across the documentation suite.

### Added

- Added live Hugging Face Space interactive demo badge and links to `README.md` and `pyproject.toml` (`[project.urls]`).
- Created complete `docs/ARCHITECTURE.md` specification detailing the two-pass extraction engine, font-size percentile hierarchy, and adaptive fingerprinting.
- Created complete `docs/SCHEMA.md` field-level reference covering all Pydantic models, type constraints, and null semantics.
- Created complete `docs/ADDING_A_FORMAT.md` step-by-step contributor implementation guide for extending format coverage.
- Added UI payload safeguards and thread ceilings in `main.py` to ensure smooth browser rendering on multi-page reports.

---

## [1.0.1]

### Release Context

Maintenance release updating package documentation, PyPI metadata, and honest technical report positioning.

### Changed

- Updated README to technical report format with detailed competitive comparison against Docling, Marker, and Unstructured.
- Repositioned adaptive layout fingerprinting and template auto-tuning as the primary differentiator.
- Fixed PyPI install instructions to reflect canonical package name `universal-doc-parser`.
- Updated package description and license disclosures for complete GPL-3.0 transparency regarding optional Outlook MSG parsing (`extract-msg`).
- Optimized banner image HTML formatting for PyPI image proxy rendering compatibility.

---

## [1.0.0]

### Release Context

This is the first stable, production-ready release of universal-doc-parser. It marks the completion of the full extraction pipeline, multi-model benchmarking hub, adaptive layout fingerprinting engine, FastMCP server integration, observability telemetry infrastructure, and automated PyPI publishing via Trusted Publisher (OIDC). The library is 100% commercially permissive, zero-GPU, and verifiably bounded under 250 MB RSS at runtime.

### Added

- Multi-Model LLM Benchmark Hub with support for 15 frontier and open-weight models across nine AI provider families: Google Gemini, OpenAI GPT-4o, Anthropic Claude, DeepSeek, Alibaba Qwen, Meta Llama, Mistral AI, Moonshot Kimi, Zhipu GLM, and Cohere.
- Full offline benchmark simulation mode for cost-free provider comparison without API keys.
- Live benchmark mode supporting OpenRouter API and direct Google Gemini API connections with automatic cost estimation per document.
- Multi-OS and multi-Python GitHub Actions CI/CD matrix covering Ubuntu, macOS, and Windows on Python 3.11 and Python 3.12.
- Automated PyPI publishing workflow triggered on version tags via Trusted Publisher OIDC authentication (no stored secrets).
- Comprehensive production README with API reference, output schema field documentation, architecture diagrams, installation instructions, memory benchmark table, and 15-model performance comparison table.
- Full CHANGELOG moved to docs/CHANGELOG.md. Root-level file removed.
- `__version__` attribute exposed in top-level `universal_parser/__init__.py`.
- Ruff lint configuration integrated into `pyproject.toml` with E, F, I, W, and UP rule sets enforced across all source files.
- All 61 test cases passing across the full test suite on all CI platforms.

### Changed

- `pyproject.toml` version bumped to `1.0.0`.
- `requires-python` constraint raised to `>=3.11` to reflect actual runtime requirements of `mcp`, `pypdfium2`, and modern type annotation syntax.
- CI matrix narrowed from Python 3.10/3.11/3.12 to Python 3.11/3.12 after confirming Python 3.10 incompatibility with multiple dependencies.
- `uv.lock` committed to repository (previously gitignored) to guarantee reproducible dependency resolution on all CI runners.

### Fixed

- `import magic` in `sniffer.py` wrapped in try/except to prevent hard `ImportError` on Linux and macOS runners where `libmagic` was not yet installed at import time.
- `lambda` expression for sort key in `native.py` replaced with a named function to satisfy Ruff `E731` lint rule.
- Test fixture files unblocked from `.gitignore` so that all CI runner environments have access to required test data without downloading from external sources.
- CI badge URL corrected from placeholder `your-username` to the actual repository owner `Edge-Explorer`.
- PyPI badge and Python badge updated to use static shields to prevent false `package or version not found` errors during PyPI CDN propagation delay.

---

## [0.11.0]

### Release Context

This release introduces the production observability layer and the initial multi-model LLM benchmarking infrastructure. These subsystems are independent of the core extraction pipeline and add zero overhead to the hot parse path.

### Added

- Multi-model LLM benchmarking engine supporting live API connections via Google Gemini and OpenRouter, with automatic fallback to offline simulation mode.
- `BaseLLMProvider` abstract class defining the benchmark interface: `run_benchmark()`, `_live_openrouter_call()`, `_mock_evaluation()`, and `_estimate_cost()`.
- Concrete provider implementations for Gemini Flash and Pro, GPT-4o and GPT-4o Mini, Claude 3.5 Sonnet and Claude 3 Opus, and DeepSeek V3 and R1.
- Singleton `MetricsCollector` class with thread-safe lock-based event appending for ingestion telemetry.
- `ParseEventMetric` dataclass capturing file name, file type, page count, element count, duration in milliseconds, whether OCR was triggered, and a list of detected anomalies.
- `export_dashboard()` function producing a standalone, self-contained HTML file with inline JavaScript and CSS for interactive visualization of ingestion telemetry — no external CDN dependencies.

---

## [0.10.0]

### Release Context

This release introduces the adaptive layout fingerprinting subsystem, which enables document template registration and parameter caching for repeating document structures such as invoices, financial reports, and regulatory filings.

### Added

- `compute_fingerprint(doc)` function producing a content-agnostic `LayoutFingerprint` from a `Document` by quantizing element bounding boxes into a 10x10 spatial occupancy grid normalized to 612x792 pt coordinate space, combined with element type distribution proportions, all hashed with SHA-256.
- `TemplateConfigCache` class implementing a thread-safe LRU cache mapping SHA-256 fingerprint digests to extractor configuration dictionaries, with exact hash lookup, fuzzy Cosine-Jaccard similarity lookup (configurable threshold, default 0.85), and atomic JSON disk persistence.
- `auto_tune()` function implementing a coordinate-descent optimizer over the extractor parameter space (column threshold, table density cutoff, heading percentile thresholds) with mathematical guardrails against degenerate convergence.

---

## [0.9.0]

### Release Context

This release integrates the Model Context Protocol (MCP) server, making the universal parser directly accessible as a tool to Claude Desktop, Cursor, and any agent framework that supports MCP over stdio.

### Added

- FastMCP server implementation exposing two tools over the stdio protocol: `parse_document(file_path, output_format)` accepting `markdown`, `chunks`, or `json` as output modes, and `list_supported_formats()` returning the full sorted format registry.
- `run_server()` entry point for starting the server from a module invocation (`python -m universal_parser.mcp.server`).
- Claude Desktop JSON configuration block documented in README.

---

## [0.8.0]

### Release Context

This release introduces the full downstream export layer for RAG pipeline integration and knowledge graph construction.

### Added

- `to_markdown(doc)` function converting any `Document` to a single GitHub-Flavored Markdown string with native heading depth rendering and pipe-table syntax for table elements.
- `to_chunks(doc, max_tokens, overlap_tokens)` hierarchical token-aware chunker that tracks the active H1/H2/H3 ancestor stack across elements, prepends the heading ancestry path as context to each chunk, and keeps table elements intact within a single chunk wherever the token budget allows.
- `Chunk` dataclass with fields: `chunk_id`, `text`, `headings`, `element_types`, `page_numbers`, and `estimated_tokens`.
- `to_graph(doc)` function producing a lightweight knowledge graph with entity nodes and containment and co-occurrence relationship edges, compatible with NetworkX and standard graph database import formats.

---

## [0.7.0]

### Release Context

This release establishes the streaming generator architecture and verifies the memory consumption guarantee.

### Added

- Generator-driven page-by-page streaming pipeline ensuring that no more than one page of a document is held in memory at any point during extraction.
- `memory_profile.py` benchmark script generating synthetic 1,000-page documents and asserting that peak RSS memory consumption remains strictly below 250 MB throughout the extraction process.

---

## [0.6.0]

### Release Context

This release adds two format families that require OLE compound binary container parsing and slide-based content extraction.

### Added

- OLE compound binary format extractor using `olefile` for container traversal and `xlrd` for Excel binary stream decoding, covering legacy `.doc`, `.xls`, and `.ppt` formats with recursive embedded asset unpacking and re-routing through the main parser.
- PowerPoint `.pptx` slide-by-slide shape, table, and title extractor using `python-pptx`, preserving slide order and shape reading order within each slide.

---

## [0.5.0]

### Release Context

This release adds the email format family with full recursive attachment handling.

### Added

- Email extractor covering `.eml` and `.mbox` formats using the Python standard library `email` module with header metadata extraction, body decoding, and recursive embedded attachment detection and re-routing.
- Outlook `.msg` extractor using `extract-msg` for binary compound email stream decoding with equivalent recursive attachment handling.

---

## [0.4.0]

### Release Context

This release adds the OCR fallback pipeline for scanned documents and raster image sources.

### Added

- OCR fallback module using RapidOCR on the ONNXRuntime CPU backend, triggered automatically when a PDF page yields zero extractable characters from the PDFium character map.
- OpenCV-based image preprocessing pipeline including auto-orientation correction, deskew using Hough line detection, bilateral noise filtering, and adaptive thresholding applied before passing each page image to the OCR engine.
- Raster image extractor supporting `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`, and `.webp` as standalone formats, routing through the same OCR pipeline.

---

## [0.3.0]

### Release Context

This release substantially broadens the supported format surface by adding web, ebook, and structured data extractors.

### Added

- HTML and XHTML extractor using the `selectolax` Lexbor DOM parser for high-performance tree traversal with `beautifulsoup4` as a fallback for complex or malformed markup, with heading hierarchy reconstruction from semantic heading elements.
- EPUB extractor using `ebooklib` for spine-ordered chapter traversal with each chapter's HTML content routed through the HTML sub-extractor.
- CSV and TSV extractor using the Python standard library `csv.Sniffer` for automatic dialect detection including delimiter, quote character, and line terminator.
- Parquet extractor using `pyarrow` for zero-copy columnar record batch streaming without loading the full dataset into memory.
- JSON extractor performing recursive tree flattening with normalized schema mapping.
- XML extractor traversing the element tree and mapping tag names and text content to normalized schema elements.

---

## [0.2.0]

### Release Context

This release adds the full table extraction subsystem built on top of the PDF extractor, implementing two complementary strategies for bordered and borderless tables.

### Added

- Lattice table detection using `pdfplumber` cell boundary detection over explicit ruling line segments for tables with visible borders.
- Stream table detection using whitespace column alignment for borderless tables, with a cell word-density heuristic (`avg_words_per_cell <= 2.5`) and a table height ratio constraint (`table_h <= 0.40 * page_h`) to suppress false positive detection on paragraph-heavy text blocks.
- Confidence score assignment for extracted tables based on cell structural uniformity and regularity.
- Table extraction operates as Pass 1 of the two-pass PDF extraction pipeline, with the results used to mask table regions from the Pass 2 text and heading extraction.

---

## [0.1.0]

### Release Context

This is the initial release establishing the core architecture, primary PDF extraction engine, and initial Office document extractors. All AGPL dependencies are removed and replaced with permissively licensed alternatives.

### Added

- Magic-byte MIME detection via `python-magic` (Windows: `python-magic-bin`, Linux/macOS: `python-magic`) with file extension fallback for environments where the system `libmagic` library is unavailable.
- Extractor routing registry using a `@register` decorator pattern to map `FileType` enum values to extractor classes at import time without requiring explicit configuration.
- Unified Pydantic v2 output schema: `Document`, `DocumentMetadata`, `Element`, `BBox`, and `TableData`.
- Native PDF text extraction via `pypdfium2` (Apache-2.0, Google Chromium PDFium engine) with multi-column spatial clustering using bounding box centroid partitioning at the page midpoint, font-size percentile heading hierarchy computation (P95=H1, P85=H2, P75=H3), and parent ID linking via a live heading ancestor stack.
- Word `.docx` extractor using `python-docx` with heading style name to heading level mapping and table cell normalization.
- Excel `.xlsx` extractor using `openpyxl` in read-only mode with merged-cell span value replication.
- Complete removal of `PyMuPDF` (AGPL-3.0) and replacement with `pypdfium2` (Apache-2.0) and `pdfplumber` (MIT). All remaining runtime dependencies confirmed as MIT, Apache-2.0, BSD-2-Clause, or BSD-3-Clause licensed.
