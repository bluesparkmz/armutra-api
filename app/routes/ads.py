import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.ads_plans import CURRENCY, PLANS
from app.db.session import get_db
from app.deps import CurrentUser
from app.models.ad import Ad
from app.models.job import Job
from app.models.post import Post
from app.models.service import Service
from app.models.user import User
from app.schemas.ad import AdCreate, AdOut, AdPay, AdPlanOut, BoostableItem
from app.schemas.payment import PaymentOut
from app.services import ads_service, payment_service

router = APIRouter(prefix="/ads", tags=["ads"])

TARGET_COLUMN = {"job": Ad.job_id, "service": Ad.service_id, "post": Ad.post_id}


def _target(ad: Ad) -> tuple[uuid_lib.UUID, str]:
    obj = {"job": ad.job, "service": ad.service, "post": ad.post}[ad.target_type]
    target_id = {"job": ad.job_id, "service": ad.service_id, "post": ad.post_id}[ad.target_type]
    return target_id, (obj.titulo if obj else None)


def _to_out(ad: Ad) -> AdOut:
    target_id, titulo = _target(ad)
    plan = PLANS.get(ad.plan, {})
    return AdOut(
        id=ad.id,
        target_type=ad.target_type,
        target_id=target_id,
        target_titulo=titulo,
        plan=ad.plan,
        plan_nome=plan.get("nome", ad.plan),
        preco=ad.preco,
        currency=ad.currency,
        duration_days=ad.duration_days,
        status=ad.status,
        starts_at=ad.starts_at,
        ends_at=ad.ends_at,
        criado_em=ad.criado_em,
        payment=PaymentOut.model_validate(ad.payment) if ad.payment else None,
    )


def _get_own_ad(db: Session, ad_id: uuid_lib.UUID, user: User) -> Ad:
    ad = db.query(Ad).filter(Ad.id == ad_id, Ad.user_id == user.id).first()
    if not ad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anúncio não encontrado")
    ads_service.expire_if_needed(db, ad)
    return ad


def _check_ownership(db: Session, user: User, target_type: str, target_id: uuid_lib.UUID) -> None:
    model, owner_col = {
        "job": (Job, Job.empresa_user_id),
        "service": (Service, Service.user_id),
        "post": (Post, Post.user_id),
    }[target_type]
    obj = db.query(model).filter(model.id == target_id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado")
    if getattr(obj, owner_col.key) != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Só pode impulsionar os seus itens"
        )


@router.get("/plans", response_model=list[AdPlanOut])
def list_plans() -> list[AdPlanOut]:
    return [
        AdPlanOut(
            id=key,
            nome=p["nome"],
            dias=p["dias"],
            preco=p["preco"],
            currency=CURRENCY,
            descricao=p["descricao"],
        )
        for key, p in PLANS.items()
    ]


@router.get("/boostable", response_model=list[BoostableItem])
def list_boostable(user: CurrentUser, db: Session = Depends(get_db)) -> list[BoostableItem]:
    """Vagas, serviços e publicações do utilizador que podem ser impulsionados."""
    ends = {
        (a.target_type, a.job_id or a.service_id or a.post_id): a.ends_at
        for a in db.query(Ad)
        .filter(Ad.user_id == user.id, Ad.status == "active", Ad.ends_at > func.now())
        .all()
    }
    items: list[BoostableItem] = []
    for j in db.query(Job).filter(Job.empresa_user_id == user.id).order_by(Job.criado_em.desc()).all():
        items.append(
            BoostableItem(
                target_type="job",
                target_id=j.id,
                titulo=j.titulo,
                subtitulo=j.localizacao,
                impulsionado_ate=ends.get(("job", j.id)),
            )
        )
    for s in db.query(Service).filter(Service.user_id == user.id).order_by(Service.criado_em.desc()).all():
        items.append(
            BoostableItem(
                target_type="service",
                target_id=s.id,
                titulo=s.titulo,
                subtitulo=s.categoria,
                impulsionado_ate=ends.get(("service", s.id)),
            )
        )
    for p in db.query(Post).filter(Post.user_id == user.id).order_by(Post.criado_em.desc()).all():
        items.append(
            BoostableItem(
                target_type="post",
                target_id=p.id,
                titulo=p.titulo,
                subtitulo=p.localizacao,
                impulsionado_ate=ends.get(("post", p.id)),
            )
        )
    return items


@router.get("", response_model=list[AdOut])
def list_my_ads(user: CurrentUser, db: Session = Depends(get_db)) -> list[AdOut]:
    ads = db.query(Ad).filter(Ad.user_id == user.id).order_by(Ad.criado_em.desc()).all()
    for ad in ads:
        ads_service.expire_if_needed(db, ad)
    db.commit()
    return [_to_out(a) for a in ads]


@router.post("", response_model=AdOut, status_code=status.HTTP_201_CREATED)
def create_ad(body: AdCreate, user: CurrentUser, db: Session = Depends(get_db)) -> AdOut:
    plan = PLANS.get(body.plan)
    if not plan:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plano inválido")
    _check_ownership(db, user, body.target_type, body.target_id)

    col = TARGET_COLUMN[body.target_type]
    active = (
        db.query(Ad)
        .filter(col == body.target_id, Ad.status == "active", Ad.ends_at > func.now())
        .first()
    )
    if active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Este item já está impulsionado até {active.ends_at:%d/%m/%Y}",
        )

    # reutiliza um boost ainda por pagar para o mesmo alvo
    ad = (
        db.query(Ad)
        .filter(col == body.target_id, Ad.user_id == user.id, Ad.status == "pending_payment")
        .first()
    )
    if ad is None:
        ad = Ad(user_id=user.id, target_type=body.target_type, status="pending_payment")
        setattr(ad, col.key, body.target_id)
        db.add(ad)
    ad.plan = body.plan
    ad.preco = plan["preco"]
    ad.currency = CURRENCY
    ad.duration_days = plan["dias"]
    db.commit()
    db.refresh(ad)
    return _to_out(ad)


@router.post("/{ad_id}/pay", response_model=AdOut)
def pay_ad(
    ad_id: uuid_lib.UUID,
    body: AdPay,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> AdOut:
    ad = _get_own_ad(db, ad_id, user)
    if ad.status != "pending_payment":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Este anúncio não está por pagar"
        )
    if ad.payment is not None:
        payment_service.refresh_payment(db, ad.payment)
        db.refresh(ad)
        if ad.status != "pending_payment":
            return _to_out(ad)
        if ad.payment is not None and ad.payment.status == "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe um pagamento a aguardar confirmação",
            )

    _, titulo = _target(ad)
    payment = payment_service.start_skywallet_payment(
        db,
        user,
        msisdn=body.msisdn,
        amount=ad.preco,
        description=f"Boost {PLANS[ad.plan]['nome']}: {titulo or ''}"[:255],
    )
    ad.payment_id = payment.id
    db.commit()
    db.refresh(ad)
    return _to_out(ad)


@router.get("/{ad_id}", response_model=AdOut)
def get_ad(ad_id: uuid_lib.UUID, user: CurrentUser, db: Session = Depends(get_db)) -> AdOut:
    """Devolve o anúncio; se o pagamento estiver pendente, consulta o SkyWallet (polling)."""
    ad = _get_own_ad(db, ad_id, user)
    if ad.status == "pending_payment" and ad.payment is not None:
        payment_service.refresh_payment(db, ad.payment)
        db.refresh(ad)
    db.commit()
    return _to_out(ad)
