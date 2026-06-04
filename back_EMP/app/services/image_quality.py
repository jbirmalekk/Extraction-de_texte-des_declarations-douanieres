"""Image quality checks to gate OCR confidence."""

from __future__ import annotations

import cv2
import numpy as np


def assess_image_quality(img: np.ndarray) -> tuple[dict[str, float], list[str]]:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Sharpness proxy: variance of Laplacian.
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    contrast_score = float(gray.std())
    brightness = float(gray.mean())

    flags: list[str] = []
    if blur_score < 35:
        flags.append("image_blurry")
    if contrast_score < 28:
        flags.append("low_contrast")
    if brightness < 55:
        flags.append("underexposed")
    elif brightness > 220:
        flags.append("overexposed")

    h, w = gray.shape[:2]
    dpi_w = w / 8.27
    dpi_h = h / 11.69
    estimated_dpi = round(min(dpi_w, dpi_h), 1)

    metrics = {
        "width_px": w,
        "height_px": h,
        "estimated_dpi": estimated_dpi,
        "blur_score": round(blur_score, 2),
        "contrast_score": round(contrast_score, 2),
        "brightness": round(brightness, 2),
    }
    return metrics, flags
