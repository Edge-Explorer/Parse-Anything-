from __future__ import annotations

from pathlib import Path

from benchmarks.providers.base import BaseLLMProvider, ProviderBenchmarkResult
from universal_parser.core.schema import Document


class GPT4oMiniProvider(BaseLLMProvider):
    model_name = "gpt-4o-mini"
    provider_name = "OpenAI"
    cost_per_1k_input_tokens = 0.00015
    cost_per_1k_output_tokens = 0.00060

    def run_benchmark(
        self, document_path: str | Path, reference_doc: Document | None = None
    ) -> ProviderBenchmarkResult:
        path = Path(document_path)
        return self._mock_evaluation(
            doc_path=path,
            base_latency_ms=850.0,
            table_accuracy=0.84,
            faithfulness=0.88,
        )