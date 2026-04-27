from sqlalchemy import (Column, Integer, String, Text,
                        DateTime, Float, ForeignKey, JSON, Boolean)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Document(Base):
    """Table principale pour les metadonnees document + compatibilite legacy OCR."""
    __tablename__ = "documents"

    id                       = Column(Integer, primary_key=True, index=True)
    fichier                  = Column(String(255))
    dossier                  = Column(String(255))
    uploaded_by_user_id      = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    mois                     = Column(String(20))
    statut                   = Column(String(50), default="pending")
    # statut cible : pending / processing / done / validated / rejected

    # Identification
    numero_declaration       = Column(String(20),  index=True)
    date_declaration         = Column(String(20))
    type_declaration         = Column(String(20))
    nbre_articles            = Column(String(10))

    # Exportateur
    exportateur_nom          = Column(String(200))
    exportateur_code         = Column(String(50))
    adresse_exportateur      = Column(Text)

    # Importateur
    importateur_nom          = Column(String(200))
    importateur_pays         = Column(String(100))
    adresse_importateur      = Column(Text)
    code_importateur         = Column(String(50))

    # Déclaration étendue
    numero_dae               = Column(String(50))
    nombre_articles          = Column(String(20))
    nombre_colis             = Column(String(20))
    numero_credit            = Column(String(50))

    # Déclarant
    declarant_code           = Column(String(20))
    declarant_nom            = Column(String(200))

    # Transport
    mode_transport           = Column(String(50))
    date_arrivee_depart      = Column(String(20))
    pays_provenance          = Column(String(100))
    pays_destination         = Column(String(100))
    pays_achat               = Column(String(100))
    pays_premiere_destination = Column(String(100))
    pays_destination_finale  = Column(String(100))
    adresse_entreposage      = Column(Text)
    transport_international_nationalite = Column(String(100))
    transport_international_mode = Column(String(100))
    transport_international_identite = Column(String(100))
    transport_national_nationalite = Column(String(100))
    transport_national_mode  = Column(String(100))

    # Finances
    mode_livraison           = Column(String(20))
    mode_paiement            = Column(String(50))
    relation_acheteur_vendeur = Column(String(100))
    engagement               = Column(Text)
    devise                   = Column(String(10))
    valeur_totale            = Column(String(50))
    assurance                = Column(String(50))
    fret                     = Column(String(50))
    montant_ptfn             = Column(String(50))
    valeur_dinars            = Column(String(50))
    valeur_fob_dt            = Column(String(50))
    taux_conversion          = Column(String(30))

    # Marchandises
    designation_marchandises = Column(Text)
    poids_brut               = Column(String(30))
    poids_net                = Column(String(30))

    # Liquidation
    bureau_douane            = Column(String(100))
    code_bureau              = Column(String(50))
    designation_bureau       = Column(String(150))
    bureau_frontiere         = Column(String(150))
    destination              = Column(String(150))
    localisation_export      = Column(String(150))
    code_gdt                 = Column(String(20))
    montant_total            = Column(String(50))
    total                    = Column(String(50))
    totaux                   = Column(String(50))
    montant_liquidation      = Column(String(50))
    itineraire               = Column(String(50))
    commissaire_douane       = Column(String(200))
    num_agrement             = Column(String(20))
    num_repertoire           = Column(String(20))
    texte_engagement         = Column(Text)
    nom_declarant            = Column(String(200))
    date_validation          = Column(String(50))
    cachet                   = Column(String(200))
    cle_authentification     = Column(String(50))
    qr_code                  = Column(String(500))

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
    uploaded_by = relationship("User", back_populates="uploaded_documents",
                               foreign_keys=[uploaded_by_user_id])
    ocr_result = relationship("OCRResult", back_populates="document",
                              uselist=False, cascade="all, delete-orphan")
    validation_sessions = relationship("ValidationSession", back_populates="document",
                                       cascade="all, delete-orphan")
    upload_traces = relationship("DocumentUploadTrace", back_populates="document",
                                 cascade="all, delete-orphan")


class OCRResult(Base):
    """Resultat OCR brut normalise (1 document = 1 resultat OCR)."""
    __tablename__ = "ocr_results"

    id                = Column(Integer, primary_key=True, index=True)
    document_id       = Column(Integer, ForeignKey("documents.id"), nullable=False,
                               unique=True, index=True)
    raw_result_json   = Column(JSON)
    global_confidence = Column(Float)
    engine_name       = Column(String(100))
    created_at        = Column(DateTime, server_default=func.now(), nullable=False)

    document = relationship("Document", back_populates="ocr_result")
    extracted_fields = relationship("ExtractedField", back_populates="ocr_result",
                                    cascade="all, delete-orphan")


class ExtractedField(Base):
    """Un champ extrait unitaire rattache a un OCRResult."""
    __tablename__ = "extracted_fields"

    id            = Column(Integer, primary_key=True, index=True)
    ocr_result_id = Column(Integer, ForeignKey("ocr_results.id"), nullable=False, index=True)
    field_key     = Column(String(120), nullable=False, index=True)
    value         = Column(Text)
    confidence    = Column(Float)
    manually_added = Column(Boolean, default=False, nullable=False)
    page_number   = Column(Integer)
    bbox_json     = Column(JSON)
    created_at    = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at    = Column(DateTime, onupdate=func.now())

    ocr_result = relationship("OCRResult", back_populates="extracted_fields")
    correction_history = relationship("CorrectionHistory", back_populates="extracted_field",
                                      cascade="all, delete-orphan")


class ValidationSession(Base):
    """Session de validation humaine d'un document."""
    __tablename__ = "validation_sessions"

    id                = Column(Integer, primary_key=True, index=True)
    document_id       = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    validator_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    status            = Column(String(30), nullable=False, default="in_progress")
    started_at        = Column(DateTime, server_default=func.now(), nullable=False)
    ended_at          = Column(DateTime)
    comment           = Column(Text)

    document = relationship("Document", back_populates="validation_sessions")
    validator = relationship("User", back_populates="validation_sessions",
                             foreign_keys=[validator_user_id])
    corrections = relationship("CorrectionHistory", back_populates="validation_session",
                               cascade="all, delete-orphan")


class CorrectionHistory(Base):
    """Historique des corrections manuelles pendant une session de validation."""
    __tablename__ = "correction_history"

    id                    = Column(Integer, primary_key=True, index=True)
    validation_session_id = Column(Integer, ForeignKey("validation_sessions.id"),
                                   nullable=False, index=True)
    extracted_field_id    = Column(Integer, ForeignKey("extracted_fields.id"), nullable=True,
                                   index=True)
    changed_by_user_id    = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    old_value             = Column(Text)
    new_value             = Column(Text)
    action_type           = Column(String(20), nullable=False, default="update")
    changed_at            = Column(DateTime, server_default=func.now(), nullable=False)

    validation_session = relationship("ValidationSession", back_populates="corrections")
    extracted_field = relationship("ExtractedField", back_populates="correction_history")
    changed_by_user = relationship("User", back_populates="correction_history",
                                   foreign_keys=[changed_by_user_id])


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


class DocumentUploadTrace(Base):
    """Traceabilite des uploads (auteur, poste client, stockage GED)."""
    __tablename__ = "document_upload_traces"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)

    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    uploaded_by_username = Column(String(150), nullable=False)

    source_filename = Column(String(255), nullable=False)
    source_content_type = Column(String(120))
    source_size_bytes = Column(Integer)

    client_pc_name = Column(String(255))
    client_ip = Column(String(64))
    client_user_agent = Column(String(512))

    nextcloud_path = Column(String(1024))
    nextcloud_url = Column(String(1024))
    nextcloud_etag = Column(String(255))

    uploaded_at = Column(DateTime, server_default=func.now(), nullable=False)

    document = relationship("Document", back_populates="upload_traces")
    uploaded_by_user = relationship("User", back_populates="upload_traces",
                                    foreign_keys=[uploaded_by_user_id])