# adaptive

The universal_parser.adaptive module implements spatial layout fingerprinting, LRU configuration caching, and coordinate-descent auto-tuning.

---

## Files and Modules

| File | Purpose | Key Classes / Functions |
|---|---|---|
| ingerprint.py | Calculates 10x10 spatial layout histograms and SHA-256 hashes. | compute_fingerprint(), LayoutFingerprint |
| cache.py | LRU template configuration cache with fuzzy Cosine-Jaccard matching. | TemplateConfigCache |
| 	uner.py | Coordinate-descent optimizer for fine-tuning extraction thresholds. | uto_tune() |

---

## Technical Details

### Spatial Fingerprinting (ingerprint.py)
Computes a 2D spatial histogram by dividing page bounds into a 10x10 grid. It quantizes bounding boxes into grid cells to capture visual layout structure independently of specific textual content.

### Template Cache (cache.py)
Stores optimal extraction configurations per layout structure. Supports exact SHA-256 matching and fuzzy Jaccard similarity lookups for slightly varied document templates.

---

## Usage Example

`python
from universal_parser.adaptive.fingerprint import compute_fingerprint
from universal_parser.adaptive.cache import TemplateConfigCache

# doc = parse(...)
# fp = compute_fingerprint(doc)
`
