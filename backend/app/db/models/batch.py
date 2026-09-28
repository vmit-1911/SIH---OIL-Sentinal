"""SQLAlchemy model for asynchronous batch processing jobs."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import (
    DateTime,
    Enum,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import BatchJobStatus

if TYPE_CHECKING:
    from app.db.models.batch_error import BatchRowError
    from app.db.models.report import SafetyReport


class BatchJob(Base):
    """Tracks status, progress, and errors of bulk ingestion and analysis jobs."""

    __tablename__ = "batch_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
        doc="Original filename of the uploaded batch",
    )
    import_schema_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="OIL_SAFETY_REPORT_CSV_V1",
        doc="Version identifier for the import schema specification",
    )
    status: Mapped[BatchJobStatus] = mapped_column(
        Enum(BatchJobStatus, name="batch_job_status_enum"),
        nullable=False,
        default=BatchJobStatus.PENDING,
        index=True,
    )
    total_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    accepted_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    rejected_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    duplicate_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    processed_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    failed_processing_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    sif_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    error_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    results_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    job_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    errors: Mapped[List["BatchRowError"]] = relationship(
        "BatchRowError",
        back_populates="batch_job",
        cascade="all, delete-orphan",
    )
    reports: Mapped[List["SafetyReport"]] = relationship(
        "SafetyReport",
        back_populates="batch_job",
    )

    # Backward-compatible property aliases
    @property
    def total_records(self) -> int:
        return self.total_rows

    @property
    def processed_records(self) -> int:
        return self.processed_rows

    @property
    def error_count(self) -> int:
        return self.rejected_rows + self.failed_processing_rows

    @property
    def error_details(self) -> Optional[Dict[str, Any]]:
        return self.error_summary

