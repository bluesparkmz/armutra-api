import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import CurrentUser
from app.models.connection import Connection
from app.models.user import User
from app.services.notification_service import notify
from app.schemas.connection import ConnectionCounts, ConnectionStatus, ConnectionUserOut

router = APIRouter(prefix="/connections", tags=["connections"])


def _counts(db: Session, user_id: uuid_lib.UUID) -> ConnectionCounts:
    seguidores = (
        db.query(func.count(Connection.id)).filter(Connection.following_id == user_id).scalar()
    )
    a_seguir = (
        db.query(func.count(Connection.id)).filter(Connection.follower_id == user_id).scalar()
    )
    return ConnectionCounts(seguidores=seguidores or 0, a_seguir=a_seguir or 0)


def _get_user_or_404(db: Session, user_id: uuid_lib.UUID) -> User:
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilizador não encontrado")
    return target


def _status(db: Session, me: User, target_id: uuid_lib.UUID) -> ConnectionStatus:
    counts = _counts(db, target_id)
    following = (
        db.query(Connection.id)
        .filter(Connection.follower_id == me.id, Connection.following_id == target_id)
        .first()
        is not None
    )
    followed_by = (
        db.query(Connection.id)
        .filter(Connection.follower_id == target_id, Connection.following_id == me.id)
        .first()
        is not None
    )
    return ConnectionStatus(
        seguidores=counts.seguidores,
        a_seguir=counts.a_seguir,
        a_seguir_utilizador=following,
        segue_me=followed_by,
    )


def _to_out(user: User, conn: Connection) -> ConnectionUserOut:
    return ConnectionUserOut(
        id=user.id,
        nome=user.nome,
        tipo=user.tipo,
        foto_perfil=user.foto_perfil,
        localizacao=user.localizacao,
        seguindo_desde=conn.criado_em,
    )


@router.get("/following", response_model=list[ConnectionUserOut])
def list_following(user: CurrentUser, db: Session = Depends(get_db)) -> list[ConnectionUserOut]:
    rows = (
        db.query(Connection)
        .filter(Connection.follower_id == user.id)
        .order_by(Connection.criado_em.desc())
        .all()
    )
    return [_to_out(c.following, c) for c in rows]


@router.get("/followers", response_model=list[ConnectionUserOut])
def list_followers(user: CurrentUser, db: Session = Depends(get_db)) -> list[ConnectionUserOut]:
    rows = (
        db.query(Connection)
        .filter(Connection.following_id == user.id)
        .order_by(Connection.criado_em.desc())
        .all()
    )
    return [_to_out(c.follower, c) for c in rows]


@router.get("/{user_id}/counts", response_model=ConnectionCounts)
def user_counts(user_id: uuid_lib.UUID, db: Session = Depends(get_db)) -> ConnectionCounts:
    _get_user_or_404(db, user_id)
    return _counts(db, user_id)


@router.get("/{user_id}/status", response_model=ConnectionStatus)
def connection_status(
    user_id: uuid_lib.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> ConnectionStatus:
    _get_user_or_404(db, user_id)
    return _status(db, user, user_id)


@router.post("/{user_id}", response_model=ConnectionStatus, status_code=status.HTTP_201_CREATED)
def follow_user(
    user_id: uuid_lib.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> ConnectionStatus:
    if user_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não pode seguir-se a si próprio")
    _get_user_or_404(db, user_id)
    exists = (
        db.query(Connection.id)
        .filter(Connection.follower_id == user.id, Connection.following_id == user_id)
        .first()
    )
    if not exists:
        db.add(Connection(follower_id=user.id, following_id=user_id))
        notify(
            db,
            recipient_id=user_id,
            actor=user,
            tipo="connection",
            titulo="Novo seguidor",
            mensagem=f"{user.nome} começou a seguir o seu perfil.",
            ref_id=user.id,
        )
        db.commit()
    return _status(db, user, user_id)


@router.delete("/{user_id}", response_model=ConnectionStatus)
def unfollow_user(
    user_id: uuid_lib.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> ConnectionStatus:
    db.query(Connection).filter(
        Connection.follower_id == user.id, Connection.following_id == user_id
    ).delete()
    db.commit()
    return _status(db, user, user_id)
