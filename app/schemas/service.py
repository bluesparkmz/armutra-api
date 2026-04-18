from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


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

    model_config = {"from_attributes": True}
