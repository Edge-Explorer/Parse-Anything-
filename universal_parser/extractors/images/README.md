# universal_parser.extractors.images

The `images` sub-package provides text extraction from raster image files through an OCR pipeline powered entirely by CPU-based ONNX inference. It handles common image formats including PNG, JPEG, TIFF, BMP, and WebP. The sub-package exists because image-based documents — scanned receipts, photographs of whiteboards, screenshots of UI text, and similar inputs — cannot be parsed by any text-layer approach; they require a vision model to locate and transcribe text regions from the raw pixel data.

The implementation deliberately avoids GPU dependencies and commercial OCR APIs, keeping the extractor self-contained and functional in any CPU-only deployment environment. The single extractor in this package is also used internally by `NativePDFExtractor` (in the `pdf` sub-package) when a PDF page contains no native text layer, providing a unified OCR path across both image and PDF formats.

---

## Files

| Filename | Purpose | Key Exported Class / Function |
|---|---|---|
| `__init__.py` | Package marker | — |
| `scan_extractor.py` | OCR-based text extraction from raster images using RapidOCR | `ImageScanExtractor` |

---

## Technical Details

### ImageScanExtractor (`scan_extractor.py`)

`ImageScanExtractor` is registered for `FileType.IMAGE` and implements a three-stage pipeline: image loading and validation, optional preprocessing, and ONNX-based OCR inference.

#### Initialization and OCR Engine

The constructor calls `RapidOCR()` from `rapidocr_onnxruntime` and stores the engine as `self._ocr`. `RapidOCR` is a Python binding to the RapidOCR C++ runtime, which bundles three ONNX models:

1. **Detection model**: A text region detector (based on DB — Differentiable Binarization) that produces quadrilateral bounding boxes around candidate text regions in the image.
2. **Classification model**: A lightweight orientation classifier that determines whether detected text is upright or rotated 180 degrees.
3. **Recognition model**: A CRNN (Convolutional Recurrent Neural Network) that reads the characters within each detected and aligned text region.

All three models run as ONNX sessions using the CPU execution provider. The `RapidOCR()` instance is cached on the object so that model weights are loaded from disk only once per extractor lifetime, not once per image.

#### Image Loading

`cv2.imread(path_str)` loads the image into a `numpy.ndarray` in BGR color order. If the return value is `None` (file not found, corrupt file, or unsupported format), the extractor returns immediately without yielding any elements. OpenCV supports the full range of common raster formats (JPEG, PNG, BMP, TIFF, WebP) natively, with TIFF support requiring that OpenCV was built with libtiff.

#### Preprocessing (`_preprocess_image`)

The `_preprocess_image` method is currently a pass-through that returns the original image unchanged. This is intentional: RapidOCR's internal pipeline handles BGR-to-RGB conversion, resizing to its internal input resolution, and normalization before feeding data to the detection model. The method exists as an extension point for format-specific preprocessing that may be added in future work — such as deskewing (correcting rotated scans via Hough line detection), adaptive thresholding for low-contrast scans, or upscaling for very low resolution images.

#### OCR Inference and Output

`self._ocr(preprocessing_img)` invokes the full RapidOCR pipeline on the NumPy array. The first return value is a list of tuples; each tuple contains:

- `dt_boxes`: A list of four `[x, y]` pixel coordinate pairs forming a quadrilateral around the detected text region.
- `text`: The recognized string for that region.
- `score`: A float confidence score from the recognition model, typically in the range `[0.0, 1.0]`.

For each result, the extractor converts `dt_boxes` to a `numpy` array of shape `(4, 2)` with dtype `float32`. The axis-aligned bounding box `(x0, y0, x1, y1)` is computed as the minimum and maximum of each coordinate column:

```
x0 = min(pts[:, 0])
y0 = min(pts[:, 1])
x1 = max(pts[:, 0])
y1 = max(pts[:, 1])
```

Note that this converts the quadrilateral (which may be a rotated rectangle for angled text) to an axis-aligned bounding box. This is a deliberate simplification: downstream consumers such as the RAG chunker and knowledge graph exporter work with axis-aligned boxes, and the recognition model's correction for rotation means the recognized text itself is not affected by this coordinate simplification.

Each detected text region is yielded as a `paragraph` element with:

- `type = "paragraph"` (no semantic classification is attempted at the image level)
- `text`: the recognized string after `strip()`
- `page = 1` (images are always treated as single-page documents)
- `bbox`: a `BBox` object with the axis-aligned coordinates
- `markdown_repr`: identical to `text`
- `confidence`: the recognition model score rounded to 3 decimal places

Empty strings (after stripping) are silently skipped.

#### Error Handling

The entire `stream()` body is wrapped in a broad `except Exception` block. If any step fails — corrupt image data, an internal ONNX runtime error, an unsupported pixel format — the extractor returns cleanly without propagating the exception. This ensures that a single unreadable image in a batch never interrupts the processing of subsequent files.

---

## Code Examples

### Extracting text from a scanned image

```python
from universal_parser.extractors.images.scan_extractor import ImageScanExtractor

extractor = ImageScanExtractor()
for element in extractor.stream("scanned_receipt.png"):
    print(f"[conf={element.confidence:.2f}] bbox={element.bbox} text={element.text}")
```

### Filtering by confidence threshold

```python
from universal_parser.extractors.images.scan_extractor import ImageScanExtractor

extractor = ImageScanExtractor()
high_confidence_lines = [
    element.text for element in extractor.stream("photo.jpg") if element.confidence >= 0.85
]
print("\n".join(high_confidence_lines))
```

### Via the engine

```python
from universal_parser.core.engine import parse

doc = parse("whiteboard_photo.jpg")
for element in doc.content_tree:
    print(element.text)
```

### Processing multiple images (sharing the engine instance)

```python
from pathlib import Path
from universal_parser.extractors.images.scan_extractor import ImageScanExtractor

# Instantiate once to avoid reloading ONNX weights
extractor = ImageScanExtractor()

image_dir = Path("scans/")
for image_path in sorted(image_dir.glob("*.png")):
    print(f"--- {image_path.name} ---")
    for element in extractor.stream(image_path):
        print(element.text)
```

---

## Dependencies

| Library | Role |
|---|---|
| `rapidocr_onnxruntime` | Bundles the DB text detector, orientation classifier, and CRNN recognizer as CPU ONNX sessions |
| `opencv-python` (`cv2`) | Image file loading across all major raster formats |
| `numpy` | Quadrilateral coordinate math for bounding box computation |

---

## Notes on Accuracy

RapidOCR is trained primarily on Chinese and English text. Accuracy on other Latin-script languages is generally high. Accuracy on non-Latin scripts (Arabic, Devanagari, Japanese, etc.) depends on whether the bundled model variant includes the relevant script. For high-accuracy multilingual OCR, a model variant with the appropriate training data should be substituted.

Image resolution significantly affects accuracy. Images below approximately 100 DPI often produce degraded results. The recommended preprocessing for very low-resolution inputs is to upsample to at least 200 DPI using `cv2.resize` with bicubic or Lanczos interpolation before passing to the extractor.
