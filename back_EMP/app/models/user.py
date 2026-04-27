"""
User Model - Modèle SQLAlchemy pour la table users
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class User(Base):
    """
    Modèle User pour l'authentification.
    Stocke : username, email, mot de passe hashé, statut actif, approbation admin, vérification email,
    dates création/modification
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user", server_default="user")
    is_active = Column(Boolean, default=True, nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    is_approved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    uploaded_documents = relationship("Document", back_populates="uploaded_by")
    upload_traces = relationship("DocumentUploadTrace", back_populates="uploaded_by_user")
    validation_sessions = relationship("ValidationSession", back_populates="validator")
    correction_history = relationship("CorrectionHistory", back_populates="changed_by_user")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"
