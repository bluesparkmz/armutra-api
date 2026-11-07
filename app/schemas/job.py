from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    titulo: str = Field(..., max_length=500)
    descricao: str
    requisitos: str
    salario: str = Field(..., max_length=120)
    localizacao: str = Field(..., max_length=255)


class JobResponse(BaseModel):
    id: UUID
    empresa_user_id: UUID
    titulo: str
    descricao: str
    requisitos: str
    salario: str
    localizacao: str
    criado_em: datetime
    impulsionado: bool = False

    model_config = {"from_attributes": True}


class JobApplyRequest(BaseModel):
    mensagem: Optional[str] = None
