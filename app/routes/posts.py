import uuid as uuid_lib
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.deps import CurrentUser
from app.models.interaction import PostComment, PostLike, PostShare
from app.models.post import Post, PostTipo
from app.schemas.post import PostAuthorBrief, PostCreate, PostResponse

router = APIRouter(prefix="/posts", tags=["posts"])


def _post_to_response(db: Session, post: Post) -> PostResponse:
    likes_count = db.query(PostLike).filter(PostLike.post_id == post.id).count()
    comments_count = db.query(PostComment).filter(PostComment.post_id == post.id).count()
    shares_count = db.query(PostShare).filter(PostShare.post_id == post.id).count()
    autor = None
    author = post.author
    if author:
        autor = PostAuthorBrief(
            id=author.id,
            nome=author.nome,
            foto_perfil=author.foto_perfil,
            tipo=author.tipo.value,
        )
    imagens = list(post.imagens) if post.imagens is not None else None
    return PostResponse(
        id=post.id,
        user_id=post.user_id,
        tipo_post=post.tipo_post,
        titulo=post.titulo,
        descricao=post.descricao,
        salario=post.salario,
        localizacao=post.localizacao,
        imagens=imagens,
        job_id=post.job_id,
        service_id=post.service_id,
        criado_em=post.criado_em,
        likes_count=likes_count,
        comments_count=comments_count,
        shares_count=shares_count,
        autor=autor,
    )


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    body: PostCreate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> PostResponse:
    p = Post(
        user_id=user.id,
        tipo_post=body.tipo_post,
        titulo=body.titulo,
        descricao=body.descricao,
        salario=body.salario,
        localizacao=body.localizacao,
        imagens=body.imagens,
        job_id=body.job_id,
        service_id=body.service_id,
    )
    db.add(p)
    db.commit()
    p = (
        db.query(Post)
        .options(joinedload(Post.author))
        .filter(Post.id == p.id)
        .first()
    )
    assert p is not None
    return _post_to_response(db, p)


@router.get("", response_model=list[PostResponse])
def list_posts(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    tipo: Optional[PostTipo] = None,
) -> list[PostResponse]:
    q = db.query(Post).options(joinedload(Post.author)).order_by(Post.criado_em.desc())
    if tipo is not None:
        q = q.filter(Post.tipo_post == tipo)
    rows = q.offset(skip).limit(limit).all()
    return [_post_to_response(db, p) for p in rows]


@router.get("/{post_id}", response_model=PostResponse)
def get_post(post_id: uuid_lib.UUID, db: Session = Depends(get_db)) -> PostResponse:
    p = (
        db.query(Post)
        .options(joinedload(Post.author))
        .filter(Post.id == post_id)
        .first()
    )
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post não encontrado")
    return _post_to_response(db, p)
