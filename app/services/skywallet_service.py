import hashlib
import hmac
import json
from decimal import Decimal
from typing import Any, Optional

import httpx

from app.core.config import get_settings

TIMEOUT = httpx.Timeout(20.0, connect=10.0)


class SkyWalletError(Exception):
    """Falha ao comunicar com o SkyWallet (mensagem segura para mostrar ao utilizador)."""


def is_configured() -> bool:
    s = get_settings()
    return bool(s.SKYWALLET_SK_ID and s.SKYWALLET_API_KEY)


def _headers() -> dict[str, str]:
    s = get_settings()
    return {
        "X-SK-ID": s.SKYWALLET_SK_ID,
        "X-API-Key": s.SKYWALLET_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _base() -> str:
    return get_settings().SKYWALLET_API_BASE.rstrip("/")


def _error_message(data: Any, fallback: str) -> str:
    if isinstance(data, dict):
        for key in ("error", "detail", "message"):
            value = data.get(key)
            if isinstance(value, str) and value:
                return value
            if isinstance(value, list) and value and isinstance(value[0], dict):
                msg = value[0].get("msg")
                if msg:
                    return str(msg)
    return fallback


def _parse(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def request_payment(
    *,
    order_id: str,
    msisdn: str,
    amount: Decimal,
    description: Optional[str],
) -> dict:
    """Inicia o pedido M-Pesa. Devolve o JSON do SkyWallet (status 'pending' se aceite)."""
    payload = {
        "msisdn": msisdn,
        "amount": float(amount),
        "currency": "MZN",
        "description": description or "Pagamento Armutra",
        "order_id": order_id,
    }
    try:
        response = httpx.post(
            f"{_base()}/api/developer/payment/request",
            headers=_headers(),
            json=payload,
            timeout=TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise SkyWalletError("Não foi possível contactar o SkyWallet. Tente novamente.") from exc

    data = _parse(response)
    if response.status_code == 429:
        raise SkyWalletError("Demasiados pedidos. Aguarde um minuto e tente novamente.")
    if response.status_code in (401, 403):
        raise SkyWalletError("Credenciais do SkyWallet inválidas no servidor.")
    if response.status_code >= 400 or (isinstance(data, dict) and data.get("success") is False):
        raise SkyWalletError(_error_message(data, "O SkyWallet recusou o pedido de pagamento."))
    return data if isinstance(data, dict) else {}


def get_status(order_id: str) -> dict:
    try:
        response = httpx.get(
            f"{_base()}/api/developer/payment/status",
            headers=_headers(),
            params={"order_id": order_id},
            timeout=TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise SkyWalletError("Não foi possível contactar o SkyWallet.") from exc

    data = _parse(response)
    if response.status_code == 429:
        raise SkyWalletError("Demasiados pedidos. Aguarde um momento.")
    if response.status_code >= 400:
        raise SkyWalletError(_error_message(data, "Não foi possível verificar o pagamento."))
    return data if isinstance(data, dict) else {}


def verify_webhook_signature(body: bytes, signature: Optional[str]) -> bool:
    """HMAC-SHA256 do JSON canónico (chaves ordenadas, sem espaços), como o SkyWallet envia."""
    secret = get_settings().SKYWALLET_WEBHOOK_SECRET
    if not secret or not signature:
        return False
    try:
        payload = json.loads(body)
    except ValueError:
        return False
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    expected = hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
