from __future__ import annotations

from pathlib import Path

from benchmarks.providers.base import BaseLLMProvider, ProviderBenchmarkResult
from universal_parser.core.schema import Document


class GeminiFlashProvider(BaseLLMProvider):
    model_name = "gemini-2.0-flash"
    provider_name = "Google Gemini"
    cost_per_1k_input_tokens = 0.00010
    cost_per_1k_output_tokens = 0.00040

    def run_benchmark(
        self, document_path: str | Path, reference_doc: Document | None = None
    ) -> ProviderBenchmarkResult:
        path = Path(document_path)
        return self._mock_evaluation(
            doc_path=path,
            base_latency_ms=620.0,
            table_accuracy=0.89,
            faithfulness=0.91,
        )