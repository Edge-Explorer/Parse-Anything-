from __future__ import annotations

import os
import time
import tracemalloc
from pathlib import Path

import fitz  # PyMuPDF
import psutil

from universal_parser.core.engine import parse
from universal_parser.exports.to_chunks import to_chunks


def generate_large_synthetic_pdf(output_path: Path, num_pages: int= 100) -> Path:
    """Generate a multi-page synthetic PDF with headings and paragraphs."""
    doc= fitz.open()
    for i in range(1, num_pages + 1):
        page= doc.new_page(width=595, height= 842)   # A4 size
        # Add heading
        page.insert_text((50, 60), f"Chapter {i}: Scalability & Performance", fontsize= 18)
        # Add paragraphs
        for p_idx in range(5):
            y_pos= 100 + p_idx * 50
            page.insert_text(
                (50, y_pos),
                f"Paragraph {p_idx+1}: Testing memory-safe streaming extraction on CPU without leaks.",
                fontsize= 11,
            )
    doc.save(str(output_path))
    doc.close()
    return output_path
    
def run_memory_benchmark(max_allowed_mb: float= 250.0) -> bool:
    """Run memory profiling on a large document and verify memory stays under budget."""
    process= psutil.Process(os.getpid())
    start_rss= process.memory_info().rss / (1024 * 1024)
    
    bench_dir= Path(__file__).parent / "temp"
    bench_dir.mkdir(exist_ok= True)
    pdf_path= bench_dir / "synthetic_100p.pdf"
    
    print("==================================================")
    print("UNIVERSAL PARSER — MEMORY & STREAMING BENCHMARK")
    print("==================================================")
    print(f"[*] Baseline Memory: {start_rss:.2f} MB")
    print("[*] Generating 100-page synthetic PDF fixture...")
    generate_large_synthetic_pdf(pdf_path, num_pages=100)
    
    tracemalloc.start()
    t0= time.perf_counter()
    
    print("[*] Parsing 100-page PDF and generating RAG chunks...")
    doc= parse(pdf_path)
    chunks= to_chunks(doc, max_tokens= 256)
    
    elapsed= time.perf_counter() - t0
    _, peak_traced_mem= tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    peak_rss= process.memory_info().rss / (1024 * 1024)
    peak_traced_mb= peak_traced_mem / (1024 * 1024)
    
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
        print(f"PASSED: Peak RSS ({peak_rss:.2f} MB) is well under the {max_allowed_mb} MB limit!\n")
        return True
    else:
        print(f"FAILED: Peak RSS ({peak_rss:.2f} MB) exceeded {max_allowed_mb} MB limit!\n")
        return False
    
if __name__ == "__main__":
    success= run_memory_benchmark(max_allowed_mb= 250.0)
    raise SystemExit(0 if success else 1)