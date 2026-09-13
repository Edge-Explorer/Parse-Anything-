from __future__ import annotations

import cv2
import numpy as np


def estimate_and_deskew(
    img: np.ndarray,
    deadband_deg: float = 0.75,
    max_angle_deg: float = 45.0,
) -> tuple[np.ndarray, float]:
    """
    Detect and correct angular skew in document images using Hough line estimation
    on text-line contours with table line suppression and deadband protection.

    Args:
        img: Input image as BGR, RGB, or Grayscale numpy array.
        deadband_deg: Angles with absolute value below this threshold are ignored
                      to prevent resampling blur on already-straight documents.
        max_angle_deg: Maximum allowed rotation angle (avoids 90/180-deg flipping).

    Returns:
        tuple[np.ndarray, float]: (deskewed_image, estimated_skew_angle_in_degrees)
    """
    if img is None or img.size == 0:
        return img, 0.0

    # Step 1: Grayscale conversion
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    h_img, w_img = gray.shape[:2]
    if h_img < 30 or w_img < 30:
        return img, 0.0

    # Step 2: Inverted binary threshold
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Step 3: Mask out long table ruling lines so they do not bias text skew angle
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(25, w_img // 20), 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(25, h_img // 15)))
    h_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, h_kernel)
    v_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, v_kernel)
    table_lines = cv2.bitwise_or(h_lines, v_lines)
    text_only = cv2.subtract(thresh, table_lines)

    # Step 4: Dilation to bridge characters into text-line strokes
    line_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    dilated = cv2.dilate(text_only, line_kernel, iterations=2)

    # Step 5: Hough Line angle collection
    edges = cv2.Canny(dilated, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=40, minLineLength=40, maxLineGap=10)

    angles: list[float] = []
    if lines is not None:
        for l_item in lines:
            line = l_item[0] if len(l_item.shape) > 1 or len(l_item) == 1 else l_item
            x1, y1, x2, y2 = int(line[0]), int(line[1]), int(line[2]), int(line[3])
            dx = x2 - x1
            dy = y2 - y1
            if dx != 0:
                angle_deg = float(np.degrees(np.arctan2(dy, dx)))
                while angle_deg > 45.0:
                    angle_deg -= 90.0
                while angle_deg < -45.0:
                    angle_deg += 90.0
                if abs(angle_deg) <= max_angle_deg:
                    angles.append(angle_deg)

    # Step 6: Oriented bounding box angles on dilated text components
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours:
        if cv2.contourArea(c) > 100:
            rect = cv2.minAreaRect(c)
            w_r, h_r = rect[1]
            if max(w_r, h_r) / max(1.0, min(w_r, h_r)) >= 2.0:
                ang = float(rect[2])
                if w_r < h_r:
                    ang = ang - 90.0 if ang > 0 else ang + 90.0
                while ang > 45.0:
                    ang -= 90.0
                while ang < -45.0:
                    ang += 90.0
                if abs(ang) <= max_angle_deg:
                    angles.append(ang)

    if not angles:
        return img, 0.0

    # Step 7: Consensus Gating & Dispersion Check
    # A genuine document skew produces tight angular agreement across text lines.
    # Random noise (blur/speckles) produces scattered angles with high variance.
    if len(angles) < 6:
        return img, 0.0

    raw_median = float(np.median(angles))
    consensus_angles = [a for a in angles if abs(a - raw_median) <= 2.5]

    if len(consensus_angles) < 6 or (len(consensus_angles) / len(angles)) < 0.50:
        return img, 0.0

    if float(np.std(consensus_angles)) > 3.0:
        return img, 0.0

    final_angle = float(np.median(consensus_angles))

    # Deadband protection: do not rotate if image is already straight
    if abs(final_angle) < deadband_deg:
        return img, 0.0

    # Step 8: Rotate image with bounding-box expansion and white background fill
    center = (w_img / 2.0, h_img / 2.0)
    rot_mat = cv2.getRotationMatrix2D(center, final_angle, 1.0)
    cos = np.abs(rot_mat[0, 0])
    sin = np.abs(rot_mat[0, 1])
    new_w = int((h_img * sin) + (w_img * cos))
    new_h = int((h_img * cos) + (w_img * sin))
    rot_mat[0, 2] += (new_w / 2.0) - center[0]
    rot_mat[1, 2] += (new_h / 2.0) - center[1]

    rotated = cv2.warpAffine(
        img,
        rot_mat,
        (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255) if len(img.shape) == 3 else 255,
    )
    return rotated, final_angle
