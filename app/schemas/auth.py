from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserType


class EmpresaProfileIn(BaseModel):
    nome_empresa: str = Field(..., max_length=255)
    descricao: Optional[str] = None
    website: Optional[str] = Field(None, max_length=512)


class CandidatoProfileIn(BaseModel):
    habilidades: list[str] = Field(default_factory=list)
    experiencia: Optional[str] = None
    educacao: Optional[str] = None


class RegisterRequest(BaseModel):
    nome: str = Field(..., max_length=255)
    email: EmailStr
    senha: str = Field(..., min_length=8, max_length=128)
    tipo: UserType
    localizacao: str = Field(..., max_length=255)
    bio: Optional[str] = None
    empresa: Optional[EmpresaProfileIn] = None
    candidato: Optional[CandidatoProfileIn] = None


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserMeResponse(BaseModel):
    id: UUID
    nome: str
    email: str
    tipo: UserType
    foto_perfil: Optional[str] = None
    bio: Optional[str] = None
    localizacao: str
    criado_em: datetime
    is_admin: bool = False

    model_config = {"from_attributes": True}
