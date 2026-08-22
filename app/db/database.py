"""Async SQLAlchemy engine + session factory.

- Runtime (FastAPI routes): async engine → AsyncSession
- Migrations (Alembic): sync engine → regular Session (unchanged)
"""
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


# ── Async engine (used by every FastAPI route) ────────────────────────────────

@lru_cache
def get_async_engine() -> AsyncEngine:
    settings = get_settings()
    # Replace postgresql+psycopg:// → postgresql+asyncpg://
    url = settings.sqlalchemy_database_url.replace(
        "postgresql+psycopg://", "postgresql+asyncpg://"
    ).replace(
        "postgresql://", "postgresql+asyncpg://"
    ).replace(
        "postgres://", "postgresql+asyncpg://"
    )
    return create_async_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=20)


@lru_cache
def get_async_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_async_engine(), expire_on_commit=False)


# ── Sync engine (kept only for Alembic migrations) ────────────────────────────

@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True, future=True)


@lru_cache
def _get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)


def SessionLocal() -> Session:
    """Sync session — used only by Alembic; never call this from a route."""
    return _get_sessionmaker()()


class Base(DeclarativeBase):
    pass
