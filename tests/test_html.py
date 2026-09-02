from pathlib import Path

from universal_parser.core.engine import parse
from universal_parser.core.schema import Document

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "html"


def test_html_returns_document():
    html_path = FIXTURES_DIR / "sample.html"
    doc = parse(html_path)
    assert isinstance(doc, Document)
    assert doc.metadata.file_type == "html"
    assert len(doc.content_tree) >= 3


def test_html_structure():
    html_path = FIXTURES_DIR / "sample.html"
    doc = parse(html_path)

    # Heading
    h1 = doc.content_tree[0]
    assert h1.type == "heading"
    assert h1.level == 1
    assert "Welcome" in (h1.text or "")

    # Paragraph
    p = doc.content_tree[1]
    assert p.type == "paragraph"

    # Table
    table = next(e for e in doc.content_tree if e.type == "table")
    assert table.data is not None
    assert table.data.headers == ["Format", "Speed"]