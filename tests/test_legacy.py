from pathlib import Path

import pytest
import xlwt

from universal_parser.core.engine import parse
from universal_parser.core.schema import Document


@pytest.fixture
def temp_xls_file(tmp_path: Path) -> Path:
    """Generate a sample legacy .xls spreadsheet."""
    file_path= tmp_path / "sample.xls"
    
    wb= xlwt.Workbook()
    ws= wb.add_sheet("Q1 Financials")
    
    ws.write(0, 0, "Quarter")
    ws.write(0, 1, "Revenue")
    ws.write(1, 0, "Q1")
    ws.write(1, 1, "50000")
    
    wb.save(str(file_path))
    return file_path

def test_legacy_xls_returns_documents(temp_xls_file: Path):
    doc= parse(temp_xls_file)
    assert isinstance(doc, Document)
    assert doc.metadata.file_type == "xls"
    assert len(doc.content_tree) == 1
    
def test_legacy_xls_table_structure(temp_xls_file: Path):
    doc= parse(temp_xls_file)
    table= doc.content_tree[0]
    
    assert table.type == "table"
    assert table.data is not None
    assert table.data.headers == ["Quarter", "Revenue"]
    assert table.data.rows[0] == ["Q1", "50000"]
    assert "|" in (table.markdown_repr or "")