from pathlib import Path

from universal_parser.core.engine import parse
from universal_parser.core.schema import Document

FIXTURES_JSON = Path(__file__).parent / "fixtures" / "json"
FIXTURES_XML = Path(__file__).parent / "fixtures" / "xml"


def test_tabular_json_parsing():
    json_path = FIXTURES_JSON / "sample_tabular.json"
    doc = parse(json_path)
    assert isinstance(doc, Document)
    assert doc.metadata.file_type == "json"
    assert len(doc.content_tree) == 1

    element = doc.content_tree[0]
    assert element.type == "table"
    assert element.data is not None
    assert element.data.headers == ["id", "name", "type"]
    assert len(element.data.rows) == 3


def test_nested_json_parsing():
    json_path = FIXTURES_JSON / "sample_nested.json"
    doc = parse(json_path)
    assert isinstance(doc, Document)
    assert doc.metadata.file_type == "json"
    assert len(doc.content_tree) == 1

    element = doc.content_tree[0]
    assert element.type == "code_block"
    assert "universal-parser" in (element.text or "")
    assert "```json" in (element.markdown_repr or "")


def test_xml_parsing():
    xml_path = FIXTURES_XML / "sample.xml"
    doc = parse(xml_path)
    assert isinstance(doc, Document)
    assert doc.metadata.file_type == "xml"
    assert len(doc.content_tree) >= 2

    # Root heading
    root_element = doc.content_tree[0]
    assert root_element.type == "heading"
    assert root_element.text == "document"

    # Child elements
    title_element = doc.content_tree[1]
    assert "title:" in (title_element.text or "").lower()
