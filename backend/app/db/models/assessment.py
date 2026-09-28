"""SQLAlchemy model for SIF potential assessments, scoring, and embeddings."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import (
    EvidenceStrength,
    PotentialOutcome,
    SIFClassification,
    TriageStatus,
)

if TYPE_CHECKING:
    from app.db.models.pattern import PrecursorPattern
    from app.db.models.report import SafetyReport
    from app.db.models.review import TriageReview


class SIFAssessment(Base):
    """Stores AI/Rule SIF classification, evidence scoring, structured precursor, and vector embedding."""

    __tablename__ = "sif_assessments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("safety_reports.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    sif_classification: Mapped[SIFClassification] = mapped_column(
        Enum(SIFClassification, name="sif_classification_enum"),
        nullable=False,
        default=SIFClassification.UNDETERMINED,
        index=True,
    )
    evidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Aggregate evidence strength score [0.0 - 1.0]",
    )
    evidence_strength: Mapped[EvidenceStrength] = mapped_column(
        Enum(EvidenceStrength, name="evidence_strength_enum"),
        nullable=False,
        default=EvidenceStrength.LOW,
        index=True,
    )
    rule_based_screening_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Deterministic domain rules match score [0.0 - 1.0]",
    )
    potential_severity: Mapped[PotentialOutcome] = mapped_column(
        Enum(PotentialOutcome, name="potential_outcome_enum"),
        nullable=False,
        default=PotentialOutcome.LOW_IMPACT,
        index=True,
    )
    potential_outcome_details: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    primary_reasoning: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    evidence_spans: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        doc="Highlighted text spans and category tags",
    )
    structured_precursor: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        doc="The structured precursor object (nullable in Phase 1C, populated in Phase 1D+)",
    )
    text_embedding: Mapped[Optional[List[float]]] = mapped_column(
        Vector(384),
        nullable=True,
        doc="Dense semantic vector embedding (nullable in Phase 0)",
    )
    precursor_signature: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    pattern_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("precursor_patterns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    triage_status: Mapped[TriageStatus] = mapped_column(
        Enum(TriageStatus, name="triage_status_enum"),
        nullable=False,
        default=TriageStatus.AUTO_SCREENED,
        index=True,
    )
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    report: Mapped["SafetyReport"] = relationship(
        "SafetyReport",
        back_populates="assessment",
    )
    pattern: Mapped[Optional["PrecursorPattern"]] = relationship(
        "PrecursorPattern",
        back_populates="assessments",
    )
    reviews: Mapped[List["TriageReview"]] = relationship(
        "TriageReview",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_sif_assessments_sif_triage", "sif_classification", "triage_status"),
        Index("ix_sif_assessments_score", "evidence_score"),
    )
