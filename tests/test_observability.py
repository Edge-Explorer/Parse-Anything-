from __future__ import annotations

from pathlib import Path

from universal_parser.core.schema import Document, DocumentMetadata, Element
from universal_parser.observability import (
    MetricsCollector,
    export_dashboard,
    generate_dashboard_html,
)


def test_metrics_collector_singleton_and_aggregation() -> None:
    collector = MetricsCollector()
    collector.clear()

    doc1 = Document(
        metadata=DocumentMetadata(file_name="report.pdf", file_type="pdf", page_count=5),
        content_tree=[Element(type="paragraph", text="Sample text") for _ in range(10)],
    )
    doc2 = Document(
        metadata=DocumentMetadata(file_name="data.xlsx", file_type="xlsx", page_count=1),
        content_tree=[Element(type="table", data=None)],
    )

    collector.record_parse(doc1, duration_ms=120.5)
    collector.record_parse(doc2, duration_ms=45.0, anomalies=["merged_cells_detected"])

    summary = collector.get_summary()
    assert summary["total_documents"] == 2
    assert summary["total_pages"] == 6
    assert summary["total_elements"] == 11
    assert summary["avg_duration_ms"] == 82.75
    assert summary["format_breakdown"] == {"pdf": 1, "xlsx": 1}
    assert summary["anomaly_count"] == 1


def test_dashboard_generation_and_export(tmp_path: Path) -> None:
    collector = MetricsCollector()
    collector.clear()

    doc = Document(
        metadata=DocumentMetadata(file_name="test.docx", file_type="docx", page_count=2),
        content_tree=[Element(type="heading", level=1, text="Title")],
    )
    collector.record_parse(doc, duration_ms=30.0)

    html = generate_dashboard_html(collector)
    assert "<!DOCTYPE html>" in html
    assert "test.docx" in html
    assert "DOCX" in html

    out_file = tmp_path / "dashboard.html"
    exported = export_dashboard(out_file, collector)
    assert exported.is_file()
    assert len(exported.read_text(encoding="utf-8")) > 500