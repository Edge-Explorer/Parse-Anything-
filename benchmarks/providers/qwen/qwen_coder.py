from __future__ import annotations

from pathlib import Path

from benchmarks.providers.base import BaseLLMProvider, ProviderBenchmarkResult
from universal_parser.core.schema import Document


class QwenCoderProvider(BaseLLMProvider):
    model_name = "qwen-2.5-coder-32b"
    provider_name = "Alibaba Qwen"
    cost_per_1k_input_tokens = 0.00020
    cost_per_1k_output_tokens = 0.00060

    def run_benchmark(
        self, document_path: str | Path, reference_doc: Document | None = None
    ) -> ProviderBenchmarkResult:
        path = Path(document_path)
        return self._mock_evaluation(
            doc_path=path,
            base_latency_ms=880.0,
            table_accuracy=0.88,
            faithfulness=0.90,
        )