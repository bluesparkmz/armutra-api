from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.post import PostTipo


class PostCreate(BaseModel):
    tipo_post: PostTipo
    titulo: str = Field(..., max_length=500)
    descricao: str
    salario: Optional[str] = Field(None, max_length=120)
    localizacao: str = Field(..., max_length=255)
    imagens: Optional[list[str]] = None
    job_id: Optional[UUID] = None
    service_id: Optional[UUID] = None


class PostAuthorBrief(BaseModel):
    id: UUID
    nome: str
    foto_perfil: Optional[str] = None
    tipo: str

    model_config = {"from_attributes": True}


class PostResponse(BaseModel):
    id: UUID
    user_id: UUID
    tipo_post: PostTipo
    titulo: str
    descricao: str
    salario: Optional[str] = None
    localizacao: str
    imagens: Optional[list[str]] = None
    job_id: Optional[UUID] = None
    service_id: Optional[UUID] = None
    criado_em: datetime
    likes_count: int = 0
    comments_count: int = 0
    shares_count: int = 0
    impulsionado: bool = False
    autor: Optional[PostAuthorBrief] = None

    model_config = {"from_attributes": True}
