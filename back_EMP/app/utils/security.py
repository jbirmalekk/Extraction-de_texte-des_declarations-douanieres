"""
Security - Fonctions pour JWT et hashing de mots de passe
"""
from datetime import datetime, timedelta
from typing import Optional
import uuid
from jose import jwt, JWTError
from passlib.context import CryptContext
from ..config import settings

# Context pour hashing des mots de passe avec bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Stockage en mémoire des tokens révoqués (jti)
# En production, utiliser Redis ou une table BD
_revoked_tokens: set[str] = set()


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


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crée un token JWT.
    
    Args:
        subject: Username ou user_id à encoder dans le token
        expires_delta: Durée de validité (par défaut depuis .env)
        
    Returns:
        Token JWT encodé
    """
    to_encode = {"sub": subject}
    
    # Ajouter un jti (JWT ID unique) pour permettre la révocation
    jti = uuid.uuid4().hex
    to_encode["jti"] = jti
    
    # Calculer l'expiration
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode["exp"] = expire
    
    # Encoder le token
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


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
    return payload


def revoke_token(jti: str) -> None:
    """
    Révoque un token en ajoutant son jti à la blacklist.
    
    Args:
        jti: JWT ID du token à révoquer
    """
    _revoked_tokens.add(jti)


def is_token_revoked(jti: str) -> bool:
    """
    Vérifie si un token a été révoqué.
    
    Args:
        jti: JWT ID du token
        
    Returns:
        True si le token est révoqué
    """
    return jti in _revoked_tokens


def clear_revoked_tokens() -> None:
    """
    Vide la liste des tokens révoqués.
    Utile pour tests ou nettoyage périodique.
    """
    _revoked_tokens.clear()
