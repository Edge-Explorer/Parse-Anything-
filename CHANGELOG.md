# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-09-08

### Added
- Multi-Model LLM Benchmark Hub supporting 15 frontier and open-weight models across Google Gemini, OpenAI GPT-4o, Anthropic Claude, DeepSeek, Alibaba Qwen, Meta Llama, Mistral AI, Moonshot Kimi, Zhipu GLM, and Cohere.
- Full multi-OS (Ubuntu, macOS, Windows) and multi-Python (3.10, 3.11, 3.12) GitHub Actions CI/CD matrix.
- Automated PyPI publishing workflow on tagged releases.
- Comprehensive production documentation, quickstart examples, architecture specifications, and benchmark comparison matrices in README.md.

## [0.11.0] - 2026-09-08

### Added
- Multi-model LLM benchmarking engine supporting live Google Gemini API and OpenRouter API connections with automated offline simulation fallback.
- Real-time observability telemetry system (`MetricsCollector`) tracking ingestion latency, page volume, element counts, and anomaly markers.
- Standalone interactive HTML/CSS telemetry and drift dashboard export (`export_dashboard()`).

## [0.10.0] - 2026-09-08

### Added
- Content-agnostic 2D spatial histogram discretization ($10 \times 10$ grid) for layout fingerprinting.
- Hybrid Cosine-Jaccard layout similarity scoring engine.
- Thread-safe LRU template configuration cache with exact SHA-256 and fuzzy matching persistence.
- Coordinate-descent heuristic auto-tuning optimizer with mathematical guardrails.

## [0.9.0] - 2026-09-08

### Added
- FastMCP server implementation over stdio protocol exposing `parse_document` and `list_supported_formats`.

## [0.8.0] - 2026-09-08

### Added
- Downstream RAG exports: clean Markdown formatter, hierarchical chunking with parent-heading breadcrumb context injection, and Graphviz/NetworkX knowledge graph export.

## [0.7.0] - 2026-09-08

### Added
- Generator-driven streaming pipeline and memory profiling verifying strictly under 250 MB RSS footprint across 1,000+ page documents.

## [0.6.0] - 2026-09-08

### Added
- OLE compound binary format extractor for legacy `.doc`, `.xls`, `.ppt` files with recursive embedded asset unpacking.
- PowerPoint `.pptx` slide shape, table, and hierarchy parser.

## [0.5.0] - 2026-09-08

### Added
- Email parser for `.eml`, `.msg`, and `.mbox` formats with recursive attachment extraction and routing.

## [0.4.0] - 2026-09-08

### Added
- Optical Character Recognition (OCR) module with RapidOCR (ONNXRuntime CPU) and OpenCV auto-orientation, deskew, and preprocessing.

## [0.3.0] - 2026-09-08

### Added
- Web and structured data extractors: HTML/XHTML via `selectolax`, EPUB, CSV/TSV with dialect auto-detection, columnar Parquet via `pyarrow`, and JSON/XML.

## [0.2.0] - 2026-09-08

### Added
- Dual-mode table extraction: Lattice and Stream table extraction with cell-density and dimensional boundary constraints.

## [0.1.0] - 2026-09-08

### Added
- Core architecture: magic-byte sniffing, extractor routing registry, and unified Pydantic schema.
- Native PDF extraction via `pypdfium2` with multi-column clustering and font-size percentile heading hierarchy.
- Word `.docx` and Excel `.xlsx` streaming extractors.
- Complete replacement of AGPL dependencies with 100% permissively licensed components.
