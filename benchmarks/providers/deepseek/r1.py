from __future__ import annotations

from pathlib import Path

from benchmarks.providers.base import BaseLLMProvider, ProviderBenchmarkResult
from universal_parser.core.schema import Document


class DeepSeekR1Provider(BaseLLMProvider):
    model_name = "deepseek-r1"
    provider_name = "DeepSeek"
    cost_per_1k_input_tokens = 0.00055
    cost_per_1k_output_tokens = 0.00219

    def run_benchmark(
        self, document_path: str | Path, reference_doc: Document | None = None
    ) -> ProviderBenchmarkResult:
        path = Path(document_path)
        return self._mock_evaluation(
            doc_path=path,
            base_latency_ms=2400.0,
            table_accuracy=0.94,
            faithfulness=0.96,
        )