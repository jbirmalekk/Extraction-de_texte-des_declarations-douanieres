"""Rapports de contrôle — liste légère (lecture SQL directe, sans proxy HTTP)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.invoice_list_service import list_invoice_summaries

router = APIRouter(prefix="/api/reports", tags=["Rapports"])


@router.get("")
def get_reports_summary(
    skip: int = 0,
    limit: int = Query(30, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = list_invoice_summaries(
        db,
        user_id=current_user.id,
        role=current_user.role or "user",
        skip=skip,
        limit=limit,
        reports_only=True,
    )
    return {
        "items": items,
        "total": total,
        "skip": max(0, skip),
        "limit": max(1, min(limit, 200)),
    }
