"""Pydantic schemas and DTOs for Phase 10 HSE Command Center / Operational Intelligence API."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.domain.enums import (
    ActionCategory,
    ActionPriority,
    ActionSourceType,
    ActionStatus,
    ActualOutcome,
    CasePriority,
    CaseSourceType,
    CaseStatus,
    CaseType,
    ConcentrationDimension,
    ObservedTrend,
    PotentialOutcome,
    ReviewDecision,
    ReviewState,
    SIFClassification,
    SourceType,
)


class ReportingPeriodDTO(BaseModel):
    """Reporting time window for aggregated metrics."""
    from_date: Optional[datetime] = Field(None, description="Start date of reporting window")
    to_date: Optional[datetime] = Field(None, description="End date of reporting window")


# ==============================================================================
# 1. COMMAND CENTER OVERVIEW DTO
# ==============================================================================


class CommandCenterOverview(BaseModel):
    """High-level descriptive overview of persisted SIF operational activity."""
    generated_at: datetime = Field(..., description="Timestamp when overview was generated")
    data_as_of: datetime = Field(..., description="Timestamp of latest underlying database state")
    reporting_period: Optional[ReportingPeriodDTO] = Field(None, description="Applied reporting period")
    
    total_reports: int = Field(0, ge=0, description="Total safety reports in period")
    total_assessments: int = Field(0, ge=0, description="Total SIF assessments evaluated")
    potential_sif_count: int = Field(0, ge=0, description="Assessments classified as POTENTIAL_SIF")
    non_sif_count: int = Field(0, ge=0, description="Assessments classified as NON_SIF")
    undetermined_count: int = Field(0, ge=0, description="Assessments classified as UNDETERMINED")
    
    reviewed_count: int = Field(0, ge=0, description="Assessments with completed human HSE review")
    unreviewed_count: int = Field(0, ge=0, description="Assessments pending human HSE review")
    
    open_action_count: int = Field(0, ge=0, description="HSE action recommendations in OPEN, ACKNOWLEDGED, or IN_PROGRESS state")
    active_case_count: int = Field(0, ge=0, description="HSE cases in OPEN, TRIAGE, INVESTIGATING, ACTION_REQUIRED, or PENDING_VERIFICATION")
    recurring_pattern_count: int = Field(0, ge=0, description="Active recurring precursor patterns discovered")
    concentration_count: int = Field(0, ge=0, description="Active risk concentrations observed")

    summary_sources: Dict[str, str] = Field(
        default_factory=lambda: {
            "total_reports": "SafetyReport",
            "total_assessments": "SIFAssessment",
            "potential_sif_count": "SIFAssessment.sif_classification == POTENTIAL_SIF",
            "non_sif_count": "SIFAssessment.sif_classification == NON_SIF",
            "undetermined_count": "SIFAssessment.sif_classification == UNDETERMINED",
            "reviewed_count": "TriageReview.status == REVIEWED",
            "unreviewed_count": "TriageReview.status in (PENDING, IN_REVIEW)",
            "open_action_count": "HSEActionRecommendation.status in (OPEN, ACKNOWLEDGED, IN_PROGRESS)",
            "active_case_count": "HSECase.status not in (CLOSED, CANCELLED)",
            "recurring_pattern_count": "PrecursorPattern.status == ACTIVE",
            "concentration_count": "RiskConcentration.status == ACTIVE",
        },
        description="Explainability mapping showing authoritative source tables for each count",
    )


# ==============================================================================
# 2. SIF OVERVIEW DTO
# ==============================================================================


class MonthlyAssessmentTrendDTO(BaseModel):
    """Monthly aggregation of SIF assessments."""
    period: str = Field(..., description="Month formatted as YYYY-MM")
    total_assessments: int = Field(0, ge=0)
    potential_sif_count: int = Field(0, ge=0)
    non_sif_count: int = Field(0, ge=0)
    undetermined_count: int = Field(0, ge=0)


class SIFOverviewDTO(BaseModel):
    """Detailed descriptive breakdown of SIF assessments and outcomes."""
    generated_at: datetime
    reporting_period: Optional[ReportingPeriodDTO] = None
    total_assessments: int = Field(0, ge=0)
    classification_counts: Dict[str, int] = Field(default_factory=dict)
    actual_severity_counts: Dict[str, int] = Field(default_factory=dict)
    potential_severity_counts: Dict[str, int] = Field(default_factory=dict)
    reviewed_count: int = Field(0, ge=0)
    unreviewed_count: int = Field(0, ge=0)
    lsr_distribution: Dict[str, int] = Field(default_factory=dict)
    assessment_trend_by_month: List[MonthlyAssessmentTrendDTO] = Field(default_factory=list)
    sources: Dict[str, str] = Field(
        default_factory=lambda: {
            "classification": "SIFAssessment.sif_classification",
            "actual_severity": "SafetyReport.actual_severity",
            "potential_severity": "SIFAssessment.potential_severity",
            "reviews": "TriageReview.status",
            "lsr": "LSRReportMapping.rule_code",
        }
    )


# ==============================================================================
# 3. PRECURSOR INTELLIGENCE DTO
# ==============================================================================


class PatternSummaryDTO(BaseModel):
    """Summary of a single precursor pattern."""
    id: uuid.UUID
    pattern_code: str
    title: str
    description: str
    hazard_category: Optional[str] = None
    activity_type: Optional[str] = None
    failed_barrier_type: Optional[str] = None
    lsr_code: Optional[str] = None
    occurrence_count: int = Field(0, ge=0)
    affected_locations: List[str] = Field(default_factory=list)
    supporting_report_count: int = Field(0, ge=0)
    first_detected_at: datetime = Field(..., description="Timestamp when the pattern was first identified")


class DimensionMetricDTO(BaseModel):
    """Metric count for a specific categorical dimension value."""
    name: str
    count: int = Field(0, ge=0)


class PrecursorOverviewDTO(BaseModel):
    """Overview of recurring precursor patterns and multi-dimensional cluster distributions."""
    generated_at: datetime
    reporting_period: Optional[ReportingPeriodDTO] = None
    total_patterns: int = Field(0, ge=0)
    top_patterns: List[PatternSummaryDTO] = Field(default_factory=list)
    top_hazard_dimensions: List[DimensionMetricDTO] = Field(default_factory=list)
    top_barrier_failure_dimensions: List[DimensionMetricDTO] = Field(default_factory=list)
    top_activity_dimensions: List[DimensionMetricDTO] = Field(default_factory=list)
    supporting_locations: List[DimensionMetricDTO] = Field(default_factory=list)
    supporting_lsrs: List[DimensionMetricDTO] = Field(default_factory=list)
    sources: Dict[str, str] = Field(
        default_factory=lambda: {
            "patterns": "PrecursorPattern (Phase 2B persisted)",
            "dimensions": "PrecursorPattern and RiskConcentration (Phase 2B & 3 persisted)",
        }
    )


# ==============================================================================
# 4. CONCENTRATION OVERVIEW DTO
# ==============================================================================


class ConcentrationSummaryDTO(BaseModel):
    """Summary of a single risk concentration finding."""
    id: uuid.UUID
    concentration_key: str
    dimension_type: ConcentrationDimension
    dimension_value: str
    occurrence_count: int = Field(0, ge=0)
    distinct_report_count: int = Field(0, ge=0)
    distinct_location_count: int = Field(0, ge=0)
    observed_trend: ObservedTrend
    supporting_locations: List[str] = Field(default_factory=list)
    first_observed_at: datetime
    last_observed_at: datetime


class ConcentrationOverviewDTO(BaseModel):
    """Overview of risk concentrations across the 6 canonical dimensions."""
    generated_at: datetime
    reporting_period: Optional[ReportingPeriodDTO] = None
    total_concentrations: int = Field(0, ge=0)
    dimension_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Counts across exact canonical dimensions: PATTERN, HAZARD, BARRIER_FAILURE, ACTIVITY, LIFE_SAVING_RULE, LOCATION",
    )
    items: List[ConcentrationSummaryDTO] = Field(default_factory=list)
    limit: int
    offset: int
    sources: Dict[str, str] = Field(
        default_factory=lambda: {
            "concentrations": "RiskConcentration (Phase 3 persisted)",
            "dimensions": "ConcentrationDimension canonical enum",
        }
    )


# ==============================================================================
# 5. LSR OVERVIEW DTO
# ==============================================================================


class LSRDetailOverviewDTO(BaseModel):
    """Descriptive statistics for a single Life-Saving Rule."""
    rule_code: str
    rule_name: str
    assessment_count: int = Field(0, ge=0)
    potential_sif_count: int = Field(0, ge=0)
    reviewed_count: int = Field(0, ge=0)
    open_action_count: int = Field(0, ge=0)


class LSROverviewDTO(BaseModel):
    """Descriptive distribution across Life-Saving Rules."""
    generated_at: datetime
    reporting_period: Optional[ReportingPeriodDTO] = None
    total_lsr_rules: int = Field(0, ge=0)
    rules: List[LSRDetailOverviewDTO] = Field(default_factory=list)
    sources: Dict[str, str] = Field(
        default_factory=lambda: {
            "rules": "LSRTaxonomy / LSRReportMapping / SIFAssessment / TriageReview / HSEActionRecommendation",
        }
    )


# ==============================================================================
# 6. ACTION OVERVIEW DTO
# ==============================================================================


class ActionOverviewDTO(BaseModel):
    """Overview of Phase 8 HSE action recommendations."""
    generated_at: datetime
    reporting_period: Optional[ReportingPeriodDTO] = None
    total_actions: int = Field(0, ge=0)
    status_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Counts by ActionStatus (OPEN, ACKNOWLEDGED, IN_PROGRESS, COMPLETED, DISMISSED)",
    )
    category_distribution: Dict[str, int] = Field(default_factory=dict)
    priority_distribution: Dict[str, int] = Field(default_factory=dict)
    source_type_distribution: Dict[str, int] = Field(default_factory=dict)
    open_actions_by_age: Dict[str, int] = Field(
        default_factory=dict,
        description="Age breakdown of open actions (< 7 days, 7-30 days, > 30 days) calculated from persisted created_at",
    )
    sources: Dict[str, str] = Field(
        default_factory=lambda: {
            "actions": "HSEActionRecommendation (Phase 8 persisted)",
        }
    )


# ==============================================================================
# 7. CASE OVERVIEW DTO
# ==============================================================================


class CaseSummaryItemDTO(BaseModel):
    """Compact summary of an individual HSE case."""
    id: uuid.UUID
    case_key: str
    title: str
    case_type: CaseType
    status: CaseStatus
    priority: CasePriority
    owner: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CaseOverviewDTO(BaseModel):
    """Overview of Phase 9 HSE investigation cases."""
    generated_at: datetime
    reporting_period: Optional[ReportingPeriodDTO] = None
    total_cases: int = Field(0, ge=0)
    status_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Counts by CaseStatus (OPEN, TRIAGE, INVESTIGATING, ACTION_REQUIRED, PENDING_VERIFICATION, CLOSED, CANCELLED)",
    )
    case_type_distribution: Dict[str, int] = Field(default_factory=dict)
    priority_distribution: Dict[str, int] = Field(default_factory=dict)
    owner_distribution: Dict[str, int] = Field(default_factory=dict)
    active_case_count: int = Field(0, ge=0)
    recently_updated_cases: List[CaseSummaryItemDTO] = Field(default_factory=list)
    sources: Dict[str, str] = Field(
        default_factory=lambda: {
            "cases": "HSECase (Phase 9 persisted)",
        }
    )


# ==============================================================================
# 8. REVIEW QUEUE OVERVIEW DTO
# ==============================================================================


class ReviewQueueOverviewDTO(BaseModel):
    """Overview of Phase 5 human triage and review workload."""
    generated_at: datetime
    reporting_period: Optional[ReportingPeriodDTO] = None
    total_reviews: int = Field(0, ge=0)
    pending_reviews: int = Field(0, ge=0)
    in_review_count: int = Field(0, ge=0)
    reviewed_count: int = Field(0, ge=0)
    decision_distribution: Dict[str, int] = Field(default_factory=dict)
    feedback_category_distribution: Dict[str, int] = Field(default_factory=dict)
    age_of_pending_reviews: Dict[str, int] = Field(
        default_factory=dict,
        description="Age breakdown of PENDING reviews based on persisted created_at (< 7 days, 7-30 days, > 30 days)",
    )
    sources: Dict[str, str] = Field(
        default_factory=lambda: {
            "reviews": "TriageReview (Phase 5 persisted)",
        }
    )


# ==============================================================================
# 9. INVESTIGATION SNAPSHOT DTO
# ==============================================================================


class SnapshotReportNode(BaseModel):
    """Report node in the operational chain."""
    id: uuid.UUID
    report_ref: str
    source_type: SourceType
    reported_location: Optional[str] = None
    created_at: datetime


class SnapshotAssessmentNode(BaseModel):
    """Assessment node in the operational chain."""
    id: uuid.UUID
    report_id: uuid.UUID
    sif_classification: SIFClassification
    potential_severity: PotentialOutcome
    evidence_score: float
    precursor_signature: Optional[str] = None


class SnapshotPatternNode(BaseModel):
    """Pattern node in the operational chain."""
    id: uuid.UUID
    pattern_code: str
    title: str
    occurrence_count: int


class SnapshotConcentrationNode(BaseModel):
    """Concentration node in the operational chain."""
    id: uuid.UUID
    concentration_key: str
    dimension_type: ConcentrationDimension
    dimension_value: str
    occurrence_count: int


class SnapshotReviewNode(BaseModel):
    """Review node in the operational chain."""
    id: uuid.UUID
    report_id: uuid.UUID
    status: ReviewState
    decision: Optional[ReviewDecision] = None
    reviewer_id: Optional[str] = None


class SnapshotActionNode(BaseModel):
    """Action node in the operational chain."""
    id: uuid.UUID
    action_key: str
    action_title: str
    status: ActionStatus
    priority: ActionPriority


class SnapshotCaseNode(BaseModel):
    """Case node in the operational chain."""
    id: uuid.UUID
    case_key: str
    title: str
    status: CaseStatus
    priority: CasePriority


class InvestigationSnapshotDTO(BaseModel):
    """Compact operational chain linking related reports, assessments, patterns, concentrations, reviews, actions, and cases."""
    generated_at: datetime
    query_target: Dict[str, Optional[str]]
    reports: List[SnapshotReportNode] = Field(default_factory=list)
    assessments: List[SnapshotAssessmentNode] = Field(default_factory=list)
    patterns: List[SnapshotPatternNode] = Field(default_factory=list)
    concentrations: List[SnapshotConcentrationNode] = Field(default_factory=list)
    reviews: List[SnapshotReviewNode] = Field(default_factory=list)
    actions: List[SnapshotActionNode] = Field(default_factory=list)
    cases: List[SnapshotCaseNode] = Field(default_factory=list)
    summary: Dict[str, int] = Field(default_factory=dict)
