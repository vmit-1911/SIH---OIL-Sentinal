import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import ActualOutcome, SourceType

if TYPE_CHECKING:
    from app.db.models.assessment import SIFAssessment
    from app.db.models.batch import BatchJob
    from app.db.models.review import TriageReview
    from app.db.models.taxonomy import LSRReportMapping


class SafetyReport(Base):
    """Stores raw safety observation narratives, metadata, and actual outcomes."""

    __tablename__ = "safety_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    report_ref: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique reference identifier for the report",
    )
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type_enum"),
        nullable=False,
        default=SourceType.NEAR_MISS,
        index=True,
    )
    raw_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Full free-text narrative of the observation or incident",
    )
    reported_location: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    reported_department: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    actual_severity: Mapped[ActualOutcome] = mapped_column(
        Enum(ActualOutcome, name="actual_outcome_enum"),
        nullable=False,
        default=ActualOutcome.NO_INJURY,
        index=True,
    )
    actual_outcome_details: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    event_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batch_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Reference to the batch job that ingested this report",
    )
    batch_row_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Original 1-indexed row number in the ingested batch file",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    batch_job: Mapped[Optional["BatchJob"]] = relationship(
        "BatchJob",
        back_populates="reports",
    )
    assessment: Mapped[Optional["SIFAssessment"]] = relationship(
        "SIFAssessment",
        back_populates="report",
        uselist=False,
        cascade="all, delete-orphan",
    )
    lsr_mappings: Mapped[List["LSRReportMapping"]] = relationship(
        "LSRReportMapping",
        back_populates="report",
        cascade="all, delete-orphan",
    )
    reviews: Mapped[List["TriageReview"]] = relationship(
        "TriageReview",
        back_populates="report",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_safety_reports_source_created", "source_type", "created_at"),
        Index("ix_safety_reports_loc_time", "reported_location", "event_timestamp"),
        Index("ix_safety_reports_batch_row", "batch_id", "batch_row_number"),
    )
