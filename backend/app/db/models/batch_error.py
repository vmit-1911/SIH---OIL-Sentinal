"""SQLAlchemy model for recording batch row-level ingestion and processing errors."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.batch import BatchJob


class BatchRowError(Base):
    """Stores row-level validation rejections, structural parse errors, or analysis execution failures."""

    __tablename__ = "batch_row_errors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batch_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    field_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    error_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    error_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    batch_job: Mapped["BatchJob"] = relationship(
        "BatchJob",
        back_populates="errors",
    )

    __table_args__ = (
        Index("ix_batch_row_errors_batch_row", "batch_id", "row_number"),
    )
