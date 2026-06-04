"""
Authentification JWT alignée sur back_EMP (+ appels internes signés depuis le proxy).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import internal_api_key, settings
from app.database import get_db
from app.models.revoked_token_ref import RevokedTokenRef
from app.models.user_ref import UserRef

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


@dataclass
class AuthUser:
    id: int
    username: str
    role: str
    token_version: int


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentification requise",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _forbidden() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces non autorise")


def get_access_token_from_request(request: Request, bearer_token: str | None) -> str:
    if bearer_token:
        return bearer_token
    cookie_token = request.cookies.get(settings.ACCESS_COOKIE_NAME)
    if cookie_token:
        return cookie_token
    raise _credentials_exception()


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("scope") != "access":
        raise JWTError("Invalid access token scope")
    return payload


def is_token_revoked(jti: str, db: Session) -> bool:
    if not jti:
        return False
    now = datetime.utcnow()
    row = (
        db.query(RevokedTokenRef)
        .filter(RevokedTokenRef.jti == jti, RevokedTokenRef.expires_at >= now)
        .first()
    )
    return row is not None


def _user_from_db(db: Session, username: str) -> UserRef | None:
    return db.query(UserRef).filter(UserRef.username == username).first()


def _auth_user_from_row(row: UserRef) -> AuthUser:
    return AuthUser(
        id=int(row.id),
        username=(row.username or "").strip() or f"user_{row.id}",
        role=(row.role or "user").strip().lower() or "user",
        token_version=int(row.token_version or 0),
    )


def _validate_internal_service(
    request: Request,
    db: Session,
    internal_key: str | None,
    user_id_hdr: str | None,
    user_role_hdr: str | None,
    username_hdr: str | None,
) -> AuthUser | None:
    expected = internal_api_key()
    if not expected or len(expected) < 16:
        return None
    provided = (internal_key or request.headers.get("X-Internal-Service-Key") or "").strip()
    if not provided or provided != expected:
        return None
    try:
        uid = int((user_id_hdr or request.headers.get("X-Authenticated-User-Id") or "").strip())
    except (TypeError, ValueError):
        return None
    if uid <= 0:
        return None
    row = db.get(UserRef, uid)
    if row:
        user = _auth_user_from_row(row)
        role_override = (user_role_hdr or request.headers.get("X-Authenticated-User-Role") or "").strip().lower()
        if role_override in ("admin", "user"):
            user.role = role_override
        return user
    username = (username_hdr or request.headers.get("X-Authenticated-Username") or "").strip()
    role = (user_role_hdr or request.headers.get("X-Authenticated-User-Role") or "user").strip().lower()
    return AuthUser(id=uid, username=username or f"user_{uid}", role=role or "user", token_version=0)


async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    x_internal_service_key: str | None = Header(None, alias="X-Internal-Service-Key"),
    x_authenticated_user_id: str | None = Header(None, alias="X-Authenticated-User-Id"),
    x_authenticated_user_role: str | None = Header(None, alias="X-Authenticated-User-Role"),
    x_authenticated_username: str | None = Header(None, alias="X-Authenticated-Username"),
) -> AuthUser:
    internal_user = _validate_internal_service(
        request,
        db,
        x_internal_service_key,
        x_authenticated_user_id,
        x_authenticated_user_role,
        x_authenticated_username,
    )
    if internal_user:
        return internal_user

    try:
        token_value = get_access_token_from_request(request, token)
        payload = decode_access_token(token_value)
        username = payload.get("sub")
        jti = payload.get("jti")
        token_version = int(payload.get("tv", 0))
        if not username:
            raise _credentials_exception()
        if jti and is_token_revoked(jti, db):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token revoque",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError as exc:
        raise _credentials_exception() from exc

    row = _user_from_db(db, username)
    if not row or row.is_active is False:
        raise _credentials_exception()
    if token_version != int(row.token_version or 0):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expiree, reconnectez-vous",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _auth_user_from_row(row)


def assert_invoice_access(inv, user: AuthUser) -> None:
    if user.role == "admin":
        return
    owner = inv.uploaded_by_user_id
    if owner is None:
        raise _forbidden()
    try:
        if int(owner) != int(user.id):
            raise _forbidden()
    except (TypeError, ValueError):
        if owner != user.id:
            raise _forbidden()
