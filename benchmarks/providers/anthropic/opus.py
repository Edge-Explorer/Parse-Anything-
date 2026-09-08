from __future__ import annotations

from pathlib import Path

from benchmarks.providers.base import BaseLLMProvider, ProviderBenchmarkResult
from universal_parser.core.schema import Document


class ClaudeOpusProvider(BaseLLMProvider):
    model_name = "claude-3-opus"
    provider_name = "Anthropic"
    cost_per_1k_input_tokens = 0.015
    cost_per_1k_output_tokens = 0.075

    def run_benchmark(
        self, document_path: str | Path, reference_doc: Document | None = None
    ) -> ProviderBenchmarkResult:
        path = Path(document_path)
        return self._mock_evaluation(
            doc_path=path,
            base_latency_ms=3100.0,
            table_accuracy=0.96,
            faithfulness=0.97,
        )