"""Stockage local des fichiers DUM lorsque Nextcloud GED est indisponible."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from app.config import settings

LOCAL_DOSSIER_PREFIX = "local://dum/"
_APP_ROOT = Path(__file__).resolve().parents[2]


def _storage_root() -> Path:
    configured = Path(settings.DUM_LOCAL_STORAGE_DIR)
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
        raise FileNotFoundError("Chemin de fichier DUM invalide.")
    return path


def save_local_document_file(document_id: int, file_bytes: bytes, filename: str) -> str:
    suffix = Path(filename or "document").suffix.lower()
    if suffix not in {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}:
        suffix = ".pdf"
    relative = f"{document_id}{suffix}"
    target = _storage_root() / relative
    target.write_bytes(file_bytes)
    return f"{LOCAL_DOSSIER_PREFIX}{relative.replace(chr(92), '/')}"


def read_local_document_file(dossier: str) -> tuple[bytes, str]:
    path = _path_from_dossier(dossier)
    if not path.is_file():
        raise FileNotFoundError(f"Fichier DUM introuvable sur le disque : {path.name}")
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return path.read_bytes(), content_type


_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif")


def local_dossier_for_document_id(document_id: int) -> str | None:
    """Chemin dossier local://dum/{id}{ext} si le fichier existe sur disque."""
    root = _storage_root()
    for ext in _EXTENSIONS:
        path = root / f"{document_id}{ext}"
        if path.is_file():
            rel = f"{document_id}{ext}".replace("\\", "/")
            return f"{LOCAL_DOSSIER_PREFIX}{rel}"
    return None


def document_has_stored_file(document_id: int, storage_path: str | None) -> bool:
    """True si un fichier source est disponible (local ou chemin GED renseigné)."""
    if find_local_document_by_id(document_id):
        return True
    if not storage_path:
        return False
    if is_local_dossier(storage_path):
        try:
            read_local_document_file(storage_path)
            return True
        except FileNotFoundError:
            return False
    return True


def find_local_document_by_id(document_id: int) -> tuple[bytes, str] | None:
    """Retrouve un fichier local {id}{ext} même si dossier n'est pas renseigné en base."""
    root = _storage_root()
    for ext in _EXTENSIONS:
        path = root / f"{document_id}{ext}"
        if path.is_file():
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            return path.read_bytes(), content_type
    return None


def delete_local_document_file(document_id: int, dossier: str | None = None) -> bool:
    """Supprime le fichier local DUM (dossier ou {id}{ext}). Retourne True si au moins un fichier supprimé."""
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
        path = root / f"{document_id}{ext}"
        if path.is_file():
            try:
                path.unlink()
                removed = True
            except OSError:
                pass
    return removed
