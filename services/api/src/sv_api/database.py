import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from sv_core.settings import settings

Base = declarative_base()


def get_database_url() -> str:
    url = os.environ.get("SV_DATABASE_URL", settings.DATABASE_URL)
    if os.environ.get("SV_TESTING") == "1" and not url.startswith("sqlite"):
        url = "sqlite+aiosqlite:///./test_dev.db"
    return url


engine = create_async_engine(
    get_database_url(),
    echo=False,
    future=True
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing an async database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
