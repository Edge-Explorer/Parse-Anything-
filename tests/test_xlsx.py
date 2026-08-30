from pathlib import Path

import pytest

from universal_parser.core.engine import parse
from universal_parser.core.schema import Document

FIXTURE = Path(__file__).parent / "fixtures" / "xlsx" / "sample.xlsx"


def test_xlsx_fixture_exists():
    assert FIXTURE.exists(), f"Missing fixture: {FIXTURE}"


def test_xlsx_returns_document():
    doc = parse(FIXTURE)
    assert isinstance(doc, Document)


def test_xlsx_metadata():
    doc = parse(FIXTURE)
    assert doc.metadata.file_name == "sample.xlsx"
    assert doc.metadata.file_type == "xlsx"
    assert doc.schema_version == "1.0"


def test_xlsx_has_content():
    doc = parse(FIXTURE)
    assert len(doc.content_tree) > 0


def test_xlsx_elements_are_tables():
    """Every element from an Excel file must be of type table."""
    doc = parse(FIXTURE)
    for element in doc.content_tree:
        assert element.type == "table"
        assert element.data is not None
        assert len(element.data.headers) > 0


def test_xlsx_markdown_repr_exists():
    """Each sheet element must have a pre-built markdown representation."""
    doc = parse(FIXTURE)
    for element in doc.content_tree:
        assert element.markdown_repr is not None
        assert "|" in element.markdown_repr  # basic table markdown check


def test_xlsx_missing_file():
    with pytest.raises(FileNotFoundError):
        parse(Path("does_not_exist.xlsx"))
