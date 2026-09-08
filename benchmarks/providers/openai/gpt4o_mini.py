from __future__ import annotations

from benchmarks.providers.base import BaseLLMProvider


class GPT4oMiniProvider(BaseLLMProvider):
    model_name = "gpt-4o-mini"
    provider_name = "OpenAI"
    openrouter_id = "openai/gpt-4o-mini"
    cost_per_1k_input_tokens = 0.00015
    cost_per_1k_output_tokens = 0.00060
    base_mock_latency_ms = 850.0
    base_mock_table_score = 0.84
    base_mock_rag_score = 0.88
