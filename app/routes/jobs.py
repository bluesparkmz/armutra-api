import uuid as uuid_lib
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.deps import CurrentUser
from app.models.job import Job, JobApplication
from app.models.user import User, UserType
from app.schemas.job import (
    ApplicationStatusUpdate,
    JobApplicationOut,
    JobApplyRequest,
    JobCreate,
    JobResponse,
    JobUpdate,
)
from app.services import ads_service
from app.services.notification_service import notify

router = APIRouter(prefix="/jobs", tags=["jobs"])


def job_to_response(job: Job, boosted: bool = False, candidaturas: int = 0) -> JobResponse:
    empresa = job.empresa
    nome = None
    foto = None
    if empresa is not None:
        foto = empresa.foto_perfil
        perfil = empresa.empresa_profile
        nome = perfil.nome_empresa if perfil is not None else empresa.nome
    return JobResponse.model_validate(job).model_copy(
        update={
            "impulsionado": boosted,
            "empresa_nome": nome,
            "empresa_foto": foto,
            "candidaturas": candidaturas,
            "estado": job.estado or "aberta",
        }
    )


def _with_empresa(query):
    return query.options(joinedload(Job.empresa).joinedload(User.empresa_profile))


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    body: JobCreate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> JobResponse:
    if user.tipo != UserType.EMPRESA:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas empresas podem criar vagas",
        )
    job = Job(
        empresa_user_id=user.id,
        titulo=body.titulo,
        descricao=body.descricao,
        requisitos=body.requisitos,
        salario=body.salario,
        localizacao=body.localizacao,
    )
    db.add(job)
    db.commit()
    job = _with_empresa(db.query(Job)).filter(Job.id == job.id).first()
    assert job is not None
    return job_to_response(job)


@router.get("/mine", response_model=list[JobResponse])
def my_jobs(user: CurrentUser, db: Session = Depends(get_db)) -> list[JobResponse]:
    if user.tipo != UserType.EMPRESA:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas empresas gerem vagas",
        )
    jobs = (
        _with_empresa(db.query(Job))
        .filter(Job.empresa_user_id == user.id)
        .order_by(Job.criado_em.desc())
        .all()
    )
    raw_counts = dict(
        db.query(JobApplication.job_id, func.count(JobApplication.id))
        .filter(JobApplication.job_id.in_([j.id for j in jobs] or [uuid_lib.uuid4()]))
        .group_by(JobApplication.job_id)
        .all()
    )
    boosted = ads_service.active_ids(db)["job"]
    return [
        job_to_response(job, job.id in boosted, int(raw_counts.get(job.id, 0))) for job in jobs
    ]


@router.get("/applications/mine", response_model=list[JobApplicationOut])
def my_applications(user: CurrentUser, db: Session = Depends(get_db)) -> list[JobApplicationOut]:
    rows = (
        db.query(JobApplication)
        .options(joinedload(JobApplication.job).joinedload(Job.empresa).joinedload(User.empresa_profile))
        .filter(JobApplication.candidato_user_id == user.id)
        .order_by(JobApplication.criado_em.desc())
        .all()
    )
    return [_application_out(row) for row in rows]


@router.get("", response_model=list[JobResponse])
def list_jobs(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    localizacao: Optional[str] = None,
    salario_contem: Optional[str] = None,
    q: Optional[str] = None,
    empresa_user_id: Optional[uuid_lib.UUID] = None,
) -> list[JobResponse]:
    qr = _with_empresa(db.query(Job)).filter(Job.estado == "aberta")
    if empresa_user_id:
        qr = qr.filter(Job.empresa_user_id == empresa_user_id)
    if localizacao:
        qr = qr.filter(Job.localizacao.ilike(f"%{localizacao}%"))
    if salario_contem:
        qr = qr.filter(Job.salario.ilike(f"%{salario_contem}%"))
    if q:
        like = f"%{q}%"
        qr = qr.filter((Job.titulo.ilike(like)) | (Job.descricao.ilike(like)))
    jobs = (
        qr.order_by(ads_service.job_rank().desc(), Job.criado_em.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    boosted = ads_service.active_ids(db)["job"]
    return [job_to_response(job, job.id in boosted) for job in jobs]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: uuid_lib.UUID, db: Session = Depends(get_db)) -> JobResponse:
    job = _with_empresa(db.query(Job)).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaga não encontrada")
    boosted = job.id in ads_service.active_ids(db)["job"]
    total = db.query(JobApplication).filter(JobApplication.job_id == job.id).count()
    return job_to_response(job, boosted, total)


@router.get("/{job_id}/applications", response_model=list[JobApplicationOut])
def list_applications(
    job_id: uuid_lib.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> list[JobApplicationOut]:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaga não encontrada")
    if job.empresa_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas a empresa da vaga pode ver as candidaturas",
        )
    rows = (
        db.query(JobApplication)
        .options(
            joinedload(JobApplication.candidato).joinedload(User.candidato_profile),
            joinedload(JobApplication.job),
        )
        .filter(JobApplication.job_id == job_id)
        .order_by(JobApplication.criado_em.desc())
        .all()
    )
    return [_application_out(row) for row in rows]


@router.post("/{job_id}/apply", status_code=status.HTTP_201_CREATED)
def apply_job(
    job_id: uuid_lib.UUID,
    body: JobApplyRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> dict:
    if user.tipo != UserType.CANDIDATO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas candidatos podem candidatar-se",
        )
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaga não encontrada")
    if job.estado != "aberta":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Esta vaga está fechada")
    if job.empresa_user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não pode candidatar-se à própria vaga",
        )
    exists = (
        db.query(JobApplication)
        .filter(
            JobApplication.job_id == job_id,
            JobApplication.candidato_user_id == user.id,
        )
        .first()
    )
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já se candidatou a esta vaga",
        )
    app = JobApplication(
        job_id=job_id,
        candidato_user_id=user.id,
        mensagem=body.mensagem,
    )
    db.add(app)
    notify(
        db,
        recipient_id=job.empresa_user_id,
        actor=user,
        tipo="job",
        titulo="Nova candidatura",
        mensagem=f"{user.nome} candidatou-se à vaga \"{job.titulo}\".",
        ref_id=job.id,
    )
    db.commit()
    db.refresh(app)
    return {"ok": True, "application_id": str(app.id)}


def _owned_job(db: Session, job_id: uuid_lib.UUID, user: User) -> Job:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaga não encontrada")
    if job.empresa_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas a empresa da vaga pode alterá-la")
    return job


@router.patch("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: uuid_lib.UUID,
    body: JobUpdate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> JobResponse:
    job = _owned_job(db, job_id, user)
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(job, key, value)
    db.commit()
    job = _with_empresa(db.query(Job)).filter(Job.id == job_id).first()
    assert job is not None
    total = db.query(JobApplication).filter(JobApplication.job_id == job.id).count()
    boosted = job.id in ads_service.active_ids(db)["job"]
    return job_to_response(job, boosted, total)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: uuid_lib.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> None:
    job = _owned_job(db, job_id, user)
    db.delete(job)
    db.commit()


@router.patch("/{job_id}/applications/{application_id}", response_model=JobApplicationOut)
def update_application(
    job_id: uuid_lib.UUID,
    application_id: uuid_lib.UUID,
    body: ApplicationStatusUpdate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> JobApplicationOut:
    job = _owned_job(db, job_id, user)
    row = (
        db.query(JobApplication)
        .options(
            joinedload(JobApplication.candidato).joinedload(User.candidato_profile),
            joinedload(JobApplication.job).joinedload(Job.empresa).joinedload(User.empresa_profile),
        )
        .filter(JobApplication.id == application_id, JobApplication.job_id == job_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidatura não encontrada")
    row.estado = body.estado
    labels = {"aceite": "aceite", "recusada": "recusada", "pendente": "em análise"}
    notify(
        db,
        recipient_id=row.candidato_user_id,
        actor=user,
        tipo="job",
        titulo="Candidatura actualizada",
        mensagem=f"A sua candidatura à vaga \"{job.titulo}\" foi {labels[body.estado]}.",
        ref_id=job.id,
    )
    db.commit()
    db.refresh(row)
    return _application_out(row)


def _application_out(row: JobApplication) -> JobApplicationOut:
    candidato = row.candidato
    cv_url = None
    nome = None
    foto = None
    localizacao = None
    if candidato is not None:
        nome = candidato.nome
        foto = candidato.foto_perfil
        localizacao = candidato.localizacao
        if candidato.candidato_profile is not None:
            cv_url = candidato.candidato_profile.cv_url
    return JobApplicationOut(
        id=row.id,
        job_id=row.job_id,
        candidato_user_id=row.candidato_user_id,
        mensagem=row.mensagem,
        criado_em=row.criado_em,
        candidato_nome=nome,
        candidato_foto=foto,
        candidato_localizacao=localizacao,
        cv_url=cv_url,
        vaga_titulo=row.job.titulo if row.job is not None else None,
        estado=row.estado or "pendente",
        empresa_user_id=row.job.empresa_user_id if row.job is not None else None,
        empresa_nome=(
            row.job.empresa.empresa_profile.nome_empresa
            if row.job is not None
            and row.job.empresa is not None
            and row.job.empresa.empresa_profile is not None
            else (row.job.empresa.nome if row.job is not None and row.job.empresa is not None else None)
        ),
    )
