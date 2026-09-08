from pathlib import Path

from universal_parser.mcp.server import list_supported_formats, parse_document

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "csv"


def test_mcp_list_supported_formats():
    formats = list_supported_formats()
    assert len(formats) >= 10
    assert "pdf" in formats
    assert "docx" in formats
    assert "xlsx" in formats
    assert "pptx" in formats
    assert "csv" in formats


def test_mcp_parse_document_markdown():
    csv_file = FIXTURES_DIR / "sample.csv"
    res = parse_document(str(csv_file), output_format="markdown")
    assert "Name" in res
    assert "|" in res


def test_mcp_parse_document_chunks():
    csv_file = FIXTURES_DIR / "sample.csv"
    res = parse_document(str(csv_file), output_format="chunks")
    assert "chunk_id" in res


def test_mcp_nonexistent_file():
    res = parse_document("nonextistent_file_123.pdf")
    assert "Error: File not found" in res
