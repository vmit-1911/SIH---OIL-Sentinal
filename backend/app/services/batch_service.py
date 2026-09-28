"""Batch processing coordination service."""

import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.batch import BatchJob
from app.domain.enums import BatchJobStatus


class BatchService:
    """Service for initiating and querying batch processing jobs."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_batch_job(self, total_records: int) -> BatchJob:
        """Initialize a new batch job tracking record."""
        job = BatchJob(
            id=uuid.uuid4(),
            status=BatchJobStatus.PENDING,
            total_records=total_records,
            processed_records=0,
            sif_count=0,
            error_count=0,
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_batch_job(self, batch_id: uuid.UUID) -> Optional[BatchJob]:
        """Fetch batch job by ID."""
        stmt = select(BatchJob).where(BatchJob.id == batch_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
