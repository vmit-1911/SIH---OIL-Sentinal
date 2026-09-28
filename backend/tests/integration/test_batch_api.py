"""Integration tests for Batch Ingestion REST API endpoints."""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.batch import BatchJob
from app.db.models.batch_error import BatchRowError
from app.db.models.report import SafetyReport
from app.domain.enums import BatchJobStatus, SourceType


@pytest.mark.asyncio
async def test_batch_upload_valid_csv(async_client: AsyncClient):
    """Verify POST /api/v1/sif/batch-upload accepts a valid CSV and returns 202."""
    csv_content = (
        'source_report_id,raw_text,reported_location\n'
        'API-01,"Air winch line parted under load on drilling rig floor.",Rig-04\n'
    ).encode("utf-8")
    files = {"file": ("safety_incidents.csv", csv_content, "text/csv")}

    response = await async_client.post("/api/v1/sif/batch-upload", files=files)
    assert response.status_code == 202

    data = response.json()
    assert "batch_id" in data
    assert uuid.UUID(data["batch_id"])
    assert data["filename"] == "safety_incidents.csv"
    assert "/sif/batch/" in data["status_check_url"]


@pytest.mark.asyncio
async def test_batch_upload_invalid_file_extension(async_client: AsyncClient):
    """Verify POST /api/v1/sif/batch-upload rejects unsupported file extension with 400."""
    files = {"file": ("reports.xlsx", b"some-fake-excel-data", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    response = await async_client.post("/api/v1/sif/batch-upload", files=files)
    assert response.status_code == 400
    data = response.json()
    assert "Unsupported file extension" in data["detail"]


@pytest.mark.asyncio
async def test_batch_upload_empty_file(async_client: AsyncClient):
    """Verify POST /api/v1/sif/batch-upload rejects empty file with 400."""
    files = {"file": ("empty.csv", b"", "text/csv")}
    response = await async_client.post("/api/v1/sif/batch-upload", files=files)
    assert response.status_code == 400
    data = response.json()
    assert "empty" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_batch_status_existing(async_client: AsyncClient, db_session: AsyncSession):
    """Verify GET /api/v1/sif/batch/{batch_id} returns 200 and accurate progress and counters."""
    job_id = uuid.uuid4()
    job = BatchJob(
        id=job_id,
        source_filename="test_status.csv",
        import_schema_version="OIL_SAFETY_REPORT_CSV_V1",
        status=BatchJobStatus.COMPLETED,
        total_rows=10,
        accepted_rows=8,
        rejected_rows=1,
        duplicate_rows=1,
        processed_rows=8,
        failed_processing_rows=0,
        sif_count=4,
    )
    db_session.add(job)
    await db_session.commit()

    response = await async_client.get(f"/api/v1/sif/batch/{job_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["batch_id"] == str(job_id)
    assert data["status"] == "COMPLETED"
    assert data["total_rows"] == 10
    assert data["accepted_rows"] == 8
    assert data["rejected_rows"] == 1
    assert data["duplicate_rows"] == 1
    assert data["processed_rows"] == 8
    assert data["sif_count"] == 4
    assert data["progress_percentage"] == 100.0


@pytest.mark.asyncio
async def test_get_batch_status_not_found(async_client: AsyncClient):
    """Verify GET /api/v1/sif/batch/{batch_id} returns 404 for non-existent job."""
    random_id = uuid.uuid4()
    response = await async_client.get(f"/api/v1/sif/batch/{random_id}")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_batch_errors_paginated(async_client: AsyncClient, db_session: AsyncSession):
    """Verify GET /api/v1/sif/batch/{batch_id}/errors returns paginated list of row errors."""
    job_id = uuid.uuid4()
    job = BatchJob(
        id=job_id,
        source_filename="test_errors.csv",
        import_schema_version="OIL_SAFETY_REPORT_CSV_V1",
        status=BatchJobStatus.COMPLETED_WITH_ERRORS,
        total_rows=5,
        rejected_rows=2,
    )
    db_session.add(job)

    err1 = BatchRowError(
        batch_id=job_id,
        row_number=2,
        field_name="raw_text",
        error_code="MISSING_REQUIRED_TEXT",
        error_message="Safety observation narrative is required",
    )
    err2 = BatchRowError(
        batch_id=job_id,
        row_number=4,
        field_name="event_timestamp",
        error_code="INVALID_DATE_FORMAT",
        error_message="Unrecognized date format",
    )
    db_session.add_all([err1, err2])
    await db_session.commit()

    response = await async_client.get(f"/api/v1/sif/batch/{job_id}/errors?limit=10&offset=0")
    assert response.status_code == 200

    data = response.json()
    assert data["batch_id"] == str(job_id)
    assert data["total_errors"] == 2
    assert len(data["errors"]) == 2
    assert data["errors"][0]["row_number"] == 2
    assert data["errors"][0]["error_code"] == "MISSING_REQUIRED_TEXT"
    assert data["errors"][1]["row_number"] == 4
    assert data["errors"][1]["error_code"] == "INVALID_DATE_FORMAT"


@pytest.mark.asyncio
async def test_get_batch_errors_not_found(async_client: AsyncClient):
    """Verify GET /api/v1/sif/batch/{batch_id}/errors returns 404 for non-existent job."""
    random_id = uuid.uuid4()
    response = await async_client.get(f"/api/v1/sif/batch/{random_id}/errors")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_retry_batch_endpoint(async_client: AsyncClient, db_session: AsyncSession):
    """Verify POST /api/v1/sif/batch/{batch_id}/retry triggers retry and returns 200."""
    job_id = uuid.uuid4()
    job = BatchJob(
        id=job_id,
        source_filename="test_retry.csv",
        import_schema_version="OIL_SAFETY_REPORT_CSV_V1",
        status=BatchJobStatus.COMPLETED_WITH_ERRORS,
        total_rows=1,
        accepted_rows=1,
        processed_rows=0,
        failed_processing_rows=1,
    )
    db_session.add(job)

    rep = SafetyReport(
        report_ref="SR-API-RETRY",
        source_type=SourceType.NEAR_MISS,
        raw_text="Overhead crane line snapped near wellhead cellar during lift.",
        batch_id=job_id,
        batch_row_number=2,
    )
    db_session.add(rep)
    await db_session.commit()

    response = await async_client.post(f"/api/v1/sif/batch/{job_id}/retry")
    assert response.status_code == 200

    data = response.json()
    assert data["batch_id"] == str(job_id)
    assert data["retried_reports_count"] == 1
    assert data["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_retry_batch_not_found(async_client: AsyncClient):
    """Verify POST /api/v1/sif/batch/{batch_id}/retry returns 404 for non-existent job."""
    random_id = uuid.uuid4()
    response = await async_client.post(f"/api/v1/sif/batch/{random_id}/retry")
    assert response.status_code == 404
