from __future__ import annotations

from benchmarks.providers.base import BaseLLMProvider


class ClaudeOpusProvider(BaseLLMProvider):
    model_name = "claude-3-opus"
    provider_name = "Anthropic"
    openrouter_id = "anthropic/claude-3-opus"
    cost_per_1k_input_tokens = 0.015
    cost_per_1k_output_tokens = 0.075
    base_mock_latency_ms = 3100.0
    base_mock_table_score = 0.96
    base_mock_rag_score = 0.97