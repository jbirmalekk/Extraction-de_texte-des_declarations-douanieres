# Copie exacte de la Cellule 9 du notebook
import cv2
import re
import pytesseract
import os

# Windows : chemin Tesseract
if os.name == "nt":
    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )


def ocr_zone_img(roi, psm=6, ocr_scale=1.5, lang="fra+eng"):
    if roi is None or roi.size == 0:
        return ""
    try:
        roi_big = cv2.resize(roi, None, fx=ocr_scale, fy=ocr_scale,
                             interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(roi_big, cv2.COLOR_BGR2GRAY)
        _, th = cv2.threshold(gray, 0, 255,
                              cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        best = ""
        for cfg in [f"--psm {psm} -l {lang}",
                    f"--psm 4 -l {lang}",
                    f"--psm 11 -l {lang}"]:
            try:
                t = pytesseract.image_to_string(th, config=cfg).strip()
                if len(t) > len(best):
                    best = t
            except:
                pass
        return best
    except:
        return ""


def clean_text(text):
    text = re.sub(
        r'[^\x00-\x7F\u00C0-\u024F\n\r\s:\/\-\.\,\(\)°\d]', ' ', text
    )
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()