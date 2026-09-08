from __future__ import annotations

from benchmarks.providers.base import BaseLLMProvider


class MistralLargeProvider(BaseLLMProvider):
    model_name = "mistral-large-2411"
    provider_name = "Mistral AI"
    openrouter_id = "mistralai/mistral-large-2411"
    cost_per_1k_input_tokens = 0.00200
    cost_per_1k_output_tokens = 0.00600
    base_mock_latency_ms = 1680.0
    base_mock_table_score = 0.94
    base_mock_rag_score = 0.97
