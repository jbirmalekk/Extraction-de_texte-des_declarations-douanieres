"""Référence table users (back_EMP) — évite NoReferencedTableError au CREATE."""

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserRef(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(150), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    token_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
