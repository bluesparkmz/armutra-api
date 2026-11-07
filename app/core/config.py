from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/mabassa"
    SECRET_KEY: str = "dev-secret-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    UPLOAD_DIR: str = "./uploads"

    # SkyWallet (pagamentos M-Pesa). As credenciais ficam só no servidor.
    SKYWALLET_API_BASE: str = "https://skywallet-api.bluesparkmz.com"
    SKYWALLET_SK_ID: str = ""
    SKYWALLET_API_KEY: str = ""
    SKYWALLET_WEBHOOK_SECRET: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
