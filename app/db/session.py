"""Async dependency: yields an AsyncSession per request."""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_sessionmaker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_async_sessionmaker()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
