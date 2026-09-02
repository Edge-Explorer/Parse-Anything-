from pathlib import Path

import pytest
from ebooklib import epub

from universal_parser.core.engine import parse
from universal_parser.core.schema import Document


@pytest.fixture
def temp_epub_file(tmp_path: Path) -> Path:
    """Generate a valid EPUB file for testing."""
    file_path = tmp_path / "sample.epub"

    book = epub.EpubBook()
    book.set_title("Test Ebook")
    book.set_language("en")

    # Chapter 1
    c1 = epub.EpubHtml(title="Chapter 1", file_name="chap_1.xhtml")
    c1.set_content("<h1>Chapter 1: Introduction</h1><p>Welcome to EPUB parsing.</p>")
    book.add_item(c1)

    # Required EPUB navigation items & spine
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", c1]

    epub.write_epub(str(file_path), book)
    return file_path


def test_epub_returns_document(temp_epub_file: Path):
    doc = parse(temp_epub_file)
    assert isinstance(doc, Document)
    assert doc.metadata.file_type == "epub"
    assert len(doc.content_tree) >= 2


def test_epub_structure(temp_epub_file: Path):
    doc = parse(temp_epub_file)

    h1 = doc.content_tree[0]
    assert h1.type == "heading"
    assert h1.level == 1
    assert "Chapter 1" in (h1.text or "")

    p = doc.content_tree[1]
    assert p.type == "paragraph"
    assert "Welcome" in (p.text or "")