"""SQLAlchemy model for HSE action recommendations and lifecycle management."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import DateTime, Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.enums import (
    ActionCategory,
    ActionPriority,
    ActionSourceType,
    ActionStatus,
)


class HSEActionRecommendation(Base):
    """Represents a deterministic, auditable HSE action recommendation derived from SIF intelligence."""

    __tablename__ = "hse_action_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    action_key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Deterministic uniqueness key: e.g. ACTION|ASSESSMENT|<UUID>|BARRIER_VERIFICATION|ACT-R01-BARRIER",
    )
    source_type: Mapped[ActionSourceType] = mapped_column(
        Enum(ActionSourceType, name="action_source_type_enum", native_enum=False),
        nullable=False,
        index=True,
        doc="Originating intelligence entity type: ASSESSMENT, PATTERN, CONCENTRATION, REVIEW",
    )
    source_id: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
        doc="UUID or key of the source intelligence record",
    )
    action_category: Mapped[ActionCategory] = mapped_column(
        Enum(ActionCategory, name="action_category_enum", native_enum=False),
        nullable=False,
        index=True,
        doc="Controlled categorical recommendation classification",
    )
    action_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Human-readable title of the recommended follow-up action",
    )
    action_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Detailed operational guidance and recommended verification steps",
    )
    priority: Mapped[ActionPriority] = mapped_column(
        Enum(ActionPriority, name="action_priority_enum", native_enum=False),
        nullable=False,
        default=ActionPriority.MEDIUM,
        index=True,
        doc="Deterministic priority level: CRITICAL_REVIEW, HIGH, MEDIUM, INFORMATIONAL",
    )
    rationale: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Explicit justification explaining why this action was generated from source evidence",
    )
    evidence_refs: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Supporting evidence items, character spans, and report references",
    )
    source_dimensions: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Snapshot of relevant precursor or concentration dimensions",
    )
    lsr_code: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Associated IOGP Life-Saving Rule code if applicable",
    )
    precursor_signature: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Precursor signature of the source assessment if applicable",
    )
    pattern_key: Mapped[Optional[str]] = mapped_column(
        String(120),
        nullable=True,
        index=True,
        doc="Associated pattern code/key if applicable",
    )
    concentration_key: Mapped[Optional[str]] = mapped_column(
        String(120),
        nullable=True,
        index=True,
        doc="Associated concentration key if applicable",
    )
    rule_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Identifier of the deterministic action rule that generated this recommendation",
    )
    rule_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="1.0.0",
        doc="Version of the action rule",
    )
    status: Mapped[ActionStatus] = mapped_column(
        Enum(ActionStatus, name="action_status_enum", native_enum=False),
        nullable=False,
        default=ActionStatus.OPEN,
        index=True,
        doc="Lifecycle state: OPEN, ACKNOWLEDGED, IN_PROGRESS, COMPLETED, DISMISSED",
    )
    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Username or designation of assigned HSE personnel",
    )
    actor_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Last user or system actor who updated the action status",
    )
    status_rationale: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Mandatory rationale when dismissing or completing an action",
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
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    dismissed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("idx_hse_actions_source", "source_type", "source_id"),
        Index("idx_hse_actions_status_priority", "status", "priority"),
    )
