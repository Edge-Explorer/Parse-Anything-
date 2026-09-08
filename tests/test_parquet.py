from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from universal_parser.core.engine import parse
from universal_parser.core.schema import Document


@pytest.fixture
def temp_parquet_file(tmp_path: Path) -> Path:
    """Generate a sample .parquet file for testing."""
    file_path = tmp_path / "sample.parquet"
    data = {
        "id": [1, 2, 3],
        "product": ["Widget A", "Widget B", "Widget C"],
        "price": [19.99, 29.99, 39.99],
    }
    table = pa.Table.from_pydict(data)
    pq.write_table(table, file_path)
    return file_path


def test_parquet_returns_document(temp_parquet_file: Path):
    doc = parse(temp_parquet_file)
    assert isinstance(doc, Document)
    assert doc.metadata.file_type == "parquet"
    assert len(doc.content_tree) == 1


def test_parquet_table_structure(temp_parquet_file: Path):
    doc = parse(temp_parquet_file)
    element = doc.content_tree[0]

    assert element.type == "table"
    assert element.data is not None
    assert element.data.headers == ["id", "product", "price"]
    assert len(element.data.rows) == 3
    assert element.data.rows[0] == ["1", "Widget A", "19.99"]
    assert "|" in (element.markdown_repr or "")
