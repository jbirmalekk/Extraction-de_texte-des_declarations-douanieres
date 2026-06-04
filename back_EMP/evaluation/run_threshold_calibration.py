#!/usr/bin/env python
"""Generate predictions for multiple OCR thresholds and evaluate them."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "back_EMP"
VALID_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".pdf"}


def _ensure_imports() -> None:
    sys.path.insert(0, str(BACKEND_DIR))


def _normalize_output_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return str(value)
    return str(value).strip()


def _run_for_threshold(
    files: list[pathlib.Path],
    fields: list[str],
    threshold: float,
    fast_mode: bool,
    use_deskew: bool,
    ocr_scale: float,
) -> list[dict]:
    from app.config import settings
    from app.services.pipeline import process_document

    settings.OCR_CONFIDENCE_THRESHOLD = threshold
    rows: list[dict] = []
    for path in files:
        try:
            result = process_document(
                path.read_bytes(),
                filename=path.name,
                fast_mode=fast_mode,
                use_deskew=use_deskew,
                ocr_scale=ocr_scale,
            )
            rows.append(
                {
                    "file": path.name,
                    "result": {field: _normalize_output_value(result.get(field)) for field in fields},
                }
            )
        except Exception as exc:
            rows.append({"file": path.name, "error": str(exc), "result": {}})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Calibrate OCR fallback threshold and print a quick report.")
    parser.add_argument(
        "--ground-truth",
        required=True,
        help="Ground truth JSON path (list of {'file','expected'} entries).",
    )
    parser.add_argument(
        "--assets-dir",
        required=True,
        help="Directory containing images/PDF documents referenced in ground truth.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(BACKEND_DIR / "evaluation"),
        help="Directory where predictions/report files are written.",
    )
    parser.add_argument(
        "--thresholds",
        default="0.58,0.62,0.68",
        help="Comma-separated threshold candidates.",
    )
    parser.add_argument(
        "--fields",
        default="numero_declaration,date_declaration,importateur_nom,poids_brut,poids_net,code_gdt,montant_liquidation,cle_authentification",
        help="Fields included in predictions/evaluation.",
    )
    parser.add_argument(
        "--critical-fields",
        default="numero_declaration,date_declaration,exportateur_nom,importateur_nom,declarant_nom,num_repertoire,code_gdt,cle_authentification",
        help="Critical fields used for KPI.",
    )
    parser.add_argument("--fast-mode", action="store_true", help="Enable fast OCR mode.")
    parser.add_argument("--no-deskew", action="store_true", help="Disable deskew.")
    parser.add_argument("--ocr-scale", type=float, default=2.0, help="OCR scale factor.")
    args = parser.parse_args()

    _ensure_imports()
    from evaluation.evaluate_ocr import _compute_report

    ground_truth_path = pathlib.Path(args.ground_truth)
    assets_dir = pathlib.Path(args.assets_dir)
    output_dir = pathlib.Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ground_truth = json.loads(ground_truth_path.read_text(encoding="utf-8"))
    fields = [f.strip() for f in args.fields.split(",") if f.strip()]
    critical_fields = [f.strip() for f in args.critical_fields.split(",") if f.strip()]
    thresholds = [float(t.strip()) for t in args.thresholds.split(",") if t.strip()]

    gt_files = {row.get("file") for row in ground_truth if row.get("file")}
    files = [
        p
        for p in sorted(assets_dir.iterdir())
        if p.is_file() and p.suffix.lower() in VALID_EXT and p.name in gt_files
    ]

    if not files:
        raise SystemExit("No matching files found in assets-dir for provided ground-truth entries.")

    calibration = []
    for threshold in thresholds:
        print(f"[calibration] running threshold={threshold}", flush=True)
        predictions = _run_for_threshold(
            files,
            fields,
            threshold,
            fast_mode=args.fast_mode,
            use_deskew=not args.no_deskew,
            ocr_scale=args.ocr_scale,
        )
        pred_path = output_dir / f"predictions_{threshold:.2f}.json"
        pred_path.write_text(json.dumps(predictions, indent=2, ensure_ascii=False), encoding="utf-8")
        report = _compute_report(predictions, ground_truth, fields, critical_fields)
        calibration.append(
            {
                "threshold": round(threshold, 2),
                "predictions_file": str(pred_path),
                "critical_f1": report["summary"]["critical_f1"],
                "macro_f1": report["summary"]["macro_f1"],
                "critical_target_80_reached": report["summary"]["critical_target_80_reached"],
            }
        )

    best = max(calibration, key=lambda item: (item["critical_f1"], item["macro_f1"]))
    summary = {"calibration": calibration, "recommended_threshold": best["threshold"]}
    report_path = output_dir / "calibration_report.json"
    report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"[calibration] report saved: {report_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
