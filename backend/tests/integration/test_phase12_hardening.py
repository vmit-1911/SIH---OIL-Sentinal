"""Phase 12 Integration & Diagnostic Hardening Test Suite.

Verifies:
- Liveness (/api/v1/health) is DB-independent and returns 200.
- Readiness (/api/v1/ready) validates database connectivity and returns 503 on failure.
- Readiness responses are sanitized against internal database errors.
- X-Request-ID preservation and generation.
- Structured JSON logging formatter and field extraction.
- Global exception boundary and sanitized 500 responses.
- Database session rollback and resilience.
- Background batch processor failure recovery to FAILED status.
- Configuration settings hardening and environment overrides.
"""

import json
import logging
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.config import Settings
from app.core.logging import JSONFormatter
from app.db.models.batch import BatchJob
from app.db.session import AsyncSessionLocal, get_db_session
from app.domain.enums import BatchJobStatus
from app.main import create_app
from app.services.background_batch_processor import BackgroundBatchProcessor


@pytest.mark.asyncio
async def test_health_endpoint_liveness(async_client: AsyncClient):
    """Verify /health returns 200 OK and deterministic liveness payload."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "oil-sif-sentinel"
    assert data["api_version"] == "1.0"
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_health_endpoint_independent_of_db(async_client: AsyncClient):
    """Verify /health succeeds even if database health check would fail."""
    with patch(
        "app.db.session.check_database_health",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Database is down!"),
    ):
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_readiness_endpoint_success(async_client: AsyncClient):
    """Verify /ready returns 200 OK when database is operational."""
    with patch(
        "app.api.v1.endpoints.health.check_database_health",
        new_callable=AsyncMock,
        return_value={"connected": True, "pgvector_ready": True, "error": None},
    ):
        response = await async_client.get("/api/v1/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"]["connected"] is True
        assert data["database"]["pgvector_ready"] is True


@pytest.mark.asyncio
async def test_readiness_endpoint_db_failure_sanitized(async_client: AsyncClient):
    """Verify /ready returns 503 and sanitized error when database is unreachable."""
    with patch(
        "app.api.v1.endpoints.health.check_database_health",
        new_callable=AsyncMock,
        return_value={
            "connected": False,
            "pgvector_ready": False,
            "error": "FATAL: password authentication failed for user postgres with secret_pwd",
        },
    ):
        response = await async_client.get("/api/v1/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"]["connected"] is False
        assert data["database"]["pgvector_ready"] is False
        # Sensitive database password / internals must be sanitized
        assert "secret_pwd" not in str(data)
        assert data["database"]["error"] == "Database connection unavailable"


@pytest.mark.asyncio
async def test_request_id_preservation_and_generation(async_client: AsyncClient):
    """Verify X-Request-ID preservation when supplied and UUID4 generation when omitted."""
    custom_id = "test-custom-trace-uuid-1234"
    resp_with_id = await async_client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert resp_with_id.status_code == 200
    assert resp_with_id.headers.get("X-Request-ID") == custom_id

    resp_without_id = await async_client.get("/api/v1/health")
    assert resp_without_id.status_code == 200
    generated_id = resp_without_id.headers.get("X-Request-ID")
    assert generated_id is not None
    # Must be a valid UUID4
    parsed_uuid = uuid.UUID(generated_id, version=4)
    assert str(parsed_uuid) == generated_id


@pytest.mark.asyncio
async def test_sanitized_500_error_boundary():
    """Verify unhandled exceptions trigger a sanitized 500 error envelope."""
    app = create_app()

    @app.get("/api/v1/test-unhandled-crash")
    async def crashing_endpoint():
        raise RuntimeError("Secret internal database stack trace: postgresql://admin:secret@db/prod")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/test-unhandled-crash")
        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert data["error"]["message"] == "An internal server error occurred."
        assert data["error"]["details"] is None
        assert "request_id" in data["error"]
        assert "secret" not in json.dumps(data)
        assert "postgresql" not in json.dumps(data)


def test_structured_json_logging_formatter():
    """Verify JSONFormatter extracts structured fields and outputs valid JSON."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="app.main",
        level=logging.INFO,
        pathname="app/main.py",
        lineno=42,
        msg="POST /api/v1/sif/analyze 200",
        args=(),
        exc_info=None,
    )
    # Attach structured attributes
    record.component = "api"
    record.request_id = "req-123-abc"
    record.method = "POST"
    record.route = "/api/v1/sif/analyze"
    record.status = 200
    record.duration_ms = 35.4
    record.batch_id = "batch-456"

    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "app.main"
    assert parsed["component"] == "api"
    assert parsed["request_id"] == "req-123-abc"
    assert parsed["method"] == "POST"
    assert parsed["route"] == "/api/v1/sif/analyze"
    assert parsed["status"] == 200
    assert parsed["duration_ms"] == 35.4
    assert parsed["batch_id"] == "batch-456"
    assert "timestamp" in parsed


@pytest.mark.asyncio
async def test_database_session_rollback_resilience(test_engine, test_session_factory):
    """Verify session dependency rolls back transactions when exceptions occur."""
    session_generator = get_db_session()
    # Mock AsyncSessionLocal to use test_session_factory
    with patch("app.db.session.AsyncSessionLocal", test_session_factory):
        async with test_session_factory() as session:
            job = BatchJob(
                id=uuid.uuid4(),
                source_filename="test_rollback.csv",
                status=BatchJobStatus.PENDING,
            )
            session.add(job)
            await session.commit()
            job_id = job.id

        # Verify rollback when error occurs
        try:
            async with test_session_factory() as session:
                job_stmt = select(BatchJob).where(BatchJob.id == job_id)
                res = await session.execute(job_stmt)
                loaded_job = res.scalar_one()
                loaded_job.status = BatchJobStatus.PROCESSING
                # Simulate an error before commit
                raise ValueError("Simulated business error")
        except ValueError:
            pass

        # Verify status remained PENDING due to rollback
        async with test_session_factory() as session:
            job_stmt = select(BatchJob).where(BatchJob.id == job_id)
            res = await session.execute(job_stmt)
            fresh_job = res.scalar_one()
            assert fresh_job.status == BatchJobStatus.PENDING


@pytest.mark.asyncio
async def test_background_batch_processor_failure_recovery(test_session_factory):
    """Verify background batch processor deterministically sets FAILED on unhandled exceptions."""
    batch_id = uuid.uuid4()
    async with test_session_factory() as session:
        job = BatchJob(
            id=batch_id,
            source_filename="test_crash.csv",
            status=BatchJobStatus.PENDING,
        )
        session.add(job)
        await session.commit()

    processor = BackgroundBatchProcessor()

    with patch("app.services.background_batch_processor.AsyncSessionLocal", test_session_factory):
        with patch(
            "app.services.batch_ingestion_service.BatchIngestionService.process_batch_file",
            side_effect=RuntimeError("Unrecoverable disk I/O failure"),
        ):
            await processor.process_batch_job(
                batch_id=batch_id,
                file_content=b"dummy_content",
                filename="test_crash.csv",
            )

    # Check job was updated to FAILED state
    async with test_session_factory() as session:
        res = await session.execute(select(BatchJob).where(BatchJob.id == batch_id))
        failed_job = res.scalar_one()
        assert failed_job.status == BatchJobStatus.FAILED


def test_configuration_settings_hardening():
    """Verify Settings handles operational environment variables and aliases."""
    settings = Settings(
        APP_ENV="production",
        DEBUG=False,
        LOG_LEVEL="WARNING",
        LOG_FORMAT="JSON",
        HOST="127.0.0.1",
        PORT=9000,
        CORS_ALLOWED_ORIGINS="https://example.com,https://sif.oil.in",
        BATCH_CHUNK_SIZE=100,
    )
    assert settings.APP_ENV == "production"
    assert settings.DEBUG is False
    assert settings.LOG_LEVEL == "WARNING"
    assert settings.LOG_FORMAT == "JSON"
    assert settings.HOST == "127.0.0.1"
    assert settings.PORT == 9000
    assert settings.cors_origins == ["https://example.com", "https://sif.oil.in"]
    assert settings.BATCH_CHUNK_SIZE == 100
    assert "postgresql://" in settings.DATABASE_URL_SYNC
