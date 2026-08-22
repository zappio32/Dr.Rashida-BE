import os
import secrets
from functools import lru_cache
from urllib.parse import urlparse

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
    COOKIE_DOMAIN: str = ""
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
    def is_production(self) -> bool:
        return self.NODE_ENV == "production"

    @property
    def is_https(self) -> bool:
        """True when APP_URL is served over HTTPS (production deployments)."""
        return self.APP_URL.startswith("https://")

    @property
    def cookie_samesite(self) -> str:
        """
        SameSite policy for the session cookie.

        - If the FE and BE share the same registered domain (e.g. both *.zadcart.com)
          we can use 'lax' — it is more compatible and works for top-level navigations.
        - If they are truly cross-site (different domains entirely) we need 'none'
          which also requires secure=True (HTTPS).
        - On localhost (http) we always use 'lax' so the browser accepts the cookie.
        """
        if not self.is_https:
            # localhost / HTTP dev — lax works fine
            return "lax"
        # Production: FE and BE on different sub-domains → need 'none'
        return "none"

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
