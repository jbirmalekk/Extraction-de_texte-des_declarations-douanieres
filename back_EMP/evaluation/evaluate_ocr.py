#!/usr/bin/env python
"""Evaluate OCR extraction against a ground-truth JSON corpus."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def _normalize(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def _safe_div(a: float, b: float) -> float:
    return (a / b) if b else 0.0


def _compute_report(predictions, ground_truth, fields, critical_fields):
    pred_by_file = {row["file"]: row.get("result", {}) for row in predictions}
    gt_by_file = {row["file"]: row.get("expected", {}) for row in ground_truth}

    report = {}
    for field in fields:
        tp = fp = fn = 0
        for filename, gt in gt_by_file.items():
            pred = pred_by_file.get(filename, {})
            gt_value = _normalize(gt.get(field))
            pred_value = _normalize(pred.get(field))

            if gt_value and pred_value == gt_value:
                tp += 1
            elif gt_value and pred_value != gt_value:
                fn += 1
                if pred_value:
                    fp += 1
            elif not gt_value and pred_value:
                fp += 1

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        report[field] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "coverage": round(_safe_div(tp + fp, max(1, len(gt_by_file))), 4),
        }

    f1_values = [row["f1"] for row in report.values()]
    macro_f1 = _safe_div(sum(f1_values), len(f1_values))
    critical_scores = [report[f]["f1"] for f in critical_fields if f in report]
    critical_f1 = _safe_div(sum(critical_scores), len(critical_scores))
    critical_pass = critical_f1 >= 0.80
    summary = {
        "documents": len(gt_by_file),
        "macro_f1": round(macro_f1, 4),
        "critical_f1": round(critical_f1, 4),
        "critical_target_80_reached": critical_pass,
    }
    return {"summary": summary, "fields": report}


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate OCR predictions by field.")
    parser.add_argument("--predictions", required=True, help="Path to predictions JSON")
    parser.add_argument("--ground-truth", required=True, help="Path to ground truth JSON")
    parser.add_argument(
        "--fields",
        default="numero_declaration,date_declaration,importateur_nom,poids_brut,poids_net,code_gdt,montant_liquidation,cle_authentification",
        help="Comma-separated fields to evaluate",
    )
    parser.add_argument(
        "--critical-fields",
        default="numero_declaration,date_declaration,exportateur_nom,importateur_nom,declarant_nom,num_repertoire,code_gdt,cle_authentification",
        help="Comma-separated critical fields for primary KPI",
    )
    parser.add_argument(
        "--calibrate-threshold",
        action="store_true",
        help="Compare multiple predictions files generated with thresholds 0.58/0.62/0.68",
    )
    parser.add_argument(
        "--predictions-pattern",
        default="",
        help="Pattern with {threshold} placeholder, e.g. predictions_{threshold}.json",
    )
    parser.add_argument(
        "--thresholds",
        default="0.58,0.62,0.68",
        help="Comma-separated thresholds used for calibration mode",
    )
    args = parser.parse_args()

    predictions = json.loads(Path(args.predictions).read_text(encoding="utf-8"))
    ground_truth = json.loads(Path(args.ground_truth).read_text(encoding="utf-8"))
    fields = [f.strip() for f in args.fields.split(",") if f.strip()]
    critical_fields = [f.strip() for f in args.critical_fields.split(",") if f.strip()]

    if args.calibrate_threshold:
        if not args.predictions_pattern or "{threshold}" not in args.predictions_pattern:
            raise SystemExit("--predictions-pattern must contain {threshold} in calibration mode")
        thresholds = [t.strip() for t in args.thresholds.split(",") if t.strip()]
        calibration = []
        for threshold in thresholds:
            path = args.predictions_pattern.format(threshold=threshold)
            pred_rows = json.loads(Path(path).read_text(encoding="utf-8"))
            report = _compute_report(pred_rows, ground_truth, fields, critical_fields)
            calibration.append(
                {
                    "threshold": threshold,
                    "critical_f1": report["summary"]["critical_f1"],
                    "macro_f1": report["summary"]["macro_f1"],
                    "critical_target_80_reached": report["summary"]["critical_target_80_reached"],
                }
            )
        best = max(calibration, key=lambda item: (item["critical_f1"], item["macro_f1"]))
        output = {
            "calibration": calibration,
            "recommended_threshold": best["threshold"],
            "critical_f1_stddev": round(
                statistics.pstdev([float(x["critical_f1"]) for x in calibration]) if len(calibration) > 1 else 0.0,
                6,
            ),
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 0

    result = _compute_report(predictions, ground_truth, fields, critical_fields)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
