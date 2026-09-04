from pathlib import Path

import pytest

from universal_parser.core.engine import parse
from universal_parser.core.schema import Document, Element

FIXTURE = Path(__file__).parent / "fixtures" / "pdf" / "sample.pdf"


def test_pdf_fixture_exists():
    """The fixture file must be present before any other test runs."""
    assert FIXTURE.exists(), f"Missing fixture: {FIXTURE}"


def test_pdf_returns_document():
    """parse() on a PDF must return a valid Document object."""
    doc = parse(FIXTURE)
    assert isinstance(doc, Document)


def test_pdf_metadata():
    """Document metadata must reflect the source file correctly."""
    doc = parse(FIXTURE)
    assert doc.metadata.file_name == "sample.pdf"
    assert doc.metadata.file_type == "pdf"
    assert doc.schema_version == "1.0"


def test_pdf_has_content():
    """A real PDF must produce at least one Element in content_tree."""
    doc = parse(FIXTURE)
    assert len(doc.content_tree) > 0


def test_pdf_elements_are_valid():
    """Every element must pass Pydantic schema validation."""
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
        
        # Table elements use data/markdown_repr, other types must have text
        if element.type != "table":
            assert element.text is not None
            assert len(element.text.strip()) > 0


def test_pdf_has_page_numbers():
    """Every element from a PDF must have a page number set."""
    doc = parse(FIXTURE)
    for element in doc.content_tree:
        assert element.page is not None
        assert element.page >= 1


def test_pdf_corrupted_file(tmp_path):
    """A corrupted PDF must not crash — engine raises ValueError or returns cleanly."""
    bad_file = tmp_path / "bad.pdf"
    bad_file.write_bytes(b"%PDF-1.4 this is not a real pdf at all")
    # We expect either a clean empty document or a ValueError
    # The parser must never throw a raw unhandled exception
    try:
        doc = parse(bad_file)
        assert isinstance(doc, Document)
    except ValueError:
        pass  # Acceptable — unsupported or unreadable


def test_pdf_missing_file():
    """A missing file must raise FileNotFoundError, not crash."""
    with pytest.raises(FileNotFoundError):
        parse(Path("does_not_exist.pdf"))

def test_scanned_pdf_ocr_fallback(tmp_path: Path):
    """Test that a scanned PDF with no native text runs OCR fallback."""
    import fitz
    from PIL import Image, ImageDraw
    
    # 1. Create an image with text
    img= Image.new("RGB", (400, 150), color= "white")
    draw= ImageDraw.Draw(img)
    draw.text((20, 50), "Scanned Invoice Document", fill= "black")
    
    img_path= tmp_path / "scan.png"
    img.save(str(img_path))
    
    # 2. Insert image into a PDF without selectable text
    pdf_path= tmp_path / "scanned.pdf"
    doc= fitz.open()
    page= doc.new_page(width= 400, height= 150)
    page.insert_image(page.rect, filename= str(img_path))
    doc.save(str(pdf_path))
    doc.close()
    
    # 3. Parse with universal-parser
    parsed_doc= parse(pdf_path)
    assert len(parsed_doc.content_tree) >= 1
    extracted_text= " ".join([e.text for e in parsed_doc.content_tree if e.text]).lower()
    assert "scanned" in extracted_text or "invoice" in extracted_text