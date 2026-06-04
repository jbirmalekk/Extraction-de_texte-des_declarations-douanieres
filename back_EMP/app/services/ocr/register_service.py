"""Document registration stage for template-aligned OCR."""

from __future__ import annotations

import cv2
import numpy as np


def _order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # top-left
    rect[2] = pts[np.argmax(s)]  # bottom-right
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # top-right
    rect[3] = pts[np.argmax(diff)]  # bottom-left
    return rect


def _find_document_quad(img: np.ndarray) -> np.ndarray | None:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 60, 180)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    edges = cv2.dilate(edges, kernel, iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    h, w = img.shape[:2]
    min_area = 0.35 * h * w
    best = None
    best_area = 0

    for contour in contours:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        if len(approx) == 4 and area > best_area:
            best_area = area
            best = approx.reshape(4, 2)

    if best is None:
        return None

    return _order_points(best.astype("float32"))


def register_page(img: np.ndarray) -> tuple[np.ndarray, dict]:
    """Project page to a stable rectangle when a page quad is found.

    Returns:
        aligned_img: page image (warped if registration succeeded, original otherwise)
        metadata: registration info for observability
    """
    if img is None or (hasattr(img, "size") and img.size == 0):
        return img, {"registered": False, "reason": "empty_image"}

    h, w = img.shape[:2]
    image_area = float(h * w) if h and w else 0.0

    quad = _find_document_quad(img)
    if quad is None:
        return img, {"registered": False, "reason": "quad_not_found", "geometry_confidence": 0.25}

    (tl, tr, br, bl) = quad
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = int(max(width_a, width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = int(max(height_a, height_b))

    if max_width < 100 or max_height < 100:
        return img, {"registered": False, "reason": "invalid_warp_size", "geometry_confidence": 0.2}

    destination = np.array(
        [[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]],
        dtype="float32",
    )
    matrix = cv2.getPerspectiveTransform(quad, destination)
    warped = cv2.warpPerspective(
        img,
        matrix,
        (max_width, max_height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )

    quad_area = float(cv2.contourArea(quad.astype(np.float32)))
    area_ratio = (quad_area / image_area) if image_area else 0.0
    geometry_confidence = max(0.0, min(1.0, 0.35 + (0.65 * min(1.0, area_ratio))))

    return warped, {
        "registered": True,
        "quad": quad.tolist(),
        "output_size": {"width": int(max_width), "height": int(max_height)},
        "area_ratio": round(area_ratio, 4),
        "geometry_confidence": round(geometry_confidence, 4),
    }
