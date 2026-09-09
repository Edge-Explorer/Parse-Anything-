# Adding a New Document Format

This guide walks contributors and integrators through the complete process of adding support for a new document format to `universal-doc-parser`.

The architecture uses a decoupled Registry and Strategy pattern: adding a new format requires implementing a single extractor class and registering it with a decorator. The core engine, validation layer, and export pipelines require zero modifications.

---

## Prerequisites and Design Constraints

Before implementing a new extractor:

1. **Permissive Licensing Only:** Any third-party library introduced must be licensed under MIT, Apache-2.0, or BSD. AGPL-licensed dependencies are strictly prohibited.
2. **Streaming Execution:** Extractors must yield `Element` objects incrementally via Python generators (`yield`). Do not buffer entire multi-gigabyte files in RAM.
3. **Graceful Failure:** Extractors must never leak raw third-party library exceptions. Catch library-specific errors and raise standard `ValueError` with descriptive diagnostic messages.
4. **No GPU Requirement:** All parsing logic must execute on CPU within the bounded memory envelope (<250 MB RSS).

---

## Step-by-Step Implementation Guide

### Step 1: Declare the Format in the Sniffer

Open `universal_parser/core/sniffer.py`:

1. Add your format to the `FileType` enum:
   ```python
   class FileType(Enum):
       # ... existing types ...
       MARKDOWN = auto()  # Example: adding Markdown support
   ```

2. Add extension mappings to `_EXT_MAP`:
   ```python
   _EXT_MAP: dict[str, FileType] = {
       # ...
       ".md": FileType.MARKDOWN,
       ".markdown": FileType.MARKDOWN,
   }
   ```

3. If the format has standard MIME types, add them to `_MIME_MAP`:
   ```python
   _MIME_MAP: dict[str, FileType] = {
       # ...
       "text/markdown": FileType.MARKDOWN,
       "text/x-markdown": FileType.MARKDOWN,
   }
   ```

---

### Step 2: Implement the Extractor Class

Create a new module in the appropriate category subdirectory under `universal_parser/extractors/`:

- `universal_parser/extractors/pdf/`
- `universal_parser/extractors/office/`
- `universal_parser/extractors/images/`
- `universal_parser/extractors/structured/`
- `universal_parser/extractors/web/`
- `universal_parser/extractors/mail/`

Create `universal_parser/extractors/structured/markdown_extractor.py`:

```python
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

from universal_parser.core.router import register
from universal_parser.core.schema import BBox, Element
from universal_parser.core.sniffer import FileType
from universal_parser.extractors.base import BaseExtractor


@register
class MarkdownExtractor(BaseExtractor):
    """Extracts structured headings, paragraphs, and code blocks from Markdown files."""

    supported_types: ClassVar[list[FileType]] = [FileType.MARKDOWN]

    def stream(self, path: str | Path) -> Iterator[Element]:
        """Stream elements from a Markdown file line-by-line."""
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {path}")

        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                for line_idx, raw_line in enumerate(f, start=1):
                    line = raw_line.strip()
                    if not line:
                        continue

                    # Heading detection
                    if line.startswith("#"):
                        level = min(6, len(line) - len(line.lstrip("#")))
                        text = line.lstrip("#").strip()
                        yield Element(
                            type="heading",
                            level=level,
                            text=text,
                            page=1,
                        )
                    else:
                        yield Element(
                            type="paragraph",
                            text=line,
                            page=1,
                        )
        except Exception as err:
            raise ValueError(f"Failed to parse Markdown file {path.name}: {err}") from err
```

---

### Step 3: Register the Extractor in Package Initialization

Open `universal_parser/__init__.py` and add the import to ensure the `@register` decorator executes when the package loads:

```python
import universal_parser.extractors.structured.markdown_extractor  # noqa: F401
```

---

### Step 4: Add Test Fixtures

Every format requires at least three real test fixture files in `tests/fixtures/<format>/`:

1. `sample.<ext>`: Standard clean document with common features (headings, text, lists).
2. `complex.<ext>`: Complex document with nested sections, large tables, or mixed encoding.
3. `malformed.<ext>`: Deliberately broken or empty file to verify graceful error handling.

Create the directory:
```bash
tests/fixtures/markdown/
├── sample.md
├── complex.md
└── malformed.md
```

---

### Step 5: Write Unit and Integration Tests

Create `tests/test_markdown.py`:

```python
from pathlib import Path
import pytest
from universal_parser import parse, to_chunks, to_markdown
from universal_parser.core.sniffer import FileType, sniff

FIXTURES = Path(__file__).parent / "fixtures" / "markdown"


def test_markdown_sniffing():
    assert sniff(FIXTURES / "sample.md") == FileType.MARKDOWN


def test_markdown_parsing():
    doc = parse(FIXTURES / "sample.md")
    assert doc.metadata.file_type == "markdown"
    assert len(doc.content_tree) > 0

    headings = [el for el in doc.content_tree if el.type == "heading"]
    assert len(headings) >= 1
    assert headings[0].level == 1


def test_markdown_chunking():
    doc = parse(FIXTURES / "sample.md")
    chunks = to_chunks(doc, max_tokens=256)
    assert len(chunks) > 0
    assert all(c.text for c in chunks)


def test_malformed_markdown_handling():
    # Verify the parser handles empty or corrupt files without crashing
    doc = parse(FIXTURES / "malformed.md")
    assert doc is not None
```

---

### Step 6: Verify Code Quality Gates

Run the local quality checks:

```bash
# 1. Lint and format checks
uv run ruff check .
uv run ruff format .

# 2. Run full test suite
uv run pytest tests/test_markdown.py -v
uv run pytest -v

# 3. Check memory limits
uv run python benchmarks/memory_profile.py
```

---

### Step 7: Update Documentation and Changelog

1. Add your format row to the Supported Formats table in `README.md`.
2. Document the new format under the `[Unreleased]` or current release section in `docs/CHANGELOG.md`.