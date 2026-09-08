# benchmarks

The enchmarks module contains benchmark suites for assessing parser memory limits, messy document parsing accuracy, and evaluating 15 frontier LLMs against local CPU document parsing.

---

## Files and Modules

| File | Purpose | Key Classes / Functions |
|---|---|---|
| memory_profile.py | Benchmarks RSS memory consumption across 1000+ page streaming documents. | profile_memory() |
| 	est_messy_document.py | Evaluates parsing accuracy on complex multi-column and noisy layout documents. | 
un_messy_doc_test() |
| 
un_llm_benchmark.py | CLI runner for benchmarking 15 LLM provider models against local extraction. | main() |
| providers/ | Submodule containing API wrappers and evaluation logic for 15 LLM providers. | See providers/README.md |
