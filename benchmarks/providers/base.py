from __future__ import annotations

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from universal_parser.core.schema import Document


class ProviderBenchmarkResult(BaseModel):
    """Benchmark metrics comparing an LLM provider against Universal Parser."""

    model_name: str
    provider: str
    latency_ms: float
    estimated_cost_usd: float
    table_score: float = Field(default=0.0, description="Table reconstruction accuracy [0.0 - 1.0]")
    rag_faithfulness_score: float = Field(
        default=0.0, description="RAG answer faithfulness / groundedness [0.0 - 1.0]"
    )
    extracted_elements_count: int = 0
    raw_response: dict[str, Any] = Field(default_factory=dict)


class BaseLLMProvider(ABC):
    """Abstract interface for multi-model LLM document ingestion benchmarks."""

    model_name: str = "base-model"
    provider_name: str = "base-provider"
    cost_per_1k_input_tokens: float = 0.005
    cost_per_1k_output_tokens: float = 0.015

    def __init__(self, api_key: str | None = None, dry_run: bool = True) -> None:
        self.api_key = api_key
        self.dry_run = dry_run

    @abstractmethod
    def run_benchmark(
        self,
        document_path: str | Path,
        reference_doc: Document | None = None,
    ) -> ProviderBenchmarkResult:
        """Executes document parsing evaluation using this model provider."""
        ...

    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculates estimated API cost in USD based on token counts."""
        input_cost = (prompt_tokens / 1000.0) * self.cost_per_1k_input_tokens
        output_cost = (completion_tokens / 1000.0) * self.cost_per_1k_output_tokens
        return round(input_cost + output_cost, 5)

    def _mock_evaluation(
        self,
        doc_path: Path,
        base_latency_ms: float,
        table_accuracy: float,
        faithfulness: float,
    ) -> ProviderBenchmarkResult:
        """Generates realistic benchmark metrics in dry-run mode (zero API cost / offline CI)."""
        t0 = time.perf_counter()
        file_size_kb = doc_path.stat().st_size / 1024.0 if doc_path.exists() else 50.0
        # Estimated token footprint for document image/text
        est_input_tokens = int(file_size_kb * 45) + 500
        est_output_tokens = int(file_size_kb * 20) + 200

        # Simulate roundtrip network + inference latency
        simulated_latency = base_latency_ms + (file_size_kb * 2.5)
        cost = self._estimate_cost(est_input_tokens, est_output_tokens)
        _ = time.perf_counter() - t0

        return ProviderBenchmarkResult(
            model_name=self.model_name,
            provider=self.provider_name,
            latency_ms=round(simulated_latency, 2),
            estimated_cost_usd=cost,
            table_score=round(table_accuracy, 3),
            rag_faithfulness_score=round(faithfulness, 3),
            extracted_elements_count=int(file_size_kb * 2.5) + 10,
            raw_response={"status": "success", "dry_run": self.dry_run},
        )