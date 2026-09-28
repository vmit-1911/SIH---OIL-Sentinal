"""Application service orchestrating batch ingestion, validation, deduplication, SIF analysis, and auditability."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.logging import get_logger
from app.db.models.assessment import SIFAssessment
from app.db.models.batch import BatchJob
from app.db.models.batch_error import BatchRowError
from app.db.models.report import SafetyReport
from app.domain.batch.deduplicator import BatchDeduplicator
from app.domain.batch.models import BatchIngestionSummary, ParsedReportRow
from app.domain.batch.validator import BatchValidator
from app.domain.enums import BatchJobStatus, SIFClassification
from app.domain.interfaces.batch import BatchParserInterface
from app.infrastructure.parsers.csv_parser import CsvSafetyReportParser
from app.services.sif_analysis_service import SIFAnalysisService

logger = get_logger(__name__)


class BatchIngestionService:
    """Orchestrates end-to-end batch file ingestion, row validation, deduplication, and SIF analysis."""

    def __init__(
        self,
        session: AsyncSession,
        parser: Optional[BatchParserInterface] = None,
        analysis_service: Optional[SIFAnalysisService] = None,
    ):
        self.session = session
        self.settings = get_settings()
        self.parser = parser or CsvSafetyReportParser()
        self.analysis_service = analysis_service or SIFAnalysisService(session=self.session)

    async def create_batch_job(
        self,
        filename: str,
        import_schema_version: Optional[str] = None,
    ) -> BatchJob:
        """Initialize a new BatchJob tracking record in PENDING state."""
        schema_ver = import_schema_version or self.settings.BATCH_DEFAULT_IMPORT_SCHEMA_VERSION
        job = BatchJob(
            id=uuid.uuid4(),
            source_filename=filename,
            import_schema_version=schema_ver,
            status=BatchJobStatus.PENDING,
            total_rows=0,
            accepted_rows=0,
            rejected_rows=0,
            duplicate_rows=0,
            processed_rows=0,
            failed_processing_rows=0,
            sif_count=0,
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_batch_job(self, batch_id: uuid.UUID) -> Optional[BatchJob]:
        """Fetch BatchJob by primary key."""
        stmt = select(BatchJob).where(BatchJob.id == batch_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_batch_errors(
        self,
        batch_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[BatchRowError]]:
        """Retrieve total count and paginated row-level errors for a batch job."""
        count_stmt = select(func.count(BatchRowError.id)).where(BatchRowError.batch_id == batch_id)
        total_res = await self.session.execute(count_stmt)
        total_errors = total_res.scalar_one() or 0

        stmt = (
            select(BatchRowError)
            .where(BatchRowError.batch_id == batch_id)
            .order_by(BatchRowError.row_number.asc())
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        errors = res.scalars().all()
        return total_errors, list(errors)

    async def process_batch_file(
        self,
        batch_id: uuid.UUID,
        file_content: bytes,
        filename: str,
    ) -> BatchJob:
        """Execute the full 3-stage batch processing lifecycle with transaction chunking."""
        job = await self.get_batch_job(batch_id)
        if not job:
            raise ValueError(f"BatchJob with id '{batch_id}' not found.")

        # Stage 1: File Validation
        job.status = BatchJobStatus.VALIDATING
        job.started_at = datetime.now(timezone.utc)
        await self.session.commit()

        is_valid_file, file_err = BatchValidator.validate_file(
            file_content=file_content,
            filename=filename,
            max_size_bytes=self.settings.BATCH_MAX_FILE_SIZE_BYTES,
            allowed_extensions=self.settings.BATCH_ALLOWED_EXTENSIONS,
        )
        if not is_valid_file:
            job = await self.get_batch_job(batch_id)
            if job:
                job.status = BatchJobStatus.FAILED
                job.error_summary = {"file_error": file_err}
                job.completed_at = datetime.now(timezone.utc)
                await self.session.commit()
                return job
            return await self.get_batch_job(batch_id)

        # Parse CSV content
        try:
            parsed_rows, syntax_errors = self.parser.parse(file_content, filename)
        except Exception as e:
            logger.error(f"Catastrophic CSV parsing error for batch {batch_id}: {e}")
            job = await self.get_batch_job(batch_id)
            if job:
                job.status = BatchJobStatus.FAILED
                job.error_summary = {"parsing_error": str(e)}
                job.completed_at = datetime.now(timezone.utc)
                await self.session.commit()
                return job
            return await self.get_batch_job(batch_id)

        # Stage 2: Ingestion & Deduplication
        total_rows = len(parsed_rows) + len(syntax_errors)
        rejected_rows = len(syntax_errors)
        duplicate_rows = 0
        accepted_rows = 0

        job = await self.get_batch_job(batch_id)
        if job:
            job.status = BatchJobStatus.INGESTING
            job.total_rows = total_rows
            job.rejected_rows = rejected_rows
            await self.session.commit()

        # Record initial syntax errors
        for s_row, s_field, s_code, s_msg in syntax_errors:
            err_record = BatchRowError(
                batch_id=batch_id,
                row_number=s_row,
                field_name=s_field,
                error_code=s_code,
                error_message=s_msg,
            )
            self.session.add(err_record)

        # Fetch existing report_refs from DB to optimize deduplication
        existing_refs_res = await self.session.execute(select(SafetyReport.report_ref))
        existing_db_refs: Set[str] = set(existing_refs_res.scalars().all())
        seen_batch_refs: Set[str] = set()

        accepted_reports: List[SafetyReport] = []
        chunk_buffer: List[SafetyReport] = []
        chunk_size = self.settings.BATCH_CHUNK_SIZE

        for row in parsed_rows:
            # 1. Row validation
            row_errors = BatchValidator.validate_row(row)
            if row_errors:
                for f_name, e_code, e_msg in row_errors:
                    err_record = BatchRowError(
                        batch_id=batch_id,
                        row_number=row.row_number,
                        field_name=f_name,
                        error_code=e_code,
                        error_message=e_msg,
                    )
                    self.session.add(err_record)
                rejected_rows += 1
                continue

            # 2. Deduplication check
            report_ref = BatchDeduplicator.resolve_report_ref(
                source_report_id=row.source_report_id,
                raw_text=row.raw_text,
                reported_location=row.reported_location,
                reported_department=row.reported_department,
                source_type=row.source_type,
                event_timestamp=row.event_timestamp,
            )

            if report_ref in existing_db_refs or report_ref in seen_batch_refs:
                duplicate_rows += 1
                continue

            # Create new SafetyReport
            report = SafetyReport(
                report_ref=report_ref,
                source_type=row.source_type,
                raw_text=row.raw_text,
                reported_location=row.reported_location,
                reported_department=row.reported_department,
                actual_severity=row.actual_severity,
                actual_outcome_details=row.actual_outcome_details,
                event_timestamp=row.event_timestamp,
                batch_id=batch_id,
                batch_row_number=row.row_number,
            )
            self.session.add(report)
            chunk_buffer.append(report)
            accepted_reports.append(report)
            seen_batch_refs.add(report_ref)
            existing_db_refs.add(report_ref)
            accepted_rows += 1

            if len(chunk_buffer) >= chunk_size:
                await self.session.commit()
                chunk_buffer = []

        if chunk_buffer:
            await self.session.commit()

        # Update job status before Stage 3
        job = await self.get_batch_job(batch_id)
        if job:
            job.status = BatchJobStatus.PROCESSING
            job.accepted_rows = accepted_rows
            job.rejected_rows = rejected_rows
            job.duplicate_rows = duplicate_rows
            await self.session.commit()

        # Stage 3: SIF Analysis Processing
        processed_rows = 0
        failed_processing_rows = 0
        sif_count = 0

        for report in accepted_reports:
            try:
                analysis_res = await self.analysis_service.analyze_existing_report(report)
                processed_rows += 1
                classification_str = (
                    analysis_res.sif_classification.value
                    if hasattr(analysis_res.sif_classification, "value")
                    else str(analysis_res.sif_classification)
                )
                if classification_str in ("POTENTIAL_SIF", "ACTUAL_SIF"):
                    sif_count += 1
            except Exception as ae:
                logger.error(f"Analysis failed for report_id={report.id}, row={report.batch_row_number}: {ae}")
                err_record = BatchRowError(
                    batch_id=batch_id,
                    row_number=report.batch_row_number or 0,
                    field_name="analysis",
                    error_code="ANALYSIS_FAILED",
                    error_message=str(ae),
                )
                self.session.add(err_record)
                failed_processing_rows += 1

        # Summary & Invariant Reconciliation
        summary = BatchIngestionSummary(
            total_rows=total_rows,
            accepted_rows=accepted_rows,
            rejected_rows=rejected_rows,
            duplicate_rows=duplicate_rows,
            processed_rows=processed_rows,
            failed_processing_rows=failed_processing_rows,
            sif_count=sif_count,
        )

        if not summary.validate_invariants():
            logger.warning(f"Batch counters invariant mismatch for batch {batch_id}: {summary}")

        job = await self.get_batch_job(batch_id)
        if job:
            job.total_rows = total_rows
            job.accepted_rows = accepted_rows
            job.rejected_rows = rejected_rows
            job.duplicate_rows = duplicate_rows
            job.processed_rows = processed_rows
            job.failed_processing_rows = failed_processing_rows
            job.sif_count = sif_count

            if rejected_rows > 0 or failed_processing_rows > 0:
                job.status = BatchJobStatus.COMPLETED_WITH_ERRORS
            else:
                job.status = BatchJobStatus.COMPLETED

            job.completed_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(job)
            return job

        return await self.get_batch_job(batch_id)

    async def retry_batch_job(self, batch_id: uuid.UUID) -> Tuple[BatchJob, int]:
        """Safely and idempotently retry unanalyzed or failed reports for a batch job.
        
        Explicit Retry Eligibility Policy:
        1. Only SafetyReports that belong to this batch and lack a valid SIFAssessment (due to analysis failure or interruption) are eligible.
        2. Successfully processed reports (with an existing SIFAssessment) are strictly non-retryable and preserved.
        3. Structural row rejections (rejected during CSV validation) are non-retryable as they have no SafetyReport representation.
        4. Retry operations are strictly idempotent: repeated executions on fully processed batches result in 0 retried reports.
        """
        job = await self.get_batch_job(batch_id)
        if not job:
            raise ValueError(f"BatchJob with id '{batch_id}' not found.")

        # Find all SafetyReports for this batch lacking an assessment
        stmt = (
            select(SafetyReport)
            .outerjoin(SIFAssessment, SafetyReport.id == SIFAssessment.report_id)
            .where(
                SafetyReport.batch_id == batch_id,
                SIFAssessment.id.is_(None),
            )
            .order_by(SafetyReport.batch_row_number.asc().nulls_last())
        )
        res = await self.session.execute(stmt)
        eligible_reports = list(res.scalars().all())

        if not eligible_reports:
            # Batch has no retryable reports; return unchanged
            return job, 0

        job.status = BatchJobStatus.PROCESSING
        await self.session.commit()

        retried_count = 0
        for rep in eligible_reports:
            try:
                analysis_res = await self.analysis_service.analyze_existing_report(rep)
                job.processed_rows += 1
                if job.failed_processing_rows > 0:
                    job.failed_processing_rows -= 1

                # Clean up any recorded ANALYSIS_FAILED error for this row
                if rep.batch_row_number:
                    stmt_err = (
                        select(BatchRowError)
                        .where(
                            BatchRowError.batch_id == batch_id,
                            BatchRowError.row_number == rep.batch_row_number,
                            BatchRowError.error_code == "ANALYSIS_FAILED",
                        )
                    )
                    res_err = await self.session.execute(stmt_err)
                    for err_rec in res_err.scalars().all():
                        await self.session.delete(err_rec)

                classification_str = (
                    analysis_res.sif_classification.value
                    if hasattr(analysis_res.sif_classification, "value")
                    else str(analysis_res.sif_classification)
                )
                if classification_str in ("POTENTIAL_SIF", "ACTUAL_SIF"):
                    job.sif_count += 1
                retried_count += 1
            except Exception as ae:
                logger.error(f"Retry analysis failed for report_id={rep.id}, row={rep.batch_row_number}: {ae}")

        # Summary & Invariant Reconciliation
        summary = BatchIngestionSummary(
            total_rows=job.total_rows,
            accepted_rows=job.accepted_rows,
            rejected_rows=job.rejected_rows,
            duplicate_rows=job.duplicate_rows,
            processed_rows=job.processed_rows,
            failed_processing_rows=job.failed_processing_rows,
            sif_count=job.sif_count,
        )
        if not summary.validate_invariants():
            logger.warning(f"Batch counters invariant mismatch after retry for batch {batch_id}: {summary}")

        if job.rejected_rows > 0 or job.failed_processing_rows > 0:
            job.status = BatchJobStatus.COMPLETED_WITH_ERRORS
        else:
            job.status = BatchJobStatus.COMPLETED

        job.completed_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(job)

        return job, retried_count
