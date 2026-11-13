from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    titulo: str = Field(..., max_length=500)
    descricao: str
    requisitos: str
    salario: str = Field(..., max_length=120)
    localizacao: str = Field(..., max_length=255)


class JobUpdate(BaseModel):
    titulo: Optional[str] = Field(None, max_length=500)
    descricao: Optional[str] = None
    requisitos: Optional[str] = None
    salario: Optional[str] = Field(None, max_length=120)
    localizacao: Optional[str] = Field(None, max_length=255)
    estado: Optional[Literal["aberta", "fechada"]] = None


class JobResponse(BaseModel):
    id: UUID
    empresa_user_id: UUID
    titulo: str
    descricao: str
    requisitos: str
    salario: str
    localizacao: str
    estado: str = "aberta"
    criado_em: datetime
    impulsionado: bool = False
    empresa_nome: Optional[str] = None
    empresa_foto: Optional[str] = None
    candidaturas: int = 0

    model_config = {"from_attributes": True}


class JobApplyRequest(BaseModel):
    mensagem: Optional[str] = None


class ApplicationStatusUpdate(BaseModel):
    estado: Literal["pendente", "aceite", "recusada"]


class JobApplicationOut(BaseModel):
    id: UUID
    job_id: UUID
    candidato_user_id: UUID
    mensagem: Optional[str] = None
    estado: str = "pendente"
    criado_em: datetime
    candidato_nome: Optional[str] = None
    candidato_foto: Optional[str] = None
    candidato_localizacao: Optional[str] = None
    cv_url: Optional[str] = None
    vaga_titulo: Optional[str] = None
    empresa_user_id: Optional[UUID] = None
    empresa_nome: Optional[str] = None
