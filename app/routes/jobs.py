import uuid as uuid_lib
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import CurrentUser
from app.models.job import Job, JobApplication
from app.models.user import UserType
from app.schemas.job import JobApplyRequest, JobCreate, JobResponse
from app.services import ads_service
from app.services.notification_service import notify

router = APIRouter(prefix="/jobs", tags=["jobs"])


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
    db.refresh(job)
    return JobResponse.model_validate(job)


@router.get("", response_model=list[JobResponse])
def list_jobs(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    localizacao: Optional[str] = None,
    salario_contem: Optional[str] = None,
    q: Optional[str] = None,
) -> list[JobResponse]:
    qr = db.query(Job)
    if localizacao:
        qr = qr.filter(Job.localizacao.ilike(f"%{localizacao}%"))
    if salario_contem:
        qr = qr.filter(Job.salario.ilike(f"%{salario_contem}%"))
    if q:
        like = f"%{q}%"
        qr = qr.filter(
            (Job.titulo.ilike(like)) | (Job.descricao.ilike(like))
        )
    jobs = (
        qr.order_by(ads_service.job_rank().desc(), Job.criado_em.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    boosted = ads_service.active_ids(db)["job"]
    return [
        JobResponse.model_validate(j).model_copy(update={"impulsionado": j.id in boosted})
        for j in jobs
    ]


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
