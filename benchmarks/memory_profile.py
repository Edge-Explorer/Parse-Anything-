from __future__ import annotations

import os
import time
import tracemalloc
from pathlib import Path

import psutil

from universal_parser.core.engine import parse
from universal_parser.exports.to_chunks import to_chunks


def generate_large_synthetic_pdf(output_path: Path, num_pages: int = 100) -> Path:
    """Generate a multi-page synthetic PDF with headings and paragraphs using standard PDF spec."""
    objects = []
    page_obj_ids = []

    # Obj 1: Font
    objects.append("1 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    # For each page, create Content Stream and Page Object
    for i in range(1, num_pages + 1):
        content = f"BT /F1 18 Tf 50 780 Td (Chapter {i}: Scalability and Performance) Tj ET\n"
        for p_idx in range(5):
            y_pos = 720 - p_idx * 40
            content += f"BT /F1 11 Tf 50 {y_pos} Td (Paragraph {p_idx + 1}: Testing memory safe streaming extraction on CPU without leaks.) Tj ET\n"

        content_bytes = content.encode("latin1")
        content_id = len(objects) + 2  # account for pages root obj
        objects.append(
            f"{content_id} 0 obj\n<< /Length {len(content_bytes)} >>\nstream\n{content}endstream\nendobj\n"
        )

        page_id = len(objects) + 2
        page_obj_ids.append(page_id)
        objects.append(
            f"{page_id} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 1 0 R >> >> /Contents {content_id} 0 R >>\nendobj\n"
        )

    # Pages root (Obj 2)
    kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    pages_obj = f"2 0 obj\n<< /Type /Pages /Kids [{kids_str}] /Count {num_pages} >>\nendobj\n"
    objects.insert(1, pages_obj)

    # Catalog
    catalog_id = len(objects) + 1
    objects.append(f"{catalog_id} 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

    # Build PDF with xref table
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

    output_path.write_bytes(body.encode("latin1"))
    return output_path


def run_memory_benchmark(max_allowed_mb: float = 250.0) -> bool:
    """Run memory profiling on a large document and verify memory stays under budget."""
    process = psutil.Process(os.getpid())
    start_rss = process.memory_info().rss / (1024 * 1024)

    bench_dir = Path(__file__).parent / "temp"
    bench_dir.mkdir(exist_ok=True)
    pdf_path = bench_dir / "synthetic_100p.pdf"

    print("==================================================")
    print("UNIVERSAL PARSER — MEMORY & STREAMING BENCHMARK")
    print("==================================================")
    print(f"[*] Baseline Memory: {start_rss:.2f} MB")
    print("[*] Generating 100-page synthetic PDF fixture...")
    generate_large_synthetic_pdf(pdf_path, num_pages=100)

    tracemalloc.start()
    t0 = time.perf_counter()

    print("[*] Parsing 100-page PDF and generating RAG chunks...")
    doc = parse(pdf_path)
    chunks = to_chunks(doc, max_tokens=256)

    elapsed = time.perf_counter() - t0
    _, peak_traced_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_rss = process.memory_info().rss / (1024 * 1024)
    peak_traced_mb = peak_traced_mem / (1024 * 1024)

    # Cleanup fixture
    if pdf_path.exists():
        pdf_path.unlink()
    if bench_dir.exists():
        bench_dir.rmdir()

    print("\n---------------- RESULTS ----------------")
    print(f"Total Elements Extracted: {len(doc.content_tree)}")
    print(f"Total RAG Chunks Created: {len(chunks)}")
    print(f"Parsing Latency:          {elapsed:.3f} seconds ({100 / elapsed:.1f} pages/sec)")
    print(f"Traced Peak Allocation:   {peak_traced_mb:.2f} MB")
    print(f"Process Peak RSS:         {peak_rss:.2f} MB")
    print(f"Budget Limit:             {max_allowed_mb:.2f} MB")
    print("-----------------------------------------")

    if peak_rss <= max_allowed_mb:
        print(
            f"PASSED: Peak RSS ({peak_rss:.2f} MB) is well under the {max_allowed_mb} MB limit!\n"
        )
        return True
    else:
        print(f"FAILED: Peak RSS ({peak_rss:.2f} MB) exceeded {max_allowed_mb} MB limit!\n")
        return False


if __name__ == "__main__":
    success = run_memory_benchmark(max_allowed_mb=250.0)
    raise SystemExit(0 if success else 1)
