import logging
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings
from app.models.base import Base

logger = logging.getLogger(__name__)

# Async SQLAlchemy Engine - tuned for 512MB container memory constraints
engine_kwargs = {
    "echo": settings.DEBUG,
    "future": True,
    "pool_pre_ping": True,
}
if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update({
        "pool_size": 3,
        "max_overflow": 5,
        "pool_recycle": 300,
    })

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

async_engine = engine

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_connection() -> dict:
    """Probes the PostgreSQL database and returns connection health details."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            value = result.scalar()
            if value == 1:
                return {"status": "connected", "details": "Database responding"}
            return {"status": "error", "details": "Unexpected response from database"}
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        return {"status": "disconnected", "details": str(exc)}
