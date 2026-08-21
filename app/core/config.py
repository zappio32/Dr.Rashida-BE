import os
import secrets
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _database_url_from_pg_env() -> str | None:
    """Railway/Heroku style Postgres service variables as a fallback."""
    for key in ("DATABASE_PUBLIC_URL", "POSTGRES_URL", "POSTGRESQL_URL"):
        value = os.getenv(key)
        if value:
            return value

    user = os.getenv("PGUSER")
    password = os.getenv("PGPASSWORD")
    host = os.getenv("PGHOST")
    port = os.getenv("PGPORT", "5432")
    name = os.getenv("PGDATABASE")
    if user and password and host and name:
        return f"postgresql://{user}:{password}@{host}:{port}/{name}"
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    NODE_ENV: str = "development"
    DEMO_MODE: bool = True
    DATABASE_URL: str = ""
    APP_URL: str = "http://localhost:3000"
    AUTH_SECRET: str = ""
    CLINIC_TIMEZONE: str = "Asia/Kolkata"
    CORS_ORIGINS: str = "http://localhost:3000"
    PAYMENT_REQUIRED: bool = False
    PAYMENT_PROVIDER: str = "configured-provider"
    PAYMENT_WEBHOOK_SECRET: str | None = None

    @model_validator(mode="after")
    def _apply_fallbacks(self) -> "Settings":
        if not self.DATABASE_URL:
            fallback = _database_url_from_pg_env()
            if fallback:
                self.DATABASE_URL = fallback

        if not self.AUTH_SECRET:
            if self.NODE_ENV == "production":
                raise ValueError("AUTH_SECRET must be set in production")
            self.AUTH_SECRET = secrets.token_urlsafe(32)

        return self

    @property
    def cors_origins_list(self) -> list[str]:
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        if self.APP_URL and self.APP_URL not in origins:
            origins.append(self.APP_URL)
        return list(dict.fromkeys(origins))

    @property
    def sqlalchemy_database_url(self) -> str:
        # psycopg (v3) driver: postgresql+psycopg://...
        url = self.DATABASE_URL
        if not url:
            raise RuntimeError(
                "DATABASE_URL is not set. Add it to the service environment variables "
                "(or link a Postgres database so PGHOST/PGUSER/PGPASSWORD/PGDATABASE are provided)."
            )
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
