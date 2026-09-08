from __future__ import annotations

from pathlib import Path

from benchmarks.providers.base import BaseLLMProvider, ProviderBenchmarkResult
from universal_parser.core.schema import Document


class DeepSeekV3Provider(BaseLLMProvider):
    model_name = "deepseek-v3"
    provider_name = "DeepSeek"
    cost_per_1k_input_tokens = 0.00014
    cost_per_1k_output_tokens = 0.00028

    def run_benchmark(
        self, document_path: str | Path, reference_doc: Document | None = None
    ) -> ProviderBenchmarkResult:
        path = Path(document_path)
        return self._mock_evaluation(
            doc_path=path,
            base_latency_ms=980.0,
            table_accuracy=0.91,
            faithfulness=0.92,
        )