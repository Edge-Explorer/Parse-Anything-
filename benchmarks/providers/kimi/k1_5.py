from __future__ import annotations

from benchmarks.providers.base import BaseLLMProvider


class KimiK15Provider(BaseLLMProvider):
    model_name = "kimi-k1.5"
    provider_name = "Moonshot AI"
    openrouter_id = "moonshotai/moonshot-v1-32k"
    cost_per_1k_input_tokens = 0.00120
    cost_per_1k_output_tokens = 0.00120
    base_mock_latency_ms = 1420.0
    base_mock_table_score = 0.93
    base_mock_rag_score = 0.95
