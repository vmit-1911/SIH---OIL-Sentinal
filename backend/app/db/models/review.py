"""SQLAlchemy models for HSE auditor reviews, triage lifecycle, and immutable audit events."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import (
    PotentialOutcome,
    ReviewAuditEventType,
    ReviewDecision,
    ReviewFeedbackCategory,
    ReviewState,
    ReviewStatus,
    SIFClassification,
)

if TYPE_CHECKING:
    from app.db.models.assessment import SIFAssessment
    from app.db.models.report import SafetyReport


class TriageReview(Base):
    """Stores human auditor verification, lifecycle status, corrections, and feedback."""

    __tablename__ = "triage_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("safety_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assessment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sif_assessments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Reference to the AI SIF assessment being reviewed",
    )
    status: Mapped[ReviewState] = mapped_column(
        Enum(ReviewState, name="review_state_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ReviewState.PENDING,
        index=True,
        doc="Lifecycle state: PENDING, IN_REVIEW, REVIEWED",
    )
    decision: Mapped[Optional[ReviewDecision]] = mapped_column(
        Enum(ReviewDecision, name="review_decision_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        index=True,
        doc="HSE expert decision: CONFIRM_AI, CORRECT, REJECT_AI, MARK_UNDETERMINED",
    )
    reviewer_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Username or badge ID of the reviewing HSE officer",
    )
    reviewer_role: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Role/designation of the reviewer (e.g. HSE_AUDITOR, SAFETY_OFFICER)",
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when review was claimed/started",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        doc="Timestamp when final review decision was submitted",
    )
    original_classification: Mapped[SIFClassification] = mapped_column(
        Enum(SIFClassification, name="sif_classification_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=SIFClassification.UNDETERMINED,
        doc="Captured original AI SIF classification",
    )
    final_classification: Mapped[Optional[SIFClassification]] = mapped_column(
        Enum(SIFClassification, name="sif_classification_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        index=True,
        doc="Verified or corrected SIF classification",
    )
    original_structured_precursor: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Captured original AI 7-dimensional structured precursor object",
    )
    final_structured_precursor: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Corrected or confirmed 7-dimensional structured precursor object",
    )
    original_lsr_code: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Captured original AI primary Life-Saving Rule code",
    )
    final_lsr_code: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Corrected or confirmed primary Life-Saving Rule code",
    )
    reviewer_rationale: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Mandatory auditor explanation when overriding/correcting AI output",
    )
    reviewer_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Operational notes, follow-up actions, or context",
    )
    feedback_category: Mapped[Optional[ReviewFeedbackCategory]] = mapped_column(
        Enum(ReviewFeedbackCategory, name="review_feedback_category_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        index=True,
        doc="Categorical error tag for model calibration",
    )
    feedback_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Structured feedback details and error breakdown",
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        doc="Optimistic locking version counter for concurrency safety",
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
    report: Mapped["SafetyReport"] = relationship(
        "SafetyReport",
        back_populates="reviews",
    )
    assessment: Mapped[Optional["SIFAssessment"]] = relationship(
        "SIFAssessment",
        back_populates="reviews",
    )
    audit_events: Mapped[List["ReviewAuditEvent"]] = relationship(
        "ReviewAuditEvent",
        back_populates="review",
        cascade="all, delete-orphan",
        order_by="ReviewAuditEvent.created_at.asc()",
    )

    # Backward-compatible property aliases
    @property
    def verified_sif_classification(self) -> SIFClassification:
        return self.final_classification or self.original_classification

    @verified_sif_classification.setter
    def verified_sif_classification(self, value: SIFClassification) -> None:
        self.final_classification = value

    @property
    def verified_lsr_code(self) -> Optional[str]:
        return self.final_lsr_code

    @verified_lsr_code.setter
    def verified_lsr_code(self, value: Optional[str]) -> None:
        self.final_lsr_code = value

    @property
    def override_reason(self) -> Optional[str]:
        return self.reviewer_rationale

    @override_reason.setter
    def override_reason(self, value: Optional[str]) -> None:
        self.reviewer_rationale = value

    @property
    def review_status(self) -> ReviewStatus:
        if self.decision in (ReviewDecision.CORRECT, ReviewDecision.REJECT_AI, ReviewDecision.MARK_UNDETERMINED):
            return ReviewStatus.OVERRIDDEN
        return ReviewStatus.VALIDATED

    @review_status.setter
    def review_status(self, value: Any) -> None:
        if isinstance(value, ReviewStatus):
            self.status = ReviewState.REVIEWED
        elif isinstance(value, ReviewState):
            self.status = value

    @property
    def reviewed_at(self) -> datetime:
        return self.completed_at or self.created_at

    @property
    def verified_potential_severity(self) -> Optional[PotentialOutcome]:
        return None

    @verified_potential_severity.setter
    def verified_potential_severity(self, value: Any) -> None:
        pass

    __table_args__ = (
        Index("ix_triage_reviews_status_created", "status", "created_at"),
        Index("ix_triage_reviews_reviewer_status", "reviewer_id", "status"),
        Index("ix_triage_reviews_report_status", "report_id", "status"),
    )


class ReviewAuditEvent(Base):
    """Append-only audit trail recording every state-changing human review event."""

    __tablename__ = "review_audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("triage_reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Identifier of the reviewer or system acting on the review",
    )
    actor_role: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Role of the actor at the time of the event",
    )
    event_type: Mapped[ReviewAuditEventType] = mapped_column(
        Enum(ReviewAuditEventType, name="review_audit_event_type_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    before_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Snapshot of relevant review fields prior to the operation",
    )
    after_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Snapshot of relevant review fields after the operation",
    )
    changed_fields: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="List of field names modified by this event",
    )
    rationale: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Auditor justification or explanation provided with the action",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    review: Mapped["TriageReview"] = relationship(
        "TriageReview",
        back_populates="audit_events",
    )

    __table_args__ = (
        Index("ix_review_audit_events_review_time", "review_id", "created_at"),
        Index("ix_review_audit_events_actor_time", "actor_id", "created_at"),
        Index("ix_review_audit_events_type_time", "event_type", "created_at"),
    )
