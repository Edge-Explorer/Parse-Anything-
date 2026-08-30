from pathlib import Path

import pytest

from universal_parser.core.engine import parse
from universal_parser.core.schema import Document, Element

FIXTURE = Path(__file__).parent / "fixtures" / "docx" / "sample.docx"


def test_docx_fixture_exists():
    assert FIXTURE.exists(), f"Missing fixture: {FIXTURE}"


def test_docx_returns_document():
    doc = parse(FIXTURE)
    assert isinstance(doc, Document)


def test_docx_metadata():
    doc = parse(FIXTURE)
    assert doc.metadata.file_name == "sample.docx"
    assert doc.metadata.file_type == "docx"
    assert doc.schema_version == "1.0"


def test_docx_has_content():
    doc = parse(FIXTURE)
    assert len(doc.content_tree) > 0


def test_docx_elements_are_valid():
    doc = parse(FIXTURE)
    for element in doc.content_tree:
        assert isinstance(element, Element)
        assert element.type in (
            "heading",
            "paragraph",
            "table",
            "figure",
            "list_item",
            "code_block",
        )


def test_docx_missing_file():
    with pytest.raises(FileNotFoundError):
        parse(Path("does_not_exist.docx"))
