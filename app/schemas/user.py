from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.user import UserType


class EmpresaProfileOut(BaseModel):
    nome_empresa: str
    descricao: Optional[str] = None
    website: Optional[str] = None

    model_config = {"from_attributes": True}


class CandidatoProfileOut(BaseModel):
    habilidades: list[str]
    experiencia: Optional[str] = None
    educacao: Optional[str] = None
    cv_url: Optional[str] = None

    model_config = {"from_attributes": True}


class UserPublicResponse(BaseModel):
    id: UUID
    nome: str
    email: str
    tipo: UserType
    foto_perfil: Optional[str] = None
    bio: Optional[str] = None
    localizacao: str
    criado_em: datetime
    empresa: Optional[EmpresaProfileOut] = None
    candidato: Optional[CandidatoProfileOut] = None

    model_config = {"from_attributes": True}


class EmpresaProfileUpdate(BaseModel):
    nome_empresa: Optional[str] = Field(None, max_length=255)
    descricao: Optional[str] = None
    website: Optional[str] = Field(None, max_length=512)


class CandidatoProfileUpdate(BaseModel):
    habilidades: Optional[list[str]] = None
    experiencia: Optional[str] = None
    educacao: Optional[str] = None


class UserUpdateRequest(BaseModel):
    nome: Optional[str] = Field(None, max_length=255)
    foto_perfil: Optional[str] = Field(None, max_length=512)
    bio: Optional[str] = None
    localizacao: Optional[str] = Field(None, max_length=255)
    senha_atual: Optional[str] = None
    senha_nova: Optional[str] = Field(None, min_length=8, max_length=128)
    empresa: Optional[EmpresaProfileUpdate] = None
    candidato: Optional[CandidatoProfileUpdate] = None
