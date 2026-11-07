from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.models.ad import Ad
from app.models.job import Job
from app.models.payment import Payment
from app.models.post import Post
from app.models.service import Service
from app.services.notification_service import notify


def _active():
    return and_(Ad.status == "active", Ad.ends_at > func.now())


def active_ids(db: Session) -> dict[str, set]:
    """IDs com boost ativo, por tipo de alvo."""
    rows = db.query(Ad.job_id, Ad.service_id, Ad.post_id).filter(_active()).all()
    return {
        "job": {r.job_id for r in rows if r.job_id},
        "service": {r.service_id for r in rows if r.service_id},
        "post": {r.post_id for r in rows if r.post_id},
    }


def job_rank():
    """Expressão SQL para ordenar vagas impulsionadas primeiro."""
    sub = select(Ad.job_id).where(Ad.job_id.isnot(None), _active())
    return case((Job.id.in_(sub), 1), else_=0)


def service_rank():
    sub = select(Ad.service_id).where(Ad.service_id.isnot(None), _active())
    return case((Service.id.in_(sub), 1), else_=0)


def post_rank():
    """Uma publicação sobe se ela, a vaga ou o serviço ligado estiverem impulsionados."""
    posts = select(Ad.post_id).where(Ad.post_id.isnot(None), _active())
    jobs = select(Ad.job_id).where(Ad.job_id.isnot(None), _active())
    services = select(Ad.service_id).where(Ad.service_id.isnot(None), _active())
    return case(
        (
            or_(
                Post.id.in_(posts),
                Post.job_id.in_(jobs),
                Post.service_id.in_(services),
            ),
            1,
        ),
        else_=0,
    )


def post_is_boosted(post: Post, ids: dict[str, set]) -> bool:
    return (
        post.id in ids["post"]
        or (post.job_id is not None and post.job_id in ids["job"])
        or (post.service_id is not None and post.service_id in ids["service"])
    )


def expire_if_needed(db: Session, ad: Ad) -> None:
    """Marca como expirado um boost cujo prazo terminou (sem commit)."""
    if ad.status != "active" or not ad.ends_at:
        return
    ends = ad.ends_at if ad.ends_at.tzinfo else ad.ends_at.replace(tzinfo=timezone.utc)
    if ends <= datetime.now(timezone.utc):
        ad.status = "expired"


def expire_overdue(db: Session) -> None:
    """Marca em massa como expirados os boosts cujo prazo terminou (com commit)."""
    db.query(Ad).filter(Ad.status == "active", Ad.ends_at <= func.now()).update(
        {Ad.status: "expired"}, synchronize_session=False
    )
    db.commit()


def on_payment_final(db: Session, payment: Payment) -> None:
    """Chamado quando um pagamento fica 'success'/'failed'. Ativa o anúncio ligado (sem commit)."""
    if payment.status != "success":
        return
    ad = (
        db.query(Ad)
        .filter(Ad.payment_id == payment.id, Ad.status == "pending_payment")
        .first()
    )
    if not ad:
        return
    now = datetime.now(timezone.utc)
    ad.status = "active"
    ad.starts_at = now
    ad.ends_at = now + timedelta(days=ad.duration_days)
    notify(
        db,
        recipient_id=ad.user_id,
        actor=None,
        tipo="ad",
        titulo="Boost ativo",
        mensagem=f"O seu anúncio está em destaque durante {ad.duration_days} dias.",
        ref_id=ad.id,
    )
