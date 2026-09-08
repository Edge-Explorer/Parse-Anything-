from __future__ import annotations

from pathlib import Path

from benchmarks.providers import (
    ClaudeOpusProvider,
    ClaudeSonnetProvider,
    CommandRPlusProvider,
    DeepSeekR1Provider,
    DeepSeekV3Provider,
    GeminiFlashProvider,
    GeminiProProvider,
    GLM4Provider,
    GPT4oMiniProvider,
    GPT4oProvider,
    KimiK15Provider,
    Llama33Provider,
    MistralLargeProvider,
    Qwen72BProvider,
    QwenCoderProvider,
)


def test_all_benchmark_providers_dry_run(tmp_path: Path):
    # Create a small sample file
    sample_txt = tmp_path / "sample.txt"
    sample_txt.write_text("Test Document Line 1\nTest Document Line 2", encoding="utf-8")

    providers = [
        GeminiFlashProvider(dry_run=True),
        GeminiProProvider(dry_run=True),
        GPT4oProvider(dry_run=True),
        GPT4oMiniProvider(dry_run=True),
        ClaudeSonnetProvider(dry_run=True),
        ClaudeOpusProvider(dry_run=True),
        DeepSeekV3Provider(dry_run=True),
        DeepSeekR1Provider(dry_run=True),
        Qwen72BProvider(dry_run=True),
        QwenCoderProvider(dry_run=True),
        Llama33Provider(dry_run=True),
        MistralLargeProvider(dry_run=True),
        KimiK15Provider(dry_run=True),
        GLM4Provider(dry_run=True),
        CommandRPlusProvider(dry_run=True),
    ]

    for p in providers:
        res = p.run_benchmark(sample_txt)
        assert res.model_name == p.model_name
        assert res.provider == p.provider_name
        assert res.latency_ms > 0
        assert 0.0 <= res.table_score <= 1.0
        assert 0.0 <= res.rag_faithfulness_score <= 1.0
