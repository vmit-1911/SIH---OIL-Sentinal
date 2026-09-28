"""SQLAlchemy model for explainable SIF risk concentration findings."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import ConcentrationDimension, ConcentrationStatus, ObservedTrend

if TYPE_CHECKING:
    from app.db.models.pattern import PrecursorPattern


class RiskConcentration(Base):
    """Represents an aggregated, explainable SIF risk concentration finding across operations."""

    __tablename__ = "risk_concentrations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    concentration_key: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        nullable=False,
        index=True,
        doc="e.g. CONC|HAZARD|SUSPENDED_LOAD or CONC|PATTERN|PAT_...",
    )
    dimension_type: Mapped[ConcentrationDimension] = mapped_column(
        Enum(ConcentrationDimension, name="concentration_dimension_enum", native_enum=False),
        nullable=False,
        index=True,
    )
    dimension_value: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    pattern_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("precursor_patterns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    occurrence_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    distinct_report_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    distinct_location_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    first_observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    observed_trend: Mapped[ObservedTrend] = mapped_column(
        Enum(ObservedTrend, name="observed_trend_enum", native_enum=False),
        nullable=False,
        default=ObservedTrend.INSUFFICIENT_DATA,
        index=True,
    )
    temporal_distribution: Mapped[Dict[str, int]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    supporting_report_ids: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    supporting_pattern_ids: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    supporting_locations: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    supporting_lsr_codes: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    evidence_summary: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    calculation_method: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="EXPLAINABLE_OBSERVED_CONCENTRATION_V1",
    )
    status: Mapped[ConcentrationStatus] = mapped_column(
        Enum(ConcentrationStatus, name="concentration_status_enum", native_enum=False),
        nullable=False,
        default=ConcentrationStatus.ACTIVE,
        index=True,
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

    pattern: Mapped[Optional["PrecursorPattern"]] = relationship(
        "PrecursorPattern",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_risk_concentrations_dim_type_val", "dimension_type", "dimension_value"),
        Index("ix_risk_concentrations_trend", "observed_trend"),
    )
