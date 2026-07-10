from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, extract
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database import get_db
from app.models.document import Document, ValidationSession
from app.models.user import User
from app.routers.auth import get_current_user, ensure_admin

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def _month_key(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return f"{dt.year:04d}-{dt.month:02d}"


def _month_label(dt: datetime | None) -> str:
    if dt is None:
        return "Inconnu"

    month_names = [
        "Jan",
        "Fév",
        "Mar",
        "Avr",
        "Mai",
        "Jun",
        "Jul",
        "Aoû",
        "Sep",
        "Oct",
        "Nov",
        "Déc",
    ]
    return f"{month_names[dt.month - 1]} {dt.year}"


def _same_month(reference: datetime | None, target: datetime) -> bool:
    if reference is None:
        return False
    return reference.year == target.year and reference.month == target.month


def _get_latest_validation_session(document: Document):
    sessions = list(document.validation_sessions or [])
    if not sessions:
        return None
    return max(
        sessions,
        key=lambda session: session.ended_at or session.started_at or datetime.min,
    )


def _format_activity_status(document: Document) -> tuple[str, str]:
    latest_session = _get_latest_validation_session(document)
    if latest_session:
        if latest_session.status == "validated":
            return "Validé", "success"
        if latest_session.status == "rejected":
            return "Rejeté", "danger"
        if latest_session.status == "in_progress":
            return "En cours", "warning"

    if document.statut == "processing":
        return "En cours", "warning"
    if document.statut == "validated":
        return "Validé", "success"
    if document.statut == "rejected":
        return "Rejeté", "danger"
    return "En attente", "warning"


def _build_month_window(reference: datetime | None = None) -> list[datetime]:
    now = reference or datetime.utcnow()
    month_window = []
    year = now.year
    month = now.month

    for _ in range(6):
        month_window.append(datetime(year, month, 1))
        month -= 1
        if month == 0:
            month = 12
            year -= 1

    month_window.reverse()
    return month_window


def _documents_base_query(db: Session, current_user: User | None = None):
    query = db.query(Document)
    if current_user and current_user.role != "admin":
        query = query.filter(Document.uploaded_by_user_id == current_user.id)
    return query


def _compute_document_stats(db: Session, current_user: User | None = None) -> dict[str, int]:
    """Compteurs SQL sans charger tous les documents."""
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)
    base = _documents_base_query(db, current_user)

    documents_processed = base.count()
    pending_validation = base.filter(Document.statut.in_(("pending", "processing", "done"))).count()
    ready_for_erp = base.filter(Document.statut == "validated").count()

    vs_q = (
        db.query(func.count(ValidationSession.id))
        .join(Document, ValidationSession.document_id == Document.id)
        .filter(ValidationSession.status == "validated")
        .filter(ValidationSession.ended_at >= month_start)
    )
    if current_user and current_user.role != "admin":
        vs_q = vs_q.filter(Document.uploaded_by_user_id == current_user.id)
    validated_this_month = vs_q.scalar() or 0

    return {
        "documents_processed": documents_processed,
        "validated_this_month": validated_this_month,
        "pending_validation": pending_validation,
        "ready_for_erp": ready_for_erp,
    }


def _build_monthly_indicators_sql(db: Session, current_user: User | None, now: datetime) -> list[dict[str, object]]:
    """Indicateurs mensuels via GROUP BY (6 derniers mois)."""
    month_window = _build_month_window(now)
    keys = {_month_key(m) for m in month_window}
    monthly_map = defaultdict(lambda: {"documents_processed": 0, "validated": 0})

    created_q = (
        db.query(
            extract("year", Document.created_at).label("y"),
            extract("month", Document.created_at).label("m"),
            func.count(Document.id),
        )
        .filter(Document.created_at.isnot(None))
        .group_by(extract("year", Document.created_at), extract("month", Document.created_at))
    )
    if current_user and current_user.role != "admin":
        created_q = created_q.filter(Document.uploaded_by_user_id == current_user.id)
    for y, m, cnt in created_q.all():
        key = f"{int(y):04d}-{int(m):02d}"
        if key in keys:
            monthly_map[key]["documents_processed"] = int(cnt)

    validated_q = (
        db.query(
            extract("year", ValidationSession.ended_at).label("y"),
            extract("month", ValidationSession.ended_at).label("m"),
            func.count(ValidationSession.id),
        )
        .join(Document, ValidationSession.document_id == Document.id)
        .filter(ValidationSession.status == "validated")
        .filter(ValidationSession.ended_at.isnot(None))
        .group_by(extract("year", ValidationSession.ended_at), extract("month", ValidationSession.ended_at))
    )
    if current_user and current_user.role != "admin":
        validated_q = validated_q.filter(Document.uploaded_by_user_id == current_user.id)
    for y, m, cnt in validated_q.all():
        key = f"{int(y):04d}-{int(m):02d}"
        if key in keys:
            monthly_map[key]["validated"] = int(cnt)

    return [
        {
            "month": _month_key(month_dt),
            "label": _month_label(month_dt),
            "documents_processed": monthly_map.get(_month_key(month_dt), {"documents_processed": 0})["documents_processed"],
            "validated": monthly_map.get(_month_key(month_dt), {"validated": 0})["validated"],
        }
        for month_dt in month_window
    ]


def _load_recent_documents(db: Session, current_user: User | None, *, limit: int = 5) -> list[Document]:
    """Activité récente : N documents seulement, sans corrections."""
    q = (
        _documents_base_query(db, current_user)
        .options(
            selectinload(Document.validation_sessions),
            joinedload(Document.uploaded_by),
        )
        .order_by(Document.created_at.desc(), Document.id.desc())
        .limit(max(1, min(limit, 20)))
    )
    return q.all()


def _document_to_activity_row(document: Document, now: datetime, *, include_owner: bool = False) -> dict:
    created_at = document.created_at or now
    status_label, tone = _format_activity_status(document)
    row = {
        "document_id": document.id,
        "document": document.numero_declaration or document.fichier or f"Document #{document.id}",
        "date": created_at.strftime("%Y-%m-%d"),
        "status": status_label,
        "tone": tone,
    }
    if include_owner:
        row["owner"] = document.uploaded_by.username if document.uploaded_by else None
    return row


def _build_user_dashboard_payload(current_user: User, db: Session):
    now = datetime.utcnow()
    stats = _compute_document_stats(db, current_user)
    recent_docs = _load_recent_documents(db, current_user, limit=5)
    recent_activity = [_document_to_activity_row(doc, now) for doc in recent_docs]

    return {
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "role": current_user.role,
        },
        "stats": stats,
        "monthly_indicators": _build_monthly_indicators_sql(db, current_user, now),
        "recent_activity": recent_activity,
    }


def _build_admin_dashboard_payload(db: Session):
    now = datetime.utcnow()
    stats = _compute_document_stats(db, None)
    user_stats = {
        "total_users": db.query(func.count(User.id)).scalar() or 0,
        "active_users": db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0,
        "approved_users": db.query(func.count(User.id)).filter(User.is_approved == True).scalar() or 0,
        "admin_users": db.query(func.count(User.id)).filter(User.role == "admin").scalar() or 0,
    }
    stats.update(user_stats)

    recent_docs = _load_recent_documents(db, None, limit=5)
    recent_activity = [_document_to_activity_row(doc, now, include_owner=True) for doc in recent_docs]

    return {
        "stats": stats,
        "monthly_indicators": _build_monthly_indicators_sql(db, None, now),
        "recent_activity": recent_activity,
        "users": {
            "total": user_stats["total_users"],
            "active": user_stats["active_users"],
            "approved": user_stats["approved_users"],
        },
    }


def _build_history_payload(documents: list[Document], now: datetime):
    history_rows: list[dict[str, object]] = []
    for document in documents:
        latest_session = _get_latest_validation_session(document)
        status_label, tone = _format_activity_status(document)
        history_rows.append(
            {
                "document_id": document.id,
                "document": document.numero_declaration or document.fichier or f"Document #{document.id}",
                "numero_declaration": document.numero_declaration,
                "date_declaration": document.date_declaration,
                "fichier": document.fichier,
                "owner": document.uploaded_by.username if document.uploaded_by else None,
                "date": (document.created_at or now).strftime("%Y-%m-%d"),
                "created_at": (document.created_at or now).isoformat(),
                "status": status_label,
                "tone": tone,
                "score": document.score_confiance,
                "validated_at": latest_session.ended_at.isoformat() if latest_session and latest_session.ended_at else None,
                "validator": latest_session.validator.username if latest_session and latest_session.validator else None,
            }
        )

    return {
        "stats": {
            "documents": len(history_rows),
            "validated": sum(1 for row in history_rows if row["status"] == "Validé"),
            "rejected": sum(1 for row in history_rows if row["status"] == "Rejeté"),
            "in_progress": sum(1 for row in history_rows if row["status"] == "En cours"),
        },
        "history": history_rows,
    }


def _history_documents_query(db: Session, current_user: User | None = None):
    return _documents_base_query(db, current_user)


def _load_documents_with_history(
    db: Session,
    current_user: User | None = None,
    *,
    skip: int = 0,
    limit: int | None = None,
) -> tuple[list[Document], int]:
    base = _history_documents_query(db, current_user)
    total = base.count()
    query = (
        base.options(
            joinedload(Document.uploaded_by),
            selectinload(Document.validation_sessions).selectinload(ValidationSession.validator),
        )
        .order_by(Document.created_at.desc(), Document.id.desc())
    )
    if limit is not None:
        query = query.offset(max(0, skip)).limit(max(1, min(limit, 200)))
    documents = query.all()
    return documents, total


@router.get("/me")
def get_my_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _build_user_dashboard_payload(current_user, db)


@router.get("/admin")
def get_admin_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin(current_user)
    return _build_admin_dashboard_payload(db)


@router.get("/history")
def get_history(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin(current_user)
    documents, total = _load_documents_with_history(db, skip=skip, limit=limit)
    payload = _build_history_payload(documents, datetime.utcnow())
    payload["total"] = total
    payload["skip"] = max(0, skip)
    payload["limit"] = max(1, min(limit, 200))
    return payload


@router.get("/me/history")
def get_my_history(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    documents, total = _load_documents_with_history(db, current_user, skip=skip, limit=limit)
    payload = _build_history_payload(documents, datetime.utcnow())
    payload["total"] = total
    payload["skip"] = max(0, skip)
    payload["limit"] = max(1, min(limit, 200))
    return payload