"""Pydantic schemas for single report analysis, retrieval, and filtering."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.domain.enums import (
    ActualOutcome,
    PotentialOutcome,
    SIFClassification,
    SourceType,
    TriageStatus,
)
from app.schemas.assessment import (
    ActualOutcomeDTO,
    ExplainabilityDTO,
    PotentialOutcomeDTO,
    ScoringBreakdownDTO,
)
from app.schemas.precursor import StructuredPrecursor
from app.schemas.taxonomy import LSRMappingDTO


class SingleReportAnalysisRequest(BaseModel):
    """Request payload for synchronous single report analysis."""
    raw_text: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description="Free-text narrative of the safety observation, near miss, or incident",
    )
    source_type: SourceType = Field(
        default=SourceType.NEAR_MISS,
        description="Report classification: UA, UC, NEAR_MISS, INCIDENT",
    )
    reported_location: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Operational location (e.g. Rig-04 / Moran Field)",
    )
    reported_department: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Department or operating discipline",
    )
    actual_severity: ActualOutcome = Field(
        default=ActualOutcome.NO_INJURY,
        description="Reported actual injury severity",
    )
    event_timestamp: Optional[datetime] = Field(
        default=None,
        description="When the observation or incident occurred (ISO-8601)",
    )


class SimilarReportDTO(BaseModel):
    """Summary of a historically similar safety report."""
    report_id: UUID
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    similarity_type: str = Field(default="HYBRID", description="HYBRID, SEMANTIC, or STRUCTURAL")
    summary: str
    location: Optional[str] = None
    event_timestamp: Optional[datetime] = None


class SingleReportAnalysisResponse(BaseModel):
    """Complete SIF Sentinel analysis response contract."""
    report_id: UUID
    sif_classification: SIFClassification
    actual_outcome: ActualOutcomeDTO
    potential_outcome: PotentialOutcomeDTO
    scoring: ScoringBreakdownDTO
    life_saving_rules: List[LSRMappingDTO] = Field(default_factory=list)
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)
    explainability: ExplainabilityDTO
    structured_precursor: Optional[StructuredPrecursor] = Field(
        default=None,
        description="Structured precursor representation (scoped for Phase 1D synthesis)",
    )
    precursor_signature: Optional[str] = None
    pattern_id: Optional[str] = None
    similar_reports: List[SimilarReportDTO] = Field(default_factory=list)
    triage_recommendation: str = Field(
        default="ROUTINE_LOGGING",
        description="Recommended action: ESCALATE_IMMEDIATE_INVESTIGATION, HSE_OFFICER_REVIEW, or ROUTINE_LOGGING",
    )


class ReportListItemDTO(BaseModel):
    """Summary item for paginated report queries."""
    id: UUID
    report_ref: str
    source_type: SourceType
    reported_location: Optional[str] = None
    actual_severity: ActualOutcome
    sif_classification: Optional[SIFClassification] = None
    evidence_score: Optional[float] = None
    potential_severity: Optional[PotentialOutcome] = None
    primary_lsr_code: Optional[str] = None
    triage_status: TriageStatus = TriageStatus.AUTO_SCREENED
    event_timestamp: Optional[datetime] = None
    created_at: datetime


class ReportFilterParams(BaseModel):
    """Query parameters for report search and filtering."""
    sif_classification: Optional[SIFClassification] = None
    source_type: Optional[SourceType] = None
    lsr_code: Optional[str] = None
    location: Optional[str] = None
    triage_status: Optional[TriageStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
