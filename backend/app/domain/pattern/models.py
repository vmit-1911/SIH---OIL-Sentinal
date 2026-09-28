"""Domain models and DTOs for recurring precursor patterns, evidence, and relationships."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.domain.enums import PatternStatus
from app.domain.precursor.model import StructuredSIFPrecursor


class PatternRelationshipEvidence(BaseModel):
    """Pairwise similarity evidence between two member reports in a discovered pattern."""
    report_a: uuid.UUID = Field(..., description="First member report identifier")
    report_b: uuid.UUID = Field(..., description="Second member report identifier")
    score: float = Field(..., ge=0.0, le=1.0, description="Pairwise similarity score [0.0 - 1.0]")
    mode: str = Field(..., description="Similarity mode: FULL_HYBRID, STRUCTURED_ONLY_FALLBACK, etc.")
    dimension_scores: Dict[str, Optional[float]] = Field(default_factory=dict)
    structured_score: Optional[float] = None
    semantic_score: Optional[float] = None


class PatternSimilaritySummary(BaseModel):
    """Statistical summary of pairwise similarity across pattern members."""
    min_score: float = Field(..., ge=0.0, le=1.0)
    max_score: float = Field(..., ge=0.0, le=1.0)
    avg_score: float = Field(..., ge=0.0, le=1.0)
    mode_counts: Dict[str, int] = Field(default_factory=dict)
    total_relationships: int = Field(default=0, ge=0)


class PatternEvidenceSummary(BaseModel):
    """Structured, auditable evidence backing a recurring precursor pattern."""
    member_count: int = Field(..., ge=1)
    member_report_ids: List[uuid.UUID] = Field(default_factory=list)
    relationships: List[PatternRelationshipEvidence] = Field(default_factory=list)
    shared_dimensions: Dict[str, List[str]] = Field(default_factory=dict)
    supporting_locations: List[str] = Field(default_factory=list)
    supporting_lsr_codes: List[str] = Field(default_factory=list)
    first_observed_at: Optional[datetime] = None
    last_observed_at: Optional[datetime] = None
    similarity_summary: PatternSimilaritySummary
    explanation: str = Field(..., description="Deterministic structured explanation generated from evidence")


class RecurringPrecursorPattern(BaseModel):
    """Canonical domain representation of a multi-report recurring precursor pattern."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    pattern_key: str = Field(..., description="Deterministic stable semantic pattern identifier")
    title: str = Field(..., description="Descriptive title of the systemic recurring pattern")
    description: str = Field(..., description="Deterministic plain-language explanation of why reports grouped")
    hazard_category: Optional[str] = None
    activity_type: Optional[str] = None
    failed_barrier_type: Optional[str] = None
    lsr_code: Optional[str] = None
    representative_precursor: StructuredSIFPrecursor
    supporting_report_count: int = Field(..., ge=1)
    supporting_report_ids: List[uuid.UUID] = Field(default_factory=list)
    supporting_lsr_codes: List[str] = Field(default_factory=list)
    supporting_locations: List[str] = Field(default_factory=list)
    first_observed_at: datetime
    last_observed_at: datetime
    similarity_summary: Dict[str, Any] = Field(default_factory=dict)
    evidence_summary: Dict[str, Any] = Field(default_factory=dict)
    discovery_method: str = Field(default="HYBRID_SIMILARITY_GROUPING_V1")
    status: PatternStatus = Field(default=PatternStatus.CANDIDATE)
