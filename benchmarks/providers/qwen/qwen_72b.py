from __future__ import annotations

from pathlib import Path

from benchmarks.providers.base import BaseLLMProvider, ProviderBenchmarkResult
from universal_parser.core.schema import Document


class Qwen72BProvider(BaseLLMProvider):
    model_name = "qwen-2.5-72b"
    provider_name = "Alibaba Qwen"
    cost_per_1k_input_tokens = 0.00040
    cost_per_1k_output_tokens = 0.00120

    def run_benchmark(
        self, document_path: str | Path, reference_doc: Document | None = None
    ) -> ProviderBenchmarkResult:
        path = Path(document_path)
        return self._mock_evaluation(
            doc_path=path,
            base_latency_ms=1150.0,
            table_accuracy=0.90,
            faithfulness=0.93,
        )