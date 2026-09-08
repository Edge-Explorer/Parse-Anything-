from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from pydantic import BaseModel, Field

from universal_parser.core.schema import Document


class LayoutFingerprint(BaseModel):
    """Structural layout fingerprint of a document or page template."""

    hash_digest: str
    spatial_grid: list[list[float]] = Field(default_factory=list)
    type_distribution: dict[str, float] = Field(default_factory=dict)
    page_count: int = 1
    avg_elements_per_page: float = 0.0


def compute_fingerprint(doc: Document, grid_size: int = 10) -> LayoutFingerprint:
    """Computes a content-agnostic structural layout fingerprint from a Document.
    Quantizes spatial bounding boxes into an N x N normalized occupancy matrix
    and aggregates element type proportions.
    """
    grid = [[0.0 for _ in range(grid_size)] for _ in range(grid_size)]
    type_counts: dict[str, int] = {}
    total_elements = len(doc.content_tree)

    page_count = doc.metadata.page_count or 1
    if page_count <= 0:
        page_count = 1

    # Standard document dimension reference (Letter / A4 approx: 612 x 792 pt)
    ref_w = 612.0
    ref_h = 792.0

    for idx, elem in enumerate(doc.content_tree):
        t = elem.type
        type_counts[t] = type_counts.get(t, 0) + 1

        if elem.bbox is not None:
            # Normalize coordinates to [0.0, 1.0]
            norm_x0 = max(0.0, min(1.0, elem.bbox.x0 / ref_w))
            norm_y0 = max(0.0, min(1.0, elem.bbox.y0 / ref_h))
            norm_x1 = max(0.0, min(1.0, elem.bbox.x1 / ref_w))
            norm_y1 = max(0.0, min(1.0, elem.bbox.y1 / ref_h))

            # Discretize into grid buckets
            gx0 = min(grid_size - 1, int(norm_x0 * grid_size))
            gy0 = min(grid_size - 1, int(norm_y0 * grid_size))
            gx1 = min(grid_size - 1, int(norm_x1 * grid_size))
            gy1 = min(grid_size - 1, int(norm_y1 * grid_size))

            for r in range(gy0, gy1 + 1):
                for c in range(gx0, gx1 + 1):
                    grid[r][c] += 1.0

        else:
            # Fallback for bbox-less elements: sequential normalized bucket
            pos_ratio = idx / max(1, total_elements)
            r = min(grid_size - 1, int(pos_ratio * grid_size))
            c = 0
            grid[r][c] += 1.0

    # Normalize grid density to sum to 1.0 (if non-empty)
    grid_sum = sum(sum(row) for row in grid)
    if grid_sum > 0:
        grid = [[round(val / grid_sum, 4) for val in row] for row in grid]

    # Normalize type distribution
    type_dist = (
        {k: round(v / total_elements, 4) for k, v in sorted(type_counts.items())}
        if total_elements > 0
        else {}
    )

    avg_elements = round(total_elements / page_count, 2)

    # Compute deterministic SHA-256 hash digest
    payload: dict[str, Any] = {
        "grid": grid,
        "types": type_dist,
        "page_count": page_count,
    }
    raw_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    hash_digest = hashlib.sha256(raw_bytes).hexdigest()

    return LayoutFingerprint(
        hash_digest=hash_digest,
        spatial_grid=grid,
        type_distribution=type_dist,
        page_count=page_count,
        avg_elements_per_page=avg_elements,
    )


def _vector_cosine(v1: list[float], v2: list[float]) -> float:
    """Computes cosine similarity between two flat float vectors."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 1.0 if norm1 == norm2 else 0.0
    return max(0.0, min(1.0, dot / (norm1 * norm2)))


def fingerprint_similarity(fp1: LayoutFingerprint, fp2: LayoutFingerprint) -> float:
    """Calculates a normalized similarity score in [0.0, 1.0] between two fingerprints.
    Combines spatial layout alignment (70% weight) and element type distribution (30% weight).
    """
    if fp1.hash_digest == fp2.hash_digest:
        return 1.0

    # 1. Flatten spatial grid
    flat_grid1 = [val for row in fp1.spatial_grid for val in row]
    flat_grid2 = [val for row in fp2.spatial_grid for val in row]
    spatial_sim = _vector_cosine(flat_grid1, flat_grid2)

    # 2. Type distribution similarity
    all_keys = sorted(set(fp1.type_distribution.keys()) | set(fp2.type_distribution.keys()))
    if not all_keys:
        type_sim = 1.0
    else:
        v1 = [fp1.type_distribution.get(k, 0.0) for k in all_keys]
        v2 = [fp2.type_distribution.get(k, 0.0) for k in all_keys]
        type_sim = _vector_cosine(v1, v2)

    # 3. Weighted total score
    score = 0.7 * spatial_sim + 0.3 * type_sim
    return round(max(0.0, min(1.0, score)), 4)
