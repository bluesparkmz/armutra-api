from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.user import UserType


class ConnectionUserOut(BaseModel):
    id: UUID
    nome: str
    tipo: UserType
    foto_perfil: Optional[str] = None
    localizacao: str
    seguindo_desde: datetime


class ConnectionCounts(BaseModel):
    seguidores: int
    a_seguir: int


class ConnectionStatus(ConnectionCounts):
    a_seguir_utilizador: bool
    segue_me: bool
