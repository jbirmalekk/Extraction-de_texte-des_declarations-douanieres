#!/usr/bin/env python
"""Unified OCR runner for local assets/testing."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError


ROOT_DIR = pathlib.Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "back_EMP"
ASSETS_DEFAULT = ROOT_DIR / "front_EMP" / "src" / "assets"
VALID_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".pdf"}


def _ensure_imports() -> None:
    sys.path.insert(0, str(BACKEND_DIR))


def _extract_summary(payload: dict) -> dict:
    keys = (
        "numero_declaration",
        "date_declaration",
        "exportateur_nom",
        "importateur_nom",
        "code_importateur",
        "mode_transport",
    )
    return {k: payload.get(k) for k in keys}


def run_file(path: pathlib.Path, fast_mode: bool, use_deskew: bool, ocr_scale: float) -> dict:
    from app.services.pipeline import process_document

    result = process_document(
        path.read_bytes(),
        filename=path.name,
        fast_mode=fast_mode,
        use_deskew=use_deskew,
        ocr_scale=ocr_scale,
    )
    return _extract_summary(result)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OCR pipeline on local files.")
    parser.add_argument("--assets-dir", default=str(ASSETS_DEFAULT), help="Directory containing OCR input files.")
    parser.add_argument("--fast-mode", action="store_true", help="Enable fast OCR mode.")
    parser.add_argument("--no-deskew", action="store_true", help="Disable deskew step.")
    parser.add_argument("--ocr-scale", type=float, default=2.0, help="OCR scale factor.")
    parser.add_argument("--timeout", type=int, default=45, help="Per-file timeout in seconds.")
    parser.add_argument("--output", default=str(ROOT_DIR / "ocr_results.json"), help="Output JSON file path.")
    args = parser.parse_args()

    assets_dir = pathlib.Path(args.assets_dir)
    output_file = pathlib.Path(args.output)
    use_deskew = not args.no_deskew

    _ensure_imports()

    if not assets_dir.exists():
        print(json.dumps({"error": f"Assets dir not found: {assets_dir}"}, ensure_ascii=False))
        return 1

    files = [p for p in sorted(assets_dir.iterdir()) if p.is_file() and p.suffix.lower() in VALID_EXT]
    results: list[dict] = []
    for path in files:
        print(f"Processing: {path.name}", flush=True)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_file, path, args.fast_mode, use_deskew, args.ocr_scale)
            try:
                summary = future.result(timeout=max(1, args.timeout))
                results.append({"file": path.name, "result": summary})
            except TimeoutError:
                results.append({"file": path.name, "error": f"Processing timeout (>{args.timeout}s)"})
            except Exception as exc:
                results.append({"file": path.name, "error": str(exc)})

    output_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResults saved to: {output_file}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
