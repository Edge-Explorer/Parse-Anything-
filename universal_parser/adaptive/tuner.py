from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from universal_parser.adaptive.config_cache import ParserConfig

SignalType = Literal[
    "missed_heading",
    "false_heading",
    "missed_table",
    "false_table",
    "merged_columns",
    "split_columns",
    "ocr_quality",
]


class FeedbackSignal(BaseModel):
    """User-flagged or auto-detected parsing error signal."""

    signal_type: SignalType
    severity: float = 1.0  # Learning step multiplier (0.1 - 2.0)
    details: dict[str, Any] = Field(default_factory=dict)


# Hard mathematical boundaries to prevent degenerate parameter drift
GUARD_RAILS: dict[str, tuple[float, float]] = {
    "column_gap_threshold": (10.0, 120.0),
    "heading_p95_ratio": (1.05, 3.00),
    "heading_p85_ratio": (1.01, 2.50),
    "min_table_confidence": (0.30, 0.95),
    "ocr_dpi": (100.0, 300.0),
}


class AdaptiveTuner:
    """Heuristic optimizer that adjusts ParserConfig parameters based on feedback signals."""

    @staticmethod
    def _clamp(param_name: str, value: float) -> float:
        if param_name in GUARD_RAILS:
            min_val, max_val = GUARD_RAILS[param_name]
            return max(min_val, min(max_val, value))
        return value

    def tune(
        self,
        current_config: ParserConfig,
        signals: list[FeedbackSignal],
        base_step: float = 0.05,
    ) -> ParserConfig:
        """Calculates parameter adjustments from feedback signals while strictly respecting guardrails."""
        cfg = current_config.model_copy(deep=True)

        for sig in signals:
            step = base_step * max(0.1, min(2.0, sig.severity))

            if sig.signal_type == "missed_heading":
                # Lower heading thresholds to make heading detection more sensitive
                cfg.heading_p95_ratio -= step * 0.5
                cfg.heading_p85_ratio -= step * 0.4
            elif sig.signal_type == "false_heading":
                # Raise heading thresholds to require larger font difference
                cfg.heading_p95_ratio += step * 0.5
                cfg.heading_p85_ratio += step * 0.4
            elif sig.signal_type == "missed_table":
                # Lower table confidence requirement or switch to stream mode
                cfg.min_table_confidence -= step * 0.5
                if cfg.min_table_confidence < 0.5:
                    cfg.table_detection_mode = "stream"
            elif sig.signal_type == "false_table":
                # Increase table confidence threshold
                cfg.min_table_confidence += step * 0.5
            elif sig.signal_type == "merged_columns":
                # Columns were incorrectly merged -> reduce gap threshold to split columns more aggressively
                cfg.column_gap_threshold -= step * 20.0
            elif sig.signal_type == "split_columns":
                # Single column was falsely split into multi-column -> increase gap threshold
                cfg.column_gap_threshold += step * 20.0
            elif sig.signal_type == "ocr_quality":
                # Higher resolution for OCR rasterization
                cfg.ocr_dpi = int(min(300, cfg.ocr_dpi + 50))

        # Apply guardrail clamping and rounding
        cfg.column_gap_threshold = round(
            self._clamp("column_gap_threshold", cfg.column_gap_threshold), 2
        )
        cfg.heading_p95_ratio = round(self._clamp("heading_p95_ratio", cfg.heading_p95_ratio), 3)
        cfg.heading_p85_ratio = round(self._clamp("heading_p85_ratio", cfg.heading_p85_ratio), 3)
        cfg.min_table_confidence = round(
            self._clamp("min_table_confidence", cfg.min_table_confidence), 3
        )
        cfg.ocr_dpi = int(self._clamp("ocr_dpi", float(cfg.ocr_dpi)))

        return cfg
