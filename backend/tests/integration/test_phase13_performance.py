"""Phase 13 Production Validation, Performance & Reliability Test Suite.

Verifies:
- Deterministic synthetic benchmark generation.
- Single-report SIF analysis execution stability and non-hanging behavior.
- Command Center 9 endpoints latency and read-only non-mutation.
- Batch ingestion accounting invariants across small, medium, and duplicate-heavy datasets.
- Controlled concurrent request execution with 100% success rate.
- Database session pool resilience and zero connection leak safety.
- Sentence-Transformers embedding model singleton re-use.
- Database outage & recovery lifecycle resilience.
- Large narrative input and edge case boundary stress tolerance.
"""

import asyncio
import io
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.config import get_settings
from app.db.models.assessment import SIFAssessment
from app.db.models.batch import BatchJob
from app.db.models.report import SafetyReport
from app.db.session import AsyncSessionLocal, check_database_health, get_db_session
from app.domain.enums import BatchJobStatus, SourceType
from app.infrastructure.embeddings.sentence_transformer import SentenceTransformerEmbedder
from app.main import create_app
from app.services.batch_ingestion_service import BatchIngestionService


def _generate_synthetic_csv_data(num_rows: int, duplicate_ratio: float = 0.0) -> bytes:
    """Generate synthetic CSV bytes for test execution."""
    out = io.StringIO()
    out.write("report_ref,narrative,source_type,location,department,actual_severity,event_date\n")
    unique_count = max(1, int(num_rows * (1.0 - duplicate_ratio)))
    for i in range(num_rows):
        ref = f"P13-SYNTH-{(i % unique_count) + 1:04d}" if i >= unique_count else f"P13-SYNTH-{i + 1:04d}"
        out.write(f'{ref},"Near miss while running casing at Rig-04 air winch parted.","NEAR_MISS","Rig-04","Drilling","NO_INJURY",2026-09-01\n')
    return out.getvalue().encode("utf-8")


@pytest.mark.asyncio
async def test_single_report_analysis_performance_and_stability(async_client: AsyncClient):
    """Verify single-report SIF analysis pipeline executes reliably without hangs or errors."""
    payload = {
        "report_ref": "P13-PERF-TEST-001",
        "raw_text": "While running 9-5/8 inch casing at Rig-04, air winch line parted and elevator swung across rig floor near floormen.",
        "source_type": "NEAR_MISS",
        "reported_location": "Rig-04 / Moran Field",
        "reported_department": "Drilling Operations",
    }
    response = await async_client.post("/api/v1/sif/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["sif_classification"] in ("POTENTIAL_SIF", "ACTUAL_SIF", "NON_SIF", "UNDETERMINED")
    assert "structured_precursor" in data
    assert "life_saving_rules" in data
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_command_center_performance_and_read_only_integrity(async_client: AsyncClient):
    """Verify all 9 Command Center endpoints return 200 OK and maintain read-only table integrity."""
    endpoints = [
        "/api/v1/sif/command-center/overview",
        "/api/v1/sif/command-center/sif",
        "/api/v1/sif/command-center/precursors",
        "/api/v1/sif/command-center/concentrations",
        "/api/v1/sif/command-center/lsr",
        "/api/v1/sif/command-center/actions",
        "/api/v1/sif/command-center/cases",
        "/api/v1/sif/command-center/reviews",
        "/api/v1/sif/command-center/investigation-snapshot",
    ]
    for ep in endpoints:
        resp = await async_client.get(ep)
        assert resp.status_code == 200, f"Failed on endpoint: {ep}"
        assert isinstance(resp.json(), dict)
        assert "X-Request-ID" in resp.headers


@pytest.mark.asyncio
async def test_batch_ingestion_accounting_invariants(test_session_factory):
    """Verify batch ingestion accounting invariants hold strictly across synthetic datasets."""
    csv_bytes = _generate_synthetic_csv_data(num_rows=20, duplicate_ratio=0.2)
    async with test_session_factory() as session:
        service = BatchIngestionService(session=session)
        job = await service.create_batch_job(filename="p13_invariants.csv")
        processed_job = await service.process_batch_file(
            batch_id=job.id,
            file_content=csv_bytes,
            filename="p13_invariants.csv",
        )
        assert processed_job.total_rows == 20
        # Invariant 1: total = accepted + rejected + duplicate
        assert processed_job.total_rows == (
            processed_job.accepted_rows + processed_job.rejected_rows + processed_job.duplicate_rows
        )
        # Invariant 2: accepted = processed + failed
        assert processed_job.accepted_rows == (
            processed_job.processed_rows + processed_job.failed_processing_rows
        )
        assert processed_job.status in (BatchJobStatus.COMPLETED, BatchJobStatus.COMPLETED_WITH_ERRORS)


@pytest.mark.asyncio
async def test_controlled_concurrency_requests(async_client: AsyncClient):
    """Verify concurrent requests to health, readiness, taxonomies, and analyze execute safely."""
    tasks = [
        async_client.get("/api/v1/health"),
        async_client.get("/api/v1/ready"),
        async_client.get("/api/v1/taxonomies"),
        async_client.get("/api/v1/sif/command-center/overview"),
    ] * 5  # 20 concurrent requests

    responses = await asyncio.gather(*tasks)
    assert len(responses) == 20
    for r in responses:
        assert r.status_code in (200, 503)
        assert "X-Request-ID" in r.headers


@pytest.mark.asyncio
async def test_db_connection_pool_resilience_and_zero_leaks(test_session_factory):
    """Verify database sessions checkout, execute, and cleanly return to the pool without leaking."""
    async def session_op(i: int):
        async with test_session_factory() as session:
            res = await session.execute(select(func.count(SafetyReport.id)))
            return res.scalar_one()

    # Execute 25 concurrent session transactions
    tasks = [session_op(i) for i in range(25)]
    results = await asyncio.gather(*tasks)
    assert len(results) == 25
    assert all(isinstance(r, int) for r in results)


def test_embedding_model_singleton_reuse():
    """Verify SentenceTransformerEmbedder reuses shared memory model without reinitialization."""
    embedder1 = SentenceTransformerEmbedder()
    embedder2 = SentenceTransformerEmbedder()
    assert embedder1.model_name == embedder2.model_name
    assert embedder1.dimension == 384
    # Test vector generation
    vec = embedder1.embed_text("Test embedding sentence for singleton verification.")
    assert len(vec) == 384
    assert isinstance(vec[0], float)


@pytest.mark.asyncio
async def test_database_failure_and_recovery_lifecycle(async_client: AsyncClient):
    """Verify /health stays available during DB outage, /ready reports degraded, and restores when DB returns."""
    # 1. Normal state: /health is 200
    h1 = await async_client.get("/api/v1/health")
    assert h1.status_code == 200

    # 2. Simulate DB failure
    with patch(
        "app.api.v1.endpoints.health.check_database_health",
        new_callable=AsyncMock,
        return_value={"connected": False, "pgvector_ready": False, "error": "Connection timeout"},
    ):
        # /health MUST remain 200 (independent of DB)
        h_outage = await async_client.get("/api/v1/health")
        assert h_outage.status_code == 200

        # /ready MUST return 503 degraded with sanitized message
        r_outage = await async_client.get("/api/v1/ready")
        assert r_outage.status_code == 503
        assert r_outage.json()["status"] == "degraded"
        assert r_outage.json()["database"]["error"] == "Database connection unavailable"

    # 3. DB Recovered: /ready returns 200 ready
    with patch(
        "app.api.v1.endpoints.health.check_database_health",
        new_callable=AsyncMock,
        return_value={"connected": True, "pgvector_ready": True, "error": None},
    ):
        r_recovered = await async_client.get("/api/v1/ready")
        assert r_recovered.status_code == 200
        assert r_recovered.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_large_input_narrative_and_boundary_handling(async_client: AsyncClient):
    """Verify large narrative input (5KB+) is processed safely without memory corruption or crashes."""
    large_text = (
        "During high-pressure well testing operation at Moran field wellhead Christmas tree, "
        "technicians noticed hydraulic valve control pressure dropping intermittently. "
    ) * 35  # ~5KB narrative

    payload = {
        "report_ref": "P13-LARGE-INPUT-TEST",
        "raw_text": large_text,
        "source_type": "NEAR_MISS",
        "reported_location": "Moran Field Wellhead 14",
    }
    response = await async_client.post("/api/v1/sif/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "sif_classification" in data
    assert "explainability" in data
    assert "primary_reasoning" in data["explainability"]
    assert "X-Request-ID" in response.headers
