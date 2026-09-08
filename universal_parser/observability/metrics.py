from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Self

from universal_parser.core.schema import Document


@dataclass
class ParseEventMetric:
    """Telemetry record for a single document parse execution."""

    file_name: str
    file_type: str
    page_count: int
    element_count: int
    duration_ms: float
    timestamp: float = field(default_factory=time.time)
    has_scanned_pages: bool = False
    anomalies: list[str] = field(default_factory=list)


class MetricsCollector:
    """Thread-safe collector for document ingestion telemetry and anomaly signals."""

    _instance: MetricsCollector | None = None
    _lock = Lock()

    def __new__(cls) -> Self:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._events = []
            return cls._instance

    def record_parse(
        self,
        doc: Document,
        duration_ms: float,
        anomalies: list[str] | None = None,
    ) -> ParseEventMetric:
        """Records telemetry for a parsed document."""
        metric = ParseEventMetric(
            file_name=doc.metadata.file_name,
            file_type=doc.metadata.file_type,
            page_count=doc.metadata.page_count or 1,
            element_count=len(doc.content_tree),
            duration_ms=round(duration_ms, 2),
            has_scanned_pages=doc.metadata.has_scanned_pages,
            anomalies=anomalies or [],
        )
        with self._lock:
            self._events.append(metric)
        return metric

    def get_events(self) -> list[ParseEventMetric]:
        with self._lock:
            return list(self._events)

    def get_summary(self) -> dict[str, Any]:
        """Calculates aggregated performance statistics across all parsed documents."""
        with self._lock:
            events = list(self._events)

        if not events:
            return {
                "total_documents": 0,
                "total_pages": 0,
                "total_elements": 0,
                "avg_duration_ms": 0.0,
                "format_breakdown": {},
                "anomaly_count": 0,
            }

        total_docs = len(events)
        total_pages = sum(e.page_count for e in events)
        total_elements = sum(e.element_count for e in events)
        avg_duration = round(sum(e.duration_ms for e in events) / total_docs, 2)

        format_breakdown: dict[str, int] = {}
        anomaly_count = 0
        for e in events:
            format_breakdown[e.file_type] = format_breakdown.get(e.file_type, 0) + 1
            anomaly_count += len(e.anomalies)

        return {
            "total_documents": total_docs,
            "total_pages": total_pages,
            "total_elements": total_elements,
            "avg_duration_ms": avg_duration,
            "format_breakdown": format_breakdown,
            "anomaly_count": anomaly_count,
        }

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
