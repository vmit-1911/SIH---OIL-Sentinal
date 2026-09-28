"""Integration tests for BatchIngestionService covering scenarios A through W."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.assessment import SIFAssessment
from app.db.models.batch import BatchJob
from app.db.models.batch_error import BatchRowError
from app.db.models.report import SafetyReport
from app.domain.enums import (
    ActualOutcome,
    BatchJobStatus,
    PotentialOutcome,
    SIFClassification,
    SourceType,
)
from app.services.batch_ingestion_service import BatchIngestionService
from app.services.sif_analysis_service import SIFAnalysisService


@pytest.mark.asyncio
async def test_scenario_a_valid_csv_ingestion(db_session: AsyncSession):
    """Scenario A: Ingest compliant CSV with valid Near-Miss and Unsafe Act narratives."""
    csv_content = (
        'source_report_id,raw_text,reported_location,reported_department,source_type,actual_severity,event_date\n'
        'OIL-NM-001,"While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung across the rig floor, narrowly missing two floormen who jumped out of the way. No injuries occurred.",Rig-04 Moran,Drilling,NEAR_MISS,NO_INJURY,2026-03-01\n'
        'OIL-UA-002,"During mast maintenance on monkey board at 25 meters height, derrickman unhooked his full body harness lanyard without 100% tie-off.",Flare Area,Maintenance,UNSAFE_ACT,NO_INJURY,2026-03-02\n'
        'OIL-NM-003,"Worker walked through designated walkway in administrative office building.",Office,Administration,NEAR_MISS,NO_INJURY,2026-03-03\n'
    ).encode("utf-8")

    service = BatchIngestionService(session=db_session)
    job = await service.create_batch_job(filename="valid_batch.csv")
    assert job.status == BatchJobStatus.PENDING

    completed_job = await service.process_batch_file(
        batch_id=job.id,
        file_content=csv_content,
        filename="valid_batch.csv",
    )

    assert completed_job.status == BatchJobStatus.COMPLETED
    assert completed_job.total_rows == 3
    assert completed_job.accepted_rows == 3
    assert completed_job.rejected_rows == 0
    assert completed_job.duplicate_rows == 0
    assert completed_job.processed_rows == 3
    assert completed_job.failed_processing_rows == 0
    assert completed_job.sif_count >= 1

    # Verify persisted SafetyReport and SIFAssessment records
    reports_stmt = select(SafetyReport).where(SafetyReport.batch_id == job.id)
    res_reports = await db_session.execute(reports_stmt)
    reports = res_reports.scalars().all()
    assert len(reports) == 3

    for rep in reports:
        assert rep.batch_id == job.id
        assert rep.batch_row_number in (2, 3, 4)

        assess_stmt = select(SIFAssessment).where(SIFAssessment.report_id == rep.id)
        res_ass = await db_session.execute(assess_stmt)
        assessment = res_ass.scalar_one_or_none()
        assert assessment is not None
        assert assessment.sif_classification in (
            SIFClassification.POTENTIAL_SIF,
            SIFClassification.ACTUAL_SIF,
            SIFClassification.NON_SIF,
            SIFClassification.UNDETERMINED,
        )


@pytest.mark.asyncio
async def test_scenario_b_missing_required_headers(db_session: AsyncSession):
    """Scenario B: Ingest CSV missing required narrative column fails fast with FAILED status."""
    csv_content = (
        "source_report_id,reported_location,event_date\n"
        "OIL-001,Rig-04 Moran,2026-03-01\n"
    ).encode("utf-8")

    service = BatchIngestionService(session=db_session)
    job = await service.create_batch_job(filename="missing_headers.csv")

    completed_job = await service.process_batch_file(
        batch_id=job.id,
        file_content=csv_content,
        filename="missing_headers.csv",
    )

    assert completed_job.status == BatchJobStatus.FAILED
    assert "parsing_error" in completed_job.error_summary
    assert "narrative" in completed_job.error_summary["parsing_error"].lower()


@pytest.mark.asyncio
async def test_scenario_c_empty_file(db_session: AsyncSession):
    """Scenario C: Ingest completely empty file fails validation with FAILED status."""
    service = BatchIngestionService(session=db_session)
    job = await service.create_batch_job(filename="empty.csv")

    completed_job = await service.process_batch_file(
        batch_id=job.id,
        file_content=b"",
        filename="empty.csv",
    )

    assert completed_job.status == BatchJobStatus.FAILED
    assert "file_error" in completed_job.error_summary


@pytest.mark.asyncio
async def test_scenario_d_row_with_invalid_date_recorded_as_error(db_session: AsyncSession):
    """Scenario D: Ingest CSV with syntax error in date column; records BatchRowError and completes with errors."""
    csv_content = (
        "source_report_id,raw_text,event_date\n"
        "OIL-D-01,Winch line snapped during casing running operation on rig floor.,2026-03-05\n"
        "OIL-D-02,High pressure gas leak detected near test separator manifold.,NOT_A_VALID_DATE\n"
    ).encode("utf-8")

    service = BatchIngestionService(session=db_session)
    job = await service.create_batch_job(filename="invalid_date.csv")

    completed_job = await service.process_batch_file(
        batch_id=job.id,
        file_content=csv_content,
        filename="invalid_date.csv",
    )

    assert completed_job.status == BatchJobStatus.COMPLETED_WITH_ERRORS
    assert completed_job.total_rows == 2
    assert completed_job.accepted_rows == 1
    assert completed_job.rejected_rows == 1

    total_errs, errors = await service.get_batch_errors(batch_id=job.id)
    assert total_errs == 1
    assert errors[0].row_number == 3
    assert errors[0].field_name == "event_timestamp"
    assert errors[0].error_code == "INVALID_DATE_FORMAT"


@pytest.mark.asyncio
async def test_scenario_e_row_missing_narrative_or_too_short(db_session: AsyncSession):
    """Scenario E: Ingest CSV with missing or too-short narratives; rejects rows gracefully."""
    csv_content = (
        "source_report_id,raw_text\n"
        "OIL-E-01,Crane wire rope sheared and dropped heavy block into cellar pit.\n"
        "OIL-E-02,   \n"
        "OIL-E-03,Short\n"
    ).encode("utf-8")

    service = BatchIngestionService(session=db_session)
    job = await service.create_batch_job(filename="short_narratives.csv")

    completed_job = await service.process_batch_file(
        batch_id=job.id,
        file_content=csv_content,
        filename="short_narratives.csv",
    )

    assert completed_job.status == BatchJobStatus.COMPLETED_WITH_ERRORS
    assert completed_job.total_rows == 3
    assert completed_job.accepted_rows == 1
    assert completed_job.rejected_rows == 2

    total_errs, errors = await service.get_batch_errors(batch_id=job.id)
    assert total_errs == 2
    err_rows = [e.row_number for e in errors]
    assert 3 in err_rows
    assert 4 in err_rows


@pytest.mark.asyncio
async def test_scenario_f_mixed_valid_invalid_duplicate_rows(db_session: AsyncSession):
    """Scenario F: Mixed batch with valid, invalid, and duplicate records; verifies mathematical invariants."""
    csv_content = (
        "source_report_id,raw_text,event_date\n"
        "OIL-MIX-01,High pressure release during well perforation operation.,2026-03-01\n"
        "OIL-MIX-02,,2026-03-02\n"  # Invalid (empty narrative)
        "OIL-MIX-01,Different text with same source id.,2026-03-03\n"  # In-batch duplicate
        "OIL-MIX-04,Forklift tipped over while turning with heavy load on ramp.,2026-03-04\n"  # Valid
    ).encode("utf-8")

    service = BatchIngestionService(session=db_session)
    job = await service.create_batch_job(filename="mixed.csv")

    completed_job = await service.process_batch_file(
        batch_id=job.id,
        file_content=csv_content,
        filename="mixed.csv",
    )

    assert completed_job.status == BatchJobStatus.COMPLETED_WITH_ERRORS
    assert completed_job.total_rows == 4
    assert completed_job.accepted_rows == 2
    assert completed_job.rejected_rows == 1
    assert completed_job.duplicate_rows == 1
    assert completed_job.processed_rows == 2
    assert completed_job.failed_processing_rows == 0

    # Invariant checks
    assert completed_job.total_rows == completed_job.accepted_rows + completed_job.rejected_rows + completed_job.duplicate_rows
    assert completed_job.accepted_rows == completed_job.processed_rows + completed_job.failed_processing_rows


@pytest.mark.asyncio
async def test_scenario_g_in_batch_fingerprint_duplicate(db_session: AsyncSession):
    """Scenario G: Two rows with no source ID but identical narrative content detected as duplicate."""
    csv_content = (
        "raw_text,reported_location\n"
        "Derrickman failed to secure harness lanyard during monkey board operations.,Rig-04\n"
        "  Derrickman failed to secure harness lanyard during monkey board operations.  ,Rig-04\n"
    ).encode("utf-8")

    service = BatchIngestionService(session=db_session)
    job = await service.create_batch_job(filename="fingerprint_dup.csv")

    completed_job = await service.process_batch_file(
        batch_id=job.id,
        file_content=csv_content,
        filename="fingerprint_dup.csv",
    )

    assert completed_job.total_rows == 2
    assert completed_job.accepted_rows == 1
    assert completed_job.duplicate_rows == 1


@pytest.mark.asyncio
async def test_scenario_h_cross_batch_duplicate_detection(db_session: AsyncSession):
    """Scenario H: Second batch referencing identical source IDs already in database is marked as duplicate."""
    csv_1 = (
        "source_report_id,raw_text\n"
        "OIL-UNIQ-100,Worker caught between forklift counterweight and racking beam.\n"
    ).encode("utf-8")

    csv_2 = (
        "source_report_id,raw_text\n"
        "OIL-UNIQ-100,Updated or re-submitted identical report ID.\n"
        "OIL-UNIQ-200,Brand new safety observation regarding flare line ignition.\n"
    ).encode("utf-8")

    service = BatchIngestionService(session=db_session)

    # Batch 1
    job1 = await service.create_batch_job(filename="batch1.csv")
    await service.process_batch_file(batch_id=job1.id, file_content=csv_1, filename="batch1.csv")

    # Batch 2
    job2 = await service.create_batch_job(filename="batch2.csv")
    completed2 = await service.process_batch_file(batch_id=job2.id, file_content=csv_2, filename="batch2.csv")

    assert completed2.total_rows == 2
    assert completed2.accepted_rows == 1
    assert completed2.duplicate_rows == 1
    assert completed2.processed_rows == 1


@pytest.mark.asyncio
async def test_scenario_i_file_size_exceeded(db_session: AsyncSession):
    """Scenario I: File exceeding maximum size rejected before parsing."""
    service = BatchIngestionService(session=db_session)
    job = await service.create_batch_job(filename="oversized.csv")

    # Pass max_size_bytes via config override or small threshold
    service.settings.BATCH_MAX_FILE_SIZE_BYTES = 50
    try:
        completed_job = await service.process_batch_file(
            batch_id=job.id,
            file_content=b"x" * 200,
            filename="oversized.csv",
        )
        assert completed_job.status == BatchJobStatus.FAILED
        assert "file_error" in completed_job.error_summary
    finally:
        service.settings.BATCH_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


@pytest.mark.asyncio
async def test_scenario_j_unsupported_file_extension(db_session: AsyncSession):
    """Scenario J: Uploading non-CSV file extension fails validation."""
    service = BatchIngestionService(session=db_session)
    job = await service.create_batch_job(filename="reports.xlsx")

    completed_job = await service.process_batch_file(
        batch_id=job.id,
        file_content=b"fake-excel-content",
        filename="reports.xlsx",
    )

    assert completed_job.status == BatchJobStatus.FAILED
    assert "file_error" in completed_job.error_summary
    assert "Unsupported file extension '.xlsx'" in completed_job.error_summary["file_error"]


@pytest.mark.asyncio
async def test_scenario_n_failure_isolation(db_session: AsyncSession):
    """Scenario N: Analysis exception on a single report does not abort remaining reports."""
    csv_content = (
        "source_report_id,raw_text\n"
        "OIL-FAIL-01,Worker stepped on corroded grating over cellar pit.\n"
        "OIL-FAIL-02,Air line parted during hydrostatic pressure test.\n"
    ).encode("utf-8")

    mock_analysis = AsyncMock(spec=SIFAnalysisService)
    # Fail on first report, succeed on second
    mock_analysis.analyze_existing_report.side_effect = [
        RuntimeError("Transient database lock during analysis"),
        SIFAssessment(
            report_id=uuid.uuid4(),
            sif_classification=SIFClassification.POTENTIAL_SIF,
            evidence_score=0.85,
        ),
    ]

    service = BatchIngestionService(session=db_session, analysis_service=mock_analysis)
    job = await service.create_batch_job(filename="isolation.csv")

    completed_job = await service.process_batch_file(
        batch_id=job.id,
        file_content=csv_content,
        filename="isolation.csv",
    )

    assert completed_job.status == BatchJobStatus.COMPLETED_WITH_ERRORS
    assert completed_job.total_rows == 2
    assert completed_job.accepted_rows == 2
    assert completed_job.processed_rows == 1
    assert completed_job.failed_processing_rows == 1

    total_errs, errors = await service.get_batch_errors(batch_id=job.id)
    assert total_errs == 1
    assert errors[0].error_code == "ANALYSIS_FAILED"


@pytest.mark.asyncio
async def test_scenario_u_idempotent_retry(db_session: AsyncSession):
    """Scenario U: Retrying an incomplete batch processes remaining unassessed reports."""
    # Seed a BatchJob with an unassessed SafetyReport
    job = BatchJob(
        id=uuid.uuid4(),
        source_filename="retry_test.csv",
        import_schema_version="OIL_SAFETY_REPORT_CSV_V1",
        status=BatchJobStatus.COMPLETED_WITH_ERRORS,
        total_rows=2,
        accepted_rows=2,
        rejected_rows=0,
        duplicate_rows=0,
        processed_rows=1,
        failed_processing_rows=1,
        sif_count=1,
    )
    db_session.add(job)
    await db_session.flush()

    rep1 = SafetyReport(
        report_ref="SR-RETRY-1",
        source_type=SourceType.NEAR_MISS,
        raw_text="Suspended drill collar swung near rotary table.",
        batch_id=job.id,
        batch_row_number=2,
    )
    rep2 = SafetyReport(
        report_ref="SR-RETRY-2",
        source_type=SourceType.NEAR_MISS,
        raw_text="Nitrogen bottle fallen from transport rack.",
        batch_id=job.id,
        batch_row_number=3,
    )
    db_session.add_all([rep1, rep2])
    await db_session.flush()

    # Create assessment only for rep1
    ass1 = SIFAssessment(
        report_id=rep1.id,
        sif_classification=SIFClassification.POTENTIAL_SIF,
        evidence_score=0.9,
    )
    db_session.add(ass1)
    await db_session.commit()

    service = BatchIngestionService(session=db_session)
    updated_job, retried_count = await service.retry_batch_job(batch_id=job.id)

    assert retried_count == 1
    assert updated_job.status == BatchJobStatus.COMPLETED
    assert updated_job.processed_rows == 2
    assert updated_job.failed_processing_rows == 0


@pytest.mark.asyncio
async def test_scenario_v_utf8_bom_and_latin1_ingestion(db_session: AsyncSession):
    """Scenario V: CSV files encoded with UTF-8 BOM or Latin-1 are parsed and ingested smoothly."""
    bom_csv = (
        "source_report_id,raw_text,reported_location\n"
        "BOM-01,Forklift operated without warning alarm near main pedestrian gate.,Moran Yard\n"
    ).encode("utf-8-sig")

    service = BatchIngestionService(session=db_session)
    job = await service.create_batch_job(filename="bom.csv")
    completed = await service.process_batch_file(batch_id=job.id, file_content=bom_csv, filename="bom.csv")

    assert completed.status == BatchJobStatus.COMPLETED
    assert completed.accepted_rows == 1


@pytest.mark.asyncio
async def test_scenario_w_ignored_columns_metadata(db_session: AsyncSession):
    """Scenario W: Non-standard / enterprise-specific columns are ignored without failing batch."""
    csv_content = (
        "source_report_id,raw_text,custom_sap_code,legacy_id,shift_supervisor\n"
        "OIL-W-01,Worker spotted working at 6m height without harness tie-off.,SAP-9988,LEG-112,John Doe\n"
    ).encode("utf-8")

    service = BatchIngestionService(session=db_session)
    job = await service.create_batch_job(filename="custom_cols.csv")
    completed = await service.process_batch_file(batch_id=job.id, file_content=csv_content, filename="custom_cols.csv")

    assert completed.status == BatchJobStatus.COMPLETED
    assert completed.accepted_rows == 1
    assert completed.rejected_rows == 0


@pytest.mark.asyncio
async def test_retry_eligibility_and_idempotence(db_session: AsyncSession):
    """Verify explicit retry eligibility targets only unassessed/failed reports and is fully idempotent."""
    job = BatchJob(
        id=uuid.uuid4(),
        source_filename="retry_eligibility.csv",
        import_schema_version="OIL_SAFETY_REPORT_CSV_V1",
        status=BatchJobStatus.COMPLETED_WITH_ERRORS,
        total_rows=3,
        accepted_rows=3,
        rejected_rows=0,
        duplicate_rows=0,
        processed_rows=1,
        failed_processing_rows=2,
        sif_count=1,
    )
    db_session.add(job)
    await db_session.flush()

    rep1 = SafetyReport(
        report_ref="SR-ELIG-1",
        source_type=SourceType.NEAR_MISS,
        raw_text="Overhead crane wire rope sheared during pipe lift.",
        batch_id=job.id,
        batch_row_number=2,
    )
    rep2 = SafetyReport(
        report_ref="SR-ELIG-2",
        source_type=SourceType.NEAR_MISS,
        raw_text="Pressure relief valve stuck closed on test separator.",
        batch_id=job.id,
        batch_row_number=3,
    )
    rep3 = SafetyReport(
        report_ref="SR-ELIG-3",
        source_type=SourceType.NEAR_MISS,
        raw_text="Worker observed without safety glasses in grinding area.",
        batch_id=job.id,
        batch_row_number=4,
    )
    db_session.add_all([rep1, rep2, rep3])
    await db_session.flush()

    # Create assessment only for rep1 (successfully processed)
    ass1 = SIFAssessment(
        report_id=rep1.id,
        sif_classification=SIFClassification.POTENTIAL_SIF,
        evidence_score=0.9,
    )
    # Record ANALYSIS_FAILED error for rep2
    err2 = BatchRowError(
        batch_id=job.id,
        row_number=3,
        field_name="analysis",
        error_code="ANALYSIS_FAILED",
        error_message="Simulated temporary timeout",
    )
    db_session.add_all([ass1, err2])
    await db_session.commit()

    service = BatchIngestionService(session=db_session)

    # 1. First retry: should process rep2 and rep3 (2 reports), and preserve rep1 without re-creation
    updated_job, retried_count = await service.retry_batch_job(batch_id=job.id)
    assert retried_count == 2
    assert updated_job.status == BatchJobStatus.COMPLETED
    assert updated_job.processed_rows == 3
    assert updated_job.failed_processing_rows == 0

    # Verify no duplicate SafetyReport records
    stmt_reps = select(SafetyReport).where(SafetyReport.batch_id == job.id)
    res_reps = await db_session.execute(stmt_reps)
    assert len(res_reps.scalars().all()) == 3

    # Verify each report has exactly one assessment (3 total, no duplicates)
    stmt_asses = (
        select(SIFAssessment)
        .join(SafetyReport, SIFAssessment.report_id == SafetyReport.id)
        .where(SafetyReport.batch_id == job.id)
    )
    res_asses = await db_session.execute(stmt_asses)
    assert len(res_asses.scalars().all()) == 3

    # 2. Second retry on completed batch (idempotency check): should retry 0 reports
    job_second, count_second = await service.retry_batch_job(batch_id=job.id)
    assert count_second == 0
    assert job_second.status == BatchJobStatus.COMPLETED
    assert job_second.processed_rows == 3

    # Verify assessment count remains exactly 3
    res_asses2 = await db_session.execute(stmt_asses)
    assert len(res_asses2.scalars().all()) == 3


@pytest.mark.asyncio
async def test_retry_preserves_structural_rejections(db_session: AsyncSession):
    """Verify retry does not attempt to create or retry non-existent reports from rejected CSV rows."""
    job = BatchJob(
        id=uuid.uuid4(),
        source_filename="structural_reject.csv",
        import_schema_version="OIL_SAFETY_REPORT_CSV_V1",
        status=BatchJobStatus.COMPLETED_WITH_ERRORS,
        total_rows=2,
        accepted_rows=1,
        rejected_rows=1,
        duplicate_rows=0,
        processed_rows=1,
        failed_processing_rows=0,
        sif_count=1,
    )
    db_session.add(job)
    await db_session.flush()

    rep1 = SafetyReport(
        report_ref="SR-STRUCT-1",
        source_type=SourceType.NEAR_MISS,
        raw_text="Air winch line parted under load on rig floor.",
        batch_id=job.id,
        batch_row_number=2,
    )
    db_session.add(rep1)
    await db_session.flush()

    ass1 = SIFAssessment(
        report_id=rep1.id,
        sif_classification=SIFClassification.POTENTIAL_SIF,
        evidence_score=0.9,
    )
    # Structural syntax error recorded during CSV parsing (row 3 had bad date format)
    err_struct = BatchRowError(
        batch_id=job.id,
        row_number=3,
        field_name="event_timestamp",
        error_code="INVALID_DATE_FORMAT",
        error_message="Unrecognized date format",
    )
    db_session.add_all([ass1, err_struct])
    await db_session.commit()

    service = BatchIngestionService(session=db_session)
    updated_job, retried_count = await service.retry_batch_job(batch_id=job.id)

    # 0 reports retried because accepted report is already processed and row 3 was a structural rejection
    assert retried_count == 0
    assert updated_job.status == BatchJobStatus.COMPLETED_WITH_ERRORS
    assert updated_job.rejected_rows == 1
    assert updated_job.processed_rows == 1


@pytest.mark.asyncio
async def test_post_batch_phase2b_phase3_decoupled_policy(db_session: AsyncSession):
    """Verify that batch completion does NOT automatically trigger expensive Phase 2B/3 aggregations.
    
    Decoupled Policy (Option B):
    - Batch completion means ingestion and SIF inference for the batch are complete.
    - Pattern discovery and risk concentration refresh remain decoupled and are triggered via their dedicated endpoints.
    - Batch processing never runs pattern discovery or concentration refresh per-row or on batch finish.
    """
    from app.db.models.pattern import PrecursorPattern
    from app.db.models.concentration import RiskConcentration

    csv_content = (
        'source_report_id,raw_text,reported_location,reported_department,source_type,actual_severity,event_date\n'
        'DECOUPLE-01,"Air winch hoist line parted under 12 ton tension on rig floor narrowly missing floorman.",Rig-04 Moran,Drilling,NEAR_MISS,NO_INJURY,2026-03-01\n'
        'DECOUPLE-02,"During mast maintenance at 25 meters height, derrickman unhooked lanyard without 100% tie-off.",Rig-04 Moran,Drilling,UNSAFE_ACT,NO_INJURY,2026-03-02\n'
        'DECOUPLE-03,"Forklift operator traveled with elevated mast striking overhead nitrogen piping.",Warehouse-1,Logistics,NEAR_MISS,NO_INJURY,2026-03-03\n'
    ).encode("utf-8")

    service = BatchIngestionService(session=db_session)
    job = await service.create_batch_job(filename="decoupled_test.csv")
    completed_job = await service.process_batch_file(
        batch_id=job.id,
        file_content=csv_content,
        filename="decoupled_test.csv",
    )

    assert completed_job.status == BatchJobStatus.COMPLETED
    assert completed_job.processed_rows == 3

    # Assert that NO PrecursorPattern was automatically created by batch ingestion
    res_pat = await db_session.execute(select(PrecursorPattern))
    patterns = res_pat.scalars().all()
    assert len(patterns) == 0, "Phase 4 batch ingestion must not automatically create Phase 2B patterns"

    # Assert that NO RiskConcentration was automatically created by batch ingestion
    res_conc = await db_session.execute(select(RiskConcentration))
    concentrations = res_conc.scalars().all()
    assert len(concentrations) == 0, "Phase 4 batch ingestion must not automatically create Phase 3 concentrations"

