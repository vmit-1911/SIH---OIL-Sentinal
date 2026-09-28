"""Pydantic schemas for recurring precursor patterns and systemic clusters."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.domain.enums import PatternStatus
from app.schemas.precursor import StructuredPrecursor


class PrecursorPatternDTO(BaseModel):
    """Details of an identified recurring precursor pattern."""
    id: UUID
    pattern_code: str = Field(..., description="Unique pattern identifier (e.g. PAT_LSR_03_SUSPENDED_LOAD_RIGGING_FAILURE)")
    title: str = Field(..., description="Canonical descriptive title of the systemic failure mode")
    description: str = Field(..., description="Detailed description or explanation of the pattern")
    hazard_category: Optional[str] = None
    activity_type: Optional[str] = None
    failed_barrier_type: Optional[str] = None
    lsr_code: Optional[str] = None
    occurrence_count: int = Field(default=1, ge=1)
    affected_locations: List[str] = Field(default_factory=list)
    supporting_report_ids: List[UUID] = Field(default_factory=list)
    supporting_lsr_codes: List[str] = Field(default_factory=list)
    representative_precursor: Optional[StructuredPrecursor] = None
    similarity_summary: Optional[Dict[str, Any]] = None
    evidence_summary: Optional[Dict[str, Any]] = None
    similarity_weights: Optional[Dict[str, Any]] = None
    discovery_method: str = Field(default="HYBRID_SIMILARITY_GROUPING_V1")
    status: PatternStatus = Field(default=PatternStatus.CANDIDATE)
    first_detected_at: datetime
    last_detected_at: datetime


class PrecursorPatternListResponse(BaseModel):
    """List response for recurring precursor pattern discovery."""
    total_patterns: int = Field(..., ge=0)
    patterns: List[PrecursorPatternDTO]


class PatternDiscoveryResponse(BaseModel):
    """Execution summary of an automated recurring precursor pattern discovery run."""
    run_id: UUID
    discovery_method: str = Field(default="HYBRID_SIMILARITY_GROUPING_V1")
    candidates_evaluated: int = Field(..., ge=0)
    relationships_identified: int = Field(..., ge=0)
    qualifying_groups_found: int = Field(..., ge=0)
    patterns_created: int = Field(..., ge=0)
    patterns_updated: int = Field(..., ge=0)
    assessments_assigned: int = Field(..., ge=0)
    discovered_patterns: List[PrecursorPatternDTO] = Field(default_factory=list)
