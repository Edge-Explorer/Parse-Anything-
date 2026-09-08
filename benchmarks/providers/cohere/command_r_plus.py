from __future__ import annotations

from benchmarks.providers.base import BaseLLMProvider


class CommandRPlusProvider(BaseLLMProvider):
    model_name = "command-r-plus"
    provider_name = "Cohere"
    openrouter_id = "cohere/command-r-plus-08-2024"
    cost_per_1k_input_tokens = 0.00250
    cost_per_1k_output_tokens = 0.01000
    base_mock_latency_ms = 1550.0
    base_mock_table_score = 0.93
    base_mock_rag_score = 0.96
