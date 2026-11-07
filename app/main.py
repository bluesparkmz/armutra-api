import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.db.init_db import init_db
from app.routes import admin_ads, ads, auth, connections, interactions, jobs, messages, notifications, payments, posts, search, services_routes, users

settings = get_settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="MABASSA API",
    description="Plataforma de serviços, empregos e feed profissional",
    version="1.0.0",
    lifespan=lifespan,
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
app.include_router(connections.router)
app.include_router(notifications.router)
app.include_router(payments.router)
app.include_router(ads.router)
app.include_router(admin_ads.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
