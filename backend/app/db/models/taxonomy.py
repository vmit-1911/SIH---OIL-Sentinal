"""SQLAlchemy models for Life-Saving Rule taxonomies and report-to-rule mappings."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.report import SafetyReport


class LSRTaxonomy(Base):
    """Stores versioned Life-Saving Rule taxonomies (e.g. IOGP Report 459 - 2018)."""

    __tablename__ = "lsr_taxonomies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    taxonomy_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="e.g. IOGP_REPORT_459",
    )
    authority: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="e.g. IOGP, OISD, OIL",
    )
    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="e.g. 2018",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    rules: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        doc="Array of rule definitions with detection patterns",
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    mappings: Mapped[List["LSRReportMapping"]] = relationship(
        "LSRReportMapping",
        back_populates="taxonomy",
        cascade="all, delete-orphan",
    )


class LSRReportMapping(Base):
    """Maps safety reports to violated Life-Saving Rules."""

    __tablename__ = "lsr_report_mappings"

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
    taxonomy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lsr_taxonomies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="e.g. LSR_07_SAFE_MECHANICAL_LIFTING",
    )
    rule_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    trigger_evidence: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    report: Mapped["SafetyReport"] = relationship(
        "SafetyReport",
        back_populates="lsr_mappings",
    )
    taxonomy: Mapped["LSRTaxonomy"] = relationship(
        "LSRTaxonomy",
        back_populates="mappings",
    )

    __table_args__ = (
        Index("ix_lsr_mappings_rule_report", "rule_code", "report_id"),
    )
