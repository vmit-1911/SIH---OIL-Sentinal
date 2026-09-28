"""SQLAlchemy model for recurring precursor patterns and systemic clusters."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import DateTime, Enum, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import PatternStatus

if TYPE_CHECKING:
    from app.db.models.assessment import SIFAssessment


class PrecursorPattern(Base):
    """Represents an identified systemic recurring precursor pattern across operations."""

    __tablename__ = "precursor_patterns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    pattern_code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="e.g. PAT_LSR_03_SUSPENDED_LOAD_RIGGING_FAILURE",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    hazard_category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    activity_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    failed_barrier_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    lsr_code: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    occurrence_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    affected_locations: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    supporting_report_ids: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    supporting_lsr_codes: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    representative_precursor: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="The 7-dimensional representative structured precursor and provenance",
    )
    similarity_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Summary statistics of similarity scores and scoring modes",
    )
    evidence_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Structured explainable evidence backing the pattern membership",
    )
    similarity_weights: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Configured weights used for discovering this cluster",
    )
    discovery_method: Mapped[str] = mapped_column(
        String(100),
        default="HYBRID_SIMILARITY_GROUPING_V1",
        nullable=False,
    )
    status: Mapped[PatternStatus] = mapped_column(
        Enum(PatternStatus, name="pattern_status_enum"),
        default=PatternStatus.CANDIDATE,
        nullable=False,
        index=True,
    )
    first_detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    last_detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    assessments: Mapped[List["SIFAssessment"]] = relationship(
        "SIFAssessment",
        back_populates="pattern",
    )

    __table_args__ = (
        Index("ix_precursor_patterns_hazard_act", "hazard_category", "activity_type"),
    )

