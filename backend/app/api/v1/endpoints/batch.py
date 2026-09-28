"""Batch safety report upload, status tracking, row-level error reporting, and retry endpoints."""

from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db_session
from app.domain.batch.validator import BatchValidator
from app.schemas.batch import (
    BatchErrorListResponse,
    BatchRetryResponse,
    BatchRowErrorDTO,
    BatchStatusResponse,
    BatchUploadResponse,
)
from app.schemas.common import ErrorResponse
from app.services.background_batch_processor import BackgroundBatchProcessor
from app.services.batch_ingestion_service import BatchIngestionService

router = APIRouter()
settings = get_settings()
batch_processor = BackgroundBatchProcessor()


@router.post(
    "/sif/batch-upload",
    response_model=BatchUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file format, size, or structure"},
    },
    summary="Upload Batch of Safety Reports for Background Processing",
    description="Accepts a CSV file of safety reports for validated asynchronous ingestion and SIF analysis.",
)
async def upload_batch(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Safety reports CSV file to ingest"),
    db: AsyncSession = Depends(get_db_session),
) -> BatchUploadResponse:
    """Upload CSV safety reports file and enqueue for asynchronous batch processing."""
    filename = file.filename or ""

    # Read uploaded bytes
    content = await file.read()

    # Pre-validate file structural properties
    is_valid, err_msg = BatchValidator.validate_file(
        file_content=content,
        filename=filename,
        max_size_bytes=settings.BATCH_MAX_FILE_SIZE_BYTES,
        allowed_extensions=settings.BATCH_ALLOWED_EXTENSIONS,
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg or "Invalid batch file.",
        )

    service = BatchIngestionService(session=db)
    job = await service.create_batch_job(filename=filename)

    # Dispatch to background task processor
    background_tasks.add_task(
        batch_processor.process_batch_job,
        batch_id=job.id,
        file_content=content,
        filename=filename,
    )

    return BatchUploadResponse(
        batch_id=job.id,
        status=job.status,
        filename=job.source_filename,
        import_schema_version=job.import_schema_version,
        total_records=job.total_rows,
        created_at=job.created_at,
        status_check_url=f"{settings.API_V1_PREFIX}/sif/batch/{job.id}",
    )


@router.get(
    "/sif/batch/{batch_id}",
    response_model=BatchStatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Batch job not found"},
    },
    summary="Get Batch Job Status and Progress",
    description="Retrieve processing progress, reconciliation counters, and results summary for a batch job.",
)
async def get_batch_status(
    batch_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> BatchStatusResponse:
    """Get status and counter reconciliation of a batch processing job."""
    service = BatchIngestionService(session=db)
    job = await service.get_batch_job(batch_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch job '{batch_id}' was not found.",
        )

    # Compute progress percentage
    if job.total_rows > 0:
        evaluated = job.processed_rows + job.failed_processing_rows + job.rejected_rows + job.duplicate_rows
        progress_pct = min(100.0, round((evaluated / job.total_rows) * 100.0, 2))
    elif job.status in ("COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"):
        progress_pct = 100.0
    else:
        progress_pct = 0.0

    return BatchStatusResponse(
        batch_id=job.id,
        status=job.status,
        source_filename=job.source_filename,
        import_schema_version=job.import_schema_version,
        total_rows=job.total_rows,
        accepted_rows=job.accepted_rows,
        rejected_rows=job.rejected_rows,
        duplicate_rows=job.duplicate_rows,
        processed_rows=job.processed_rows,
        failed_processing_rows=job.failed_processing_rows,
        sif_count=job.sif_count,
        progress_percentage=progress_pct,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_summary=job.error_summary,
        results_summary=job.results_summary,
    )


@router.get(
    "/sif/batch/{batch_id}/errors",
    response_model=BatchErrorListResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Batch job not found"},
    },
    summary="Get Row-Level Batch Errors",
    description="Retrieve paginated list of row-level validation rejections, parse errors, and processing failures.",
)
async def get_batch_errors(
    batch_id: UUID,
    limit: int = Query(50, ge=1, le=500, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: AsyncSession = Depends(get_db_session),
) -> BatchErrorListResponse:
    """Retrieve paginated row-level error details for a batch job."""
    service = BatchIngestionService(session=db)
    job = await service.get_batch_job(batch_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch job '{batch_id}' was not found.",
        )

    total_errors, errors = await service.get_batch_errors(batch_id, limit=limit, offset=offset)

    return BatchErrorListResponse(
        batch_id=batch_id,
        total_errors=total_errors,
        errors=[
            BatchRowErrorDTO(
                id=err.id,
                row_number=err.row_number,
                field_name=err.field_name,
                error_code=err.error_code,
                error_message=err.error_message,
                created_at=err.created_at,
            )
            for err in errors
        ],
        limit=limit,
        offset=offset,
    )


@router.post(
    "/sif/batch/{batch_id}/retry",
    response_model=BatchRetryResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Batch job not found"},
    },
    summary="Retry Failed or Incomplete Reports in Batch",
    description="Safely retries unanalyzed reports or reports that failed analysis without creating duplicate records.",
)
async def retry_batch(
    batch_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> BatchRetryResponse:
    """Trigger idempotent retry on unanalyzed reports for a batch job."""
    service = BatchIngestionService(session=db)
    job = await service.get_batch_job(batch_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch job '{batch_id}' was not found.",
        )

    updated_job, retried_count = await service.retry_batch_job(batch_id)

    return BatchRetryResponse(
        batch_id=batch_id,
        status=updated_job.status,
        retried_reports_count=retried_count,
        message=f"Retried {retried_count} unanalyzed or failed reports for batch '{batch_id}'.",
    )

