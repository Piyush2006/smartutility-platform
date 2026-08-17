"""
Central application settings, read from environment variables / .env.
Never hard-code secrets here -- this file only defines defaults for local dev.
"""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "UtilityOS"
    ENV: str = "development"

    # Postgres in docker-compose; overridden by DATABASE_URL env var.
    DATABASE_URL: str = "postgresql+psycopg2://utilityos:utilityos@localhost:5432/utilityos"

    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET_KEY: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    UPLOAD_DIR: str = "./.uploads"
    MAX_LOGO_MB: int = 2
    MAX_ID_DOC_MB: int = 5

    # Used to build links inside outgoing emails (invite links, etc).
    FRONTEND_URL: str = "http://localhost:3000"
    INVITE_TOKEN_EXPIRE_DAYS: int = 7

    # SMTP is optional. When unset, send_email() logs a warning and returns
    # False instead of raising -- the invite flow still works end-to-end in
    # dev (the API response includes the invite link directly), it just
    # doesn't get emailed until real credentials are provided here.
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_USE_TLS: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
