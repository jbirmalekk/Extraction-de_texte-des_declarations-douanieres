# Copie exacte de la Cellule 5 du notebook
import io

import cv2
import numpy as np
from PIL import Image

from app.config import settings


def _pil_to_bgr(pil_img):
    """Convertit une image PIL vers ndarray OpenCV BGR."""
    return cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)


def _load_pdf_first_page(pdf_bytes):
    """Charge la 1ere page d'un PDF en image OpenCV BGR."""
    from pdf2image import convert_from_bytes

    # Essaye d'abord avec POPPLER_PATH si configure, sinon fallback auto.
    poppler_path = settings.POPPLER_PATH or None

    try:
        pages = convert_from_bytes(
            pdf_bytes,
            first_page=1,
            last_page=1,
            poppler_path=poppler_path,
        )
    except Exception:
        pages = convert_from_bytes(
            pdf_bytes,
            first_page=1,
            last_page=1,
        )

    if not pages:
        return None

    return _pil_to_bgr(pages[0])


def load_image(path_or_bytes):
    """
    Charge une image depuis un chemin ou des bytes.
    Gere les accents et espaces dans les chemins.
    """
    try:
        # Cas 1: chemin local
        if isinstance(path_or_bytes, str):
            pil_img = Image.open(path_or_bytes)
            return _pil_to_bgr(pil_img)

        # Cas 2: bytes/bytearray provenant de FastAPI UploadFile
        if isinstance(path_or_bytes, (bytes, bytearray)):
            raw = bytes(path_or_bytes)

            # PDF: on convertit la 1ere page en image
            if raw.startswith(b"%PDF"):
                return _load_pdf_first_page(raw)

            # Image binaire (jpg/png/tiff)
            pil_img = Image.open(io.BytesIO(raw))
            return _pil_to_bgr(pil_img)

        # Cas 3: objet fichier-like
        if hasattr(path_or_bytes, "read"):
            data = path_or_bytes.read()
            return load_image(data)

        # Fallback PIL
        pil_img = Image.open(path_or_bytes)
        return _pil_to_bgr(pil_img)
    except Exception as e:
        print(f"Erreur chargement image: {e}")
        return None


def preprocess(img):
    gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur  = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(
        blur, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    return thresh


def deskew(thresh):
    """
    Deskew (correction de l'inclinaison) de l'image.
    
    Args:
        thresh: Image binarisée (numpy array)
    
    Returns:
        Image deskewed (numpy array)
    
    Raises:
        ValueError: Si thresh n'est pas un numpy array
    """
    # Validation
    if not isinstance(thresh, np.ndarray):
        raise ValueError(f"thresh must be numpy.ndarray, got {type(thresh)}")
    
    if thresh.size == 0:
        raise ValueError("thresh is empty")
    
    coords = np.column_stack(np.where(thresh > 0))
    
    if len(coords) == 0:
        # Image vide ou aucun pixel blanc
        print("⚠️ Warning: No white pixels found in thresh, returning original")
        return thresh
    
    angle  = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = thresh.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(
        thresh, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )