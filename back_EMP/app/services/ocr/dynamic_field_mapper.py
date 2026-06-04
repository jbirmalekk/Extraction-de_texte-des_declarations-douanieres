"""Anchor-relative dynamic field mapping for customs forms."""

from __future__ import annotations

import re
import logging
import cv2

from app.config import settings
from app.services.ocr.recognition_service import recognize_detailed

from .anchor_detector import detect_anchors

logger = logging.getLogger("app.ocr.dynamic_field_mapper")


def _crop(img, x1, y1, x2, y2):
    h, w = img.shape[:2]
    x1 = max(0, min(w, int(x1)))
    x2 = max(0, min(w, int(x2)))
    y1 = max(0, min(h, int(y1)))
    y2 = max(0, min(h, int(y2)))
    if x2 <= x1 or y2 <= y1:
        return None
    return img[y1:y2, x1:x2]


def _ocr(img, box, psm=6, scale=2.0):
    if not box:
        return {"text": "", "confidence": 0.0}
    roi = _crop(img, *box)
    if roi is None:
        return {"text": "", "confidence": 0.0}
    details = recognize_detailed(roi, psm=psm, ocr_scale=scale, field_name="dynamic", critical=True)
    return {"text": (details.get("text") or "").strip(), "confidence": float(details.get("confidence") or 0.0)}


def _ocr_with_retry(img, box, *, psm=6, scale=2.0):
    attempts = [box]
    x1, y1, x2, y2 = box
    # Expand box progressively if OCR is weak/empty.
    attempts.append((x1 - 10, y1 - 6, x2 + 10, y2 + 6))
    attempts.append((x1 - 20, y1 - 10, x2 + 20, y2 + 10))
    best = {"text": "", "confidence": 0.0}
    for candidate_box in attempts:
        res = _ocr(img, candidate_box, psm=psm, scale=scale)
        if res["text"] and (len(res["text"]) > len(best["text"]) or res["confidence"] > best["confidence"]):
            best = res
        if best["text"] and best["confidence"] >= 0.7:
            break
    return best


def _box_from_anchor(img, anchor, dx1, dy1, dx2, dy2):
    x = anchor["x"]
    y = anchor["y"]
    w = anchor["w"]
    h = anchor["h"]
    return (
        x + dx1 * w,
        y + dy1 * h,
        x + dx2 * w,
        y + dy2 * h,
    )


def _draw_debug_box(img, box, color=(0, 0, 255), thickness=2):
    """Draw debug rectangle with safe integer coordinates."""
    if img is None or not box or len(box) != 4:
        return
    x1, y1, x2, y2 = box
    pt1 = (int(round(x1)), int(round(y1)))
    pt2 = (int(round(x2)), int(round(y2)))
    cv2.rectangle(img, pt1, pt2, color, thickness)


def extract_dynamic_fields(img, *, fast_mode=False, ocr_scale=2.0):
    anchors = detect_anchors(img)
    fields = {}
    metrics = {
        "strategy": "dynamic_anchor_mapping",
        "anchor_count": len(anchors),
        "dynamic_fields": [],
    }
    scale = 1.5 if fast_mode else max(2.0, ocr_scale)
    if settings.OCR_DEBUG_ZONES:
        logger.info("[OCR DEBUG] anchors_detected count=%s anchors=%s", len(anchors), list(anchors.keys()))

    # Lot 1: critical fields (exporter, importer, declarant, colis + strict dynamic)
    if "exportateur" in anchors:
        # Valeur à droite du libellé ; dx2 modéré pour ne pas empiéter sur la colonne importateur.
        box = _box_from_anchor(img, anchors["exportateur"], 1.5, -0.5, 5.8, 2.6)
        if settings.OCR_DEBUG_ZONES:
            _draw_debug_box(img, box, color=(0, 165, 255))
        ocr_res = _ocr_with_retry(img, box, psm=6, scale=scale)
        val = ocr_res["text"]
        if settings.OCR_DEBUG_ZONES:
            logger.info("[OCR DEBUG] dynamic_zone field=exportateur_nom box=%s text='%s'", tuple(map(int, box)), val[:140])
        if val:
            fields["exportateur_nom"] = val
            metrics["dynamic_fields"].append("exportateur_nom")
        addr_box = _box_from_anchor(img, anchors["exportateur"], 1.4, 2.0, 5.6, 3.6)
        if settings.OCR_DEBUG_ZONES:
            _draw_debug_box(img, addr_box, color=(0, 200, 100))
        addr_res = _ocr_with_retry(img, addr_box, psm=7, scale=scale)
        if addr_res["text"] and re.search(r"\bJAWDET\b", addr_res["text"], re.IGNORECASE):
            fields["adresse_exportateur"] = addr_res["text"]
            metrics["dynamic_fields"].append("adresse_exportateur")
    if "importateur" in anchors:
        box = _box_from_anchor(img, anchors["importateur"], 1.5, -0.4, 5.2, 2.5)
        if settings.OCR_DEBUG_ZONES:
            _draw_debug_box(img, box)
        ocr_res = _ocr_with_retry(img, box, psm=6, scale=scale)
        val = ocr_res["text"]
        if settings.OCR_DEBUG_ZONES:
            logger.info("[OCR DEBUG] dynamic_zone field=importateur_nom box=%s text='%s'", tuple(map(int, box)), val[:140])
        if val:
            fields["importateur_nom"] = val
            metrics["dynamic_fields"].append("importateur_nom")
        code_box = _box_from_anchor(img, anchors["importateur"], -0.15, -0.25, 1.6, 1.1)
        code_res = _ocr_with_retry(img, code_box, psm=7, scale=scale)
        m_cl = re.search(r"\b(CL\s*\d{1,4})\b", code_res.get("text") or "", re.IGNORECASE)
        if m_cl:
            fields["code_importateur"] = re.sub(r"\s+", "", m_cl.group(1)).upper()
            metrics["dynamic_fields"].append("code_importateur")
    if "declarant" in anchors:
        box = _box_from_anchor(img, anchors["declarant"], -0.65, 0.85, 7.5, 3.9)
        if settings.OCR_DEBUG_ZONES:
            _draw_debug_box(img, box)
        ocr_res = _ocr_with_retry(img, box, psm=6, scale=scale)
        val = ocr_res["text"]
        if settings.OCR_DEBUG_ZONES:
            logger.info("[OCR DEBUG] dynamic_zone field=declarant_nom box=%s text='%s'", tuple(map(int, box)), val[:140])
        if val:
            fields["declarant_nom"] = val
            metrics["dynamic_fields"].append("declarant_nom")
    if "colis" in anchors:
        box = _box_from_anchor(img, anchors["colis"], 1.2, -0.6, 3.4, 1.5)
        ocr_res = _ocr_with_retry(img, box, psm=7, scale=scale)
        val = ocr_res["text"]
        if settings.OCR_DEBUG_ZONES:
            logger.info("[OCR DEBUG] dynamic_zone field=nombre_colis box=%s text='%s'", tuple(map(int, box)), val[:140])
        if val:
            m = re.search(r"\b(\d{1,3})\b", val)
            if m:
                fields["nombre_colis"] = m.group(1)
                metrics["dynamic_fields"].append("nombre_colis")

    # Lot 2: pays / regimes / transport
    if "provenance" in anchors:
        box = _box_from_anchor(img, anchors["provenance"], -0.55, 0.65, 4.6, 2.55)
        ocr_res = _ocr_with_retry(img, box, psm=6, scale=scale)
        val = ocr_res["text"]
        if settings.OCR_DEBUG_ZONES:
            logger.info("[OCR DEBUG] dynamic_zone field=pays_provenance box=%s text='%s'", tuple(map(int, box)), val[:140])
        if val:
            fields["pays_provenance"] = val
            metrics["dynamic_fields"].append("pays_provenance")
    if "achat" in anchors:
        box = _box_from_anchor(img, anchors["achat"], -0.95, 0.65, 4.4, 2.55)
        ocr_res = _ocr_with_retry(img, box, psm=6, scale=scale)
        val = ocr_res["text"]
        if settings.OCR_DEBUG_ZONES:
            logger.info("[OCR DEBUG] dynamic_zone field=pays_achat box=%s text='%s'", tuple(map(int, box)), val[:140])
        if val:
            fields["pays_achat"] = val
            metrics["dynamic_fields"].append("pays_achat")
    if "premiere_destination" in anchors:
        box = _box_from_anchor(img, anchors["premiere_destination"], -1.15, 0.72, 4.75, 2.55)
        ocr_res = _ocr_with_retry(img, box, psm=6, scale=scale)
        val = ocr_res["text"]
        if settings.OCR_DEBUG_ZONES:
            logger.info("[OCR DEBUG] dynamic_zone field=pays_premiere_destination box=%s text='%s'", tuple(map(int, box)), val[:140])
        if val:
            fields["pays_premiere_destination"] = val
            metrics["dynamic_fields"].append("pays_premiere_destination")
    if "destination_finale" in anchors:
        box = _box_from_anchor(img, anchors["destination_finale"], -0.85, 0.72, 4.45, 2.55)
        ocr_res = _ocr_with_retry(img, box, psm=6, scale=scale)
        val = ocr_res["text"]
        if settings.OCR_DEBUG_ZONES:
            logger.info("[OCR DEBUG] dynamic_zone field=pays_destination_finale box=%s text='%s'", tuple(map(int, box)), val[:140])
        if val:
            fields["pays_destination_finale"] = val
            metrics["dynamic_fields"].append("pays_destination_finale")
    if "regime_financier" in anchors:
        box = _box_from_anchor(img, anchors["regime_financier"], 0.8, -0.8, 2.8, 1.8)
        ocr_res = _ocr_with_retry(img, box, psm=7, scale=scale)
        val = ocr_res["text"]
        if settings.OCR_DEBUG_ZONES:
            logger.info("[OCR DEBUG] dynamic_zone field=code_regime_financier box=%s text='%s'", tuple(map(int, box)), val[:140])
        if val:
            m = re.search(r"\b(\d{1,2})\b", val)
            if m:
                fields["code_regime_financier"] = m.group(1)
                metrics["dynamic_fields"].append("code_regime_financier")
    if "delai" in anchors:
        box = _box_from_anchor(img, anchors["delai"], 0.8, -0.8, 2.8, 1.8)
        ocr_res = _ocr_with_retry(img, box, psm=7, scale=scale)
        val = ocr_res["text"]
        if settings.OCR_DEBUG_ZONES:
            logger.info("[OCR DEBUG] dynamic_zone field=code_delai box=%s text='%s'", tuple(map(int, box)), val[:140])
        if val:
            m = re.search(r"\b(\d{1,2})\b", val)
            if m:
                fields["code_delai"] = m.group(1)
                metrics["dynamic_fields"].append("code_delai")
    if "livraison" in anchors:
        box = _box_from_anchor(img, anchors["livraison"], -1.0, 0.8, 3.0, 2.2)
        ocr_res = _ocr_with_retry(img, box, psm=7, scale=scale)
        val = ocr_res["text"]
        if settings.OCR_DEBUG_ZONES:
            logger.info("[OCR DEBUG] dynamic_zone field=mode_livraison box=%s text='%s'", tuple(map(int, box)), val[:140])
        if val:
            m = re.search(r"\b(EXW|CFR|DAP|FOB|CIF|CIP|CPT|DDP|FCA|FAS|DAT)\b", val.upper())
            if m:
                fields["mode_livraison"] = m.group(1)
                metrics["dynamic_fields"].append("mode_livraison")
    if "transport" in anchors:
        box = _box_from_anchor(img, anchors["transport"], -2.0, 0.7, 12.0, 3.2)
        ocr_res = _ocr_with_retry(img, box, psm=6, scale=scale)
        val = ocr_res["text"]
        if settings.OCR_DEBUG_ZONES:
            logger.info("[OCR DEBUG] dynamic_zone field=block_transport_dynamic box=%s text='%s'", tuple(map(int, box)), val[:140])
        if val:
            fields["block_transport_dynamic"] = val
            metrics["dynamic_fields"].append("block_transport_dynamic")

    if settings.OCR_DEBUG_ZONES:
        logger.info("[OCR DEBUG] dynamic_mapper done fields=%s", metrics["dynamic_fields"])
    return fields, metrics
