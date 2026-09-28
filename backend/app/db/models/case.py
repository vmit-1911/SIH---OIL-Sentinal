"""SQLAlchemy models for HSE Case Management and Operational Follow-up."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import (
    CaseEventType,
    CasePriority,
    CaseSourceType,
    CaseStatus,
    CaseType,
)


class HSECase(Base):
    """Represents an HSE case/investigation grouping safety reports, assessments, patterns, concentrations, reviews, and actions."""

    __tablename__ = "hse_cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    case_key: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique stable case identifier (e.g. CASE-01J... or CASE-<UUID>)",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Human-readable title of the investigation or case",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Detailed context, objective, and scope of the HSE case",
    )
    case_type: Mapped[CaseType] = mapped_column(
        Enum(CaseType, name="case_type_enum", native_enum=False),
        nullable=False,
        index=True,
        doc="Categorical classification: SIF_INVESTIGATION, PATTERN_INVESTIGATION, LOCATION_REVIEW, etc.",
    )
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus, name="case_status_enum", native_enum=False),
        nullable=False,
        default=CaseStatus.OPEN,
        index=True,
        doc="Operational lifecycle status: OPEN, TRIAGE, INVESTIGATING, ACTION_REQUIRED, PENDING_VERIFICATION, CLOSED, CANCELLED",
    )
    priority: Mapped[CasePriority] = mapped_column(
        Enum(CasePriority, name="case_priority_enum", native_enum=False),
        nullable=False,
        default=CasePriority.MEDIUM,
        index=True,
        doc="Operational review priority: CRITICAL_REVIEW, HIGH, MEDIUM, INFORMATIONAL",
    )
    owner: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Username or designation of assigned HSE case investigator/owner",
    )
    created_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Actor/Auditor who created the case",
    )
    assigned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when case was assigned to owner",
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    closure_rationale: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Mandatory justification when closing or cancelling a case",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    sources: Mapped[List["HSECaseSourceAssociation"]] = relationship(
        "HSECaseSourceAssociation",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="HSECaseSourceAssociation.attached_at.asc()",
        lazy="selectin",
    )
    events: Mapped[List["HSECaseEvent"]] = relationship(
        "HSECaseEvent",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="HSECaseEvent.created_at.asc()",
        lazy="selectin",
    )


    __table_args__ = (
        Index("idx_hse_cases_status_priority", "status", "priority"),
        Index("idx_hse_cases_owner_status", "owner", "status"),
        Index("idx_hse_cases_type_status", "case_type", "status"),
    )


class HSECaseSourceAssociation(Base):
    """Explicit association linking an HSE case to an authoritative source intelligence record."""

    __tablename__ = "hse_case_source_associations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hse_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[CaseSourceType] = mapped_column(
        Enum(CaseSourceType, name="case_source_type_enum", native_enum=False),
        nullable=False,
        index=True,
        doc="Originating intelligence entity type: REPORT, ASSESSMENT, PATTERN, CONCENTRATION, REVIEW, ACTION",
    )
    source_id: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
        doc="UUID or key of the associated source intelligence record",
    )
    source_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Lightweight reference snapshot (title, category, status) for fast presentation",
    )
    attached_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Actor who attached this source reference to the case",
    )
    attached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    case: Mapped["HSECase"] = relationship(
        "HSECase",
        back_populates="sources",
    )

    __table_args__ = (
        UniqueConstraint("case_id", "source_type", "source_id", name="uq_hse_case_source"),
        Index("idx_hse_case_sources_lookup", "source_type", "source_id"),
    )


class HSECaseEvent(Base):
    """Append-only audit trail recording every state mutation and source attachment in an HSE case."""

    __tablename__ = "hse_case_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hse_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[CaseEventType] = mapped_column(
        Enum(CaseEventType, name="case_event_type_enum", native_enum=False),
        nullable=False,
        index=True,
        doc="Lifecycle event type: CASE_CREATED, CASE_ASSIGNED, CASE_STATUS_CHANGED, SOURCE_ATTACHED, etc.",
    )
    actor_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Actor/Auditor who triggered the mutation",
    )
    before_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Snapshot of relevant state fields before transition",
    )
    after_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Snapshot of relevant state fields after transition",
    )
    source_reference: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Metadata regarding the source attached, detached, or modified",
    )
    rationale: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Optional or mandatory justification for the mutation",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    case: Mapped["HSECase"] = relationship(
        "HSECase",
        back_populates="events",
    )

    __table_args__ = (
        Index("idx_hse_case_events_case_created", "case_id", "created_at"),
    )
