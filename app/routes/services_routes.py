from decimal import Decimal
from typing import Optional

import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.deps import CurrentUser
from app.models.service import Service
from app.models.user import User
from app.schemas.service import ServiceCreate, ServiceResponse, ServiceUpdate
from app.services import ads_service

router = APIRouter(prefix="/services", tags=["services"])


@router.post("", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service(
    body: ServiceCreate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> ServiceResponse:
    s = Service(
        user_id=user.id,
        titulo=body.titulo,
        descricao=body.descricao,
        preco=body.preco,
        categoria=body.categoria.strip(),
    )
    db.add(s)
    db.commit()
    s = db.query(Service).options(joinedload(Service.owner)).filter(Service.id == s.id).first()
    assert s is not None
    return _service_out(s)


def _service_out(s: Service, impulsionado: bool = False) -> ServiceResponse:
    owner = s.owner
    return ServiceResponse(
        id=s.id,
        user_id=s.user_id,
        titulo=s.titulo,
        descricao=s.descricao,
        preco=str(Decimal(str(s.preco))),
        categoria=s.categoria,
        criado_em=s.criado_em,
        impulsionado=impulsionado,
        owner_nome=owner.nome if owner is not None else None,
        owner_foto=owner.foto_perfil if owner is not None else None,
        localizacao=owner.localizacao if owner is not None else None,
    )


@router.get("", response_model=list[ServiceResponse])
def list_services(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    categoria: Optional[str] = None,
    preco_max: Optional[Decimal] = None,
    localizacao: Optional[str] = None,
    q: Optional[str] = None,
    user_id: Optional[uuid_lib.UUID] = None,
) -> list[ServiceResponse]:
    qr = db.query(Service).options(joinedload(Service.owner)).join(User, User.id == Service.user_id)
    if user_id:
        qr = qr.filter(Service.user_id == user_id)
    if categoria:
        qr = qr.filter(Service.categoria.ilike(f"%{categoria.strip()}%"))
    if preco_max is not None:
        qr = qr.filter(Service.preco <= preco_max)
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


@router.get("/mine", response_model=list[ServiceResponse])
def my_services(user: CurrentUser, db: Session = Depends(get_db)) -> list[ServiceResponse]:
    rows = (
        db.query(Service)
        .options(joinedload(Service.owner))
        .filter(Service.user_id == user.id)
        .order_by(Service.criado_em.desc())
        .all()
    )
    boosted = ads_service.active_ids(db)["service"]
    return [_service_out(s, s.id in boosted) for s in rows]


@router.patch("/{service_id}", response_model=ServiceResponse)
def update_service(
    service_id: uuid_lib.UUID,
    body: ServiceUpdate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> ServiceResponse:
    row = db.query(Service).options(joinedload(Service.owner)).filter(Service.id == service_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Serviço não encontrado")
    if row.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Só pode editar os seus serviços")
    data = body.model_dump(exclude_unset=True)
    if "categoria" in data and data["categoria"]:
        data["categoria"] = data["categoria"].strip()
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return _service_out(row, row.id in ads_service.active_ids(db)["service"])


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    service_id: uuid_lib.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> None:
    row = db.query(Service).filter(Service.id == service_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Serviço não encontrado")
    if row.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Só pode apagar os seus serviços")
    db.delete(row)
    db.commit()


@router.get("/{service_id}", response_model=ServiceResponse)
def get_service(service_id: uuid_lib.UUID, db: Session = Depends(get_db)) -> ServiceResponse:
    row = (
        db.query(Service)
        .options(joinedload(Service.owner))
        .filter(Service.id == service_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Serviço não encontrado")
    boosted = row.id in ads_service.active_ids(db)["service"]
    return _service_out(row, boosted)
