from __future__ import annotations

from benchmarks.providers.base import BaseLLMProvider


class Qwen72BProvider(BaseLLMProvider):
    model_name = "qwen-2.5-72b"
    provider_name = "Alibaba Qwen"
    openrouter_id = "qwen/qwen-2.5-72b-instruct"
    cost_per_1k_input_tokens = 0.00040
    cost_per_1k_output_tokens = 0.00120
    base_mock_latency_ms = 1150.0
    base_mock_table_score = 0.90
    base_mock_rag_score = 0.93