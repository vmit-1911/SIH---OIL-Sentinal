"""Pydantic schemas for HSE officer audit review, triage lifecycle, and audit trail."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.domain.enums import (
    PotentialOutcome,
    ReviewAuditEventType,
    ReviewDecision,
    ReviewFeedbackCategory,
    ReviewState,
    ReviewStatus,
    SIFClassification,
)


class PrecursorCorrectionRequest(BaseModel):
    """Partial or full correction payload for the 7 precursor dimensions."""
    hazard: Optional[Dict[str, Any]] = Field(default=None, description="Corrected hazard category and description")
    activity: Optional[Dict[str, Any]] = Field(default=None, description="Corrected activity type and context")
    barrier_failure: Optional[Dict[str, Any]] = Field(default=None, description="Corrected barrier failure type and status")
    exposure: Optional[Dict[str, Any]] = Field(default=None, description="Corrected human/process exposure details")
    potential_consequence: Optional[Dict[str, Any]] = Field(default=None, description="Corrected potential outcome severity and details")
    life_saving_rule: Optional[Dict[str, Any]] = Field(default=None, description="Corrected Life-Saving Rule mapping")
    location: Optional[Dict[str, Any]] = Field(default=None, description="Corrected location or operational facility")


class ReviewFeedbackRequest(BaseModel):
    """Structured feedback error tagging for calibration analysis."""
    category: ReviewFeedbackCategory = Field(..., description="Feedback categorization")
    notes: Optional[str] = Field(default=None, description="Detailed explanatory feedback on the AI error")
    specific_error_details: Optional[Dict[str, Any]] = Field(default=None, description="Targeted field or dimension breakdown")


class ReviewFeedbackResponse(BaseModel):
    """Persisted review feedback details."""
    category: ReviewFeedbackCategory
    notes: Optional[str] = None
    specific_error_details: Optional[Dict[str, Any]] = None


class ReviewClaimRequest(BaseModel):
    """Payload to claim a review item from the triage queue."""
    reviewer_id: str = Field(..., min_length=1, description="Username or badge ID of the claiming HSE officer")
    reviewer_role: Optional[str] = Field(default=None, description="Designation/role of the reviewer")


class ReviewDecisionRequest(BaseModel):
    """Submission payload for an authoritative HSE review decision and corrections."""
    reviewer_id: str = Field(..., min_length=1, description="Username or badge ID of the reviewing HSE officer")
    reviewer_role: Optional[str] = Field(default=None, description="Designation/role of the reviewer")
    decision: ReviewDecision = Field(..., description="Review decision: CONFIRM_AI, CORRECT, REJECT_AI, MARK_UNDETERMINED")
    final_classification: Optional[SIFClassification] = Field(default=None, description="Verified or overridden SIF classification")
    final_structured_precursor: Optional[PrecursorCorrectionRequest] = Field(default=None, description="Corrected precursor dimensions")
    final_lsr_code: Optional[str] = Field(default=None, description="Verified or corrected Life-Saving Rule code")
    reviewer_rationale: Optional[str] = Field(default=None, description="Mandatory rationale when changing AI assessment values")
    reviewer_notes: Optional[str] = Field(default=None, description="Operational notes or follow-up recommendations")
    feedback: Optional[ReviewFeedbackRequest] = Field(default=None, description="Structured calibration feedback")


class ReviewReopenRequest(BaseModel):
    """Payload to reopen a previously completed review."""
    reviewer_id: str = Field(..., min_length=1, description="Username or badge ID of the HSE officer reopening the item")
    reviewer_role: Optional[str] = Field(default=None, description="Role of the reviewer")
    reopen_rationale: str = Field(..., min_length=1, description="Mandatory explanation for reopening a completed review")


class ReviewAuditEventResponse(BaseModel):
    """Audit trail record of a review lifecycle action."""
    id: UUID
    review_id: UUID
    actor_id: str
    actor_role: Optional[str] = None
    event_type: ReviewAuditEventType
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    changed_fields: Optional[List[str]] = None
    rationale: Optional[str] = None
    created_at: datetime


class ReviewDetailResponse(BaseModel):
    """Full detail of a triage review, including report, AI baseline, corrections, and audit history."""
    id: UUID
    report_id: UUID
    assessment_id: Optional[UUID] = None
    status: ReviewState
    decision: Optional[ReviewDecision] = None
    reviewer_id: Optional[str] = None
    reviewer_role: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    original_classification: SIFClassification
    final_classification: Optional[SIFClassification] = None
    original_structured_precursor: Optional[Dict[str, Any]] = None
    final_structured_precursor: Optional[Dict[str, Any]] = None
    original_lsr_code: Optional[str] = None
    final_lsr_code: Optional[str] = None
    reviewer_rationale: Optional[str] = None
    reviewer_notes: Optional[str] = None
    feedback: Optional[ReviewFeedbackResponse] = None
    version: int
    created_at: datetime
    updated_at: datetime
    report_narrative: Optional[str] = None
    reported_location: Optional[str] = None
    source_type: Optional[str] = None
    event_timestamp: Optional[datetime] = None
    recent_audit_events: List[ReviewAuditEventResponse] = Field(default_factory=list)


class TriageQueueItem(BaseModel):
    """Summary item in the triage queue."""
    review_id: UUID
    report_id: UUID
    assessment_id: Optional[UUID] = None
    status: ReviewState
    decision: Optional[ReviewDecision] = None
    reviewer_id: Optional[str] = None
    classification: SIFClassification
    life_saving_rule: Optional[str] = None
    reported_location: Optional[str] = None
    source_type: str
    event_timestamp: Optional[datetime] = None
    created_at: datetime
    batch_id: Optional[UUID] = None


class TriageQueueResponse(BaseModel):
    """Paginated triage queue response."""
    items: List[TriageQueueItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class ReviewAnalyticsSummary(BaseModel):
    """Descriptive audit statistics of human-in-the-loop review actions."""
    total_reviews: int
    pending_count: int
    in_review_count: int
    reviewed_count: int
    confirmations_count: int
    corrections_count: int
    rejections_count: int
    undetermined_count: int
    classification_corrections_count: int
    lsr_corrections_count: int
    precursor_corrections_count: int
    feedback_breakdown: Dict[str, int]
    disclaimer: str = (
        "Descriptive audit statistics of HSE human-in-the-loop review actions only. "
        "Not a calibrated statistical model accuracy or precision metric."
    )


# Backward-compatible schemas for Phase 0 endpoints
class HumanReviewRequest(BaseModel):
    """Legacy review submission payload."""
    reviewer_id: str = Field(..., description="ID or username of the reviewing HSE officer")
    verified_sif_classification: SIFClassification = Field(..., description="Auditor verified SIF status")
    verified_potential_severity: Optional[PotentialOutcome] = Field(
        default=None,
        description="Auditor verified potential consequence severity",
    )
    verified_life_saving_rule: Optional[str] = Field(
        default=None,
        description="Auditor verified Life-Saving Rule code",
    )
    override_reason: Optional[str] = Field(
        default=None,
        description="Explanation if overriding the automated screening decision",
    )
    reviewer_notes: Optional[str] = Field(
        default=None,
        description="Operational context or corrective actions taken",
    )
    review_status: ReviewStatus = Field(
        default=ReviewStatus.VALIDATED,
        description="Review status: VALIDATED or OVERRIDDEN",
    )


class HumanReviewResponse(BaseModel):
    """Legacy response returned after recording auditor review."""
    report_id: UUID
    review_id: UUID
    status: ReviewStatus
    updated_at: datetime
