"""Async database session and engine management."""

from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Engine creation
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_pre_ping=True,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            try:
                await session.commit()
            except Exception as commit_err:
                logger.warning(f"Database commit error (db offline or rollback state): {commit_err}")
                try:
                    await session.rollback()
                except Exception:
                    pass
        except Exception:
            try:
                await session.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                await session.close()
            except Exception:
                pass


async def check_database_health() -> dict:
    """Verify database connectivity and pgvector extension availability."""
    result = {
        "connected": False,
        "pgvector_ready": False,
        "error": None,
    }
    try:
        async with engine.connect() as conn:
            # Check basic connection
            res = await conn.execute(text("SELECT 1"))
            if res.scalar() == 1:
                result["connected"] = True

            # Check pgvector extension
            ext_res = await conn.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            )
            if ext_res.scalar() == 1:
                result["pgvector_ready"] = True
    except Exception as exc:
        result["error"] = str(exc)
        logger.warning(f"Database health check failed: {exc}")

    return result
