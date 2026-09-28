"""Integration tests for Phase 5 Human-in-the-Loop review REST API endpoints."""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.assessment import SIFAssessment
from app.db.models.report import SafetyReport
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
from app.services.triage_service import TriageService


@pytest.fixture
async def setup_review_fixtures(db_session: AsyncSession):
    """Populate database with structured safety reports and AI assessments for API testing."""
    service = TriageService(db_session)
    reviews = []

    # Report 1: Rig-04, Potential SIF, Energy Isolation
    rep1 = SafetyReport(
        id=uuid.uuid4(),
        report_ref="OIL-2026-RIG-001",
        source_type=SourceType.NEAR_MISS,
        raw_text="High pressure pump valve failed during cement circulation at Rig 04.",
        reported_location="Rig-04 Dikom",
        actual_severity=ActualOutcome.NO_INJURY,
    )
    db_session.add(rep1)
    await db_session.flush()

    ass1 = SIFAssessment(
        id=uuid.uuid4(),
        report_id=rep1.id,
        sif_classification=SIFClassification.POTENTIAL_SIF,
        evidence_score=0.88,
        evidence_strength=EvidenceStrength.HIGH,
        rule_based_screening_score=0.92,
        potential_severity=PotentialOutcome.FATALITY,
        structured_precursor={
            "hazard": {"category": "PRESSURE_HAZARD"},
            "activity": {"type": "CEMENTING"},
            "barrier_failure": {"type": "PRESSURE_CONTAINMENT"},
            "life_saving_rule": {"rule_code": "ENERGY_ISOLATION"},
        },
        triage_status=TriageStatus.AUTO_SCREENED,
    )
    db_session.add(ass1)
    await db_session.flush()
    rev1 = await service.ensure_review_for_assessment(ass1.id)
    reviews.append(rev1)

    # Report 2: Moran EPS, Non SIF
    rep2 = SafetyReport(
        id=uuid.uuid4(),
        report_ref="OIL-2026-EPS-002",
        source_type=SourceType.UC,
        raw_text="Missing safety signage near chemical storage shed at Moran EPS.",
        reported_location="Moran EPS",
        actual_severity=ActualOutcome.NO_INJURY,
    )
    db_session.add(rep2)
    await db_session.flush()

    ass2 = SIFAssessment(
        id=uuid.uuid4(),
        report_id=rep2.id,
        sif_classification=SIFClassification.NON_SIF,
        evidence_score=0.15,
        evidence_strength=EvidenceStrength.LOW,
        rule_based_screening_score=0.10,
        potential_severity=PotentialOutcome.LOW_IMPACT,
        structured_precursor={
            "hazard": {"category": "HOUSEKEEPING"},
            "life_saving_rule": {"rule_code": "BYPASSING_SAFETY_CONTROLS"},
        },
        triage_status=TriageStatus.AUTO_SCREENED,
    )
    db_session.add(ass2)
    await db_session.flush()
    rev2 = await service.ensure_review_for_assessment(ass2.id)
    reviews.append(rev2)

    await db_session.commit()
    return reviews


@pytest.mark.asyncio
async def test_get_triage_queue_filtering_and_pagination(async_client: AsyncClient, setup_review_fixtures):
    """Verify GET /api/v1/sif/reviews/queue supports deterministic filtering and pagination."""
    # 1. Default queue fetch
    res = await async_client.get("/api/v1/sif/reviews/queue")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] >= 2
    assert len(data["items"]) >= 2
    assert "total_pages" in data

    # 2. Filter by location
    res_loc = await async_client.get("/api/v1/sif/reviews/queue?location=Moran")
    assert res_loc.status_code == 200
    data_loc = res_loc.json()
    assert data_loc["total_count"] == 1
    assert data_loc["items"][0]["reported_location"] == "Moran EPS"

    # 3. Filter by classification
    res_class = await async_client.get("/api/v1/sif/reviews/queue?classification=POTENTIAL_SIF")
    assert res_class.status_code == 200
    data_class = res_class.json()
    assert data_class["total_count"] == 1
    assert data_class["items"][0]["classification"] == "POTENTIAL_SIF"

    # 4. Filter by Life-Saving Rule
    res_lsr = await async_client.get("/api/v1/sif/reviews/queue?life_saving_rule=ENERGY_ISOLATION")
    assert res_lsr.status_code == 200
    data_lsr = res_lsr.json()
    assert data_lsr["total_count"] == 1
    assert data_lsr["items"][0]["life_saving_rule"] == "ENERGY_ISOLATION"


@pytest.mark.asyncio
async def test_review_claim_and_conflict_workflow(async_client: AsyncClient, setup_review_fixtures):
    """Verify claim endpoint transitions PENDING -> IN_REVIEW, and conflicting claim returns 409."""
    review_id = str(setup_review_fixtures[0].id)

    # Claim review
    claim_payload = {
        "reviewer_id": "AUDITOR_PRIYA",
        "reviewer_role": "FIELD_SAFETY_LEAD",
    }
    res = await async_client.post(f"/api/v1/sif/reviews/{review_id}/claim", json=claim_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "IN_REVIEW"
    assert data["reviewer_id"] == "AUDITOR_PRIYA"
    assert data["started_at"] is not None

    # Conflicting claim by another officer -> 409 Conflict
    conflict_payload = {
        "reviewer_id": "AUDITOR_AMIT",
        "reviewer_role": "DRILLING_HSE_OFFICER",
    }
    conflict_res = await async_client.post(f"/api/v1/sif/reviews/{review_id}/claim", json=conflict_payload)
    assert conflict_res.status_code == 409
    err_data = conflict_res.json()
    assert "already claimed by reviewer 'AUDITOR_PRIYA'" in err_data["message"]


@pytest.mark.asyncio
async def test_review_decision_submission_corrections_and_history(async_client: AsyncClient, setup_review_fixtures):
    """Verify decision endpoint allows authoritative correction, emits audit events, and updates analytics."""
    review_id = str(setup_review_fixtures[0].id)

    # 1. Claim
    await async_client.post(
        f"/api/v1/sif/reviews/{review_id}/claim",
        json={"reviewer_id": "AUDITOR_PRIYA", "reviewer_role": "FIELD_SAFETY_LEAD"},
    )

    # 2. Submit Decision with Correction & Feedback
    decision_payload = {
        "reviewer_id": "AUDITOR_PRIYA",
        "reviewer_role": "FIELD_SAFETY_LEAD",
        "decision": "CORRECT",
        "final_classification": "ACTUAL_SIF",
        "final_lsr_code": "ENERGY_ISOLATION",
        "final_structured_precursor": {
            "barrier_failure": {"type": "PRIMARY_CONTAINMENT", "status": "FAILED"}
        },
        "reviewer_rationale": "Direct burst caused immediate physical injury to pump technician; categorized as Actual SIF.",
        "reviewer_notes": "Immediate safety stand-down initiated on Rig 04.",
        "feedback": {
            "category": "CLASSIFICATION_ERROR",
            "notes": "Narrative contained injury reference in post-event report",
        },
    }
    res = await async_client.post(f"/api/v1/sif/reviews/{review_id}/decision", json=decision_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "REVIEWED"
    assert data["decision"] == "CORRECT"
    assert data["final_classification"] == "ACTUAL_SIF"
    assert data["original_classification"] == "POTENTIAL_SIF"  # Preserved original AI
    assert data["feedback"]["category"] == "CLASSIFICATION_ERROR"

    # 3. Verify History Endpoint
    hist_res = await async_client.get(f"/api/v1/sif/reviews/{review_id}/history")
    assert hist_res.status_code == 200
    events = hist_res.json()
    assert len(events) >= 3
    types = [e["event_type"] for e in events]
    assert "REVIEW_CREATED" in types
    assert "REVIEW_CLAIMED" in types
    assert "REVIEW_SUBMITTED" in types
    assert "CLASSIFICATION_CORRECTED" in types


@pytest.mark.asyncio
async def test_review_idempotent_decision_resubmission(async_client: AsyncClient, setup_review_fixtures):
    """Verify repeated identical decision submission on completed review is idempotent."""
    review_id = str(setup_review_fixtures[1].id)

    decision_payload = {
        "reviewer_id": "AUDITOR_PRIYA",
        "decision": "CONFIRM_AI",
        "reviewer_notes": "Low energy observation verified.",
    }

    # First submission
    res1 = await async_client.post(f"/api/v1/sif/reviews/{review_id}/decision", json=decision_payload)
    assert res1.status_code == 200

    # Repeat identical submission
    res2 = await async_client.post(f"/api/v1/sif/reviews/{review_id}/decision", json=decision_payload)
    assert res2.status_code == 200
    assert res2.json()["status"] == "REVIEWED"


@pytest.mark.asyncio
async def test_review_reopen_workflow(async_client: AsyncClient, setup_review_fixtures):
    """Verify POST /api/v1/sif/reviews/{review_id}/reopen transitions REVIEWED -> IN_REVIEW."""
    review_id = str(setup_review_fixtures[1].id)

    # Submit decision first
    await async_client.post(
        f"/api/v1/sif/reviews/{review_id}/decision",
        json={"reviewer_id": "AUDITOR_PRIYA", "decision": "CONFIRM_AI"},
    )

    # Reopen
    reopen_payload = {
        "reviewer_id": "AUDITOR_LEAD",
        "reopen_rationale": "Reopened following quality audit check on signage reports.",
    }
    res = await async_client.post(f"/api/v1/sif/reviews/{review_id}/reopen", json=reopen_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "IN_REVIEW"
    assert data["reviewer_id"] == "AUDITOR_LEAD"


@pytest.mark.asyncio
async def test_review_analytics_summary_endpoint(async_client: AsyncClient, setup_review_fixtures):
    """Verify GET /api/v1/sif/reviews/analytics/summary returns aggregated descriptive metrics and disclaimer."""
    res = await async_client.get("/api/v1/sif/reviews/analytics/summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_reviews" in data
    assert "pending_count" in data
    assert "in_review_count" in data
    assert "reviewed_count" in data
    assert "confirmations_count" in data
    assert "corrections_count" in data
    assert "disclaimer" in data
    assert "Descriptive audit statistics" in data["disclaimer"]


@pytest.mark.asyncio
async def test_legacy_review_endpoint_backward_compatibility(async_client: AsyncClient, setup_review_fixtures):
    """Verify legacy POST /api/v1/sif/reports/{report_id}/review functions without regressions."""
    report_id = str(setup_review_fixtures[0].report_id)

    legacy_payload = {
        "reviewer_id": "LEGACY_AUDITOR",
        "verified_sif_classification": "POTENTIAL_SIF",
        "review_status": "VALIDATED",
        "reviewer_notes": "Validated via legacy endpoint",
    }
    res = await async_client.post(f"/api/v1/sif/reports/{report_id}/review", json=legacy_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["report_id"] == report_id
    assert data["status"] == "VALIDATED"
