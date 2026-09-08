from __future__ import annotations

from benchmarks.providers.base import BaseLLMProvider


class Llama33Provider(BaseLLMProvider):
    model_name = "llama-3.3-70b"
    provider_name = "Meta"
    openrouter_id = "meta-llama/llama-3.3-70b-instruct"
    cost_per_1k_input_tokens = 0.00018
    cost_per_1k_output_tokens = 0.00040
    base_mock_latency_ms = 1350.0
    base_mock_table_score = 0.94
    base_mock_rag_score = 0.97
