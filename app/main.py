import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.routes import auth, interactions, jobs, messages, posts, search, services_routes, users

settings = get_settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="MABASSA API",
    description="Plataforma de serviços, empregos e feed profissional",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(posts.router)
app.include_router(jobs.router)
app.include_router(services_routes.router)
app.include_router(interactions.router)
app.include_router(messages.router)
app.include_router(search.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
