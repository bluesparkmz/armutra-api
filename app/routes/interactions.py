import uuid as uuid_lib
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import CurrentUser
from app.models.interaction import PostComment, PostLike, PostShare
from app.models.post import Post
from app.models.user import User

from app.schemas.interaction import CommentCreate, CommentResponse
from app.services.notification_service import notify

router = APIRouter(tags=["interactions"])

TargetType = Literal["post", "service", "job"]


class SocialTarget(BaseModel):
    user_id: Optional[uuid_lib.UUID] = None
    target_type: TargetType
    target_id: uuid_lib.UUID


class SocialCommentCreate(SocialTarget):
    content: str = Field(..., min_length=1, max_length=5000)
    parent_id: Optional[uuid_lib.UUID] = None


def _require_post(db: Session, target_type: str, target_id: uuid_lib.UUID) -> Post:
    if target_type != "post":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nesta API só publicações aceitam gostos e comentários",
        )
    post = db.query(Post).filter(Post.id == target_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post não encontrado")
    return post


def _comment_out(comment: PostComment, nome: str) -> dict:
    return {
        "id": str(comment.id),
        "user_id": str(comment.user_id),
        "target_type": "post",
        "target_id": str(comment.post_id),
        "content": comment.conteudo,
        "conteudo": comment.conteudo,
        "parent_id": None,
        "created_at": comment.criado_em,
        "criado_em": comment.criado_em,
        "autor_nome": nome,
        "user": {"id": str(comment.user_id), "name": nome, "nome": nome},
    }


@router.post("/social/likes", status_code=status.HTTP_201_CREATED)
def social_like(body: SocialTarget, user: CurrentUser, db: Session = Depends(get_db)) -> dict:
    post = _require_post(db, body.target_type, body.target_id)
    existing = (
        db.query(PostLike)
        .filter(PostLike.post_id == post.id, PostLike.user_id == user.id)
        .first()
    )
    if not existing:
        db.add(PostLike(post_id=post.id, user_id=user.id))
        notify(
            db,
            recipient_id=post.user_id,
            actor=user,
            tipo="like",
            titulo="Novo gosto",
            mensagem=f"{user.nome} gostou da sua publicação \"{post.titulo}\".",
            ref_id=post.id,
        )
        db.commit()
    return {"ok": True, "liked": True}


@router.delete("/social/likes", status_code=status.HTTP_200_OK)
def social_unlike(body: SocialTarget, user: CurrentUser, db: Session = Depends(get_db)) -> dict:
    post = _require_post(db, body.target_type, body.target_id)
    db.query(PostLike).filter(PostLike.post_id == post.id, PostLike.user_id == user.id).delete()
    db.commit()
    return {"ok": True, "liked": False}


@router.get("/social/likes/check")
def social_like_check(
    target_type: TargetType,
    target_id: uuid_lib.UUID,
    user_id: uuid_lib.UUID = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    if target_type != "post":
        return {"liked": False}
    liked = (
        db.query(PostLike)
        .filter(PostLike.post_id == target_id, PostLike.user_id == user_id)
        .first()
        is not None
    )
    return {"liked": liked}


@router.get("/social/comments")
def social_list_comments(
    target_type: TargetType,
    target_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
) -> list[dict]:
    if target_type != "post":
        return []
    rows = (
        db.query(PostComment, User.nome)
        .join(User, User.id == PostComment.user_id)
        .filter(PostComment.post_id == target_id)
        .order_by(PostComment.criado_em.asc())
        .all()
    )
    return [_comment_out(comment, nome) for comment, nome in rows]


@router.post("/social/comments", status_code=status.HTTP_201_CREATED)
def social_comment(
    body: SocialCommentCreate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> dict:
    post = _require_post(db, body.target_type, body.target_id)
    comment = PostComment(post_id=post.id, user_id=user.id, conteudo=body.content)
    db.add(comment)
    notify(
        db,
        recipient_id=post.user_id,
        actor=user,
        tipo="comment",
        titulo="Novo comentário",
        mensagem=f"{user.nome} comentou a sua publicação \"{post.titulo}\".",
        ref_id=post.id,
    )
    db.commit()
    db.refresh(comment)
    return _comment_out(comment, user.nome)


@router.post("/like/{post_id}", status_code=status.HTTP_201_CREATED)
def like_post(
    post_id: uuid_lib.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> dict:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post não encontrado")
    existing = (
        db.query(PostLike)
        .filter(PostLike.post_id == post_id, PostLike.user_id == user.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já curtiu este post")
    db.add(PostLike(post_id=post_id, user_id=user.id))
    notify(
        db,
        recipient_id=post.user_id,
        actor=user,
        tipo="like",
        titulo="Novo gosto",
        mensagem=f"{user.nome} gostou da sua publicação \"{post.titulo}\".",
        ref_id=post.id,
    )
    db.commit()
    return {"ok": True}


@router.post("/comment/{post_id}", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def comment_post(
    post_id: uuid_lib.UUID,
    body: CommentCreate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> CommentResponse:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post não encontrado")
    c = PostComment(post_id=post_id, user_id=user.id, conteudo=body.conteudo)
    db.add(c)
    notify(
        db,
        recipient_id=post.user_id,
        actor=user,
        tipo="comment",
        titulo="Novo comentário",
        mensagem=f"{user.nome} comentou a sua publicação \"{post.titulo}\".",
        ref_id=post.id,
    )
    db.commit()
    db.refresh(c)
    return CommentResponse(
        id=c.id,
        post_id=c.post_id,
        user_id=c.user_id,
        conteudo=c.conteudo,
        criado_em=c.criado_em,
        autor_nome=user.nome,
    )


@router.post("/share/{post_id}", status_code=status.HTTP_201_CREATED)
def share_post(
    post_id: uuid_lib.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> dict:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post não encontrado")
    db.add(PostShare(post_id=post_id, user_id=user.id))
    db.commit()
    return {"ok": True}
