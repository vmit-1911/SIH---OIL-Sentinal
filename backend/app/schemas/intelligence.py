"""Pydantic schemas for Phase 7 HSE intelligence, evidence graph, explainability, and investigation context."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.domain.enums import (
    ActualOutcome,
    ConcentrationDimension,
    ConcentrationStatus,
    DerivationType,
    EvidenceStrength,
    ObservedTrend,
    PotentialOutcome,
    SIFClassification,
    SourceType,
    TriageStatus,
)
from app.schemas.analytics import RiskConcentrationDTO
from app.schemas.assessment import (
    EvidenceSpanDTO,
    PotentialOutcomeDTO,
    ScoringBreakdownDTO,
)
from app.schemas.pattern import PrecursorPatternDTO
from app.schemas.precursor import (
    PrecursorFieldProvenanceDTO,
    StructuredPrecursor,
)
from app.schemas.review import (
    ReviewAuditEventResponse,
    ReviewDetailResponse,
)
from app.schemas.taxonomy import LSRMappingDTO


class EvidenceType(str, Enum):
    """Normalized categorical evidence types for traceability."""
    HAZARD = "HAZARD"
    ACTIVITY = "ACTIVITY"
    ENERGY = "ENERGY"
    EXPOSURE = "EXPOSURE"
    BARRIER = "BARRIER"
    CONSEQUENCE = "CONSEQUENCE"
    LSR = "LSR"
    LOCATION = "LOCATION"
    PEOPLE_ROLE = "PEOPLE_ROLE"
    UNSAFE_ACT = "UNSAFE_ACT"
    UNSAFE_CONDITION = "UNSAFE_CONDITION"
    OTHER = "OTHER"


class EvidenceItemDTO(BaseModel):
    """Normalized evidence item representing a verified factual span or attribute."""
    evidence_id: str = Field(..., description="Deterministic unique evidence identifier")
    assessment_id: Optional[UUID] = Field(default=None, description="Associated SIF assessment UUID")
    report_id: Optional[UUID] = Field(default=None, description="Associated source report UUID")
    evidence_type: EvidenceType = Field(..., description="Categorical evidence classification")
    source_text: str = Field(..., description="Exact substring matched in the raw narrative")
    start_offset: Optional[int] = Field(default=None, description="Start character offset in narrative")
    end_offset: Optional[int] = Field(default=None, description="End character offset in narrative")
    normalized_concept: Optional[str] = Field(default=None, description="Canonical domain concept name")
    dimension: Optional[str] = Field(default=None, description="Associated precursor dimension if applicable")
    derivation_type: Optional[DerivationType] = Field(default=None, description="Origin: DIRECT_MATCH, RULE_INFERENCE, etc.")
    provenance_rule: Optional[str] = Field(default=None, description="Rule ID or lexicon pattern establishing this evidence")
    strength: Optional[EvidenceStrength] = Field(default=None, description="Evidence strength rating")
    is_negated: bool = Field(default=False, description="Whether the evidence item was linguistically negated in context")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Supplementary domain attributes")


class ReportEvidenceListResponse(BaseModel):
    """List of all evidence items associated with a report and its assessment."""
    report_id: UUID
    assessment_id: Optional[UUID] = None
    total_evidence_items: int
    evidence_items: List[EvidenceItemDTO] = Field(default_factory=list)


class FactorExplanationDTO(BaseModel):
    """Factual breakdown of an individual SIF screening evidence factor."""
    factor_name: str
    present: bool
    evidence_strength: EvidenceStrength
    contribution_score: float
    evidence_items: List[str] = Field(default_factory=list)
    evidence_spans: List[EvidenceSpanDTO] = Field(default_factory=list)


class TriggeredRuleDTO(BaseModel):
    """Provenance record of a deterministic SIF screening rule triggered."""
    rule_id: str
    description: str
    evidence_spans: List[EvidenceSpanDTO] = Field(default_factory=list)
    derivation_type: DerivationType = DerivationType.RULE_INFERENCE


class ScreeningExplanationDTO(BaseModel):
    """Structured, explainable justification for a deterministic SIF assessment."""
    report_id: UUID
    assessment_id: UUID
    classification: SIFClassification
    evidence_score: float = Field(..., ge=0.0, le=1.0)
    evidence_strength: EvidenceStrength
    rule_based_screening_score: float = Field(..., ge=0.0, le=1.0)
    primary_reasoning: str
    factors: Dict[str, FactorExplanationDTO] = Field(default_factory=dict)
    triggered_rules: List[TriggeredRuleDTO] = Field(default_factory=list)
    evidence_spans: List[EvidenceSpanDTO] = Field(default_factory=list)
    potential_consequence: Optional[PotentialOutcomeDTO] = None
    primary_lsr: Optional[LSRMappingDTO] = None
    structured_precursor: Optional[StructuredPrecursor] = None
    precursor_provenance: Dict[str, PrecursorFieldProvenanceDTO] = Field(default_factory=dict)


class AssessmentSimilarReportDTO(BaseModel):
    """Pairwise similarity explanation between target assessment and another historical assessment."""
    target_assessment_id: UUID
    matched_assessment_id: UUID
    matched_report_id: UUID
    matched_report_ref: str
    matched_narrative: str
    matched_location: Optional[str] = None
    matched_sif_classification: Optional[SIFClassification] = None
    hybrid_score: float = Field(..., ge=0.0, le=1.0, description="Weighted hybrid similarity score")
    structured_score: Optional[float] = Field(default=None, description="7D structured dimension similarity score")
    semantic_score: Optional[float] = Field(default=None, description="Dense embedding cosine similarity score")
    similarity_mode: str = Field(..., description="Scoring mode: FULL_HYBRID, STRUCTURED_ONLY_FALLBACK, etc.")
    dimension_scores: Dict[str, Optional[float]] = Field(default_factory=dict, description="Dimension-by-dimension similarity breakdown")
    matching_dimensions: List[str] = Field(default_factory=list, description="List of precursor dimensions with strong alignment")
    missing_dimensions: List[str] = Field(default_factory=list, description="List of dimensions missing in either precursor")


class AssessmentSimilarityResponse(BaseModel):
    """List of historically similar safety reports with multi-modal similarity explanations."""
    assessment_id: UUID
    report_id: UUID
    total_similar_reports: int
    similar_reports: List[AssessmentSimilarReportDTO] = Field(default_factory=list)


class AssessmentPatternResponse(BaseModel):
    """Recurring pattern association and co-membership for an assessment."""
    assessment_id: UUID
    report_id: UUID
    has_pattern: bool
    pattern: Optional[PrecursorPatternDTO] = None
    co_members_count: int = 0
    co_member_report_ids: List[UUID] = Field(default_factory=list)
    message: Optional[str] = None


class PatternSupportingReportEvidenceDTO(BaseModel):
    """Traceable underlying safety report contributing to a precursor pattern."""
    report_id: UUID
    report_ref: str
    location: Optional[str] = None
    department: Optional[str] = None
    narrative: str
    event_timestamp: Optional[datetime] = None
    assessment_id: UUID
    sif_classification: SIFClassification
    evidence_score: float
    structured_precursor: Optional[StructuredPrecursor] = None


class PatternEvidenceResponse(BaseModel):
    """Full evidence and supporting report traceability for a recurring precursor pattern."""
    pattern_id: UUID
    pattern_code: str
    title: str
    description: str
    hazard_category: Optional[str] = None
    activity_type: Optional[str] = None
    failed_barrier_type: Optional[str] = None
    lsr_code: Optional[str] = None
    occurrence_count: int
    affected_locations: List[str] = Field(default_factory=list)
    supporting_report_ids: List[UUID] = Field(default_factory=list)
    supporting_lsr_codes: List[str] = Field(default_factory=list)
    representative_precursor: Optional[StructuredPrecursor] = None
    temporal_range: Dict[str, Optional[datetime]] = Field(default_factory=dict)
    similarity_summary: Optional[Dict[str, Any]] = None
    cohesion_evidence: Optional[Dict[str, Any]] = None
    discovery_method: str
    status: str
    supporting_reports: List[PatternSupportingReportEvidenceDTO] = Field(default_factory=list)


class ConcentrationSupportingReportDTO(BaseModel):
    """Traceable safety report underlying a risk concentration finding."""
    report_id: UUID
    report_ref: str
    location: Optional[str] = None
    department: Optional[str] = None
    narrative: str
    event_timestamp: Optional[datetime] = None
    sif_classification: Optional[SIFClassification] = None
    structured_precursor: Optional[StructuredPrecursor] = None


class ConcentrationEvidenceResponse(BaseModel):
    """Full explainable evidence and underlying reports for a SIF risk concentration."""
    concentration_key: str
    dimension_type: ConcentrationDimension
    dimension_value: str
    pattern_id: Optional[UUID] = None
    occurrence_count: int
    distinct_report_count: int
    distinct_location_count: int
    first_observed_at: datetime
    last_observed_at: datetime
    observed_trend: ObservedTrend
    temporal_distribution: Dict[str, int] = Field(default_factory=dict)
    supporting_report_ids: List[UUID] = Field(default_factory=list)
    supporting_pattern_ids: List[UUID] = Field(default_factory=list)
    supporting_locations: List[str] = Field(default_factory=list)
    supporting_lsr_codes: List[str] = Field(default_factory=list)
    evidence_summary: Dict[str, Any] = Field(default_factory=dict)
    calculation_method: str
    status: ConcentrationStatus
    supporting_reports: List[ConcentrationSupportingReportDTO] = Field(default_factory=list)


class SIFInvestigationContextReportDTO(BaseModel):
    """Report baseline within the investigation context."""
    id: UUID
    report_ref: str
    source_type: SourceType
    reported_location: Optional[str] = None
    reported_department: Optional[str] = None
    actual_severity: ActualOutcome
    raw_text: str
    event_timestamp: Optional[datetime] = None
    created_at: datetime


class SIFInvestigationContextAssessmentDTO(BaseModel):
    """Assessment baseline within the investigation context."""
    id: UUID
    report_id: UUID
    sif_classification: SIFClassification
    evidence_score: float
    evidence_strength: EvidenceStrength
    rule_based_screening_score: float
    potential_severity: Optional[PotentialOutcome] = None
    triage_status: TriageStatus
    pattern_id: Optional[UUID] = None
    assessed_at: datetime


class SIFInvestigationContextResponse(BaseModel):
    """Consolidated 10-dimension HSE investigation context combining raw report through audit history."""
    report: SIFInvestigationContextReportDTO
    assessment: Optional[SIFInvestigationContextAssessmentDTO] = None
    evidence: List[EvidenceItemDTO] = Field(default_factory=list)
    screening: Optional[ScreeningExplanationDTO] = None
    precursor: Optional[StructuredPrecursor] = None
    precursor_provenance: Dict[str, PrecursorFieldProvenanceDTO] = Field(default_factory=dict)
    similar_reports: List[AssessmentSimilarReportDTO] = Field(default_factory=list)
    pattern: Optional[PrecursorPatternDTO] = None
    concentrations: List[RiskConcentrationDTO] = Field(default_factory=list)
    review: Optional[ReviewDetailResponse] = None
    audit_history: List[ReviewAuditEventResponse] = Field(default_factory=list)
