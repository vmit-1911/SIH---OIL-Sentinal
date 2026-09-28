"""Integration tests for Phase 7 HSE intelligence, evidence graph, and explainability endpoints."""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.assessment import SIFAssessment
from app.db.models.concentration import RiskConcentration
from app.db.models.pattern import PrecursorPattern
from app.db.models.report import SafetyReport
from app.db.models.review import ReviewAuditEvent, TriageReview
from app.domain.enums import (
    ActualOutcome,
    ConcentrationDimension,
    ConcentrationStatus,
    EvidenceStrength,
    ObservedTrend,
    PatternStatus,
    PotentialOutcome,
    ReviewAuditEventType,
    ReviewDecision,
    ReviewState,
    SIFClassification,
    SourceType,
    TriageStatus,
)
from app.schemas.report import SingleReportAnalysisRequest
from app.schemas.review import ReviewClaimRequest, ReviewDecisionRequest
from app.services.sif_analysis_service import SIFAnalysisService
from app.services.triage_service import TriageService


@pytest.mark.asyncio
async def test_get_report_evidence_endpoint(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/sif/reports/{report_id}/evidence returns factual evidence spans."""
    sif_service = SIFAnalysisService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="OIL-INTEL-001",
            raw_text=(
                "While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung "
                "across the rig floor, narrowly missing two floormen who jumped out of the way. No injuries occurred."
            ),
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04 / Moran Field",
        )
    )

    response = await async_client.get(f"/api/v1/sif/reports/{res.report_id}/evidence")
    assert response.status_code == 200
    data = response.json()
    assert data["report_id"] == str(res.report_id)
    assert data["total_evidence_items"] >= 4
    for item in data["evidence_items"]:
        assert item["evidence_id"].startswith("EV-")
        assert item["source_text"] is not None
        assert item["start_offset"] is not None
        assert item["end_offset"] is not None


@pytest.mark.asyncio
async def test_get_report_explanation_endpoint(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/sif/reports/{report_id}/explanation returns structured factor breakdowns and triggered rules."""
    sif_service = SIFAnalysisService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="OIL-INTEL-002",
            raw_text="Technician began unbolting high pressure flange on production manifold. Pressurized gas vented because double-block-and-bleed valve was not fully closed.",
            source_type=SourceType.NEAR_MISS,
            reported_location="EPS-Moran",
        )
    )

    response = await async_client.get(f"/api/v1/sif/reports/{res.report_id}/explanation")
    assert response.status_code == 200
    data = response.json()
    assert data["report_id"] == str(res.report_id)
    assert data["classification"] == "POTENTIAL_SIF"
    assert "energy_hazard" in data["factors"]
    assert "barrier_degradation" in data["factors"]
    assert data["factors"]["energy_hazard"]["present"] is True
    assert len(data["precursor_provenance"]) >= 2


@pytest.mark.asyncio
async def test_get_assessment_similarity_and_pattern_endpoints(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/sif/assessments/{assessment_id}/similarity and /pattern."""
    sif_service = SIFAnalysisService(db_session)

    # Insert 2 similar reports
    res1 = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="OIL-SIM-A",
            raw_text="While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung across the rig floor, narrowly missing two floormen.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04 / Moran",
        )
    )
    res2 = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="OIL-SIM-B",
            raw_text="While running 9-5/8 inch casing at Rig-04, the wire rope snapped and the heavy elevator swung across the rig floor, with floormen standing under load.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04 / Moran",
        )
    )

    # Get assessment ID
    ass1_res = await async_client.get(f"/api/v1/sif/reports/{res1.report_id}/explanation")
    assessment_id = ass1_res.json()["assessment_id"]

    # Test Similarity
    sim_res = await async_client.get(f"/api/v1/sif/assessments/{assessment_id}/similarity?threshold=0.50")
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["total_similar_reports"] >= 1
    assert sim_data["similar_reports"][0]["matched_report_ref"] == res2.report_ref

    # Test Assessment Pattern (when no pattern is assigned)
    pat_res = await async_client.get(f"/api/v1/sif/assessments/{assessment_id}/pattern")
    assert pat_res.status_code == 200
    pat_data = pat_res.json()
    assert pat_data["has_pattern"] is False


@pytest.mark.asyncio
async def test_get_pattern_and_concentration_evidence_endpoints(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/sif/patterns/{pattern_id}/evidence and /concentrations/{key}/evidence."""
    # 1. Create Report & Assessment
    r = SafetyReport(
        id=uuid.uuid4(),
        report_ref="OIL-PAT-TEST-01",
        source_type=SourceType.NEAR_MISS,
        raw_text="Rigging failure during crane lift on rig floor.",
        reported_location="Rig-04",
        actual_severity=ActualOutcome.NO_INJURY,
    )
    db_session.add(r)
    await db_session.flush()

    a = SIFAssessment(
        id=uuid.uuid4(),
        report_id=r.id,
        sif_classification=SIFClassification.POTENTIAL_SIF,
        evidence_score=0.9,
        evidence_strength=EvidenceStrength.HIGH,
        rule_based_screening_score=0.9,
        potential_severity=PotentialOutcome.FATALITY,
        structured_precursor={"hazard": "Suspended Load", "barrier_failure": "Rigging Failure"},
        triage_status=TriageStatus.AUTO_SCREENED,
    )
    db_session.add(a)

    # 2. Create Pattern
    pattern_id = uuid.uuid4()
    pattern = PrecursorPattern(
        id=pattern_id,
        pattern_code="PAT_TEST_RIGGING_01",
        title="Recurring Rigging Failure",
        description="Repeated rigging line failures on Rig-04",
        hazard_category="Suspended Load",
        failed_barrier_type="Rigging Failure",
        occurrence_count=1,
        affected_locations=["Rig-04"],
        supporting_report_ids=[str(r.id)],
        status=PatternStatus.ACTIVE,
        first_detected_at=datetime.now(timezone.utc),
        last_detected_at=datetime.now(timezone.utc),
    )
    db_session.add(pattern)

    # 3. Create Concentration
    conc = RiskConcentration(
        id=uuid.uuid4(),
        concentration_key="CONC|LOCATION|RIG_04",
        dimension_type=ConcentrationDimension.LOCATION,
        dimension_value="Rig-04",
        occurrence_count=1,
        distinct_report_count=1,
        distinct_location_count=1,
        first_observed_at=datetime.now(timezone.utc),
        last_observed_at=datetime.now(timezone.utc),
        observed_trend=ObservedTrend.STABLE,
        supporting_report_ids=[str(r.id)],
        supporting_locations=["Rig-04"],
        status=ConcentrationStatus.ACTIVE,
        calculation_method="FREQUENCY_AGGREGATION_V1",
    )
    db_session.add(conc)
    await db_session.flush()

    # Test Pattern Evidence Endpoint
    pat_res = await async_client.get(f"/api/v1/sif/patterns/{pattern_id}/evidence")
    assert pat_res.status_code == 200
    pat_data = pat_res.json()
    assert pat_data["pattern_code"] == "PAT_TEST_RIGGING_01"
    assert len(pat_data["supporting_reports"]) == 1
    assert pat_data["supporting_reports"][0]["report_ref"] == "OIL-PAT-TEST-01"

    # Test Concentration Evidence Endpoint
    conc_res = await async_client.get("/api/v1/sif/concentrations/CONC|LOCATION|RIG_04/evidence")
    assert conc_res.status_code == 200
    conc_data = conc_res.json()
    assert conc_data["concentration_key"] == "CONC|LOCATION|RIG_04"
    assert len(conc_data["supporting_reports"]) == 1
    assert conc_data["supporting_reports"][0]["report_ref"] == "OIL-PAT-TEST-01"


@pytest.mark.asyncio
async def test_get_investigation_context_endpoint_reviewed_report(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/sif/reports/{report_id}/investigation-context on a reviewed report."""
    sif_service = SIFAnalysisService(db_session)
    triage_service = TriageService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="OIL-FULL-CTX-001",
            raw_text="During mast maintenance on monkey board at 25 meters height, derrickman unhooked his full body harness lanyard without 100% tie-off.",
            source_type=SourceType.INCIDENT,
            reported_location="Moran GGS",
            actual_severity=ActualOutcome.NO_INJURY,
        )
    )

    # Perform Review
    ass_res = await async_client.get(f"/api/v1/sif/reports/{res.report_id}/explanation")
    assessment_id = uuid.UUID(ass_res.json()["assessment_id"])

    review = await triage_service.ensure_review_for_assessment(assessment_id)
    await triage_service.claim_review(review.id, ReviewClaimRequest(reviewer_id="HSE_EXPERT_1"))
    await triage_service.submit_decision(
        review.id,
        ReviewDecisionRequest(
            reviewer_id="HSE_EXPERT_1",
            decision=ReviewDecision.CONFIRM_AI,
            reviewer_notes="Confirmed working at height violation without fall protection tie-off.",
        ),
    )

    # Fetch Consolidated Investigation Context
    ctx_res = await async_client.get(f"/api/v1/sif/reports/{res.report_id}/investigation-context")
    assert ctx_res.status_code == 200
    ctx_data = ctx_res.json()

    # 1. Report
    assert ctx_data["report"]["report_ref"] == res.report_ref
    # 2. Assessment
    assert ctx_data["assessment"]["sif_classification"] == "POTENTIAL_SIF"
    # 3. Evidence
    assert len(ctx_data["evidence"]) >= 3
    # 4. Screening
    assert ctx_data["screening"] is not None
    # 5. Precursor
    assert ctx_data["precursor"] is not None
    assert len(ctx_data["precursor_provenance"]) >= 2
    # 6. Review & Audit
    assert ctx_data["review"] is not None
    assert ctx_data["review"]["decision"] == "CONFIRM_AI"
    assert len(ctx_data["audit_history"]) >= 3


@pytest.mark.asyncio
async def test_intelligence_endpoints_404_errors(async_client: AsyncClient):
    """Verify clean 404 responses for nonexistent IDs."""
    fake_id = uuid.uuid4()

    r1 = await async_client.get(f"/api/v1/sif/reports/{fake_id}/evidence")
    assert r1.status_code == 404

    r2 = await async_client.get(f"/api/v1/sif/reports/{fake_id}/explanation")
    assert r2.status_code == 404

    r3 = await async_client.get(f"/api/v1/sif/reports/{fake_id}/investigation-context")
    assert r3.status_code == 404

    r4 = await async_client.get(f"/api/v1/sif/assessments/{fake_id}/evidence")
    assert r4.status_code == 404

    r5 = await async_client.get(f"/api/v1/sif/assessments/{fake_id}/similarity")
    assert r5.status_code == 404

    r6 = await async_client.get(f"/api/v1/sif/assessments/{fake_id}/pattern")
    assert r6.status_code == 404

    r7 = await async_client.get(f"/api/v1/sif/patterns/{fake_id}/evidence")
    assert r7.status_code == 404

    r8 = await async_client.get("/api/v1/sif/concentrations/NONEXISTENT_CONC_KEY/evidence")
    assert r8.status_code == 404
