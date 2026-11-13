import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import get_settings
from app.deps import CurrentUser

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALLOWED = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_BYTES = 5 * 1024 * 1024


@router.post("/images")
async def upload_image(user: CurrentUser, file: UploadFile = File(...)) -> dict:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(status_code=400, detail="Use uma imagem JPG, PNG, WEBP ou GIF")

    settings = get_settings()
    upload_root = Path(settings.UPLOAD_DIR)
    upload_root.mkdir(parents=True, exist_ok=True)
    dest_name = f"{user.id}-{uuid.uuid4().hex}{ext}"
    dest = upload_root / dest_name

    size = 0
    with dest.open("wb") as buf:
        while True:
            chunk = await file.read(1024 * 64)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_BYTES:
                buf.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail="A imagem passa de 5 MB")
            buf.write(chunk)

    return {"image_url": f"/uploads/{dest_name}"}
