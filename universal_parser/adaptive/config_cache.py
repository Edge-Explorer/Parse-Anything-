from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path
from threading import Lock
from typing import Any

from pydantic import BaseModel, Field

from universal_parser.adaptive.fingerprint import (
    LayoutFingerprint,
    fingerprint_similarity,
)


class ParserConfig(BaseModel):
    """Hyperparameters and configuration tuned for a specific document layout template."""

    column_gap_threshold: float = 30.0
    heading_p95_ratio: float = 1.30
    heading_p85_ratio: float = 1.15
    table_detection_mode: str = "auto"  # "lattice", "stream", "auto"
    ocr_dpi: int = 150
    min_table_confidence: float = 0.60
    custom_overrides: dict[str, Any] = Field(default_factory=dict)


class TemplateConfigCache:
    """Thread-safe, LRU cache for template fingerprints and parser configurations."""

    def __init__(self, capacity: int = 1000) -> None:
        self.capacity = capacity
        self._cache: OrderedDict[str, tuple[LayoutFingerprint, ParserConfig]] = OrderedDict()
        self._lock = Lock()

    def get_exact(self, hash_digest: str) -> ParserConfig | None:
        """Retrieves matching ParserConfig strictly by exact SHA-256 hash."""
        with self._lock:
            if hash_digest in self._cache:
                self._cache.move_to_end(hash_digest)
                _, config = self._cache[hash_digest]
                return config.model_copy(deep=True)
            return None

    def get(
        self, fingerprint: LayoutFingerprint, similarity_threshold: float = 0.85
    ) -> tuple[str, ParserConfig] | None:
        """Retrieves matching ParserConfig either by exact hash or best fuzzy match >= similarity_threshold."""
        with self._lock:
            # 1. Exact match
            if fingerprint.hash_digest in self._cache:
                self._cache.move_to_end(fingerprint.hash_digest)
                _, config = self._cache[fingerprint.hash_digest]
                return fingerprint.hash_digest, config.model_copy(deep=True)

            # 2. Fuzzy similarity search
            best_match_key: str | None = None
            best_score = 0.0
            best_config: ParserConfig | None = None

            for key, (cached_fp, cached_cfg) in self._cache.items():
                sim = fingerprint_similarity(fingerprint, cached_fp)
                if sim > best_score:
                    best_score = sim
                    best_match_key = key
                    best_config = cached_cfg

            if (
                best_match_key is not None
                and best_score >= similarity_threshold
                and best_config is not None
            ):
                self._cache.move_to_end(best_match_key)
                return best_match_key, best_config.model_copy(deep=True)

            return None

    def set(self, fingerprint: LayoutFingerprint, config: ParserConfig) -> None:
        """Saves or updates a template fingerprint and its tuned configuration."""
        with self._lock:
            if fingerprint.hash_digest in self._cache:
                self._cache.move_to_end(fingerprint.hash_digest)
            self._cache[fingerprint.hash_digest] = (
                fingerprint,
                config.model_copy(deep=True),
            )
            if len(self._cache) > self.capacity:
                self._cache.popitem(last=False)

    def save(self, file_path: str | Path) -> None:
        """Serializes cached template configurations to a JSON file."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            data = {}
            for digest, (fp, cfg) in self._cache.items():
                data[digest] = {
                    "fingerprint": fp.model_dump(),
                    "config": cfg.model_dump(),
                }
            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

    def load(self, file_path: str | Path) -> None:
        """Loads template configurations from a JSON file."""
        path = Path(file_path)
        if not path.is_file():
            return

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        with self._lock:
            self._cache.clear()
            for digest, payload in data.items():
                fp = LayoutFingerprint.model_validate(payload["fingerprint"])
                cfg = ParserConfig.model_validate(payload["config"])
                self._cache[digest] = (fp, cfg)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)
