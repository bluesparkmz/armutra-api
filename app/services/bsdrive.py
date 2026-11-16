import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings

TIMEOUT = httpx.Timeout(60.0, connect=15.0)


class StorageError(Exception):
    """Falha ao gravar ou ler um ficheiro no BS Drive."""


def _settings():
    settings = get_settings()
    if not settings.BSDRIVE_API_KEY:
        raise StorageError("O armazenamento BS Drive não está configurado no servidor")
    return settings


def _headers() -> dict[str, str]:
    return {
        "X-API-Key": _settings().BSDRIVE_API_KEY,
        "Accept": "application/json",
    }


def _base() -> str:
    return _settings().BSDRIVE_API_BASE.rstrip("/")


async def store_bytes(*, filename: str, content_type: str, data: bytes) -> str:
    """Pede um URL de upload, envia os bytes e confirma. Devolve o id do ficheiro."""
    if not data:
        raise StorageError("O ficheiro está vazio")
    base = _base()
    headers = _headers()
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            created = await client.post(
                f"{base}/files/upload-url",
                headers=headers,
                json={
                    "filename": filename,
                    "content_type": content_type,
                    "size": len(data),
                },
            )
            if created.status_code >= 400:
                raise StorageError("O BS Drive recusou o pedido de upload")
            payload = created.json()
            file_id = payload.get("file_id")
            upload_url = payload.get("upload_url")
            if not file_id or not upload_url:
                raise StorageError("Resposta de upload inválida")
            put_headers = payload.get("headers") or {"Content-Type": content_type}
            uploaded = await client.put(upload_url, content=data, headers=put_headers)
            if uploaded.status_code >= 400:
                raise StorageError("Não foi possível enviar o ficheiro")
            done = await client.post(
                f"{base}/files/complete",
                headers=headers,
                json={"file_id": file_id},
            )
            if done.status_code >= 400:
                raise StorageError("Não foi possível confirmar o ficheiro")
            return str(file_id)
    except StorageError:
        raise
    except httpx.HTTPError as exc:
        raise StorageError("Não foi possível contactar o BS Drive") from exc


async def download_url(file_id: str) -> str:
    """URL temporário para ler o ficheiro. Expira ao fim de poucos minutos."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{_base()}/files/{file_id}/download-url",
                headers=_headers(),
            )
    except httpx.HTTPError as exc:
        raise StorageError("Não foi possível obter o ficheiro") from exc
    if response.status_code == 404:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ficheiro não encontrado")
    if response.status_code >= 400:
        raise StorageError("Não foi possível obter o ficheiro")
    url = response.json().get("download_url")
    if not url:
        raise StorageError("Resposta de download inválida")
    return url
