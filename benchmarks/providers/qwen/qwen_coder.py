from __future__ import annotations

from benchmarks.providers.base import BaseLLMProvider


class QwenCoderProvider(BaseLLMProvider):
    model_name = "qwen-2.5-coder-32b"
    provider_name = "Alibaba Qwen"
    openrouter_id = "qwen/qwen-2.5-coder-32b-instruct"
    cost_per_1k_input_tokens = 0.00020
    cost_per_1k_output_tokens = 0.00060
    base_mock_latency_ms = 880.0
    base_mock_table_score = 0.88
    base_mock_rag_score = 0.90
