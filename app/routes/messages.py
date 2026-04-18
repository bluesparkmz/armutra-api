import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.deps import CurrentUser
from app.models.message import Conversation, Message
from app.models.user import User
from app.schemas.message import MessageCreate, MessageItem, MessagesListResponse
from app.utils.conversation import ordered_user_ids

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("", response_model=MessagesListResponse, status_code=status.HTTP_201_CREATED)
def send_message(
    body: MessageCreate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> MessagesListResponse:
    if body.destinatario_user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Destinatário inválido",
        )
    other = db.query(User).filter(User.id == body.destinatario_user_id).first()
    if not other:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destinatário não encontrado")

    a, b = ordered_user_ids(user.id, body.destinatario_user_id)
    conv = (
        db.query(Conversation)
        .filter(
            Conversation.participant_a_id == a,
            Conversation.participant_b_id == b,
        )
        .first()
    )
    if not conv:
        conv = Conversation(participant_a_id=a, participant_b_id=b)
        db.add(conv)
        db.flush()

    msg = Message(
        conversation_id=conv.id,
        sender_id=user.id,
        conteudo=body.conteudo,
    )
    db.add(msg)
    db.commit()
    db.refresh(conv)
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.criado_em.asc())
        .all()
    )
    return MessagesListResponse(
        conversation_id=conv.id,
        messages=[MessageItem.model_validate(m) for m in msgs],
    )


@router.get("/{conversation_id}", response_model=MessagesListResponse)
def list_messages(
    conversation_id: uuid_lib.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> MessagesListResponse:
    conv = (
        db.query(Conversation)
        .options(joinedload(Conversation.messages))
        .filter(Conversation.id == conversation_id)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada")
    if user.id not in (conv.participant_a_id, conv.participant_b_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    msgs = sorted(conv.messages, key=lambda m: m.criado_em)
    return MessagesListResponse(
        conversation_id=conv.id,
        messages=[MessageItem.model_validate(m) for m in msgs],
    )
