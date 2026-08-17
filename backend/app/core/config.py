"""
Central application settings, read from environment variables / .env.
Never hard-code secrets here -- this file only defines defaults for local dev.
"""
import json
from functools import lru_cache
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "UtilityOS"
    ENV: str = "development"

    # Postgres in docker-compose; overridden by DATABASE_URL env var.
    DATABASE_URL: str = "postgresql+psycopg2://utilityos:utilityos@localhost:5432/utilityos"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _normalize_database_url(cls, v):
        """Managed Postgres providers (Render, Railway, Heroku, ...) hand
        out connection strings as `postgres://...` or `postgresql://...`,
        never the SQLAlchemy-specific `postgresql+psycopg2://...` this app
        needs -- normalize automatically instead of making every deploy
        hand-edit the URL they were given."""
        if isinstance(v, str) and v.startswith("postgres://"):
            return "postgresql+psycopg2://" + v[len("postgres://"):]
        if isinstance(v, str) and v.startswith("postgresql://"):
            return "postgresql+psycopg2://" + v[len("postgresql://"):]
        return v

    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET_KEY: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Deliberately typed as a plain str, not list[str]: pydantic-settings
    # treats any list-typed field as "complex" and force-JSON-decodes the
    # raw env value *before* any field validator ever sees it -- so even a
    # mode="before" validator can't rescue a value a hosting dashboard
    # (Render, Vercel, Railway, ...) mangled while accepting it into a
    # plain text box (those don't preserve literal `["..."]` reliably the
    # way a real .env file does). Keeping this a plain string sidesteps
    # that parsing entirely; see cors_origins_list below for the accessor.
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        """Accepts either JSON (`["https://a.com","https://b.com"]`) or a
        plain comma-separated string (`https://a.com,https://b.com`) --
        the latter is what you should actually type into a hosting
        dashboard's env var box."""
        v = self.CORS_ORIGINS.strip()
        if v.startswith("["):
            return json.loads(v)
        return [origin.strip() for origin in v.split(",") if origin.strip()]

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
