from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


def normalize_msisdn(v) -> str:
    """Valida e normaliza um número M-Pesa (84/85 + 7 dígitos; aceita prefixo 258)."""
    if not isinstance(v, str):
        raise ValueError("O número tem de ser texto")
    digits = "".join(ch for ch in v if ch.isdigit())
    if digits.startswith("258") and len(digits) == 12:
        digits = digits[3:]
    if len(digits) != 9 or digits[:2] not in ("84", "85"):
        raise ValueError("Número M-Pesa inválido (use 84xxxxxxx ou 85xxxxxxx)")
    return digits


class SkyWalletPaymentCreate(BaseModel):
    msisdn: str = Field(..., description="Número M-Pesa (84/85 + 7 dígitos), como texto")
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    description: Optional[str] = Field(None, max_length=255)

    @field_validator("msisdn", mode="before")
    @classmethod
    def validate_msisdn(cls, v):
        return normalize_msisdn(v)


class PaymentOut(BaseModel):
    id: UUID
    provider: str
    order_id: str
    reference: Optional[str] = None
    msisdn: str
    amount: Decimal
    currency: str
    description: Optional[str] = None
    status: str
    error: Optional[str] = None
    criado_em: datetime
    atualizado_em: datetime

    model_config = {"from_attributes": True}
