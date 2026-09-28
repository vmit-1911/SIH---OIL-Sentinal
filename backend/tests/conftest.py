"""Pytest fixtures and configuration."""

import pytest
from httpx import ASGITransport, AsyncClient
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.compiler import compiles

from app.config import Settings, get_settings
from app.db.base import Base
import app.db.models  # Ensure all SQLAlchemy models are registered
from app.db.session import get_db_session
from app.domain.taxonomy.loader import get_default_taxonomy
from app.main import create_app

# Register SQLite compilation hooks for PostgreSQL specific types
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"


@compiles(Vector, "sqlite")
def compile_vector_sqlite(type_, compiler, **kw):
    return "TEXT"


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Get application settings for testing."""
    return get_settings()


@pytest.fixture(scope="session")
async def test_engine():
    """Create in-memory SQLite async engine with all tables for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    """Session factory for async test sessions."""
    return async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def db_session(test_engine, test_session_factory) -> AsyncSession:
    """Yield an isolated test database session with clean tables."""
    async with test_session_factory() as session:
        yield session
        await session.rollback()
    # Clean all database tables after test for strict test isolation
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest.fixture
def test_app(test_session_factory):
    """Create FastAPI application with test database dependency override."""
    app = create_app()

    async def override_get_db_session():
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db_session
    return app


@pytest.fixture
async def async_client(test_app) -> AsyncClient:
    """Provide an async HTTP test client."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="session")
def loaded_taxonomy():
    """Provide the default loaded IOGP Report 459 taxonomy."""
    return get_default_taxonomy()
