from __future__ import annotations

from pathlib import Path

from universal_parser.observability.metrics import MetricsCollector


def generate_dashboard_html(collector: MetricsCollector | None = None) -> str:
    """Generates a self-contained, responsive HTML observability dashboard."""
    col = collector or MetricsCollector()
    summary = col.get_summary()
    events = col.get_events()

    # Generate format table rows
    format_rows = ""
    for fmt, count in summary["format_breakdown"].items():
        format_rows += f"<tr><td><strong>{fmt.upper()}</strong></td><td>{count}</td></tr>\n"

    if not format_rows:
        format_rows = "<tr><td colspan='2' style='text-align:center; color:#888;'>No events recorded yet</td></tr>"

    # Generate recent events table rows
    event_rows = ""
    for e in reversed(events[-20:]):
        anomaly_badge = (
            f"<span class='badge badge-warn'>{len(e.anomalies)} anomalies</span>"
            if e.anomalies
            else "<span class='badge badge-ok'>clean</span>"
        )
        event_rows += f"""
        <tr>
            <td>{e.file_name}</td>
            <td>{e.file_type.upper()}</td>
            <td>{e.page_count}</td>
            <td>{e.element_count}</td>
            <td>{e.duration_ms} ms</td>
            <td>{anomaly_badge}</td>
        </tr>
        """

    if not event_rows:
        event_rows = "<tr><td colspan='6' style='text-align:center; color:#888;'>No events recorded yet</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Universal Parser — Observability & Drift Dashboard</title>
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #38bdf8;
            --accent: #818cf8;
            --success: #4ade80;
            --warning: #fbbf24;
            --border: #334155;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 24px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        header {{
            margin-bottom: 32px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 16px;
        }}
        h1 {{
            margin: 0 0 8px 0;
            font-size: 28px;
            color: var(--primary);
        }}
        .subtitle {{
            color: var(--text-muted);
            margin: 0;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }}
        .card {{
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
        }}
        .card-title {{
            color: var(--text-muted);
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}
        .card-value {{
            font-size: 32px;
            font-weight: bold;
            color: var(--text-main);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 12px;
            background-color: var(--card-bg);
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid var(--border);
        }}
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
        }}
        th {{
            background-color: rgba(0, 0, 0, 0.2);
            color: var(--primary);
            font-weight: 600;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        .badge {{
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }}
        .badge-ok {{
            background-color: rgba(74, 222, 128, 0.15);
            color: var(--success);
        }}
        .badge-warn {{
            background-color: rgba(251, 191, 36, 0.15);
            color: var(--warning);
        }}
        .layout-two-col {{
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 24px;
        }}
        @media (max-width: 768px) {{
            .layout-two-col {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Universal Parser — Observability Dashboard</h1>
            <p class="subtitle">Real-time performance telemetry, anomaly tracking, and multi-format throughput.</p>
        </header>

        <div class="grid">
            <div class="card">
                <div class="card-title">Total Documents</div>
                <div class="card-value">{summary["total_documents"]}</div>
            </div>
            <div class="card">
                <div class="card-title">Total Pages</div>
                <div class="card-value">{summary["total_pages"]}</div>
            </div>
            <div class="card">
                <div class="card-title">Avg Latency</div>
                <div class="card-value">{summary["avg_duration_ms"]}<span style="font-size:16px; color:var(--text-muted);"> ms</span></div>
            </div>
            <div class="card">
                <div class="card-title">Drift / Anomalies</div>
                <div class="card-value" style="color: {'var(--warning)' if summary['anomaly_count'] > 0 else 'var(--success)'};">{summary["anomaly_count"]}</div>
            </div>
        </div>

        <div class="layout-two-col">
            <div>
                <h2>Formats Handled</h2>
                <table>
                    <thead>
                        <tr><th>Format</th><th>Documents</th></tr>
                    </thead>
                    <tbody>
                        {format_rows}
                    </tbody>
                </table>
            </div>

            <div>
                <h2>Recent Ingestion Stream</h2>
                <table>
                    <thead>
                        <tr>
                            <th>File</th>
                            <th>Type</th>
                            <th>Pages</th>
                            <th>Elements</th>
                            <th>Latency</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {event_rows}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
"""
    return html


def export_dashboard(output_path: str | Path, collector: MetricsCollector | None = None) -> Path:
    """Exports the observability dashboard to an HTML file on disk."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    html = generate_dashboard_html(collector)
    path.write_text(html, encoding="utf-8")
    return path