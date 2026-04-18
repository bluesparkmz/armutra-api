from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.profile import CandidatoProfile, EmpresaProfile
from app.models.user import User, UserType
from app.schemas.auth import RegisterRequest


def create_user(db: Session, data: RegisterRequest) -> User:
    if db.query(User).filter(User.email == str(data.email)).first():
        raise ValueError("Email já registado")

    user = User(
        nome=data.nome,
        email=str(data.email).lower(),
        hashed_password=hash_password(data.senha),
        tipo=data.tipo,
        bio=data.bio,
        localizacao=data.localizacao,
    )
    db.add(user)
    db.flush()

    if data.tipo == UserType.EMPRESA:
        ep = data.empresa
        empresa = EmpresaProfile(
            user_id=user.id,
            nome_empresa=ep.nome_empresa if ep else data.nome,
            descricao=ep.descricao if ep else None,
            website=ep.website if ep else None,
        )
        db.add(empresa)
    else:
        cp = data.candidato
        candidato = CandidatoProfile(
            user_id=user.id,
            habilidades=(cp.habilidades if cp else []) or [],
            experiencia=cp.experiencia if cp else None,
            educacao=cp.educacao if cp else None,
        )
        db.add(candidato)

    db.commit()
    db.refresh(user)
    return user
