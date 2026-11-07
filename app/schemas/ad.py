from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.payment import PaymentOut, normalize_msisdn


class AdPlanOut(BaseModel):
    id: str
    nome: str
    dias: int
    preco: Decimal
    currency: str
    descricao: str


class AdCreate(BaseModel):
    target_type: Literal["job", "service", "post"]
    target_id: UUID
    plan: str


class AdPay(BaseModel):
    msisdn: str

    @field_validator("msisdn", mode="before")
    @classmethod
    def validate_msisdn(cls, v):
        return normalize_msisdn(v)


class AdOut(BaseModel):
    id: UUID
    target_type: str
    target_id: UUID
    target_titulo: Optional[str] = None
    plan: str
    plan_nome: str
    preco: Decimal
    currency: str
    duration_days: int
    status: str  # pending_payment | active | expired
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    criado_em: datetime
    payment: Optional[PaymentOut] = None


class AdminAdUser(BaseModel):
    id: UUID
    nome: str
    email: str


class AdminAdOut(AdOut):
    user: AdminAdUser
    pago: bool  # pagamento SkyWallet confirmado
    cortesia: bool  # ativado manualmente pelo administrador, sem pagamento


class AdminAdStats(BaseModel):
    total: int
    ativos: int
    por_pagar: int
    expirados: int
    cortesias: int
    receita: Decimal
    currency: str


class AdminAdActivate(BaseModel):
    dias: Optional[int] = Field(None, ge=1, le=365)


class AdminAdExtend(BaseModel):
    dias: int = Field(..., ge=1, le=365)


class BoostableItem(BaseModel):
    target_type: str
    target_id: UUID
    titulo: str
    subtitulo: Optional[str] = None
    impulsionado_ate: Optional[datetime] = None
