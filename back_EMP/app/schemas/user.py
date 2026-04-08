"""
User Schemas - Schémas Pydantic pour validation et sérialisation
"""
from enum import Enum
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserRole(str, Enum):
    """Rôles disponibles pour les utilisateurs"""
    admin = "admin"
    user = "user"


class UserBase(BaseModel):
    """Schéma de base pour User"""
    username: str = Field(..., min_length=3, max_length=150)
    email: Optional[EmailStr] = None
    role: UserRole = UserRole.user


class UserCreate(UserBase):
    """Schéma pour la création d'un utilisateur (sign-up)"""
    # Aligné avec le front : minimum 8 caractères
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """Schéma pour la mise à jour partielle d'un utilisateur"""
    username: Optional[str] = Field(None, min_length=3, max_length=150)
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)


class UserLogin(BaseModel):
    """Schéma pour le login avec email et password"""
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    """Demande de reset (email)"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Reset effectif avec token et nouveau mot de passe"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class UserOut(UserBase):
    """Schéma pour renvoyer les infos utilisateur (sans mot de passe)"""
    id: int
    is_active: bool
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True  # Pydantic V2 (avant: orm_mode = True)


class UserInDB(UserBase):
    """Schéma interne avec mot de passe hashé"""
    id: int
    hashed_password: str
    is_active: bool
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schéma pour le token JWT renvoyé après login"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Données extraites du token JWT"""
    username: Optional[str] = None
    jti: Optional[str] = None
