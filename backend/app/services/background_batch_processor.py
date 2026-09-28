"""Background batch task processing implementation using AsyncSessionLocal."""

from uuid import UUID
from sqlalchemy import select

from app.core.logging import get_logger
from app.db.models.batch import BatchJob
from app.db.session import AsyncSessionLocal
from app.domain.enums import BatchJobStatus
from app.domain.interfaces.batch import BatchProcessorInterface
from app.services.batch_ingestion_service import BatchIngestionService

logger = get_logger(__name__)


class BackgroundBatchProcessor(BatchProcessorInterface):
    """Executes asynchronous batch processing in the background with structured observability."""

    async def process_batch_job(
        self,
        batch_id: UUID,
        file_content: bytes,
        filename: str,
    ) -> None:
        """Execute batch file processing in a dedicated database session with fatal failure recovery."""
        logger.info(
            f"Starting background batch processing for batch_id={batch_id}, file={filename}",
            extra={"component": "batch_processor", "batch_id": str(batch_id)},
        )
        try:
            async with AsyncSessionLocal() as session:
                service = BatchIngestionService(session=session)
                job = await service.process_batch_file(
                    batch_id=batch_id,
                    file_content=file_content,
                    filename=filename,
                )
                logger.info(
                    f"Finished background batch processing for batch_id={batch_id}: status={job.status.value}",
                    extra={
                        "component": "batch_processor",
                        "batch_id": str(batch_id),
                        "status": job.status.value,
                    },
                )
        except Exception as e:
            logger.error(
                f"Fatal unhandled exception in background batch processor for batch {batch_id}: {e}",
                exc_info=True,
                extra={
                    "component": "batch_processor",
                    "batch_id": str(batch_id),
                    "exception_category": e.__class__.__name__,
                },
            )
            # Attempt recovery: mark the BatchJob as FAILED so it does not hang in intermediate state
            try:
                async with AsyncSessionLocal() as recovery_session:
                    stmt = select(BatchJob).where(BatchJob.id == batch_id)
                    res = await recovery_session.execute(stmt)
                    failed_job = res.scalar_one_or_none()
                    if failed_job and failed_job.status not in (
                        BatchJobStatus.COMPLETED,
                        BatchJobStatus.COMPLETED_WITH_ERRORS,
                        BatchJobStatus.FAILED,
                    ):
                        failed_job.status = BatchJobStatus.FAILED
                        await recovery_session.commit()
                        logger.info(
                            f"Marked batch {batch_id} as FAILED after unhandled background error",
                            extra={"component": "batch_processor", "batch_id": str(batch_id)},
                        )
            except Exception as recovery_err:
                logger.error(
                    f"Failed to record FAILED status for batch {batch_id}: {recovery_err}",
                    extra={
                        "component": "batch_processor",
                        "batch_id": str(batch_id),
                        "exception_category": recovery_err.__class__.__name__,
                    },
                )
