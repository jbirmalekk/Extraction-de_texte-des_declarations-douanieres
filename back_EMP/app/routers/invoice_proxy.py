"""
Proxy authentifié vers back_EMP_Fact — le navigateur n'appelle que back_EMP (cookies JWT).
"""
from __future__ import annotations

import logging
from typing import Iterable

import requests
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import StreamingResponse

from app.config import settings
from app.models.user import User
from app.routers.auth import get_access_token_from_request, get_current_user

logger = logging.getLogger("app.invoice_proxy")

router = APIRouter(prefix="/api/invoices", tags=["Factures (proxy)"])

_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


def _internal_key() -> str:
    custom = (getattr(settings, "INVOICE_INTERNAL_API_KEY", None) or "").strip()
    if custom:
        return custom
    return (settings.SECRET_KEY or "").strip()


def _forward_headers(request: Request, user: User, bearer: str | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in request.headers.items():
        low = key.lower()
        if low in _HOP_HEADERS:
            continue
        if low in ("x-uploaded-by-user-id", "x-user-role", "x-uploaded-by-username"):
            continue
        out[key] = value
    out["X-Internal-Service-Key"] = _internal_key()
    out["X-Authenticated-User-Id"] = str(user.id)
    out["X-Authenticated-User-Role"] = (user.role or "user").strip().lower()
    out["X-Authenticated-Username"] = (user.username or "").strip()
    if bearer:
        out["Authorization"] = f"Bearer {bearer}" if not bearer.startswith("Bearer ") else bearer
    return out


def _target_url(path: str, query: str) -> str:
    base = (settings.INVOICE_API_URL or "http://localhost:8001").rstrip("/")
    suffix = path.strip("/")
    url = f"{base}/api/invoices"
    if suffix:
        url = f"{url}/{suffix}"
    if query:
        url = f"{url}?{query}"
    return url


async def _proxy_request(
    request: Request,
    user: User,
    path: str = "",
) -> Response:
    try:
        token = get_access_token_from_request(request, None)
    except Exception:
        token = None

    url = _target_url(path, request.url.query)
    headers = _forward_headers(request, user, token)
    body = (
        await request.body()
        if request.method not in ("GET", "HEAD", "OPTIONS")
        else None
    )

    try:
        upstream = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=body,
            timeout=max(settings.INVOICE_API_TIMEOUT_SECONDS, 30),
            stream=True,
        )
    except requests.RequestException as exc:
        logger.warning("invoice_proxy_failed url=%s err=%s", url, exc)
        return Response(
            content='{"detail":"Service factures indisponible"}',
            status_code=502,
            media_type="application/json",
        )

    excluded: Iterable[str] = _HOP_HEADERS
    resp_headers = {
        k: v
        for k, v in upstream.headers.items()
        if k.lower() not in excluded
    }

    if request.method == "HEAD":
        upstream.close()
        return Response(status_code=upstream.status_code, headers=resp_headers)

    def stream_chunks():
        try:
            for chunk in upstream.iter_content(chunk_size=65536):
                if chunk:
                    yield chunk
        finally:
            upstream.close()

    return StreamingResponse(
        stream_chunks(),
        status_code=upstream.status_code,
        headers=resp_headers,
        media_type=upstream.headers.get("content-type"),
    )


@router.api_route("", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def proxy_invoices(
    request: Request,
    path: str = "",
    current_user: User = Depends(get_current_user),
):
    if request.method == "OPTIONS":
        return Response(status_code=204)
    return await _proxy_request(request, current_user, path)
