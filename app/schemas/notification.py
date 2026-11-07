from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: UUID
    tipo: str
    titulo: str
    mensagem: str
    actor_id: Optional[UUID] = None
    ref_id: Optional[UUID] = None
    lida: bool
    criado_em: datetime

    model_config = {"from_attributes": True}


class UnreadCount(BaseModel):
    nao_lidas: int
