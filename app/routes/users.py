import uuid as uuid_lib
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.deps import CurrentUser
from app.models.user import User, UserType
from app.schemas.user import CandidatoProfileOut, EmpresaProfileOut, UserPublicResponse, UserUpdateRequest
from app.services import bsdrive

router = APIRouter(prefix="/users", tags=["users"])


def _to_public(user: User) -> UserPublicResponse:
    empresa = None
    candidato = None
    if user.empresa_profile:
        empresa = EmpresaProfileOut.model_validate(user.empresa_profile)
    if user.candidato_profile:
        c = user.candidato_profile
        candidato = CandidatoProfileOut(
            habilidades=list(c.habilidades or []),
            experiencia=c.experiencia,
            educacao=c.educacao,
            cv_url=c.cv_url,
        )
    return UserPublicResponse(
        id=user.id,
        nome=user.nome,
        email=user.email,
        tipo=user.tipo,
        foto_perfil=user.foto_perfil,
        bio=user.bio,
        localizacao=user.localizacao,
        criado_em=user.criado_em,
        empresa=empresa,
        candidato=candidato,
    )


@router.put("/update", response_model=UserPublicResponse)
def update_me(
    body: UserUpdateRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> UserPublicResponse:
    if body.senha_nova:
        if not body.senha_atual or not verify_password(body.senha_atual, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual inválida")
        user.hashed_password = hash_password(body.senha_nova)

    if body.nome is not None:
        user.nome = body.nome
    if body.foto_perfil is not None:
        user.foto_perfil = body.foto_perfil
    if body.bio is not None:
        user.bio = body.bio
    if body.localizacao is not None:
        user.localizacao = body.localizacao

    if body.empresa is not None:
        if user.tipo != UserType.EMPRESA or not user.empresa_profile:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Perfil de empresa inexistente")
        ep = user.empresa_profile
        u = body.empresa
        if u.nome_empresa is not None:
            ep.nome_empresa = u.nome_empresa
        if u.descricao is not None:
            ep.descricao = u.descricao
        if u.website is not None:
            ep.website = u.website

    if body.candidato is not None:
        if user.tipo != UserType.CANDIDATO or not user.candidato_profile:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Perfil de candidato inexistente")
        cp = user.candidato_profile
        c = body.candidato
        if c.habilidades is not None:
            cp.habilidades = c.habilidades
        if c.experiencia is not None:
            cp.experiencia = c.experiencia
        if c.educacao is not None:
            cp.educacao = c.educacao

    db.commit()
    db.refresh(user)
    return _to_public(user)


@router.get("/{user_id}", response_model=UserPublicResponse)
def get_user(user_id: uuid_lib.UUID, db: Session = Depends(get_db)) -> UserPublicResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilizador não encontrado")
    return _to_public(user)


@router.post("/me/cv", response_model=UserPublicResponse)
async def upload_cv(
    user: CurrentUser,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
) -> UserPublicResponse:
    if user.tipo != UserType.CANDIDATO or not user.candidato_profile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Apenas candidatos podem enviar CV")

    ext = Path(file.filename or "").suffix.lower() or ".pdf"
    content_types = {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    content_type = content_types.get(ext)
    if not content_type:
        raise HTTPException(status_code=400, detail="Formato de ficheiro não suportado (use PDF ou Word)")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="O ficheiro está vazio")
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="O CV passa de 8 MB")
    try:
        file_id = await bsdrive.store_bytes(
            filename=f"{user.id}-cv{ext}",
            content_type=content_type,
            data=data,
        )
    except bsdrive.StorageError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    user.candidato_profile.cv_url = f"/uploads/files/{file_id}"
    db.commit()
    db.refresh(user)
    return _to_public(user)
