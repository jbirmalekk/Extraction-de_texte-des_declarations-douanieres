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


def _load_pdf_all_pages(pdf_bytes, poppler_path=None):
    """
    Charge TOUTES les pages d'un PDF.
    Retourne une liste d'images OpenCV BGR.
    """
    from pdf2image import convert_from_bytes

    try:
        pages = convert_from_bytes(
            pdf_bytes,
            dpi=300,                    # meilleure lisibilité OCR pour petits caractères
            poppler_path=poppler_path,
        )
    except Exception:
        pages = convert_from_bytes(pdf_bytes, dpi=300)

    return [_pil_to_bgr(page) for page in pages if page]


def load_image(path_or_bytes):
    """
    Retourne maintenant une LISTE d'images (une par page).
    Pour les images normales : liste d'un seul élément.
    """
    try:
        if isinstance(path_or_bytes, str):
            pil_img = Image.open(path_or_bytes)
            return [_pil_to_bgr(pil_img)]

        if isinstance(path_or_bytes, (bytes, bytearray)):
            raw = bytes(path_or_bytes)

            # PDF → toutes les pages
            if raw.startswith(b"%PDF"):
                poppler_path = getattr(settings, "POPPLER_PATH", None) or None
                pages = _load_pdf_all_pages(raw, poppler_path)
                return pages if pages else []

            # Image normale → liste d'un seul élément
            pil_img = Image.open(io.BytesIO(raw))
            return [_pil_to_bgr(pil_img)]

        if hasattr(path_or_bytes, "read"):
            return load_image(path_or_bytes.read())

        pil_img = Image.open(path_or_bytes)
        return [_pil_to_bgr(pil_img)]

    except Exception as e:
        print(f"Erreur chargement image: {e}")
        return []
    
def enhance_scan(img: np.ndarray) -> np.ndarray:
    """Contraste local + netteté légère avant OCR (partie 6)."""
    if img is None or not isinstance(img, np.ndarray) or img.size == 0:
        return img
    if len(img.shape) == 2:
        gray = img
    else:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    blur = cv2.GaussianBlur(enhanced, (0, 0), 1.0)
    sharp = cv2.addWeighted(enhanced, 1.35, blur, -0.35, 0)
    if len(img.shape) == 2:
        return sharp
    return cv2.cvtColor(sharp, cv2.COLOR_GRAY2BGR)


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
    
    # Le texte est sombre (0) sur fond clair (255) après seuillage binaire.
    # Utiliser les pixels de texte évite de mesurer l'angle du fond de page.
    coords = np.column_stack(np.where(thresh < 128))
    
    if len(coords) == 0:
        # Image vide ou aucun pixel blanc
        print("⚠️ Warning: No white pixels found in thresh, returning original")
        return thresh
    
    angle  = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Evite les rotations destructrices dues au bruit OCR.
    if abs(angle) < 0.2 or abs(angle) > 15:
        return thresh
    (h, w) = thresh.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(
        thresh, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )