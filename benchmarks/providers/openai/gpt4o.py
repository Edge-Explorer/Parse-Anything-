from __future__ import annotations

from pathlib import Path

from benchmarks.providers.base import BaseLLMProvider, ProviderBenchmarkResult
from universal_parser.core.schema import Document


class GPT4oProvider(BaseLLMProvider):
    model_name = "gpt-4o"
    provider_name = "OpenAI"
    cost_per_1k_input_tokens = 0.005
    cost_per_1k_output_tokens = 0.015

    def run_benchmark(
        self, document_path: str | Path, reference_doc: Document | None = None
    ) -> ProviderBenchmarkResult:
        path = Path(document_path)
        return self._mock_evaluation(
            doc_path=path,
            base_latency_ms=1850.0,
            table_accuracy=0.92,
            faithfulness=0.94,
        )