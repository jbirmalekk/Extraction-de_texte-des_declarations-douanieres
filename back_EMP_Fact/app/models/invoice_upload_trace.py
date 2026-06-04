from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class InvoiceUploadTrace(Base):
    """Traçabilité upload facture (auteur, poste client, GED Nextcloud) — aligné document_upload_traces."""

    __tablename__ = "invoice_upload_traces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )

    uploaded_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    uploaded_by_username: Mapped[str] = mapped_column(String(150), nullable=False)

    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    client_pc_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    client_user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    nextcloud_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    nextcloud_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    nextcloud_etag: Mapped[str | None] = mapped_column(String(255), nullable=True)

    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="upload_traces")
