from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import CurrentUser
from app.models.service import Service
from app.models.user import User
from app.schemas.service import ServiceCreate, ServiceResponse

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
    db.refresh(s)
    return _service_out(s)


def _service_out(s: Service) -> ServiceResponse:
    return ServiceResponse(
        id=s.id,
        user_id=s.user_id,
        titulo=s.titulo,
        descricao=s.descricao,
        preco=str(Decimal(str(s.preco))),
        categoria=s.categoria,
        criado_em=s.criado_em,
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
) -> list[ServiceResponse]:
    qr = db.query(Service).join(User, User.id == Service.user_id)
    if categoria:
        qr = qr.filter(Service.categoria.ilike(f"%{categoria.strip()}%"))
    if preco_max is not None:
        qr = qr.filter(Service.preco <= preco_max)
    if localizacao:
        qr = qr.filter(User.localizacao.ilike(f"%{localizacao}%"))
    if q:
        like = f"%{q}%"
        qr = qr.filter((Service.titulo.ilike(like)) | (Service.descricao.ilike(like)))
    rows = qr.order_by(Service.criado_em.desc()).offset(skip).limit(limit).all()
    return [_service_out(s) for s in rows]
