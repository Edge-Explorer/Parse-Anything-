from __future__ import annotations

from benchmarks.providers.base import BaseLLMProvider


class DeepSeekV3Provider(BaseLLMProvider):
    model_name = "deepseek-v3"
    provider_name = "DeepSeek"
    openrouter_id = "deepseek/deepseek-chat"
    cost_per_1k_input_tokens = 0.00014
    cost_per_1k_output_tokens = 0.00028
    base_mock_latency_ms = 980.0
    base_mock_table_score = 0.91
    base_mock_rag_score = 0.92
