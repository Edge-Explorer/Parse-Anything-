# observability

The universal_parser.observability module provides real-time telemetry metrics collection and HTML dashboard exports for monitoring document ingestion pipelines.

---

## Files and Modules

| File | Purpose | Key Classes / Functions |
|---|---|---|
| 	elemetry.py | Singleton thread-safe metrics collector for tracking parsing latency and anomalies. | MetricsCollector, ParseEventMetric |
| dashboard.py | Generates self-contained HTML/JS telemetry and drift monitoring dashboards. | export_dashboard() |

---

## Technical Details

MetricsCollector collects parsing duration, element counts, page counts, and anomaly indicators. export_dashboard() renders a standalone interactive dashboard without external server or CDN requirements.
