from __future__ import annotations

from benchmarks.providers.base import BaseLLMProvider


class GPT4oProvider(BaseLLMProvider):
    model_name = "gpt-4o"
    provider_name = "OpenAI"
    openrouter_id = "openai/gpt-4o"
    cost_per_1k_input_tokens = 0.005
    cost_per_1k_output_tokens = 0.015
    base_mock_latency_ms = 1850.0
    base_mock_table_score = 0.92
    base_mock_rag_score = 0.94