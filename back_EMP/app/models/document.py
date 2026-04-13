from sqlalchemy import (Column, Integer, String, Text,
                        DateTime, Float, ForeignKey, JSON)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Document(Base):
    """Table principale — un document = une déclaration."""
    __tablename__ = "documents"

    id                       = Column(Integer, primary_key=True, index=True)
    fichier                  = Column(String(255))
    dossier                  = Column(String(255))
    mois                     = Column(String(20))
    statut                   = Column(String(50), default="ocr_extrait")
    # statut possible : ocr_extrait / valide / corrige / erreur

    # Identification
    numero_declaration       = Column(String(20),  index=True)
    date_declaration         = Column(String(20))
    type_declaration         = Column(String(20))
    nbre_articles            = Column(String(10))

    # Exportateur
    exportateur_nom          = Column(String(200))
    exportateur_code         = Column(String(50))

    # Importateur
    importateur_nom          = Column(String(200))
    importateur_pays         = Column(String(100))

    # Déclarant
    declarant_code           = Column(String(20))
    declarant_nom            = Column(String(200))

    # Transport
    mode_transport           = Column(String(50))
    date_arrivee_depart      = Column(String(20))
    pays_provenance          = Column(String(100))
    pays_destination         = Column(String(100))
    adresse_entreposage      = Column(Text)

    # Finances
    mode_livraison           = Column(String(20))
    devise                   = Column(String(10))
    montant_ptfn             = Column(String(50))
    valeur_fob_dt            = Column(String(50))
    taux_conversion          = Column(String(30))

    # Marchandises
    designation_marchandises = Column(Text)
    poids_brut               = Column(String(30))
    poids_net                = Column(String(30))

    # Liquidation
    bureau_douane            = Column(String(100))
    code_gdt                 = Column(String(20))
    montant_liquidation      = Column(String(50))
    itineraire               = Column(String(50))
    num_agrement             = Column(String(20))
    num_repertoire           = Column(String(20))
    cle_authentification     = Column(String(50))

    # Qualité OCR
    score_confiance          = Column(Integer)
    qualite                  = Column(String(20))
    flags_validation         = Column(JSON)

    # Texte brut (pour debug)
    texte_brut               = Column(Text)

    # Timestamps
    created_at               = Column(DateTime, server_default=func.now())
    updated_at               = Column(DateTime, onupdate=func.now())

    # Relations
    taxes    = relationship("Taxe",    back_populates="document",
                            cascade="all, delete-orphan")
    articles = relationship("Article", back_populates="document",
                            cascade="all, delete-orphan")


class Taxe(Base):
    """Table taxes — plusieurs taxes par document."""
    __tablename__ = "taxes"

    id          = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), index=True)
    code        = Column(String(20))
    assiette    = Column(String(50))
    quotite     = Column(String(50))
    montant     = Column(String(50))

    document = relationship("Document", back_populates="taxes")


class Article(Base):
    """Table articles — plusieurs articles par document."""
    __tablename__ = "articles"

    id            = Column(Integer, primary_key=True, index=True)
    document_id   = Column(Integer, ForeignKey("documents.id"), index=True)
    num_ligne     = Column(Integer)
    code_hs       = Column(String(20))
    designation   = Column(Text)
    quantite      = Column(Float)
    unite         = Column(String(20))
    prix_unitaire = Column(Float)
    total_ligne   = Column(Float)

    document = relationship("Document", back_populates="articles")