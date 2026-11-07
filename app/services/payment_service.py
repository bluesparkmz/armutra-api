import uuid as uuid_lib
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.models.user import User
from app.services import ads_service
from app.services import skywallet_service as sky
from app.services.notification_service import notify

FINAL_STATUSES = {"success", "failed"}


def apply_status(
    db: Session,
    payment: Payment,
    new_status: Optional[str],
    error: Optional[str],
    reference: Optional[str] = None,
) -> None:
    """Atualiza o pagamento; ao ficar final notifica e ativa o que dependia dele (sem commit)."""
    if reference:
        payment.reference = reference
    if new_status not in ("pending", "success", "failed"):
        return
    if payment.status in FINAL_STATUSES:
        return  # estados finais não mudam
    changed = new_status != payment.status
    payment.status = new_status
    payment.error = error if new_status == "failed" else None
    if changed and new_status in FINAL_STATUSES:
        ok = new_status == "success"
        notify(
            db,
            recipient_id=payment.user_id,
            actor=None,
            tipo="payment",
            titulo="Pagamento confirmado" if ok else "Pagamento não realizado",
            mensagem=(
                f"O pagamento de {payment.amount} {payment.currency} foi confirmado."
                if ok
                else payment.error or "O pagamento foi cancelado ou recusado."
            ),
            ref_id=payment.id,
        )
        ads_service.on_payment_final(db, payment)


def refresh_payment(db: Session, payment: Payment) -> None:
    """Se estiver pendente, consulta o SkyWallet e atualiza (com commit). Falhas de rede são ignoradas."""
    if payment.status != "pending" or not sky.is_configured():
        return
    try:
        data = sky.get_status(payment.order_id)
    except sky.SkyWalletError:
        return
    apply_status(db, payment, data.get("status"), data.get("error"), reference=data.get("reference"))
    db.commit()
    db.refresh(payment)


def start_skywallet_payment(
    db: Session,
    user: User,
    *,
    msisdn: str,
    amount: Decimal,
    description: Optional[str],
) -> Payment:
    """Cria o registo e pede o pagamento M-Pesa. Em falha do SkyWallet fica 'failed' com a mensagem."""
    if not sky.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SkyWallet não está configurado no servidor",
        )
    # order_id: único, alfanumérico, máx. 20 caracteres (limite do M-Pesa)
    order_id = ("ARM" + uuid_lib.uuid4().hex[:17]).upper()
    payment = Payment(
        user_id=user.id,
        provider="skywallet",
        order_id=order_id,
        msisdn=msisdn,
        amount=amount,
        currency="MZN",
        description=description,
        status="pending",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    try:
        data = sky.request_payment(
            order_id=order_id, msisdn=msisdn, amount=amount, description=description
        )
        apply_status(db, payment, "pending", None, reference=data.get("reference"))
    except sky.SkyWalletError as exc:
        apply_status(db, payment, "failed", str(exc))
    db.commit()
    db.refresh(payment)
    return payment
