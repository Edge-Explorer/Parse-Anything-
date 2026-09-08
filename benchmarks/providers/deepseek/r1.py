from __future__ import annotations

from benchmarks.providers.base import BaseLLMProvider


class DeepSeekR1Provider(BaseLLMProvider):
    model_name = "deepseek-r1"
    provider_name = "DeepSeek"
    openrouter_id = "deepseek/deepseek-r1"
    cost_per_1k_input_tokens = 0.00055
    cost_per_1k_output_tokens = 0.00219
    base_mock_latency_ms = 2400.0
    base_mock_table_score = 0.94
    base_mock_rag_score = 0.96