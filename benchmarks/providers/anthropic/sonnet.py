from __future__ import annotations

from benchmarks.providers.base import BaseLLMProvider


class ClaudeSonnetProvider(BaseLLMProvider):
    model_name = "claude-3-5-sonnet"
    provider_name = "Anthropic"
    openrouter_id = "anthropic/claude-3.5-sonnet"
    cost_per_1k_input_tokens = 0.003
    cost_per_1k_output_tokens = 0.015
    base_mock_latency_ms = 1920.0
    base_mock_table_score = 0.95
    base_mock_rag_score = 0.96
