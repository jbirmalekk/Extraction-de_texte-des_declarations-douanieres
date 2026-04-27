"""Nextcloud WebDAV storage service for uploaded OCR source files."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import quote

import requests
from requests.auth import HTTPBasicAuth

from app.config import settings


class NextcloudUploadError(RuntimeError):
    """Raised when file upload to Nextcloud fails."""


def _sanitize_segment(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (value or "").strip())
    cleaned = cleaned.strip("._-")
    return cleaned or fallback


def _get_webdav_base_url() -> str:
    base_url = settings.NEXTCLOUD_BASE_URL.strip().rstrip("/")
    if not base_url:
        raise NextcloudUploadError("NEXTCLOUD_BASE_URL is not configured.")

    if not settings.NEXTCLOUD_USERNAME or not settings.NEXTCLOUD_PASSWORD:
        raise NextcloudUploadError("NEXTCLOUD_USERNAME and NEXTCLOUD_PASSWORD are required.")

    encoded_user = quote(settings.NEXTCLOUD_USERNAME, safe="")
    return f"{base_url}/remote.php/dav/files/{encoded_user}"


def _build_webdav_url(base_webdav_url: str, remote_path: str) -> str:
    encoded_path = "/".join(quote(part, safe="") for part in remote_path.split("/") if part)
    return f"{base_webdav_url}/{encoded_path}"


def _ensure_remote_directories(
    session: requests.Session,
    base_webdav_url: str,
    remote_dir: str,
) -> None:
    parts = [part for part in remote_dir.split("/") if part]
    current: list[str] = []

    for part in parts:
        current.append(part)
        partial_path = "/".join(current)
        mkcol_url = _build_webdav_url(base_webdav_url, partial_path)

        try:
            response = session.request(
                "MKCOL",
                mkcol_url,
                timeout=settings.NEXTCLOUD_TIMEOUT_SECONDS,
                verify=settings.NEXTCLOUD_VERIFY_SSL,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise NextcloudUploadError(
                f"Unable to reach Nextcloud while creating folder '{partial_path}': {exc}"
            ) from exc

        if response.status_code in (201, 301, 405):
            continue

        raise NextcloudUploadError(
            f"Failed to create Nextcloud folder '{partial_path}' (status={response.status_code})."
        )


def upload_file_to_nextcloud(
    *,
    file_bytes: bytes,
    filename: str,
    content_type: str | None,
    uploader_name: str,
) -> dict | None:
    """
    Upload a file to Nextcloud using WebDAV.

    Returns:
        dict with remote_path, webdav_url, etag, uploaded_at if enabled.
        None if Nextcloud integration is disabled.
    """
    if not settings.NEXTCLOUD_ENABLED:
        return None

    base_webdav_url = _get_webdav_base_url()
    timestamp = datetime.now(timezone.utc)

    safe_uploader = _sanitize_segment(uploader_name, "unknown_user")
    safe_filename = _sanitize_segment(filename, "document")
    root_folder = _sanitize_segment(settings.NEXTCLOUD_UPLOAD_ROOT, "EMP-SmartOCR")

    date_folder = timestamp.strftime("%Y/%m/%d")
    remote_dir = f"{root_folder}/{safe_uploader}/{date_folder}"
    remote_name = f"{timestamp.strftime('%H%M%S')}_{safe_filename}"
    remote_path = f"{remote_dir}/{remote_name}"

    with requests.Session() as session:
        session.auth = HTTPBasicAuth(settings.NEXTCLOUD_USERNAME, settings.NEXTCLOUD_PASSWORD)

        _ensure_remote_directories(session, base_webdav_url, remote_dir)

        upload_url = _build_webdav_url(base_webdav_url, remote_path)
        try:
            response = session.put(
                upload_url,
                data=file_bytes,
                headers={"Content-Type": content_type or "application/octet-stream"},
                timeout=settings.NEXTCLOUD_TIMEOUT_SECONDS,
                verify=settings.NEXTCLOUD_VERIFY_SSL,
            )
        except requests.RequestException as exc:
            raise NextcloudUploadError(
                f"Unable to upload file to Nextcloud path '{remote_path}': {exc}"
            ) from exc

        if response.status_code not in (201, 204):
            raise NextcloudUploadError(
                f"Nextcloud upload failed for '{remote_path}' (status={response.status_code})."
            )

    return {
        "remote_path": remote_path,
        "webdav_url": upload_url,
        "etag": response.headers.get("ETag"),
        "uploaded_at": timestamp.isoformat(),
    }
