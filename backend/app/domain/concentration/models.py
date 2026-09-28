"""Domain models for SIF risk concentration findings and explainable evidence."""

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.domain.enums import ConcentrationDimension, ConcentrationStatus, ObservedTrend


def normalize_dimension_identity(text: Optional[str]) -> str:
    """Deterministically normalize a dimension token for stable concentration identity."""
    if not text:
        return "UNSPECIFIED"
    cleaned = str(text).strip().upper()
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", cleaned).strip("_")
    return normalized or "UNSPECIFIED"


def generate_concentration_key(dimension: ConcentrationDimension, value: str) -> str:
    """Generate a stable, deterministic concentration finding key.

    Format: CONC|<DIMENSION_TYPE>|<NORMALIZED_VALUE>
    Examples:
        CONC|HAZARD|SUSPENDED_LOAD
        CONC|PATTERN|PAT_LSR_03_MECHANICAL_LIFTING_A1B2C3D4
        CONC|LOCATION|RIG_04_MORAN
    """
    dim_type = dimension.value if isinstance(dimension, ConcentrationDimension) else str(dimension)
    norm_val = normalize_dimension_identity(value)
    return f"CONC|{dim_type}|{norm_val}"[:120]


class ConcentrationEvidence(BaseModel):
    """Structured, explainable evidence justifying a risk concentration finding."""
    dimension: ConcentrationDimension
    value: str
    occurrence_count: int
    distinct_report_count: int
    distinct_location_count: int
    report_ids: List[uuid.UUID] = Field(default_factory=list)
    pattern_ids: List[uuid.UUID] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    lsr_codes: List[str] = Field(default_factory=list)
    first_observed_at: datetime
    last_observed_at: datetime
    temporal_distribution: Dict[str, int] = Field(default_factory=dict)
    observed_trend: ObservedTrend = ObservedTrend.INSUFFICIENT_DATA
    explanation: str


class ConcentrationFinding(BaseModel):
    """Pure domain representation of an explainable SIF risk concentration finding."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    concentration_key: str
    dimension_type: ConcentrationDimension
    dimension_value: str
    pattern_id: Optional[uuid.UUID] = None
    occurrence_count: int = 1
    distinct_report_count: int = 1
    distinct_location_count: int = 0
    first_observed_at: datetime
    last_observed_at: datetime
    observed_trend: ObservedTrend = ObservedTrend.INSUFFICIENT_DATA
    temporal_distribution: Dict[str, int] = Field(default_factory=dict)
    supporting_report_ids: List[uuid.UUID] = Field(default_factory=list)
    supporting_pattern_ids: List[uuid.UUID] = Field(default_factory=list)
    supporting_locations: List[str] = Field(default_factory=list)
    supporting_lsr_codes: List[str] = Field(default_factory=list)
    evidence_summary: Dict[str, Any] = Field(default_factory=dict)
    calculation_method: str = "EXPLAINABLE_OBSERVED_CONCENTRATION_V1"
    status: ConcentrationStatus = ConcentrationStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
