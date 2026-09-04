import email.message
from pathlib import Path

import pytest

from universal_parser.core.engine import parse
from universal_parser.core.schema import Document


@pytest.fixture
def temp_eml_file(tmp_path: Path) -> Path:
    """Generate a sample .eml file with an attachment."""
    file_path = tmp_path / "sample.eml"

    msg = email.message.EmailMessage()
    msg["Subject"] = "Quarterly Business Report"
    msg["From"] = "ceo@enterprise.com"
    msg["To"] = "team@enterprise.com"
    msg.set_content("Please find attached the quarterly business report for review.")

    # Add a CSV attachment
    csv_data = b"Product,Q1_Revenue,Q2_Revenue\nSaaS,100000,150000\nServices,50000,60000\n"
    msg.add_attachment(csv_data, maintype="text", subtype="csv", filename="q_report.csv")

    with open(file_path, "wb") as f:
        f.write(msg.as_bytes())

    return file_path


def test_eml_returns_document(temp_eml_file: Path):
    doc = parse(temp_eml_file)
    assert isinstance(doc, Document)
    assert doc.metadata.file_type == "eml"
    assert len(doc.content_tree) >= 3


def test_eml_attachment_recursion(temp_eml_file: Path):
    doc = parse(temp_eml_file)

    # Check subject heading
    subject_elem = doc.content_tree[0]
    assert "Quarterly Business Report" in (subject_elem.text or "")

    # Check that attachment was extracted as a table element!
    tables = [e for e in doc.content_tree if e.type == "table"]
    assert len(tables) >= 1
    assert tables[0].data is not None
    assert "Product" in tables[0].data.headers