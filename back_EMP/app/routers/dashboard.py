from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

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


def _build_monthly_indicators(documents: list[Document], now: datetime) -> list[dict[str, object]]:
    month_window = _build_month_window(now)
    monthly_map = defaultdict(lambda: {"documents_processed": 0, "validated": 0})

    for document in documents:
        created_at = document.created_at or now
        created_key = _month_key(created_at)
        if created_key:
            monthly_map[created_key]["documents_processed"] += 1

        latest_session = _get_latest_validation_session(document)
        if latest_session and latest_session.status == "validated":
            validated_key = _month_key(latest_session.ended_at or latest_session.started_at)
            if validated_key:
                monthly_map[validated_key]["validated"] += 1

    return [
        {
            "month": _month_key(month_dt),
            "label": _month_label(month_dt),
            "documents_processed": monthly_map.get(_month_key(month_dt), {"documents_processed": 0})["documents_processed"],
            "validated": monthly_map.get(_month_key(month_dt), {"validated": 0})["validated"],
        }
        for month_dt in month_window
    ]


def _build_user_dashboard_payload(current_user: User, db: Session):
    now = datetime.utcnow()
    documents = (
        db.query(Document)
        .options(joinedload(Document.validation_sessions))
        .filter(Document.uploaded_by_user_id == current_user.id)
        .order_by(Document.created_at.desc(), Document.id.desc())
        .all()
    )

    documents_processed = len(documents)
    validated_this_month = 0
    pending_validation = 0
    ready_for_erp = 0

    recent_activity = []
    for document in documents:
        created_at = document.created_at or now
        latest_session = _get_latest_validation_session(document)

        if latest_session and latest_session.status == "validated" and _same_month(latest_session.ended_at, now):
            validated_this_month += 1

        if document.statut == "validated":
            ready_for_erp += 1

        if document.statut in {"pending", "processing", "done"}:
            pending_validation += 1

        status_label, tone = _format_activity_status(document)
        recent_activity.append(
            {
                "document_id": document.id,
                "document": document.numero_declaration or document.fichier or f"Document #{document.id}",
                "date": created_at.strftime("%Y-%m-%d"),
                "status": status_label,
                "tone": tone,
            }
        )

    return {
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "role": current_user.role,
        },
        "stats": {
            "documents_processed": documents_processed,
            "validated_this_month": validated_this_month,
            "pending_validation": pending_validation,
            "ready_for_erp": ready_for_erp,
        },
        "monthly_indicators": _build_monthly_indicators(documents, now),
        "recent_activity": recent_activity[:5],
    }


def _build_admin_dashboard_payload(db: Session):
    now = datetime.utcnow()
    documents = (
        db.query(Document)
        .options(joinedload(Document.validation_sessions), joinedload(Document.uploaded_by))
        .order_by(Document.created_at.desc(), Document.id.desc())
        .all()
    )
    users = db.query(User).all()

    documents_processed = len(documents)
    pending_validation = 0
    ready_for_erp = 0
    validated_this_month = 0

    recent_activity = []
    for document in documents:
        created_at = document.created_at or now
        latest_session = _get_latest_validation_session(document)

        if latest_session and latest_session.status == "validated" and _same_month(latest_session.ended_at, now):
            validated_this_month += 1

        if document.statut == "validated":
            ready_for_erp += 1

        if document.statut in {"pending", "processing", "done"}:
            pending_validation += 1

        status_label, tone = _format_activity_status(document)
        recent_activity.append(
            {
                "document_id": document.id,
                "document": document.numero_declaration or document.fichier or f"Document #{document.id}",
                "date": created_at.strftime("%Y-%m-%d"),
                "status": status_label,
                "tone": tone,
                "owner": document.uploaded_by.username if document.uploaded_by else None,
            }
        )

    return {
        "stats": {
            "documents_processed": documents_processed,
            "validated_this_month": validated_this_month,
            "pending_validation": pending_validation,
            "ready_for_erp": ready_for_erp,
            "total_users": len(users),
            "active_users": sum(1 for user in users if user.is_active),
            "approved_users": sum(1 for user in users if user.is_approved),
            "admin_users": sum(1 for user in users if user.role == "admin"),
        },
        "monthly_indicators": _build_monthly_indicators(documents, now),
        "recent_activity": recent_activity[:5],
        "users": {
            "total": len(users),
            "active": sum(1 for user in users if user.is_active),
            "approved": sum(1 for user in users if user.is_approved),
        },
    }


def _build_history_payload(documents: list[Document], now: datetime):
    history_rows: list[dict[str, object]] = []
    for document in documents:
        latest_session = _get_latest_validation_session(document)
        status_label, tone = _format_activity_status(document)
        corrections_count = sum(len(session.corrections or []) for session in document.validation_sessions or [])
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
                "corrections_count": corrections_count,
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
    query = db.query(Document)
    if current_user and current_user.role != "admin":
        query = query.filter(Document.uploaded_by_user_id == current_user.id)
    return query


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
            joinedload(Document.validation_sessions).joinedload(ValidationSession.validator),
            joinedload(Document.validation_sessions).joinedload(ValidationSession.corrections),
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