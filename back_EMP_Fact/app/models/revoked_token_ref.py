"""Référence table revoked_tokens (back_EMP) — révocation JWT partagée."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RevokedTokenRef(Base):
    __tablename__ = "revoked_tokens"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    token_type: Mapped[str] = mapped_column(String(20), nullable=False, default="access")
    username: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
