"""Unit tests for Phase 5 Human-in-the-Loop review lifecycle, transitions, audit trail, and models."""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    InvalidStateTransitionException,
    ReviewConflictException,
    ReviewNotFoundException,
    ReviewRationaleRequiredException,
)
from app.db.models.assessment import SIFAssessment
from app.db.models.report import SafetyReport
from app.db.models.review import ReviewAuditEvent, TriageReview
from app.domain.enums import (
    ActualOutcome,
    EvidenceStrength,
    PotentialOutcome,
    ReviewAuditEventType,
    ReviewDecision,
    ReviewFeedbackCategory,
    ReviewState,
    SIFClassification,
    SourceType,
    TriageStatus,
)
from app.schemas.review import (
    PrecursorCorrectionRequest,
    ReviewClaimRequest,
    ReviewDecisionRequest,
    ReviewFeedbackRequest,
    ReviewReopenRequest,
)
from app.services.triage_service import TriageService


@pytest.fixture
async def sample_assessment_fixture(db_session: AsyncSession):
    """Create a sample SafetyReport and SIFAssessment fixture for unit tests."""
    report = SafetyReport(
        id=uuid.uuid4(),
        report_ref=f"OIL-TEST-REV-{uuid.uuid4().hex[:8]}",
        source_type=SourceType.NEAR_MISS,
        raw_text="Drill pipe slipped from elevator during hoisting at Rig 12; high-energy barrier failed.",
        reported_location="Rig-12",
        actual_severity=ActualOutcome.NO_INJURY,
    )
    db_session.add(report)
    await db_session.flush()

    assessment = SIFAssessment(
        id=uuid.uuid4(),
        report_id=report.id,
        sif_classification=SIFClassification.POTENTIAL_SIF,
        evidence_score=0.85,
        evidence_strength=EvidenceStrength.HIGH,
        rule_based_screening_score=0.90,
        potential_severity=PotentialOutcome.FATALITY,
        structured_precursor={
            "hazard": {"category": "FALLING_DROPPED_OBJECTS", "description": "Suspended drill pipe"},
            "activity": {"type": "HOISTING", "description": "Hoisting pipe"},
            "barrier_failure": {"type": "EQUIPMENT_INTEGRITY", "status": "FAILED"},
            "exposure": {"group": "RIG_CREW", "count": 2},
            "potential_consequence": {"severity": "FATALITY"},
            "life_saving_rule": {"rule_code": "ENERGY_ISOLATION"},
            "location": {"facility": "Rig-12"},
        },
        triage_status=TriageStatus.AUTO_SCREENED,
    )
    db_session.add(assessment)
    await db_session.flush()
    return report, assessment


@pytest.mark.asyncio
async def test_ensure_review_creates_pending_review_and_audit_event(db_session: AsyncSession, sample_assessment_fixture):
    """Verify ensure_review_for_assessment initializes PENDING state with captured AI snapshot and initial audit event."""
    report, assessment = sample_assessment_fixture
    service = TriageService(db_session)

    review = await service.ensure_review_for_assessment(assessment.id)
    assert review.id is not None
    assert review.status == ReviewState.PENDING
    assert review.original_classification == SIFClassification.POTENTIAL_SIF
    assert review.final_classification == SIFClassification.POTENTIAL_SIF
    assert review.original_lsr_code == "ENERGY_ISOLATION"
    assert review.version == 1

    # Verify initial audit event
    events = await service.get_review_history(review.id)
    assert len(events) == 1
    assert events[0].event_type == ReviewAuditEventType.REVIEW_CREATED
    assert events[0].actor_id == "system"


@pytest.mark.asyncio
async def test_claim_review_lifecycle(db_session: AsyncSession, sample_assessment_fixture):
    """Verify claiming transitions PENDING -> IN_REVIEW and emits REVIEW_CLAIMED audit event."""
    report, assessment = sample_assessment_fixture
    service = TriageService(db_session)
    review = await service.ensure_review_for_assessment(assessment.id)

    claim_req = ReviewClaimRequest(reviewer_id="AUDITOR_RAJESH", reviewer_role="SENIOR_HSE_AUDITOR")
    claimed_review = await service.claim_review(review.id, claim_req)

    assert claimed_review.status == ReviewState.IN_REVIEW
    assert claimed_review.reviewer_id == "AUDITOR_RAJESH"
    assert claimed_review.reviewer_role == "SENIOR_HSE_AUDITOR"
    assert claimed_review.started_at is not None
    assert claimed_review.version == 2

    # Verify audit event history
    events = await service.get_review_history(review.id)
    assert len(events) == 2
    assert events[1].event_type == ReviewAuditEventType.REVIEW_CLAIMED
    assert events[1].actor_id == "AUDITOR_RAJESH"


@pytest.mark.asyncio
async def test_claim_review_concurrency_conflict(db_session: AsyncSession, sample_assessment_fixture):
    """Verify attempting to claim an item already IN_REVIEW by another officer raises ReviewConflictException."""
    report, assessment = sample_assessment_fixture
    service = TriageService(db_session)
    review = await service.ensure_review_for_assessment(assessment.id)

    # First officer claims
    await service.claim_review(review.id, ReviewClaimRequest(reviewer_id="AUDITOR_A"))

    # Second officer attempts to claim
    with pytest.raises(ReviewConflictException) as exc_info:
        await service.claim_review(review.id, ReviewClaimRequest(reviewer_id="AUDITOR_B"))
    assert "already claimed by reviewer 'AUDITOR_A'" in str(exc_info.value)


@pytest.mark.asyncio
async def test_claim_review_idempotency_same_reviewer(db_session: AsyncSession, sample_assessment_fixture):
    """Verify re-claiming an active item by the SAME reviewer is idempotent and safe."""
    report, assessment = sample_assessment_fixture
    service = TriageService(db_session)
    review = await service.ensure_review_for_assessment(assessment.id)

    await service.claim_review(review.id, ReviewClaimRequest(reviewer_id="AUDITOR_A"))
    reclaimed = await service.claim_review(review.id, ReviewClaimRequest(reviewer_id="AUDITOR_A"))

    assert reclaimed.status == ReviewState.IN_REVIEW
    assert reclaimed.reviewer_id == "AUDITOR_A"


@pytest.mark.asyncio
async def test_confirm_ai_decision_lifecycle(db_session: AsyncSession, sample_assessment_fixture):
    """Verify CONFIRM_AI preserves AI assessment, marks VALIDATED, and records REVIEW_SUBMITTED."""
    report, assessment = sample_assessment_fixture
    service = TriageService(db_session)
    review = await service.ensure_review_for_assessment(assessment.id)
    await service.claim_review(review.id, ReviewClaimRequest(reviewer_id="AUDITOR_A"))

    decision_req = ReviewDecisionRequest(
        reviewer_id="AUDITOR_A",
        decision=ReviewDecision.CONFIRM_AI,
        reviewer_notes="Confirmed high-energy hazard and barrier failure.",
    )
    reviewed = await service.submit_decision(review.id, decision_req)

    assert reviewed.status == ReviewState.REVIEWED
    assert reviewed.decision == ReviewDecision.CONFIRM_AI
    assert reviewed.final_classification == SIFClassification.POTENTIAL_SIF
    assert reviewed.completed_at is not None

    # Assessment triage_status updated without changing original AI values
    assert assessment.triage_status == TriageStatus.VALIDATED
    assert assessment.sif_classification == SIFClassification.POTENTIAL_SIF
    assert assessment.evidence_score == 0.85


@pytest.mark.asyncio
async def test_correction_with_rationale_and_preservation(db_session: AsyncSession, sample_assessment_fixture):
    """Verify CORRECT updates final fields, emits fine-grained audit events, and leaves original AI assessment untouched."""
    report, assessment = sample_assessment_fixture
    service = TriageService(db_session)
    review = await service.ensure_review_for_assessment(assessment.id)
    await service.claim_review(review.id, ReviewClaimRequest(reviewer_id="AUDITOR_A"))

    correction_req = ReviewDecisionRequest(
        reviewer_id="AUDITOR_A",
        decision=ReviewDecision.CORRECT,
        final_classification=SIFClassification.ACTUAL_SIF,
        final_lsr_code="LINE_OF_FIRE",
        final_structured_precursor=PrecursorCorrectionRequest(
            hazard={"category": "LINE_OF_FIRE", "description": "Uncontrolled drill pipe trajectory"}
        ),
        reviewer_rationale="Field investigation confirmed worker suffered permanent hand injury (Actual SIF).",
        feedback=ReviewFeedbackRequest(
            category=ReviewFeedbackCategory.CLASSIFICATION_ERROR,
            notes="AI missed medical record indicating disabling injury",
        ),
    )
    reviewed = await service.submit_decision(review.id, correction_req)

    assert reviewed.status == ReviewState.REVIEWED
    assert reviewed.decision == ReviewDecision.CORRECT
    assert reviewed.final_classification == SIFClassification.ACTUAL_SIF
    assert reviewed.final_lsr_code == "LINE_OF_FIRE"
    assert reviewed.final_structured_precursor["hazard"]["category"] == "LINE_OF_FIRE"
    assert reviewed.original_classification == SIFClassification.POTENTIAL_SIF  # AI preserved in review
    assert reviewed.feedback_category == ReviewFeedbackCategory.CLASSIFICATION_ERROR

    # AI Assessment in DB remains preserved
    assert assessment.sif_classification == SIFClassification.POTENTIAL_SIF
    assert assessment.triage_status == TriageStatus.OVERRIDDEN

    # Audit trail contains fine-grained events
    events = await service.get_review_history(review.id)
    event_types = [e.event_type for e in events]
    assert ReviewAuditEventType.REVIEW_SUBMITTED in event_types
    assert ReviewAuditEventType.CLASSIFICATION_CORRECTED in event_types
    assert ReviewAuditEventType.LSR_CORRECTED in event_types
    assert ReviewAuditEventType.PRECURSOR_CORRECTED in event_types
    assert ReviewAuditEventType.AUDITOR_OVERRIDE in event_types


@pytest.mark.asyncio
async def test_override_requires_mandatory_rationale(db_session: AsyncSession, sample_assessment_fixture):
    """Verify attempting to override/correct AI without rationale raises ReviewRationaleRequiredException."""
    report, assessment = sample_assessment_fixture
    service = TriageService(db_session)
    review = await service.ensure_review_for_assessment(assessment.id)
    await service.claim_review(review.id, ReviewClaimRequest(reviewer_id="AUDITOR_A"))

    req = ReviewDecisionRequest(
        reviewer_id="AUDITOR_A",
        decision=ReviewDecision.REJECT_AI,
        final_classification=SIFClassification.NON_SIF,
        reviewer_rationale="",  # Empty rationale
    )
    with pytest.raises(ReviewRationaleRequiredException):
        await service.submit_decision(review.id, req)


@pytest.mark.asyncio
async def test_reopen_review_lifecycle(db_session: AsyncSession, sample_assessment_fixture):
    """Verify reopening transitions REVIEWED -> IN_REVIEW with mandatory rationale."""
    report, assessment = sample_assessment_fixture
    service = TriageService(db_session)
    review = await service.ensure_review_for_assessment(assessment.id)
    await service.claim_review(review.id, ReviewClaimRequest(reviewer_id="AUDITOR_A"))
    await service.submit_decision(
        review.id,
        ReviewDecisionRequest(
            reviewer_id="AUDITOR_A",
            decision=ReviewDecision.CONFIRM_AI,
        ),
    )
    assert review.status == ReviewState.REVIEWED

    # Reopen
    reopen_req = ReviewReopenRequest(
        reviewer_id="AUDITOR_B",
        reopen_rationale="New witness statement provides additional high-voltage hazard details.",
    )
    reopened = await service.reopen_review(review.id, reopen_req)

    assert reopened.status == ReviewState.IN_REVIEW
    assert reopened.reviewer_id == "AUDITOR_B"
    assert reopened.completed_at is None

    events = await service.get_review_history(review.id)
    assert events[-1].event_type == ReviewAuditEventType.REVIEW_REOPENED
    assert events[-1].rationale == "New witness statement provides additional high-voltage hazard details."


@pytest.mark.asyncio
async def test_invalid_reopen_on_pending_item(db_session: AsyncSession, sample_assessment_fixture):
    """Verify attempting to reopen an unreviewed (PENDING) item raises InvalidStateTransitionException."""
    report, assessment = sample_assessment_fixture
    service = TriageService(db_session)
    review = await service.ensure_review_for_assessment(assessment.id)

    with pytest.raises(InvalidStateTransitionException):
        await service.reopen_review(
            review.id,
            ReviewReopenRequest(reviewer_id="AUDITOR_A", reopen_rationale="Invalid attempt"),
        )
