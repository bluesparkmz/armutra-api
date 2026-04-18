from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token_safe,
    verify_password,
)
from app.db.session import get_db
from app.deps import CurrentUser
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserMeResponse,
)
from app.services.auth_service import create_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        user = create_user(db, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    access = create_access_token(user.id, extra_claims={"email": user.email})
    refresh = create_refresh_token(user.id)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == str(body.email).lower()).first()
    if not user or not verify_password(body.senha, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos",
        )
    access = create_access_token(user.id, extra_claims={"email": user.email})
    refresh = create_refresh_token(user.id)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    payload = decode_token_safe(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido ou expirado",
        )
    from uuid import UUID

    try:
        uid = UUID(payload["sub"])
    except (KeyError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido",
        ) from e
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilizador não encontrado")
    access = create_access_token(user.id, extra_claims={"email": user.email})
    new_refresh = create_refresh_token(user.id)
    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.get("/me", response_model=UserMeResponse)
def me(user: CurrentUser) -> UserMeResponse:
    return UserMeResponse.model_validate(user)
