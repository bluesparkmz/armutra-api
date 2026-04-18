from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    conteudo: str = Field(..., min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    id: UUID
    post_id: UUID
    user_id: UUID
    conteudo: str
    criado_em: datetime
    autor_nome: str | None = None
