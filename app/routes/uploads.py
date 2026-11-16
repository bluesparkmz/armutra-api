import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import RedirectResponse

from app.deps import CurrentUser
from app.services import bsdrive

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALLOWED = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}
MAX_BYTES = 5 * 1024 * 1024


async def _read_limited(file: UploadFile, max_bytes: int) -> bytes:
    size = 0
    chunks: list[bytes] = []
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > max_bytes:
            raise HTTPException(status_code=400, detail="O ficheiro é demasiado grande")
        chunks.append(chunk)
    if not chunks:
        raise HTTPException(status_code=400, detail="O ficheiro está vazio")
    return b"".join(chunks)


@router.post("/images")
async def upload_image(user: CurrentUser, file: UploadFile = File(...)) -> dict:
    ext = Path(file.filename or "").suffix.lower()
    content_type = ALLOWED.get(ext)
    if not content_type:
        raise HTTPException(status_code=400, detail="Use uma imagem JPG, PNG, WEBP ou GIF")
    data = await _read_limited(file, MAX_BYTES)
    filename = f"{user.id}-{uuid.uuid4().hex}{ext}"
    try:
        file_id = await bsdrive.store_bytes(filename=filename, content_type=content_type, data=data)
    except bsdrive.StorageError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"image_url": f"/uploads/files/{file_id}"}


@router.get("/files/{file_id}")
async def open_stored_file(file_id: str) -> RedirectResponse:
    """Endereço estável. O link real do BS Drive expira, por isso renovamos aqui."""
    try:
        url = await bsdrive.download_url(file_id)
    except bsdrive.StorageError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return RedirectResponse(url, status_code=302)
