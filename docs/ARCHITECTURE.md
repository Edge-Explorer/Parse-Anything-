# Architecture and System Design

This document provides a comprehensive technical overview of `universal-doc-parser`. It details the internal data structures, algorithms, subsystem boundaries, and design rationales governing the document ingestion engine.

---

## 1. High-Level System Architecture

The parser follows a multi-stage, generator-driven pipeline designed for deterministic memory consumption (<250 MB RSS) and zero cloud API dependency.

```
+-----------------------------------------------------------------------------------+
|                                  Input Document                                   |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        Stage 1: Sniffer (MIME & Byte Detection)                   |
|  - Magic byte inspection via python-magic (optional OS fallback)                  |
|  - Extension-based disambiguation and normalization                               |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        Stage 2: Router & Extractor Registry                       |
|  - Maps FileType enum to registered BaseExtractor subclass                        |
|  - Dynamic registry populated via @register decorators                            |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                    Stage 3: Streaming Extractor Execution                         |
|  - Yields Element generator stream page-by-page / record-by-record                |
|  - PDF: 2-Pass Table Extraction -> Font Percentile Headings -> Column Order       |
|  - Office / Compound: Recursive embedded asset unpacker                           |
|  - Scanned / Image: RapidOCR ONNX CPU inference with deskewing                    |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                     Stage 4: Normalizer & Tree Assembler                          |
|  - UUID v4 assignment for document and elements                                   |
|  - Heading ancestry stack: links child paragraphs/tables to nearest parent_id     |
|  - Pydantic v2 strict schema validation                                           |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        Stage 5: Downstream Export Layer                           |
|  - to_markdown(): Pre-rendered GFM Markdown                                       |
|  - to_chunks(): Hierarchical token-budgeted chunks with breadcrumb ancestry       |
|  - to_graph(): Knowledge graph nodes and edges for GraphRAG                       |
|  - FastMCP Server: Stdio tool interface for AI agents                             |
+-----------------------------------------------------------------------------------+
```

---

## 2. Core Ingestion Pipeline

### 2.1 Sniffer (`universal_parser/core/sniffer.py`)
File identification relies on a multi-tier sniffing strategy:
1. **Magic Bytes:** Reads the initial 2048 bytes of the file stream using `python-magic` to inspect file signatures (e.g., `%PDF-`, `PK\x03\x04`, `\xD0\xCF\x11\xE0`).
2. **Ambiguity Resolution:** For plain text containers (where MIME is `text/plain` or `text/csv`), the file extension is evaluated against `_EXT_MAP` to disambiguate CSV, TSV, JSON, and XML.
3. **Graceful Fallback:** If `python-magic` or `libmagic` is unavailable at the OS level, sniffing safely defaults to extension mapping without raising exceptions. Unrecognized formats return `FileType.UNKNOWN`.

### 2.2 Router (`universal_parser/core/router.py`)
The router maintains an in-memory mapping of `FileType -> type[BaseExtractor]`. Extractors register themselves using the `@register` decorator upon module import. This decouples individual parser implementations from the core dispatch loop.

### 2.3 Streaming Generator Pipeline (`universal_parser/core/engine.py`)
Every extractor implements `BaseExtractor.stream(path: Path) -> Iterator[Element]`. Memory consumption remains bounded because elements are yielded lazily as individual pages or records are processed, rather than assembling the entire document in memory.

---

## 3. PDF Extraction Subsystem

PDF documents represent the highest layout complexity. The PDF engine in `universal_parser/extractors/pdf/` uses a cooperative multi-pass strategy:

```
PDF Page Stream
       |
       +---> Pass 1: Table Extraction (PDFTableExtractor)
       |       |-- Lattice Strategy: Explicit horizontal/vertical vector lines
       |       |-- Stream Strategy: Whitespace column clustering with density guardrails
       |       +-> Computes Table Bounding Boxes
       |
       +---> Pass 2: Native Text Extraction (pypdfium2 / pdfplumber)
       |       |-- Filters out words falling inside Table Bounding Boxes
       |       |-- Computes font size percentiles (H1: >=95th, H2: >=85th, H3: >=75th)
       |       |-- Column Band Clustering: partitions into Left, Right, Full-Width bands
       |       +-> Orders elements in natural reading sequence
       |
       +---> Scanned Fallback (if 0 text characters found)
               +-> RapidOCR ONNX inference on CPU at 200 DPI with deskew preprocessing
```

### 3.1 Two-Pass Table Extraction (`tables.py`)
1. **Lattice Strategy:** Identifies bordered tables by analyzing intersecting vector ruling lines using explicit coordinate snap and join tolerances (`snap_tolerance=3`, `join_tolerance=3`). Confidence is scored at `0.95+`.
2. **Stream Strategy:** Identifies borderless tables using whitespace gaps and text alignment. False positives (such as multi-column paragraphs) are suppressed using two mathematical constraints:
   - **Word Density Constraint:** Average words per non-empty cell must be $\le 2.5$. If cells contain paragraph sentences, the candidate table is rejected.
   - **Height Ratio Constraint:** The table bounding box must not exceed 40% of the total page height ($table\_h \le 0.40 \times page\_h$).

### 3.2 Font-Size Percentile Hierarchy (`native.py`)
Rather than relying on brittle hardcoded point sizes (e.g. `size > 14`), the parser samples the font size distribution across the document and calculates empirical percentiles:
- **H1 (Top-level Title):** $\ge 95\text{th percentile}$ (guaranteed $\ge \text{median} + 3.0\text{pt}$)
- **H2 (Section Header):** $\ge 85\text{th percentile}$ (guaranteed $\ge \text{median} + 1.5\text{pt}$)
- **H3 (Subsection Header):** $\ge 75\text{th percentile}$ (guaranteed $\ge \text{median} + 0.5\text{pt}$)
- **Paragraphs / Body Text:** All remaining text below the 75th percentile.

### 3.3 Multi-Column Reading Order Reconstruction (`native.py`)
Elements are partitioned spatially relative to the page horizontal midpoint ($X_{\text{mid}} = \frac{\text{page\_width}}{2}$):
1. **Full-Width Header Zone:** Spans with bounding box width $> 0.70 \times \text{page\_width}$ appearing near the top are yielded first.
2. **Left Column:** Elements where $x_1 \le X_{\text{mid}} + 15\text{pt}$, sorted top-to-bottom ($y_0$).
3. **Right Column:** Elements where $x_0 \ge X_{\text{mid}} - 15\text{pt}$, sorted top-to-bottom ($y_0$).
4. **Full-Width Footer Zone:** Full-width elements at the bottom of the page.

---

## 4. Adaptive Layout Fingerprinting Subsystem (`universal_parser/adaptive/`)

In recurring document workflows (invoices, tax forms, financial 10-K filings), identical templates are ingested repeatedly. The adaptive subsystem enables self-tuning parameter caching for recurring document structures.

```
Document Bounding Boxes
          |
          v
[ Spatial Grid Quantization ] -> 10x10 Content-Agnostic Occupancy Matrix
          |
          v
[ SHA-256 Fingerprint Hash ]  -> Hex Digest + Spatial Histogram
          |
          v
[ TemplateConfigCache ]       -> Exact Match OR Fuzzy Cosine-Jaccard Lookup (Threshold >= 0.85)
          |
          v
[ Auto-Tuned Extractor Config ] -> Injects optimal column/table thresholds into extractor
```

1. **Fingerprinter (`fingerprint.py`):** Normalizes all element coordinates to a reference 612x792 pt coordinate space and quantizes them into a 10x10 binary spatial occupancy grid. Combines the spatial grid with element type distribution proportions and hashes the payload with SHA-256.
2. **Configuration Cache (`config_cache.py`):** Thread-safe LRU cache with atomic JSON disk persistence. Supports exact SHA-256 lookup and fuzzy Cosine-Jaccard similarity matching for documents with minor layout shifts.
3. **Auto-Tuner (`tuner.py`):** Uses coordinate descent optimization against reference ground-truth data to automatically discover optimal extraction parameters (such as column split boundaries and table tolerances) without manual configuration.

---

## 5. Downstream RAG & Export Subsystem

### 5.1 Hierarchical Chunking (`universal_parser/exports/to_chunks.py`)
Standard token-window chunking slices text arbitrarily, splitting paragraphs and losing title context. The hierarchical chunker:
- Accumulates elements while respecting a configurable token budget (`max_tokens`, default 512).
- Prepends full heading ancestry to every chunk: `Context: Executive Summary > Financial Results\n\n{text}`.
- Keeps tables intact within a single chunk whenever budget permits.

### 5.2 Knowledge Graph Generator (`universal_parser/exports/to_graph.py`)
Generates GraphRAG-compatible nodes and edges:
- **Document Root Node:** Links metadata properties.
- **Section Nodes:** Represents headings with hierarchical `CONTAINS_SECTION` edges.
- **Content Nodes:** Paragraphs and tables linked to parent sections via `CONTAINS` edges and sequenced via `FOLLOWS` edges.

---

## 6. Observability and FastMCP Integration

1. **Telemetry Collector (`universal_parser/observability/metrics.py`):** Thread-safe singleton capturing parsing latency, element distributions, scanned page occurrences, and structural anomalies per invocation. Exports standalone interactive HTML dashboards.
2. **FastMCP Server (`universal_parser/mcp/server.py`):** Exposes `parse_document` and `list_supported_formats` tools over stdio for Claude Desktop, Cursor, and agent frameworks.