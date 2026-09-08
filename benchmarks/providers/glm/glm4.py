from __future__ import annotations

from benchmarks.providers.base import BaseLLMProvider


class GLM4Provider(BaseLLMProvider):
    model_name = "glm-4-9b"
    provider_name = "Zhipu AI"
    openrouter_id = "thudm/glm-4-9b-chat"
    cost_per_1k_input_tokens = 0.00010
    cost_per_1k_output_tokens = 0.00010
    base_mock_latency_ms = 1150.0
    base_mock_table_score = 0.91
    base_mock_rag_score = 0.94
