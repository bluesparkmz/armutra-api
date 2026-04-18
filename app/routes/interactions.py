import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import CurrentUser
from app.models.interaction import PostComment, PostLike, PostShare
from app.models.post import Post

from app.schemas.interaction import CommentCreate, CommentResponse

router = APIRouter(tags=["interactions"])


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
