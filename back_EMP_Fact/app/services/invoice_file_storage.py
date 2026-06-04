"""Stockage local des fichiers facture lorsque Nextcloud GED est indisponible."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from app.config import settings

LOCAL_DOSSIER_PREFIX = "local://invoice/"
_APP_ROOT = Path(__file__).resolve().parents[2]


def _storage_root() -> Path:
    configured = Path(settings.INVOICE_LOCAL_STORAGE_DIR)
    root = configured if configured.is_absolute() else (_APP_ROOT / configured)
    root.mkdir(parents=True, exist_ok=True)
    return root


def is_local_dossier(dossier: str | None) -> bool:
    return bool(dossier and str(dossier).startswith(LOCAL_DOSSIER_PREFIX))


def _path_from_dossier(dossier: str) -> Path:
    relative = str(dossier).removeprefix(LOCAL_DOSSIER_PREFIX).strip("/\\")
    path = (_storage_root() / relative).resolve()
    root = _storage_root().resolve()
    if not str(path).startswith(str(root)):
        raise FileNotFoundError("Chemin de fichier facture invalide.")
    return path


def save_local_invoice_file(invoice_id: int, file_bytes: bytes, filename: str) -> str:
    """Enregistre le fichier sous storage/invoices/{id}{ext} et retourne le chemin dossier."""
    suffix = Path(filename or "document").suffix.lower()
    if suffix not in {".pdf", ".png", ".jpg", ".jpeg"}:
        suffix = ".pdf"
    relative = f"{invoice_id}{suffix}"
    target = _storage_root() / relative
    target.write_bytes(file_bytes)
    return f"{LOCAL_DOSSIER_PREFIX}{relative.replace(chr(92), '/')}"


def read_local_invoice_file(dossier: str) -> tuple[bytes, str]:
    path = _path_from_dossier(dossier)
    if not path.is_file():
        raise FileNotFoundError(f"Fichier facture introuvable sur le disque : {path.name}")
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return path.read_bytes(), content_type


_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif")


def find_local_invoice_by_id(invoice_id: int) -> tuple[bytes, str] | None:
    root = _storage_root()
    for ext in _EXTENSIONS:
        path = root / f"{invoice_id}{ext}"
        if path.is_file():
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            return path.read_bytes(), content_type
    return None


def delete_local_invoice_file(invoice_id: int, dossier: str | None = None) -> bool:
    """Supprime le fichier local facture (dossier ou {id}{ext})."""
    removed = False
    if dossier and is_local_dossier(dossier):
        try:
            path = _path_from_dossier(dossier)
            if path.is_file():
                path.unlink()
                removed = True
        except (FileNotFoundError, OSError):
            pass
    root = _storage_root()
    for ext in _EXTENSIONS:
        path = root / f"{invoice_id}{ext}"
        if path.is_file():
            try:
                path.unlink()
                removed = True
            except OSError:
                pass
    return removed
