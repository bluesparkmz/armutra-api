import uuid as uuid_lib
from typing import Optional

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.user import User


def notify(
    db: Session,
    *,
    recipient_id: uuid_lib.UUID,
    actor: Optional[User],
    tipo: str,
    titulo: str,
    mensagem: str,
    ref_id: Optional[uuid_lib.UUID] = None,
) -> None:
    """Regista uma notificação (sem commit; o chamador faz commit). Ignora auto-notificações."""
    if actor is not None and actor.id == recipient_id:
        return
    db.add(
        Notification(
            user_id=recipient_id,
            actor_id=actor.id if actor else None,
            tipo=tipo,
            titulo=titulo,
            mensagem=mensagem,
            ref_id=ref_id,
        )
    )
