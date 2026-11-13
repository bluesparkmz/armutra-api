from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    """Cria ou reutiliza conversa com destinatário e envia mensagem."""

    destinatario_user_id: UUID
    conteudo: str = Field(..., min_length=1, max_length=8000)


class MessageItem(BaseModel):
    id: UUID
    conversation_id: UUID
    sender_id: UUID
    conteudo: str
    criado_em: datetime

    model_config = {"from_attributes": True}


class MessagesListResponse(BaseModel):
    conversation_id: UUID
    messages: list[MessageItem]


class ConversationSummary(BaseModel):
    id: UUID
    outro_user_id: UUID
    outro_nome: str
    outro_foto: str | None = None
    ultima_mensagem: str | None = None
    atualizado_em: datetime
