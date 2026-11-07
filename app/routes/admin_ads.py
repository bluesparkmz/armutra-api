import uuid as uuid_lib
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.ads_plans import CURRENCY
from app.db.session import get_db
from app.deps import AdminUser
from app.models.ad import Ad
from app.models.payment import Payment
from app.models.user import User
from app.routes.ads import TARGET_COLUMN, _to_out
from app.schemas.ad import (
    AdminAdActivate,
    AdminAdExtend,
    AdminAdOut,
    AdminAdStats,
    AdminAdUser,
)
from app.services import ads_service
from app.services.notification_service import notify

router = APIRouter(prefix="/admin/ads", tags=["admin-ads"])


def _admin_out(ad: Ad) -> AdminAdOut:
    base = _to_out(ad)
    paid = ad.payment is not None and ad.payment.status == "success"
    return AdminAdOut(
        **base.model_dump(),
        user=AdminAdUser(id=ad.user.id, nome=ad.user.nome, email=ad.user.email),
        pago=paid,
        cortesia=ad.payment_id is None and ad.starts_at is not None,
    )


def _get_ad(db: Session, ad_id: uuid_lib.UUID) -> Ad:
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anúncio não encontrado")
    return ad


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


@router.get("/stats", response_model=AdminAdStats)
def ads_stats(_: AdminUser, db: Session = Depends(get_db)) -> AdminAdStats:
    ads_service.expire_overdue(db)

    def count(*conds) -> int:
        return db.query(func.count(Ad.id)).filter(*conds).scalar() or 0

    revenue = (
        db.query(func.coalesce(func.sum(Ad.preco), 0))
        .join(Payment, Payment.id == Ad.payment_id)
        .filter(Payment.status == "success")
        .scalar()
    )
    return AdminAdStats(
        total=count(),
        ativos=count(Ad.status == "active"),
        por_pagar=count(Ad.status == "pending_payment"),
        expirados=count(Ad.status == "expired"),
        cortesias=count(Ad.payment_id.is_(None), Ad.starts_at.isnot(None)),
        receita=Decimal(str(revenue or 0)),
        currency=CURRENCY,
    )


@router.get("", response_model=list[AdminAdOut])
def list_ads(
    _: AdminUser,
    db: Session = Depends(get_db),
    estado: Optional[Literal["pending_payment", "active", "expired"]] = None,
    tipo: Optional[Literal["job", "service", "post"]] = None,
    q: Optional[str] = Query(None, description="Nome ou email do dono"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[AdminAdOut]:
    ads_service.expire_overdue(db)
    qr = db.query(Ad).join(User, User.id == Ad.user_id).options(joinedload(Ad.user))
    if estado:
        qr = qr.filter(Ad.status == estado)
    if tipo:
        qr = qr.filter(Ad.target_type == tipo)
    if q:
        like = f"%{q.strip()}%"
        qr = qr.filter((User.nome.ilike(like)) | (User.email.ilike(like)))
    rows = qr.order_by(Ad.criado_em.desc()).offset(skip).limit(limit).all()
    return [_admin_out(a) for a in rows]


@router.post("/{ad_id}/activate", response_model=AdminAdOut)
def activate_ad(
    ad_id: uuid_lib.UUID,
    admin: AdminUser,
    body: AdminAdActivate,
    db: Session = Depends(get_db),
) -> AdminAdOut:
    """Ativa manualmente (cortesia, sem pagamento) um boost por pagar ou expirado."""
    ad = _get_ad(db, ad_id)
    ads_service.expire_if_needed(db, ad)
    if ad.status == "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O anúncio já está ativo; use prolongar",
        )
    col = TARGET_COLUMN[ad.target_type]
    target_id = {"job": ad.job_id, "service": ad.service_id, "post": ad.post_id}[ad.target_type]
    other = (
        db.query(Ad)
        .filter(col == target_id, Ad.id != ad.id, Ad.status == "active", Ad.ends_at > func.now())
        .first()
    )
    if other:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este item já tem outro boost ativo",
        )
    days = body.dias or ad.duration_days
    now = datetime.now(timezone.utc)
    ad.status = "active"
    ad.duration_days = days
    ad.starts_at = now
    ad.ends_at = now + timedelta(days=days)
    notify(
        db,
        recipient_id=ad.user_id,
        actor=None,
        tipo="ad",
        titulo="Boost ativo",
        mensagem=f"O seu anúncio está em destaque durante {days} dias.",
        ref_id=ad.id,
    )
    db.commit()
    db.refresh(ad)
    return _admin_out(ad)


@router.post("/{ad_id}/extend", response_model=AdminAdOut)
def extend_ad(
    ad_id: uuid_lib.UUID,
    _: AdminUser,
    body: AdminAdExtend,
    db: Session = Depends(get_db),
) -> AdminAdOut:
    ad = _get_ad(db, ad_id)
    ads_service.expire_if_needed(db, ad)
    if ad.status != "active" or not ad.ends_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Só é possível prolongar anúncios ativos"
        )
    ad.ends_at = _aware(ad.ends_at) + timedelta(days=body.dias)
    db.commit()
    db.refresh(ad)
    return _admin_out(ad)


@router.post("/{ad_id}/end", response_model=AdminAdOut)
def end_ad(ad_id: uuid_lib.UUID, _: AdminUser, db: Session = Depends(get_db)) -> AdminAdOut:
    """Termina de imediato um boost ativo."""
    ad = _get_ad(db, ad_id)
    if ad.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Só é possível terminar anúncios ativos"
        )
    ad.status = "expired"
    ad.ends_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ad)
    return _admin_out(ad)


@router.delete("/{ad_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ad(ad_id: uuid_lib.UUID, _: AdminUser, db: Session = Depends(get_db)) -> None:
    ad = _get_ad(db, ad_id)
    db.delete(ad)
    db.commit()
