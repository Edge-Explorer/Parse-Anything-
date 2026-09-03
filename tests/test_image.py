from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from universal_parser.core.engine import parse
from universal_parser.core.schema import Document


@pytest.fixture
def temp_image_file(tmp_path: Path) -> Path:
    """Generate a sample image with rendered text for OCR testing."""
    file_path= tmp_path / "sample.png"
    
    # Create a blank white image (400x150)
    img= Image.new("RGB", (400, 150), color= "White")
    draw= ImageDraw.Draw(img)
    
    # Draw text in black
    draw.text((20, 30), "Universal Parser OCR", fill= "black")
    draw.text((20, 80), "Zero GPU Document Engine", fill= "black")
    
    img.save(str(file_path))
    return file_path

def test_image_returns_document(temp_image_file: Path):
    doc= parse(temp_image_file)
    assert isinstance(doc, Document)
    assert doc.metadata.file_type == "image"
    assert len(doc.content_tree) >=1
    
def test_image_ocr_text_and_bbox(temp_image_file: Path):
    doc= parse(temp_image_file)
    
    extracted_texts= [e.text for e in doc.content_tree if e.text]
    full_text= " ".join(extracted_texts).lower()
    
    # Verify OCR captured keywords
    assert "universal" in full_text or "parser" in full_text
    
    # Verify bounding boxes exist
    for elem in doc.content_tree:
        assert elem.bbox is not None
        assert elem.confidence is not None
        assert elem.confidence > 0.0