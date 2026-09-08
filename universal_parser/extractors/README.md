# universal_parser.extractors

The `extractors` package is the format-specific parsing layer of Universal Parser. Each sub-package in this directory is responsible for reading a single family of file formats and converting their raw binary or text content into a uniform stream of `Element` objects defined by `universal_parser.core.schema`. The extractors exist as a separate layer so that the core engine (`universal_parser.core`) remains completely format-agnostic: adding support for a new file format requires only creating a new extractor class and registering it — nothing in the core routing, schema, or export layers needs to change.

The package is intentionally structured so that each extractor sub-package maps to one conceptual document category: PDF files, Microsoft Office documents, raster images, email messages, structured data files, and web/markup formats. This grouping makes it straightforward to audit dependencies, add format variants, or swap underlying parsing libraries without touching unrelated code.

---

## Directory Structure

| Path | Type | Purpose |
|---|---|---|
| `__init__.py` | File | Empty package marker; no public re-exports at this level |
| `base.py` | File | `BaseExtractor` abstract class that every concrete extractor must inherit from |
| `pdf/` | Package | Native and OCR-assisted PDF extraction (`NativePDFExtractor`) |
| `office/` | Package | Microsoft Office formats: DOCX, PPTX, XLSX, and legacy DOC/XLS/PPT |
| `images/` | Package | Raster image OCR extraction via RapidOCR ONNX (`ImageScanExtractor`) |
| `mail/` | Package | Email formats: EML, MSG, MBOX with recursive attachment handling |
| `structured/` | Package | Structured data: CSV, TSV, JSON, XML, Parquet |
| `web/` | Package | HTML and EPUB markup extraction via selectolax |

---

## File Reference

| Filename | Purpose | Key Exported Class / Function |
|---|---|---|
| `__init__.py` | Package marker | — |
| `base.py` | Abstract contract for all extractors | `BaseExtractor` |

---

## Technical Details

### BaseExtractor (`base.py`)

`BaseExtractor` is the single abstract class that every extractor in this package must subclass. It imposes two structural requirements on all implementations.

**`supported_types`** is a `ClassVar[list[FileType]]` that declares which MIME/format identifiers the extractor handles. The router (`universal_parser.core.router`) reads this attribute at registration time to build its dispatch table. When `parse()` is called with a file, the sniffer identifies the `FileType`, and the router looks up the matching extractor by scanning all registered `supported_types` lists. An extractor can declare support for multiple types (e.g., `LegacyOfficeExtractor` covers `DOC`, `XLS`, and `PPT`).

**`stream(path)`** is the sole abstract method. It accepts either a `str` or `pathlib.Path` and must return an `Iterator[Element]`. The contract, documented in the base class docstring, is strict: the method must `yield` one `Element` at a time and must never accumulate a full list of results in memory before returning. This streaming discipline is what allows the engine to process documents of arbitrary size — including 1,000-page PDFs — without exceeding a fixed memory budget. The method must also never raise a recoverable error; on encountering a malformed element, the implementation should log and skip rather than propagate an exception to the caller. If the file itself cannot be opened at all, returning immediately (an empty iterator) is the correct behavior.

**Registration** is handled by the `@register` decorator imported from `universal_parser.core.router`. Any class decorated with `@register` that inherits from `BaseExtractor` is automatically inserted into the router's dispatch table on import. This means the engine never needs an explicit mapping file; importing the extractor module is sufficient.

### Adding a New Extractor

To add support for a new file format:

1. Create a new file (or sub-package) under `universal_parser/extractors/`.
2. Define a class that inherits from `BaseExtractor` and applies `@register`.
3. Set `supported_types` to include the relevant `FileType` enum member(s).
4. Implement `stream()` to yield `Element` objects in reading order.
5. Import the new module anywhere that causes it to be loaded before `parse()` is called — typically in the package's `__init__.py` or in `universal_parser/core/engine.py`.

---

## Code Examples

### Implementing a minimal extractor

```python
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

from universal_parser.core.router import register
from universal_parser.core.schema import Element
from universal_parser.core.sniffer import FileType
from universal_parser.extractors.base import BaseExtractor


@register
class PlainTextExtractor(BaseExtractor):
    supported_types: ClassVar[list[FileType]] = [FileType.TXT]

    def stream(self, path: str | Path) -> Iterator[Element]:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    text = line.strip()
                    if text:
                        yield Element(type="paragraph", text=text)
        except Exception:
            return
```

### Using an extractor directly (bypassing the engine)

```python
from pathlib import Path
from universal_parser.extractors.pdf.native import NativePDFExtractor

extractor = NativePDFExtractor()
for element in extractor.stream(Path("report.pdf")):
    print(element.type, element.text)
```

### Using the engine (recommended path)

```python
from universal_parser.core.engine import parse

doc = parse("report.pdf")
for element in doc.content_tree:
    print(element.type, element.text)
```

---

## Design Invariants

- Every extractor must be side-effect free with respect to the file it reads. It must not modify or delete the source file.
- Extractors must not cache state between `stream()` calls. Each call is a fresh parse.
- `stream()` must close all file handles and external resources in a `finally` block, even when the caller stops consuming the iterator early.
- `confidence` values on yielded `Element` objects range from `0.0` to `1.0`. Native text extraction sets `confidence=1.0` implicitly; OCR-derived elements carry the raw model confidence score.
