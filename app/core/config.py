from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    NODE_ENV: str = "development"
    DEMO_MODE: bool = True
    DATABASE_URL: str
    APP_URL: str
    AUTH_SECRET: str
    CLINIC_TIMEZONE: str = "Asia/Kolkata"
    CORS_ORIGINS: str = "http://localhost:3000"
    PAYMENT_REQUIRED: bool = False
    PAYMENT_PROVIDER: str = "configured-provider"
    PAYMENT_WEBHOOK_SECRET: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        # psycopg (v3) driver: postgresql+psycopg://...
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
