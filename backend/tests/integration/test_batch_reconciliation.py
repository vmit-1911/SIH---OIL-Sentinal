"""Integration and domain tests for Batch Ingestion Counter Reconciliation and Invariants."""

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.batch.models import BatchIngestionSummary
from app.domain.enums import BatchJobStatus
from app.services.batch_ingestion_service import BatchIngestionService


def test_batch_ingestion_summary_invariants_valid():
    """Verify BatchIngestionSummary validates true when mathematical invariants hold."""
    summary = BatchIngestionSummary(
        total_rows=100,
        accepted_rows=80,
        rejected_rows=15,
        duplicate_rows=5,
        processed_rows=78,
        failed_processing_rows=2,
        sif_count=35,
    )
    assert summary.validate_invariants() is True
    assert summary.total_rows == summary.accepted_rows + summary.rejected_rows + summary.duplicate_rows
    assert summary.accepted_rows == summary.processed_rows + summary.failed_processing_rows
    assert summary.sif_count <= summary.processed_rows


def test_batch_ingestion_summary_invariants_mismatch_total():
    """Verify validate_invariants returns False when total_rows != accepted + rejected + duplicate."""
    summary = BatchIngestionSummary(
        total_rows=100,
        accepted_rows=70,  # 70 + 10 + 5 = 85 != 100
        rejected_rows=10,
        duplicate_rows=5,
        processed_rows=70,
        failed_processing_rows=0,
        sif_count=10,
    )
    assert summary.validate_invariants() is False


def test_batch_ingestion_summary_invariants_mismatch_processed():
    """Verify validate_invariants returns False when accepted_rows != processed + failed."""
    summary = BatchIngestionSummary(
        total_rows=50,
        accepted_rows=50,
        rejected_rows=0,
        duplicate_rows=0,
        processed_rows=40,
        failed_processing_rows=5,  # 40 + 5 = 45 != 50
        sif_count=10,
    )
    assert summary.validate_invariants() is False


def test_batch_ingestion_summary_invariants_sif_count_exceeds_processed():
    """Verify validate_invariants returns False when sif_count > processed_rows."""
    summary = BatchIngestionSummary(
        total_rows=10,
        accepted_rows=10,
        rejected_rows=0,
        duplicate_rows=0,
        processed_rows=10,
        failed_processing_rows=0,
        sif_count=15,  # 15 > 10
    )
    assert summary.validate_invariants() is False


def test_batch_ingestion_summary_invariants_negative_counter():
    """Verify validate_invariants returns False if any counter is negative."""
    summary = BatchIngestionSummary(
        total_rows=10,
        accepted_rows=10,
        rejected_rows=-1,
        duplicate_rows=1,
        processed_rows=10,
        failed_processing_rows=0,
        sif_count=2,
    )
    assert summary.validate_invariants() is False


@pytest.mark.asyncio
async def test_batch_service_reconciliation_lifecycle(db_session: AsyncSession):
    """Verify end-to-end ingestion strictly maintains reconciliation invariants at each stage."""
    csv_content = (
        'source_report_id,raw_text,event_date\n'
        'REC-01,"Crane hoist block unhooked from load sling during drilling operation.",2026-03-01\n'
        'REC-02,"",2026-03-02\n'  # Rejected (empty text)
        'REC-01,"Duplicate of REC-01 in same file.",2026-03-01\n'  # Duplicate
        'REC-04,"Worker slipped on oily platform walkway.",INVALID_DATE\n'  # Rejected (invalid date)
        'REC-05,"Hydrogen sulfide gas release detected near wellhead separator manifold.",2026-03-05\n'  # Accepted
    ).encode("utf-8")

    service = BatchIngestionService(session=db_session)
    job = await service.create_batch_job(filename="reconcile.csv")
    completed_job = await service.process_batch_file(
        batch_id=job.id,
        file_content=csv_content,
        filename="reconcile.csv",
    )

    assert completed_job.total_rows == 5
    assert completed_job.accepted_rows == 2  # REC-01, REC-05
    assert completed_job.rejected_rows == 2  # REC-02, REC-04
    assert completed_job.duplicate_rows == 1  # 2nd REC-01
    assert completed_job.processed_rows == 2
    assert completed_job.failed_processing_rows == 0

    # Invariant 1: total = accepted + rejected + duplicate
    assert completed_job.total_rows == (
        completed_job.accepted_rows + completed_job.rejected_rows + completed_job.duplicate_rows
    )
    # Invariant 2: accepted = processed + failed_processing
    assert completed_job.accepted_rows == (
        completed_job.processed_rows + completed_job.failed_processing_rows
    )
    # Invariant 3: sif_count <= processed_rows
    assert completed_job.sif_count <= completed_job.processed_rows
    # Invariant 4: non-negative
    for val in (
        completed_job.total_rows,
        completed_job.accepted_rows,
        completed_job.rejected_rows,
        completed_job.duplicate_rows,
        completed_job.processed_rows,
        completed_job.failed_processing_rows,
        completed_job.sif_count,
    ):
        assert val >= 0
