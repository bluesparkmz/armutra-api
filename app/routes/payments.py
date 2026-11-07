import json
import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import CurrentUser
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payment import PaymentOut, SkyWalletPaymentCreate
from app.services import payment_service
from app.services import skywallet_service as sky

router = APIRouter(prefix="/payments", tags=["payments"])


def _get_own_payment(db: Session, payment_id: uuid_lib.UUID, user: User) -> Payment:
    payment = (
        db.query(Payment).filter(Payment.id == payment_id, Payment.user_id == user.id).first()
    )
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pagamento não encontrado")
    return payment


@router.post("/skywallet", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_skywallet_payment(
    body: SkyWalletPaymentCreate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> PaymentOut:
    payment = payment_service.start_skywallet_payment(
        db, user, msisdn=body.msisdn, amount=body.amount, description=body.description
    )
    return PaymentOut.model_validate(payment)


@router.get("", response_model=list[PaymentOut])
def list_payments(
    user: CurrentUser,
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
) -> list[PaymentOut]:
    rows = (
        db.query(Payment)
        .filter(Payment.user_id == user.id)
        .order_by(Payment.criado_em.desc())
        .limit(limit)
        .all()
    )
    return [PaymentOut.model_validate(p) for p in rows]


@router.post("/skywallet/webhook")
async def skywallet_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    body = await request.body()
    if not sky.verify_webhook_signature(body, request.headers.get("X-Webhook-Signature")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura inválida")
    payload = json.loads(body)
    payment = db.query(Payment).filter(Payment.order_id == payload.get("order_id")).first()
    if payment:
        payment_service.apply_status(
            db,
            payment,
            payload.get("status"),
            payload.get("error"),
            reference=payload.get("reference"),
        )
        db.commit()
    return {"ok": True}


@router.get("/{payment_id}", response_model=PaymentOut)
def get_payment(
    payment_id: uuid_lib.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> PaymentOut:
    """Devolve o pagamento; se ainda estiver pendente, consulta o SkyWallet (polling)."""
    payment = _get_own_payment(db, payment_id, user)
    payment_service.refresh_payment(db, payment)
    return PaymentOut.model_validate(payment)
