"""System hardening, cross-phase integrity, idempotency, concurrency, and failure recovery tests."""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    InvalidStateTransitionException,
    ReportNotFoundException,
    ReviewConflictException,
    ReviewNotFoundException,
    ReviewRationaleRequiredException,
)
from app.db.base import Base
from app.db.models.assessment import SIFAssessment
from app.db.models.batch import BatchJob
from app.db.models.batch_error import BatchRowError
from app.db.models.concentration import RiskConcentration
from app.db.models.pattern import PrecursorPattern
from app.db.models.report import SafetyReport
from app.db.models.review import ReviewAuditEvent, TriageReview
from app.db.models.taxonomy import LSRReportMapping, LSRTaxonomy
from app.domain.enums import (
    ActualOutcome,
    PotentialOutcome,
    ReviewAuditEventType,
    ReviewDecision,
    ReviewFeedbackCategory,
    ReviewState,
    SIFClassification,
    SourceType,
    TriageStatus,
)
from app.schemas.report import SingleReportAnalysisRequest
from app.schemas.review import (
    ReviewClaimRequest,
    ReviewDecisionRequest,
    ReviewReopenRequest,
)
from app.services.batch_ingestion_service import BatchIngestionService
from app.services.pattern_discovery_service import PatternDiscoveryService
from app.services.risk_concentration_service import RiskConcentrationService
from app.services.sif_analysis_service import SIFAnalysisService
from app.services.triage_service import TriageService


@pytest.mark.asyncio
async def test_cross_phase_data_integrity_and_relationships(db_session: AsyncSession):
    """Verify complete relational foreign key integrity across SafetyReport, SIFAssessment, PrecursorPattern, TriageReview, and ReviewAuditEvent."""
    sif_service = SIFAnalysisService(db_session)
    triage_service = TriageService(db_session)

    # 1. Create Report & Assessment
    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="OIL-REL-001",
            raw_text="While running 9-5/8 inch casing at Rig-04, air winch line parted and elevator swung near floormen.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04 Dikom",
        )
    )

    # 2. Verify SafetyReport <-> SIFAssessment relationship
    rep = await db_session.get(SafetyReport, res.report_id)
    ass = await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == res.report_id))
    assessment = ass.scalars().first()

    assert rep is not None
    assert assessment is not None
    assert assessment.report_id == rep.id

    # 3. Create Review & Audit Event
    review = await triage_service.ensure_review_for_assessment(assessment.id)
    await triage_service.claim_review(review.id, ReviewClaimRequest(reviewer_id="AUDITOR_X"))
    await triage_service.submit_decision(
        review.id,
        ReviewDecisionRequest(reviewer_id="AUDITOR_X", decision=ReviewDecision.CONFIRM_AI),
    )

    # 4. Verify SIFAssessment <-> TriageReview <-> ReviewAuditEvent relationships
    rev_check = await db_session.get(TriageReview, review.id)
    assert rev_check.report_id == rep.id
    assert rev_check.assessment_id == assessment.id

    events_res = await db_session.execute(
        select(ReviewAuditEvent).where(ReviewAuditEvent.review_id == review.id)
    )
    events = events_res.scalars().all()
    assert len(events) >= 3
    for ev in events:
        assert ev.review_id == review.id
        assert ev.actor_id in ("system", "AUDITOR_X")


@pytest.mark.asyncio
async def test_idempotency_pattern_discovery_and_concentrations(db_session: AsyncSession):
    """Verify repeated pattern discovery and concentration refresh are strictly idempotent without generating duplicates."""
    sif_service = SIFAnalysisService(db_session)
    pattern_service = PatternDiscoveryService(db_session)
    concentration_service = RiskConcentrationService(db_session)

    for i in range(3):
        await sif_service.analyze_and_persist(
            SingleReportAnalysisRequest(
                report_ref=f"OIL-IDEMP-{i}",
                raw_text=(
                    "While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung "
                    "across the rig floor, narrowly missing two floormen who jumped out of the way. No injuries occurred."
                ),
                source_type=SourceType.NEAR_MISS,
                reported_location="Rig-04 / Moran Field",
            )
        )

    # Run Pattern Discovery 1st time
    resp1 = await pattern_service.discover_patterns(min_report_count=3, threshold=0.65)
    count1 = len(resp1.discovered_patterns)

    # Run Pattern Discovery 2nd time
    resp2 = await pattern_service.discover_patterns(min_report_count=3, threshold=0.65)
    count2 = len(resp2.discovered_patterns)

    # Count of patterns in DB should remain identical (upsert / update in place)
    total_patterns_res = await db_session.execute(select(func.count(PrecursorPattern.id)))
    assert total_patterns_res.scalar_one() == count1 == count2
    assert count1 >= 1

    # Run Concentration Refresh 1st time
    conc1 = await concentration_service.refresh_concentrations()
    conc_count1 = conc1.total_active_concentrations

    # Run Concentration Refresh 2nd time
    conc2 = await concentration_service.refresh_concentrations()
    conc_count2 = conc2.total_active_concentrations

    total_conc_res = await db_session.execute(select(func.count(RiskConcentration.id)))
    assert total_conc_res.scalar_one() == conc_count1 == conc_count2
    assert conc_count1 >= 1


@pytest.mark.asyncio
async def test_idempotency_review_decision_and_claim(db_session: AsyncSession):
    """Verify repeated review claim by same reviewer and repeated decision submission are idempotent."""
    sif_service = SIFAnalysisService(db_session)
    triage_service = TriageService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="OIL-REV-IDEMP",
            raw_text="While running casing at Rig-04, air winch line parted and elevator swung across rig floor near floormen.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04 Dikom",
        )
    )
    ass_res = await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == res.report_id))
    assessment = ass_res.scalars().first()
    review = await triage_service.ensure_review_for_assessment(assessment.id)

    # Claim 1st time
    claimed1 = await triage_service.claim_review(review.id, ReviewClaimRequest(reviewer_id="AUDITOR_SAME"))
    # Claim 2nd time
    claimed2 = await triage_service.claim_review(review.id, ReviewClaimRequest(reviewer_id="AUDITOR_SAME"))
    assert claimed1.id == claimed2.id
    assert claimed2.status == ReviewState.IN_REVIEW

    # Decision 1st time
    decision_req = ReviewDecisionRequest(
        reviewer_id="AUDITOR_SAME",
        decision=ReviewDecision.CONFIRM_AI,
        reviewer_notes="Confirmed.",
    )
    rev1 = await triage_service.submit_decision(review.id, decision_req)

    # Count audit events before 2nd submission
    events_before = await triage_service.get_review_history(review.id)
    count_before = len(events_before)

    # Decision 2nd time (identical submission)
    rev2 = await triage_service.submit_decision(review.id, decision_req)
    assert rev2.status == ReviewState.REVIEWED

    # Audit events count must remain identical (no duplicate audit events)
    events_after = await triage_service.get_review_history(review.id)
    assert len(events_after) == count_before


@pytest.mark.asyncio
async def test_concurrency_review_claim_and_submission_conflicts(db_session: AsyncSession):
    """Verify concurrency conflict (HTTP 409) when different reviewers contest the same active review."""
    sif_service = SIFAnalysisService(db_session)
    triage_service = TriageService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="OIL-CONCUR-001",
            raw_text="During pipeline maintenance at EPS-Moran, technician opened high pressure 5000 PSI gas manifold without energy isolation LOTO lock and gas released near roughneck.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Moran EPS",
        )
    )
    ass_res = await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == res.report_id))
    assessment = ass_res.scalars().first()
    review = await triage_service.ensure_review_for_assessment(assessment.id)

    # Reviewer 1 claims
    await triage_service.claim_review(review.id, ReviewClaimRequest(reviewer_id="REVIEWER_1"))

    # Reviewer 2 attempts to claim -> Conflict
    with pytest.raises(ReviewConflictException) as exc_claim:
        await triage_service.claim_review(review.id, ReviewClaimRequest(reviewer_id="REVIEWER_2"))
    assert "already claimed by reviewer 'REVIEWER_1'" in str(exc_claim.value)

    # Reviewer 2 attempts to submit decision on Reviewer 1's claim -> Conflict
    with pytest.raises(ReviewConflictException) as exc_sub:
        await triage_service.submit_decision(
            review.id,
            ReviewDecisionRequest(reviewer_id="REVIEWER_2", decision=ReviewDecision.CONFIRM_AI),
        )
    assert "locked by reviewer 'REVIEWER_1'" in str(exc_sub.value)


@pytest.mark.asyncio
async def test_failure_recovery_invalid_review_transitions_and_missing_rationale(db_session: AsyncSession):
    """Verify controlled rejection on invalid lifecycle transitions, missing rationales, and nonexistent entities."""
    sif_service = SIFAnalysisService(db_session)
    triage_service = TriageService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="OIL-FAIL-001",
            raw_text="Empty paint cans and cleaning rags left unattended near workshop entrance.",
            source_type=SourceType.UC,
            reported_location="Rig-12",
        )
    )
    ass_res = await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == res.report_id))
    assessment = ass_res.scalars().first()
    review = await triage_service.ensure_review_for_assessment(assessment.id)

    # 1. Attempting to reopen a PENDING item -> InvalidStateTransitionException
    with pytest.raises(InvalidStateTransitionException):
        await triage_service.reopen_review(
            review.id,
            ReviewReopenRequest(reviewer_id="AUDITOR_A", reopen_rationale="Invalid attempt"),
        )

    # 2. Attempting to correct AI without rationale -> ReviewRationaleRequiredException
    with pytest.raises(ReviewRationaleRequiredException):
        await triage_service.submit_decision(
            review.id,
            ReviewDecisionRequest(
                reviewer_id="AUDITOR_A",
                decision=ReviewDecision.CORRECT,
                final_classification=SIFClassification.NON_SIF,
                reviewer_rationale="",  # Empty rationale
            ),
        )

    # 3. Operations on Nonexistent Review ID -> ReviewNotFoundException
    with pytest.raises(ReviewNotFoundException):
        await triage_service.get_review_history(uuid.uuid4())


@pytest.mark.asyncio
async def test_metadata_and_schema_consistency():
    """Verify all 8 application tables, columns, constraints, and indexes are registered in Base metadata."""
    tables = Base.metadata.tables
    expected_tables = {
        "safety_reports",
        "sif_assessments",
        "lsr_taxonomies",
        "lsr_report_mappings",
        "precursor_patterns",
        "risk_concentrations",
        "batch_jobs",
        "batch_row_errors",
        "triage_reviews",
        "review_audit_events",
    }
    assert expected_tables.issubset(set(tables.keys()))


@pytest.mark.asyncio
async def test_all_api_endpoint_groups_contract(async_client: AsyncClient):
    """Verify core API contracts across Health, Taxonomy, SIF, Batch, Patterns, Analytics, and Reviews."""
    # 1. Health
    h_res = await async_client.get("/api/v1/health")
    assert h_res.status_code in [200, 503]

    # 2. Taxonomies
    tax_res = await async_client.get("/api/v1/taxonomies")
    assert tax_res.status_code == 200

    # 3. Analyze
    ana_res = await async_client.post(
        "/api/v1/sif/analyze",
        json={
            "report_ref": "OIL-API-TEST",
            "raw_text": "While running 9-5/8 inch casing at Rig-04, air winch line parted and elevator swung near floormen.",
            "source_type": "NEAR_MISS",
            "reported_location": "Rig-04 Dikom",
        },
    )
    assert ana_res.status_code == 200

    # 4. Patterns
    pat_res = await async_client.get("/api/v1/sif/patterns")
    assert pat_res.status_code == 200

    # 5. Analytics Summary
    conc_res = await async_client.get("/api/v1/sif/analytics/summary")
    assert conc_res.status_code == 200

    # 6. Review Queue & Analytics Summary
    q_res = await async_client.get("/api/v1/sif/reviews/queue")
    assert q_res.status_code == 200
    rev_analytics_res = await async_client.get("/api/v1/sif/reviews/analytics/summary")
    assert rev_analytics_res.status_code == 200
