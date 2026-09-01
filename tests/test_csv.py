from pathlib import Path

from universal_parser.core.engine import parse
from universal_parser.core.schema import Document

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "csv"


def test_csv_returns_document():
    csv_path = FIXTURES_DIR / "sample.csv"
    doc = parse(csv_path)
    assert isinstance(doc, Document)
    assert doc.metadata.file_type == "csv"
    assert len(doc.content_tree) == 1


def test_csv_table_structure():
    csv_path = FIXTURES_DIR / "sample.csv"
    doc = parse(csv_path)
    element = doc.content_tree[0]

    assert element.type == "table"
    assert element.data is not None
    assert element.data.headers == ["Name", "Age", "Role", "Department"]
    assert len(element.data.rows) == 3
    assert element.data.rows[0] == ["Alice", "30", "Engineer", "R&D"]
    assert "|" in element.markdown_repr


def test_tsv_returns_document():
    tsv_path = FIXTURES_DIR / "sample.tsv"
    doc = parse(tsv_path)
    assert isinstance(doc, Document)
    assert doc.metadata.file_type == "tsv"
    assert len(doc.content_tree) == 1


def test_tsv_table_structure():
    tsv_path = FIXTURES_DIR / "sample.tsv"
    doc = parse(tsv_path)
    element = doc.content_tree[0]

    assert element.type == "table"
    assert element.data is not None
    assert element.data.headers == ["ID", "Item", "Price", "Stock"]
    assert len(element.data.rows) == 3
    assert element.data.rows[0] == ["101", "Laptop", "999.99", "15"]
    assert "|" in element.markdown_repr
