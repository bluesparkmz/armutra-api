from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ServiceUpdate(BaseModel):
    titulo: str | None = Field(None, max_length=500)
    descricao: str | None = None
    preco: Decimal | None = Field(None, ge=0)
    categoria: str | None = Field(None, max_length=120)


class ServiceCreate(BaseModel):
    titulo: str = Field(..., max_length=500)
    descricao: str
    preco: Decimal = Field(..., ge=0)
    categoria: str = Field(..., max_length=120)


class ServiceResponse(BaseModel):
    id: UUID
    user_id: UUID
    titulo: str
    descricao: str
    preco: str
    categoria: str
    criado_em: datetime
    impulsionado: bool = False
    owner_nome: str | None = None
    owner_foto: str | None = None
    localizacao: str | None = None

    model_config = {"from_attributes": True}
