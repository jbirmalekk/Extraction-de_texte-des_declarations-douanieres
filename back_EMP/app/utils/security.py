"""
Security - Fonctions pour JWT et hashing de mots de passe
"""
from datetime import datetime, timedelta
from typing import Optional
import re
import uuid
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from ..config import settings
from ..database import SessionLocal
from ..models.user import RevokedToken

# Context pour hashing des mots de passe avec bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

PASSWORD_POLICY_MESSAGE = (
    "Password must contain at least 8 characters, including at least one uppercase letter, "
    "one lowercase letter, one digit, and one special character."
)


def validate_password_policy(password: str) -> str:
    """Valide la robustesse du mot de passe selon les normes minimales."""
    if len(password) < 8:
        raise ValueError(PASSWORD_POLICY_MESSAGE)

    if len(password) > 100:
        raise ValueError("Password must not exceed 100 characters.")

    if re.search(r"\s", password):
        raise ValueError("Password must not contain spaces.")

    if not re.search(r"[a-z]", password):
        raise ValueError(PASSWORD_POLICY_MESSAGE)

    if not re.search(r"[A-Z]", password):
        raise ValueError(PASSWORD_POLICY_MESSAGE)

    if not re.search(r"\d", password):
        raise ValueError(PASSWORD_POLICY_MESSAGE)

    if not re.search(r"[^A-Za-z0-9]", password):
        raise ValueError(PASSWORD_POLICY_MESSAGE)

    return password


def get_password_hash(password: str) -> str:
    """
    Hash un mot de passe en utilisant bcrypt.
    
    Args:
        password: Mot de passe en clair
        
    Returns:
        Mot de passe hashé
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifie si un mot de passe en clair correspond au hash.
    
    Args:
        plain_password: Mot de passe en clair
        hashed_password: Mot de passe hashé
        
    Returns:
        True si le mot de passe est correct
    """
    return pwd_context.verify(plain_password, hashed_password)


def _create_signed_token(payload: dict, expires_delta: timedelta) -> str:
    to_encode = payload.copy()
    to_encode["jti"] = uuid.uuid4().hex
    to_encode["exp"] = datetime.utcnow() + expires_delta
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(
    subject: str,
    token_version: int = 0,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crée un token JWT.
    
    Args:
        subject: Username ou user_id à encoder dans le token
        expires_delta: Durée de validité (par défaut depuis .env)
        
    Returns:
        Token JWT encodé
    """
    ttl = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_signed_token(
        {
            "sub": subject,
            "scope": "access",
            "tv": token_version,
        },
        ttl,
    )


def create_refresh_token(
    subject: str,
    token_version: int = 0,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Crée un refresh token JWT pour renouveler la session."""
    ttl = expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return _create_signed_token(
        {
            "sub": subject,
            "scope": "refresh",
            "tv": token_version,
        },
        ttl,
    )


def create_reset_token(subject: str, expires_minutes: int = 15) -> str:
    """Crée un token de réinitialisation de mot de passe (court)."""
    expires_delta = timedelta(minutes=expires_minutes)
    to_encode = {
        "sub": subject,
        "scope": "password_reset",
        "exp": datetime.utcnow() + expires_delta,
    }
    # Pas de jti/révocation pour un flux simple de reset
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_email_verification_token(email: str, expires_minutes: int = 24 * 60) -> str:
    """Crée un token de vérification d'email (24h par défaut)."""
    expires_delta = timedelta(minutes=expires_minutes)
    to_encode = {
        "sub": email,
        "scope": "email_verification",
        "exp": datetime.utcnow() + expires_delta,
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_email_verification_token(token: str) -> dict:
    """Décode un token de vérification d'email et vérifie le scope."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("scope") != "email_verification":
        raise JWTError("Invalid email verification token scope")
    return payload


def decode_reset_token(token: str) -> dict:
    """Décode un token de reset et vérifie le scope."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("scope") != "password_reset":
        raise JWTError("Invalid reset token scope")
    return payload


def decode_access_token(token: str) -> dict:
    """
    Décode et valide un token JWT.
    
    Args:
        token: Token JWT à décoder
        
    Returns:
        Payload du token (dict avec 'sub', 'exp', 'jti', etc.)
        
    Raises:
        JWTError: Si le token est invalide ou expiré
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("scope") != "access":
        raise JWTError("Invalid access token scope")
    return payload


def decode_refresh_token(token: str) -> dict:
    """Décode et valide un refresh token."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("scope") != "refresh":
        raise JWTError("Invalid refresh token scope")
    return payload


def _to_utc_datetime(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.utcfromtimestamp(int(value))
    except (TypeError, ValueError, OSError):
        return None


def _cleanup_expired_revoked_tokens(db: Session) -> None:
    now = datetime.utcnow()
    db.query(RevokedToken).filter(RevokedToken.expires_at < now).delete()


def revoke_token(
    jti: str,
    exp: datetime | int | float | None = None,
    db: Session | None = None,
    token_type: str = "access",
    username: str | None = None,
) -> None:
    """
    Révoque un token en ajoutant son jti à la blacklist.
    
    Args:
        jti: JWT ID du token à révoquer
    """
    token_exp = _to_utc_datetime(exp) or (datetime.utcnow() + timedelta(days=1))
    owns_session = db is None
    session = db or SessionLocal()
    try:
        existing = session.query(RevokedToken).filter(RevokedToken.jti == jti).first()
        if existing is None:
            session.add(
                RevokedToken(
                    jti=jti,
                    expires_at=token_exp,
                    token_type=token_type,
                    username=username,
                )
            )
        _cleanup_expired_revoked_tokens(session)
        session.commit()
    finally:
        if owns_session:
            session.close()


def is_token_revoked(jti: str, db: Session | None = None) -> bool:
    """
    Vérifie si un token a été révoqué.
    
    Args:
        jti: JWT ID du token
        
    Returns:
        True si le token est révoqué
    """
    owns_session = db is None
    session = db or SessionLocal()
    try:
        _cleanup_expired_revoked_tokens(session)
        session.commit()
        return session.query(RevokedToken.id).filter(RevokedToken.jti == jti).first() is not None
    finally:
        if owns_session:
            session.close()


def clear_revoked_tokens() -> None:
    """
    Vide la liste des tokens révoqués.
    Utile pour tests ou nettoyage périodique.
    """
    session = SessionLocal()
    try:
        session.query(RevokedToken).delete()
        session.commit()
    finally:
        session.close()
