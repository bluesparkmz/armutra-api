import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import CurrentUser
from app.models.notification import Notification
from app.schemas.notification import NotificationOut, UnreadCount

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    user: CurrentUser,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[NotificationOut]:
    rows = (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.criado_em.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [NotificationOut.model_validate(n) for n in rows]


@router.get("/unread-count", response_model=UnreadCount)
def unread_count(user: CurrentUser, db: Session = Depends(get_db)) -> UnreadCount:
    total = (
        db.query(func.count(Notification.id))
        .filter(Notification.user_id == user.id, Notification.lida.is_(False))
        .scalar()
    )
    return UnreadCount(nao_lidas=total or 0)


@router.post("/read-all", response_model=UnreadCount)
def mark_all_read(user: CurrentUser, db: Session = Depends(get_db)) -> UnreadCount:
    db.query(Notification).filter(
        Notification.user_id == user.id, Notification.lida.is_(False)
    ).update({Notification.lida: True})
    db.commit()
    return UnreadCount(nao_lidas=0)


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: uuid_lib.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> NotificationOut:
    n = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user.id)
        .first()
    )
    if not n:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificação não encontrada")
    n.lida = True
    db.commit()
    db.refresh(n)
    return NotificationOut.model_validate(n)
