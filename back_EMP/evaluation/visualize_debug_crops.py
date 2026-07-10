#!/usr/bin/env python
"""Génère un rapport HTML : crops OCR côte à côte avec texte OCR et valeurs finales."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

PARTY_FIELDS = (
    "exportateur_nom",
    "exportateur",
    "exportateur_code",
    "adresse_exportateur",
    "importateur_nom",
    "importateur",
    "code_importateur",
    "adresse_importateur",
    "declarant_nom",
    "declarant_code",
    "num_repertoire",
)


def _load_manifest(session_dir: Path) -> dict:
    manifest_path = session_dir / "extraction_manifest.json"
    if manifest_path.is_file():
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    return {"zone_records": [], "final_party_fields": {}}


def _pick_session(crops_root: Path, session: str | None) -> Path:
    if session:
        candidate = crops_root / session
        if not candidate.is_dir():
            raise FileNotFoundError(f"Session introuvable: {candidate}")
        return candidate
    sessions = sorted([p for p in crops_root.iterdir() if p.is_dir()], reverse=True)
    if not sessions:
        raise FileNotFoundError(f"Aucune session dans {crops_root}")
    return sessions[0]


def _records_by_field(manifest: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in manifest.get("zone_records") or []:
        field = str(row.get("field") or "")
        if not field:
            continue
        tag = str(row.get("tag") or "")
        priority = 0 if tag == "header_cell" else 1 if tag == "fixed_zone" else 2
        prev = out.get(field)
        if prev is None or priority < prev.get("_priority", 99):
            out[field] = {**row, "_priority": priority}
    return out


def build_html(session_dir: Path, manifest: dict) -> str:
    records = _records_by_field(manifest)
    final_fields = manifest.get("final_party_fields") or {}
    reject_reasons = manifest.get("field_reject_reasons") or []
    flags = manifest.get("flags_validation") or []

    rows_html = []
    party_set = set(PARTY_FIELDS)
    all_fields = sorted(party_set.union(records.keys()))

    for field in all_fields:
        rec = records.get(field) or {}
        crop_path = rec.get("crop_path")
        rel_img = ""
        if crop_path:
            try:
                rel_img = Path(crop_path).relative_to(session_dir).as_posix()
            except ValueError:
                rel_img = Path(crop_path).name

        ocr_text = html.escape(str(rec.get("ocr_text") or "—"))
        conf = rec.get("confidence")
        conf_s = f"{float(conf):.2f}" if conf is not None else "—"
        engine = html.escape(str(rec.get("engine") or "—"))
        final_val = html.escape(str(final_fields.get(field) or "—"))
        tag = html.escape(str(rec.get("tag") or "—"))

        img_cell = (
            f'<img src="{html.escape(rel_img)}" alt="{html.escape(field)}" '
            f'style="max-width:320px;max-height:120px;border:1px solid #ccc;" />'
            if rel_img and (session_dir / rel_img).is_file()
            else "<em>Pas de crop</em>"
        )

        rows_html.append(
            f"""
            <tr>
              <td><strong>{html.escape(field)}</strong><br/><small>{tag}</small></td>
              <td>{img_cell}</td>
              <td><code>{ocr_text}</code><br/>conf={conf_s} · {engine}</td>
              <td><strong>{final_val}</strong></td>
            </tr>
            """
        )

    reasons_block = "<br/>".join(html.escape(str(r)) for r in reject_reasons) or "—"
    flags_block = "<br/>".join(html.escape(str(f)) for f in flags) or "—"

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <title>Rapport OCR — {html.escape(session_dir.name)}</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; color: #1a1a1a; }}
    h1 {{ font-size: 1.4rem; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
    th {{ background: #f4f6f8; text-align: left; }}
    .meta {{ background: #fafafa; padding: 12px; border-radius: 8px; margin: 12px 0; }}
    code {{ white-space: pre-wrap; word-break: break-word; }}
  </style>
</head>
<body>
  <h1>Rapport calibration OCR — session {html.escape(session_dir.name)}</h1>
  <div class="meta">
    <div><strong>Dossier :</strong> {html.escape(str(session_dir))}</div>
    <div><strong>Flags :</strong> {flags_block}</div>
    <div><strong>Raisons rejet :</strong> {reasons_block}</div>
  </div>
  <table>
    <thead>
      <tr>
        <th>Champ</th>
        <th>Crop</th>
        <th>Texte OCR zone</th>
        <th>Valeur finale</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows_html)}
    </tbody>
  </table>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Visualiser crops OCR + valeurs extraites.")
    parser.add_argument(
        "--crops-dir",
        default="ocr_debug_crops",
        help="Racine des sessions debug (défaut: ocr_debug_crops)",
    )
    parser.add_argument("--session", help="ID session YYYYMMDD_HHMMSS (défaut: la plus récente)")
    parser.add_argument(
        "--output",
        help="Fichier HTML de sortie (défaut: <session>/report.html)",
    )
    args = parser.parse_args()

    crops_root = Path(args.crops_dir)
    if not crops_root.is_absolute():
        crops_root = Path.cwd() / crops_root

    session_dir = _pick_session(crops_root, args.session)
    manifest = _load_manifest(session_dir)
    html_doc = build_html(session_dir, manifest)

    out_path = Path(args.output) if args.output else session_dir / "report.html"
    out_path.write_text(html_doc, encoding="utf-8")
    print(f"Rapport généré: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
