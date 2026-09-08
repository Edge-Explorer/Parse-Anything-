from __future__ import annotations

import time
from pathlib import Path

from universal_parser.core.engine import parse
from universal_parser.exports.to_chunks import to_chunks
from universal_parser.exports.to_graph import to_graph
from universal_parser.exports.to_markdown import to_markdown


def create_ultra_messy_pdf(output_path: Path) -> Path:
    """Generates an ultra-challenging PDF with 2-column text, multiple headings, and borderless tables."""
    objects = []
    page_obj_ids = []

    # Obj 1 & 2: Fonts
    objects.append("1 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    objects.append("2 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n")

    # Ultra-messy document content:
    # 1. Main Title
    # 2. Left Column & Right Column at identical vertical Y positions
    # 3. Mid-page Section Heading
    # 4. Borderless Financial Table
    # 5. Footer Disclaimer
    content = """
BT /F2 20 Tf 50 780 Td (Mega Corporation Global Audit & Strategy Report 2026) Tj ET
BT /F2 13 Tf 50 745 Td (1. Executive & Operational Breakdown) Tj ET

BT /F2 11 Tf 50 715 Td (Left Column: Strategic Operations) Tj ET
BT /F1 10 Tf 50 690 Td (LEFT COL [Line 1]: Global expansion yielded 24.8% growth in APAC region.) Tj ET
BT /F1 10 Tf 50 670 Td (LEFT COL [Line 2]: Automated ingestion pipelines replaced legacy OCR systems.) Tj ET
BT /F1 10 Tf 50 650 Td (LEFT COL [Line 3]: Enterprise CPU clusters achieved zero cloud API dependency.) Tj ET

BT /F2 11 Tf 310 715 Td (Right Column: Engineering Infrastructure) Tj ET
BT /F1 10 Tf 310 690 Td (RIGHT COL [Line 1]: High-concurrency streaming parser handled 1,000 pages.) Tj ET
BT /F1 10 Tf 310 670 Td (RIGHT COL [Line 2]: RSS memory consumption remained strictly under 250 MB.) Tj ET
BT /F1 10 Tf 310 650 Td (RIGHT COL [Line 3]: Graph nodes and AST breadcrumbs preserved active context.) Tj ET

BT /F2 14 Tf 50 595 Td (2. Q3 Consolidated Financial Performance Table) Tj ET

BT /F2 10 Tf 50 560 Td (Department) Tj 140 0 Td (Q3 Units) Tj 90 0 Td (Unit Cost) Tj 90 0 Td (Total Net USD) Tj ET
BT /F1 10 Tf 50 535 Td (Core Parser Engine) Tj 140 0 Td (15,200) Tj 90 0 Td ($45.00) Tj 90 0 Td ($684,000.00) Tj ET
BT /F1 10 Tf 50 510 Td (FastMCP Server Layer) Tj 140 0 Td (8,450) Tj 90 0 Td ($20.00) Tj 90 0 Td ($169,000.00) Tj ET
BT /F1 10 Tf 50 485 Td (GraphRAG Knowledge AST) Tj 140 0 Td (3,120) Tj 90 0 Td ($95.00) Tj 90 0 Td ($296,400.00) Tj ET
BT /F1 10 Tf 50 460 Td (Adaptive Tuner Cache) Tj 140 0 Td (22,900) Tj 90 0 Td ($8.50) Tj 90 0 Td ($194,650.00) Tj ET

BT /F2 12 Tf 50 415 Td (3. Compliance & Governance Certification) Tj ET
BT /F1 9 Tf 50 385 Td (CONFIDENTIAL FOOTNOTE: All figures verified under Apache 2.0 and MIT permissive licensing compliance standards.) Tj ET
"""

    content_bytes = content.encode("latin1")
    objects.append(
        f"4 0 obj\n<< /Length {len(content_bytes)} >>\nstream\n{content}endstream\nendobj\n"
    )

    page_id = 5
    page_obj_ids.append(page_id)
    objects.append(
        "5 0 obj\n<< /Type /Page /Parent 3 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 1 0 R /F2 2 0 R >> >> /Contents 4 0 R >>\nendobj\n"
    )

    # Pages root (Obj 3)
    kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    pages_obj = f"3 0 obj\n<< /Type /Pages /Kids [{kids_str}] /Count 1 >>\nendobj\n"
    objects.insert(2, pages_obj)

    # Catalog (Obj 6)
    catalog_id = 6
    objects.append("6 0 obj\n<< /Type /Catalog /Pages 3 0 R >>\nendobj\n")

    # Build PDF binary
    body = "%PDF-1.4\n"
    xref_offsets = []
    for obj in objects:
        xref_offsets.append(len(body.encode("latin1")))
        body += obj

    xref_pos = len(body.encode("latin1"))
    body += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    for offset in xref_offsets:
        body += f"{offset:010d} 00000 n \n"

    body += f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(body.encode("latin1"))
    return output_path


def run_messy_document_stress_test() -> None:
    temp_dir = Path(__file__).parent / "temp"
    pdf_path = temp_dir / "ultra_messy_complex.pdf"

    print("================================================================================")
    print("UNIVERSAL PARSER — ULTRA-MESSY COMPLEX DOCUMENT STRESS TEST")
    print("================================================================================")
    print("[*] Generating ultra-messy 2-column + table + multi-heading PDF fixture...")
    create_ultra_messy_pdf(pdf_path)

    # 1. Parse document with Universal Parser
    t0 = time.perf_counter()
    doc = parse(pdf_path)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    print(f"\n[+] Parse Completed in: {latency_ms:.2f} ms")
    print(f"[+] Total Elements Extracted: {len(doc.content_tree)}")

    # 2. Inspect Reading Order (Verify Left Column is read completely BEFORE Right Column!)
    print("\n" + "=" * 80)
    print("NATURAL READING ORDER VERIFICATION (Left Column -> Right Column):")
    print("=" * 80)
    for idx, el in enumerate(doc.content_tree, 1):
        type_badge = f"[{el.type.upper()}]"
        if el.type == "heading":
            type_badge += f" (H{el.level})"
        text_preview = el.text or (f"Table with {len(el.data.rows)} rows" if el.data else "")
        print(f"{idx:02d}. {type_badge:<16} : {text_preview}")

    # 3. Export to Markdown
    print("\n" + "=" * 80)
    print("EXTRACTED MARKDOWN PREVIEW:")
    print("=" * 80)
    md = to_markdown(doc)
    print(md)

    # 4. Export to Hierarchical RAG Chunks (Preserving Heading Breadcrumbs)
    print("\n" + "=" * 80)
    print("HIERARCHICAL RAG CHUNKS (with Active Heading Breadcrumb Inheritance):")
    print("=" * 80)
    chunks = to_chunks(doc, max_tokens=90)
    for i, chunk in enumerate(chunks, 1):
        print(f"\n--- [RAG Chunk #{i}] (Tokens: ~{chunk.estimated_tokens}) ---")
        print(chunk.text)

    # 5. Export to Knowledge Graph
    graph = to_graph(doc)
    print("\n" + "=" * 80)
    print(
        f"KNOWLEDGE GRAPH AST: {len(graph.nodes)} Nodes, {len(graph.edges)} Edges Generated for GraphRAG/Neo4j"
    )
    print("================================================================================\n")


if __name__ == "__main__":
    run_messy_document_stress_test()
