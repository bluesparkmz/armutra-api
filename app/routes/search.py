from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.job import Job
from app.models.service import Service
from app.models.user import User, UserType
from app.schemas.job import JobResponse
from app.schemas.service import ServiceResponse
from app.schemas.user import UserPublicResponse
from app.routes.jobs import _with_empresa, job_to_response
from app.routes.services_routes import _service_out
from app.routes.users import _to_public
from app.services import ads_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/jobs", response_model=list[JobResponse])
def search_jobs(
    db: Session = Depends(get_db),
    q: Optional[str] = None,
    localizacao: Optional[str] = None,
    salario: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
) -> list[JobResponse]:
    qr = _with_empresa(db.query(Job)).filter(Job.estado == "aberta")
    if localizacao:
        qr = qr.filter(Job.localizacao.ilike(f"%{localizacao}%"))
    if salario:
        qr = qr.filter(Job.salario.ilike(f"%{salario}%"))
    if q:
        like = f"%{q}%"
        qr = qr.filter((Job.titulo.ilike(like)) | (Job.descricao.ilike(like)))
    jobs = (
        qr.order_by(ads_service.job_rank().desc(), Job.criado_em.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    boosted = ads_service.active_ids(db)["job"]
    return [job_to_response(j, j.id in boosted) for j in jobs]


@router.get("/services", response_model=list[ServiceResponse])
def search_services(
    db: Session = Depends(get_db),
    q: Optional[str] = None,
    categoria: Optional[str] = None,
    preco_max: Optional[float] = None,
    localizacao: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
) -> list[ServiceResponse]:
    from decimal import Decimal

    qr = db.query(Service).options(joinedload(Service.owner)).join(User, User.id == Service.user_id)
    if categoria:
        qr = qr.filter(Service.categoria.ilike(f"%{categoria}%"))
    if preco_max is not None:
        qr = qr.filter(Service.preco <= Decimal(str(preco_max)))
    if localizacao:
        qr = qr.filter(User.localizacao.ilike(f"%{localizacao}%"))
    if q:
        like = f"%{q}%"
        qr = qr.filter((Service.titulo.ilike(like)) | (Service.descricao.ilike(like)))
    rows = (
        qr.order_by(ads_service.service_rank().desc(), Service.criado_em.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    boosted = ads_service.active_ids(db)["service"]
    return [_service_out(s, s.id in boosted) for s in rows]


@router.get("/users", response_model=list[UserPublicResponse])
def search_users(
    db: Session = Depends(get_db),
    q: Optional[str] = None,
    tipo: Optional[UserType] = None,
    localizacao: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
) -> list[UserPublicResponse]:
    qr = (
        db.query(User)
        .options(
            joinedload(User.empresa_profile),
            joinedload(User.candidato_profile),
        )
    )
    if tipo is not None:
        qr = qr.filter(User.tipo == tipo)
    if localizacao:
        qr = qr.filter(User.localizacao.ilike(f"%{localizacao}%"))
    if q:
        like = f"%{q}%"
        qr = qr.filter((User.nome.ilike(like)) | (User.email.ilike(like)))
    rows = qr.order_by(User.criado_em.desc()).offset(skip).limit(limit).all()
    return [_to_public(u) for u in rows]
