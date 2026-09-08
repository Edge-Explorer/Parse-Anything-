from __future__ import annotations

from pathlib import Path

from universal_parser.adaptive import (
    AdaptiveTuner,
    FeedbackSignal,
    ParserConfig,
    TemplateConfigCache,
    compute_fingerprint,
    fingerprint_similarity,
)
from universal_parser.core.schema import BBox, Document, DocumentMetadata, Element


def _create_sample_doc(text_prefix: str = "Doc A", two_columns: bool = False) -> Document:
    elements = [
        Element(
            type="heading",
            level=1,
            text=f"{text_prefix} Heading",
            page=1,
            bbox=BBox(x0=50.0, y0=50.0, x1=300.0, y1=80.0),
        ),
        Element(
            type="paragraph",
            text=f"{text_prefix} paragraph 1",
            page=1,
            bbox=BBox(x0=50.0, y0=90.0, x1=280.0, y1=200.0),
        ),
    ]
    if two_columns:
        elements.append(
            Element(
                type="paragraph",
                text=f"{text_prefix} column 2 paragraph",
                page=1,
                bbox=BBox(x0=320.0, y0=90.0, x1=550.0, y1=200.0),
            )
        )
    return Document(
        metadata=DocumentMetadata(file_name="sample.pdf", file_type="pdf", page_count=1),
        content_tree=elements,
    )


def test_compute_fingerprint_deterministic() -> None:
    doc1 = _create_sample_doc(text_prefix="Invoice 001")
    doc2 = _create_sample_doc(text_prefix="Invoice 001")

    fp1 = compute_fingerprint(doc1)
    fp2 = compute_fingerprint(doc2)

    assert fp1.hash_digest == fp2.hash_digest
    assert fp1.spatial_grid == fp2.spatial_grid
    assert fp1.type_distribution == fp2.type_distribution
    assert fingerprint_similarity(fp1, fp2) == 1.0


def test_fingerprint_invariance_to_text_changes() -> None:
    # Same layout geometry and element types, but different string contents
    doc1 = _create_sample_doc(text_prefix="Company ABC Invoice #1234")
    doc2 = _create_sample_doc(text_prefix="Company XYZ Invoice #9876")

    fp1 = compute_fingerprint(doc1)
    fp2 = compute_fingerprint(doc2)

    assert fp1.hash_digest == fp2.hash_digest
    assert fingerprint_similarity(fp1, fp2) == 1.0


def test_fingerprint_dissimilarity() -> None:
    doc_single_col = _create_sample_doc(two_columns=False)
    doc_two_col = _create_sample_doc(two_columns=True)

    fp1 = compute_fingerprint(doc_single_col)
    fp2 = compute_fingerprint(doc_two_col)

    assert fp1.hash_digest != fp2.hash_digest
    sim = fingerprint_similarity(fp1, fp2)
    assert 0.0 < sim < 1.0


def test_config_cache_exact_and_fuzzy_match() -> None:
    cache = TemplateConfigCache(capacity=10)
    doc = _create_sample_doc(text_prefix="Template Base")
    fp = compute_fingerprint(doc)

    custom_cfg = ParserConfig(column_gap_threshold=45.0, heading_p95_ratio=1.45)
    cache.set(fp, custom_cfg)

    # 1. Exact match lookup
    res = cache.get(fp)
    assert res is not None
    key, retrieved_cfg = res
    assert key == fp.hash_digest
    assert retrieved_cfg.column_gap_threshold == 45.0
    assert retrieved_cfg.heading_p95_ratio == 1.45

    # 2. Fuzzy match lookup with a slightly modified layout
    doc_similar = _create_sample_doc(text_prefix="Template Variation")
    fp_similar = compute_fingerprint(doc_similar)
    fuzzy_res = cache.get(fp_similar, similarity_threshold=0.8)
    assert fuzzy_res is not None


def test_config_cache_lru_eviction() -> None:
    cache = TemplateConfigCache(capacity=2)
    doc1 = _create_sample_doc(text_prefix="Doc 1", two_columns=False)
    doc2 = _create_sample_doc(text_prefix="Doc 2", two_columns=True)
    doc3 = Document(
        metadata=DocumentMetadata(file_name="empty.pdf", file_type="pdf", page_count=1),
        content_tree=[],
    )

    fp1 = compute_fingerprint(doc1)
    fp2 = compute_fingerprint(doc2)
    fp3 = compute_fingerprint(doc3)

    cache.set(fp1, ParserConfig(column_gap_threshold=15.0))
    cache.set(fp2, ParserConfig(column_gap_threshold=25.0))
    assert len(cache) == 2

    # Inserting 3rd item should evict fp1 (least recently used)
    cache.set(fp3, ParserConfig(column_gap_threshold=35.0))
    assert len(cache) == 2
    assert cache.get_exact(fp1.hash_digest) is None
    assert cache.get_exact(fp2.hash_digest) is not None
    assert cache.get_exact(fp3.hash_digest) is not None


def test_config_cache_persistence(tmp_path: Path) -> None:
    cache_file = tmp_path / "templates.json"
    cache = TemplateConfigCache()
    doc = _create_sample_doc()
    fp = compute_fingerprint(doc)
    cfg = ParserConfig(column_gap_threshold=50.0, table_detection_mode="stream")

    cache.set(fp, cfg)
    cache.save(cache_file)

    # Load into new cache
    new_cache = TemplateConfigCache()
    new_cache.load(cache_file)
    assert len(new_cache) == 1
    res = new_cache.get(fp)
    assert res is not None
    _, loaded_cfg = res
    assert loaded_cfg.column_gap_threshold == 50.0
    assert loaded_cfg.table_detection_mode == "stream"


def test_adaptive_tuner_feedback_signals() -> None:
    tuner = AdaptiveTuner()
    base_cfg = ParserConfig(
        column_gap_threshold=30.0,
        heading_p95_ratio=1.30,
        heading_p85_ratio=1.15,
        min_table_confidence=0.60,
    )

    # Missed heading signal -> decreases ratio
    signals = [FeedbackSignal(signal_type="missed_heading", severity=1.0)]
    tuned = tuner.tune(base_cfg, signals)
    assert tuned.heading_p95_ratio < base_cfg.heading_p95_ratio
    assert tuned.heading_p85_ratio < base_cfg.heading_p85_ratio

    # False heading signal -> increases ratio
    signals_false = [FeedbackSignal(signal_type="false_heading", severity=1.0)]
    tuned_false = tuner.tune(base_cfg, signals_false)
    assert tuned_false.heading_p95_ratio > base_cfg.heading_p95_ratio

    # Merged column signal -> reduces column gap threshold
    signals_col = [FeedbackSignal(signal_type="merged_columns", severity=1.0)]
    tuned_col = tuner.tune(base_cfg, signals_col)
    assert tuned_col.column_gap_threshold < base_cfg.column_gap_threshold


def test_adaptive_tuner_guardrails() -> None:
    tuner = AdaptiveTuner()
    base_cfg = ParserConfig(column_gap_threshold=15.0)

    # Aggressively trigger merged_columns 50 times
    extreme_signals = [FeedbackSignal(signal_type="merged_columns", severity=2.0) for _ in range(50)]
    tuned = tuner.tune(base_cfg, extreme_signals)

    # Must not drop below guardrail minimum of 10.0
    assert tuned.column_gap_threshold >= 10.0