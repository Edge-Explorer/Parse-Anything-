# Benchmarks

The benchmarks directory provides reproducible evaluation suites for measuring parser memory bounds, throughput latency, messy document layout accuracy, and standardized metrics against industry-standard document parsing engines.

---

## Active Benchmark Suites

| File | Purpose | Key Metrics / Functions |
|---|---|---|
| memory_profile.py | Evaluates peak RSS memory consumption and heap allocations across streaming documents (100 to 1,000+ pages). | Asserts RSS delta <= 250 MB and heap <= 200 MB via profile_memory(). |
| test_messy_document.py | Evaluates extraction quality on complex multi-column, rotated, noisy, and borderless table layouts. | run_messy_doc_test() |

---

## Standardized Document Evaluation Harness (Planned)

The benchmark harness is expanding to include ground-truth quantitative metrics:

1. **Table Structure Recognition (TEDS):** Tree-Edit-Distance-based Similarity against PubTables-1M and ICDAR ground truth tables.
2. **OCR Accuracy (CER / WER):** Character and Word Error Rate on labeled scanned corpora.
3. **Head-to-Head Comparative Baselines:** Local CPU execution benchmarks comparing Universal Doc Parser directly with **IBM Docling**, **Surya / Marker**, and **Unstructured.io**.

---

## Running Benchmarks

Run the memory profiling suite:

`ash
uv run python benchmarks/memory_profile.py
`

Run the messy document layout test:

`ash
uv run python benchmarks/test_messy_document.py
`
