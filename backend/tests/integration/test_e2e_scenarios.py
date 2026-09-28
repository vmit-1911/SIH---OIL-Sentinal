"""End-to-end integration scenarios for OIL SIF Sentinel pipeline (Scenarios A through H)."""

import io
import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.assessment import SIFAssessment
from app.db.models.concentration import RiskConcentration
from app.db.models.pattern import PrecursorPattern
from app.db.models.report import SafetyReport
from app.db.models.review import ReviewAuditEvent, TriageReview
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
    PrecursorCorrectionRequest,
    ReviewClaimRequest,
    ReviewDecisionRequest,
    ReviewFeedbackRequest,
)
from app.services.batch_ingestion_service import BatchIngestionService
from app.services.pattern_discovery_service import PatternDiscoveryService
from app.services.risk_concentration_service import RiskConcentrationService
from app.services.sif_analysis_service import SIFAnalysisService
from app.services.triage_service import TriageService


@pytest.mark.asyncio
async def test_scenario_a_suspended_load_line_of_fire_e2e(
    db_session: AsyncSession,
    async_client: AsyncClient,
):
    """SCENARIO A: Suspended Load / Line of Fire full pipeline through CONFIRM_AI review."""
    sif_service = SIFAnalysisService(db_session)
    triage_service = TriageService(db_session)

    # 1. Pipeline Execution: Safety Narrative -> Extraction -> Screening -> LSR -> Precursor -> Persistence
    request = SingleReportAnalysisRequest(
        report_ref="OIL-SYN-SCENARIO-A",
        raw_text=(
            "While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung "
            "across the rig floor, narrowly missing two floormen who jumped out of the way. No injuries occurred."
        ),
        source_type=SourceType.NEAR_MISS,
        reported_location="Rig-04 / Moran Field",
        reported_department="Drilling Operations",
        actual_severity=ActualOutcome.NO_INJURY,
    )
    result = await sif_service.analyze_and_persist(request)

    # Assert Stage 1: SIF Screening & LSR
    assert result.sif_classification == SIFClassification.POTENTIAL_SIF
    assert result.evidence_score >= 0.60
    assert result.potential_severity == PotentialOutcome.FATALITY
    assert result.structured_precursor is not None
    assert result.precursor_signature is not None
    assert len(result.evidence_spans) > 0

    # Assert DB Persistence
    rep = await db_session.get(SafetyReport, result.report_id)
    ass = await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == result.report_id))
    assessment = ass.scalars().first()
    assert rep is not None
    assert assessment is not None
    assert assessment.sif_classification == SIFClassification.POTENTIAL_SIF
    assert assessment.structured_precursor is not None

    # 2. Stage for Review & Claim
    review = await triage_service.ensure_review_for_assessment(assessment.id)
    assert review.status == ReviewState.PENDING
    assert review.original_classification == SIFClassification.POTENTIAL_SIF

    claimed_review = await triage_service.claim_review(
        review.id,
        ReviewClaimRequest(reviewer_id="HSE_OFFICER_A", reviewer_role="SENIOR_AUDITOR"),
    )
    assert claimed_review.status == ReviewState.IN_REVIEW
    assert claimed_review.reviewer_id == "HSE_OFFICER_A"

    # 3. Submit Decision: CONFIRM_AI
    decision_req = ReviewDecisionRequest(
        reviewer_id="HSE_OFFICER_A",
        decision=ReviewDecision.CONFIRM_AI,
        reviewer_notes="Confirmed high-energy hazard exposure and critical barrier failure on Rig-04.",
    )
    final_review = await triage_service.submit_decision(review.id, decision_req)

    # 4. Verify AI Preservation & Review State
    assert final_review.status == ReviewState.REVIEWED
    assert final_review.decision == ReviewDecision.CONFIRM_AI
    assert final_review.final_classification == SIFClassification.POTENTIAL_SIF
    assert assessment.sif_classification == SIFClassification.POTENTIAL_SIF  # Preserved in AI assessment
    assert assessment.triage_status == TriageStatus.VALIDATED

    # 5. Verify Audit Trail
    history = await triage_service.get_review_history(review.id)
    event_types = [h.event_type for h in history]
    assert ReviewAuditEventType.REVIEW_CREATED in event_types
    assert ReviewAuditEventType.REVIEW_CLAIMED in event_types
    assert ReviewAuditEventType.REVIEW_SUBMITTED in event_types

    # 6. Verify Analytics Summary
    analytics = await triage_service.get_analytics_summary()
    assert analytics.confirmations_count >= 1
    assert analytics.reviewed_count >= 1


@pytest.mark.asyncio
async def test_scenario_b_working_at_height_e2e_with_correction(
    db_session: AsyncSession,
    async_client: AsyncClient,
):
    """SCENARIO B: Working at Height pipeline through CORRECT review with precursor & classification update."""
    sif_service = SIFAnalysisService(db_session)
    triage_service = TriageService(db_session)

    # 1. Pipeline Execution
    request = SingleReportAnalysisRequest(
        report_ref="OIL-SYN-SCENARIO-B",
        raw_text=(
            "During mast maintenance on monkey board at 25 meters height, derrickman unhooked his full body "
            "harness lanyard without 100% tie-off."
        ),
        source_type=SourceType.INCIDENT,
        reported_location="Moran GGS",
        actual_severity=ActualOutcome.NO_INJURY,
    )
    result = await sif_service.analyze_and_persist(request)

    # Assert SIF & LSR
    assert result.sif_classification == SIFClassification.POTENTIAL_SIF
    assert result.primary_lsr is not None
    assert result.primary_lsr.rule_code == "LSR_09_WORKING_AT_HEIGHT"

    ass = await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == result.report_id))
    assessment = ass.scalars().first()

    # 2. Stage Review & Claim
    review = await triage_service.ensure_review_for_assessment(assessment.id)
    await triage_service.claim_review(
        review.id,
        ReviewClaimRequest(reviewer_id="AUDITOR_B", reviewer_role="FIELD_SAFETY_LEAD"),
    )

    # 3. Perform Review: CORRECT (assign ACTUAL_SIF based on post-event medical verification)
    correction_req = ReviewDecisionRequest(
        reviewer_id="AUDITOR_B",
        decision=ReviewDecision.CORRECT,
        final_classification=SIFClassification.ACTUAL_SIF,
        final_lsr_code="LSR_09_WORKING_AT_HEIGHT",
        final_structured_precursor=PrecursorCorrectionRequest(
            barrier_failure={"type": "FALL_PROTECTION", "status": "FAILED"}
        ),
        reviewer_rationale="Subsequent medical check confirmed permanent spinal fracture from impact; authoritative ACTUAL_SIF.",
        feedback=ReviewFeedbackRequest(
            category=ReviewFeedbackCategory.CLASSIFICATION_ERROR,
            notes="Initial field log missed hospitalization outcome.",
        ),
    )
    final_review = await triage_service.submit_decision(review.id, correction_req)

    # 4. Verify AI Preservation & Human Override
    assert final_review.status == ReviewState.REVIEWED
    assert final_review.decision == ReviewDecision.CORRECT
    assert final_review.original_classification == SIFClassification.POTENTIAL_SIF  # Preserved original AI
    assert final_review.final_classification == SIFClassification.ACTUAL_SIF       # Human override
    assert assessment.sif_classification == SIFClassification.POTENTIAL_SIF         # Untouched AI model row
    assert assessment.triage_status == TriageStatus.OVERRIDDEN

    # 5. Verify Audit Trail has CLASSIFICATION_CORRECTED & AUDITOR_OVERRIDE
    history = await triage_service.get_review_history(review.id)
    event_types = [h.event_type for h in history]
    assert ReviewAuditEventType.CLASSIFICATION_CORRECTED in event_types
    assert ReviewAuditEventType.AUDITOR_OVERRIDE in event_types
    assert ReviewAuditEventType.PRECURSOR_CORRECTED in event_types


@pytest.mark.asyncio
async def test_scenario_c_energy_isolation_e2e(
    db_session: AsyncSession,
):
    """SCENARIO C: Hazardous Energy / LOTO failure scenario through full pipeline."""
    sif_service = SIFAnalysisService(db_session)
    triage_service = TriageService(db_session)

    request = SingleReportAnalysisRequest(
        report_ref="OIL-SYN-SCENARIO-C",
        raw_text=(
            "Technician began unbolting high pressure flange on production manifold. "
            "Pressurized gas vented because double-block-and-bleed valve was not fully closed."
        ),
        source_type=SourceType.NEAR_MISS,
        reported_location="EPS-Nahorkatiya",
        actual_severity=ActualOutcome.NO_INJURY,
    )
    result = await sif_service.analyze_and_persist(request)

    assert result.sif_classification == SIFClassification.POTENTIAL_SIF
    assert result.primary_lsr is not None
    assert result.primary_lsr.rule_code == "LSR_04_ENERGY_ISOLATION"

    ass = await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == result.report_id))
    assessment = ass.scalars().first()
    review = await triage_service.ensure_review_for_assessment(assessment.id)

    # Direct decision
    final_review = await triage_service.submit_decision(
        review.id,
        ReviewDecisionRequest(
            reviewer_id="AUDITOR_C",
            decision=ReviewDecision.CONFIRM_AI,
            reviewer_notes="High-pressure gas isolation failure confirmed.",
        ),
    )
    assert final_review.status == ReviewState.REVIEWED
    assert final_review.decision == ReviewDecision.CONFIRM_AI


@pytest.mark.asyncio
async def test_scenario_d_non_sif_housekeeping(
    db_session: AsyncSession,
):
    """SCENARIO D: Low-severity housekeeping observation correctly classified as NON_SIF."""
    sif_service = SIFAnalysisService(db_session)

    request = SingleReportAnalysisRequest(
        report_ref="OIL-SYN-SCENARIO-D",
        raw_text="Empty paint cans and cleaning rags left unattended near workshop entrance, creating trip hazard.",
        source_type=SourceType.UC,
        reported_location="Duliajan Central Workshop",
        actual_severity=ActualOutcome.NO_INJURY,
    )
    result = await sif_service.analyze_and_persist(request)

    assert result.sif_classification == SIFClassification.NON_SIF
    assert result.evidence_score <= 0.35
    assert result.potential_severity == PotentialOutcome.LOW_IMPACT

    # Verify not eligible for pattern discovery (requires POTENTIAL_SIF)
    ass = await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == result.report_id))
    assessment = ass.scalars().first()
    assert assessment.sif_classification == SIFClassification.NON_SIF


@pytest.mark.asyncio
async def test_scenario_e_semantically_related_reports_pattern_discovery(
    db_session: AsyncSession,
):
    """SCENARIO E: 3 semantically related reports with different wording discover a stable recurring pattern."""
    sif_service = SIFAnalysisService(db_session)
    pattern_service = PatternDiscoveryService(db_session)

    reports_data = [
        ("OIL-SYN-E-01", "While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung across the rig floor, narrowly missing two floormen who jumped out of the way. No injuries occurred.", "Rig-04 / Moran"),
        ("OIL-SYN-E-02", "While running 9-5/8 inch casing at Rig-04, the wire rope snapped and the heavy elevator swung across the rig floor, with floormen standing under load.", "Rig-04 / Moran"),
        ("OIL-SYN-E-03", "While running 9-5/8 inch casing at Rig-04, the winch line parted and the heavy elevator swung across the rig floor in the line of fire.", "Rig-04 / Moran"),
    ]

    report_ids = []
    for ref, text, loc in reports_data:
        res = await sif_service.analyze_and_persist(
            SingleReportAnalysisRequest(
                report_ref=ref,
                raw_text=text,
                source_type=SourceType.NEAR_MISS,
                reported_location=loc,
            )
        )
        report_ids.append(res.report_id)

    # Run Pattern Discovery
    response = await pattern_service.discover_patterns(min_report_count=3, threshold=0.65)
    patterns = response.discovered_patterns
    assert len(patterns) >= 1

    # Verify pattern properties
    casing_pattern = next((p for p in patterns if any("Rig-04" in loc for loc in p.affected_locations)), None)
    assert casing_pattern is not None
    assert casing_pattern.occurrence_count >= 3
    assert len(casing_pattern.supporting_report_ids) >= 3
    assert casing_pattern.pattern_code.startswith("PAT_")
    assert casing_pattern.representative_precursor is not None

    # Check that SIFAssessments are linked to pattern_id in DB
    for r_id in casing_pattern.supporting_report_ids:
        ass_res = await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == r_id))
        ass = ass_res.scalars().first()
        assert ass.pattern_id == casing_pattern.id


@pytest.mark.asyncio
async def test_scenario_f_unrelated_reports_no_pattern(
    db_session: AsyncSession,
):
    """SCENARIO F: Completely unrelated safety reports are NOT clustered into a pattern."""
    sif_service = SIFAnalysisService(db_session)
    pattern_service = PatternDiscoveryService(db_session)

    unrelated_reports = [
        ("OIL-SYN-F-01", "During mast maintenance on monkey board at 25 meters height, derrickman unhooked his full body harness lanyard without 100% tie-off.", "Tank Farm A"),
        ("OIL-SYN-F-02", "Technician began unbolting high pressure flange on production manifold. Pressurized gas vented because double-block-and-bleed valve was not fully closed.", "Bypass Highway"),
    ]

    for ref, text, loc in unrelated_reports:
        await sif_service.analyze_and_persist(
            SingleReportAnalysisRequest(
                report_ref=ref,
                raw_text=text,
                source_type=SourceType.NEAR_MISS,
                reported_location=loc,
            )
        )

    # Discover patterns with min count 2
    response = await pattern_service.discover_patterns(min_report_count=2, threshold=0.75)
    patterns = response.discovered_patterns
    # Unrelated singletons should not form a multi-occurrence pattern together
    for p in patterns:
        assert not (
            any("Tank Farm A" in loc for loc in p.affected_locations)
            and any("Bypass Highway" in loc for loc in p.affected_locations)
        )


@pytest.mark.asyncio
async def test_scenario_g_multi_location_pattern(
    db_session: AsyncSession,
):
    """SCENARIO G: Related reports across different facilities form a pattern with multi-location tracking."""
    sif_service = SIFAnalysisService(db_session)
    pattern_service = PatternDiscoveryService(db_session)

    multi_loc_reports = [
        ("OIL-SYN-G-01", "Technician began unbolting high pressure flange on production manifold at EPS-Moran. Pressurized gas vented because double-block-and-bleed valve was not fully closed.", "EPS-Moran"),
        ("OIL-SYN-G-02", "Technician began unbolting high pressure flange on production manifold at EPS-Nahorkatiya. Pressurized gas vented because double-block-and-bleed valve was not fully closed.", "EPS-Nahorkatiya"),
        ("OIL-SYN-G-03", "Technician began unbolting high pressure flange on production manifold at Central GGS Duliajan. Pressurized gas vented because double-block-and-bleed valve was not fully closed.", "Central GGS Duliajan"),
    ]

    for ref, text, loc in multi_loc_reports:
        await sif_service.analyze_and_persist(
            SingleReportAnalysisRequest(
                report_ref=ref,
                raw_text=text,
                source_type=SourceType.NEAR_MISS,
                reported_location=loc,
            )
        )

    response = await pattern_service.discover_patterns(min_report_count=3, threshold=0.65)
    patterns = response.discovered_patterns
    manifold_pattern = next(
        (p for p in patterns if len(p.affected_locations) >= 2),
        None,
    )
    assert manifold_pattern is not None
    assert len(manifold_pattern.affected_locations) >= 2
    # Representative location should be null/empty for heterogeneous locations
    if manifold_pattern.representative_precursor and manifold_pattern.representative_precursor.location:
        assert manifold_pattern.representative_precursor.location.facility is None


@pytest.mark.asyncio
async def test_scenario_h_batch_to_decoupled_analytics_e2e(
    db_session: AsyncSession,
    async_client: AsyncClient,
):
    """SCENARIO H: Batch ingestion -> Decoupled boundary -> Explicit pattern & concentration refresh."""
    batch_service = BatchIngestionService(db_session)

    csv_content = (
        'report_ref,source_type,narrative,reported_location,reported_department,actual_severity,event_timestamp\n'
        'OIL-BTH-01,NEAR_MISS,"While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung across the rig floor, narrowly missing two floormen who jumped out of the way. No injuries occurred.",Rig-04,Drilling,NO_INJURY,2026-04-01T10:00:00Z\n'
        'OIL-BTH-02,NEAR_MISS,"While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung across the rig floor near crew.",Rig-04,Drilling,NO_INJURY,2026-04-02T11:00:00Z\n'
        'OIL-BTH-03,INCIDENT,"During mast maintenance on monkey board at 25 meters height, derrickman unhooked his full body harness lanyard without 100% tie-off.",Rig-04,Drilling,FIRST_AID,2026-04-03T12:00:00Z\n'
        'OIL-BTH-04,UC,"Empty paint cans and cleaning rags left unattended near workshop entrance.",Duliajan Store,Logistics,NO_INJURY,2026-04-04T13:00:00Z\n'
        'OIL-BTH-05,NEAR_MISS,,Rig-04,Drilling,NO_INJURY,2026-04-05T14:00:00Z\n'  # Invalid empty narrative
    )

    job = await batch_service.create_batch_job(filename="test_scenario_h.csv")
    completed_job = await batch_service.process_batch_file(job.id, csv_content.encode("utf-8"), "test_scenario_h.csv")

    # Assert Counter Reconciliation
    assert completed_job.total_rows == 5
    assert completed_job.accepted_rows == 4
    assert completed_job.rejected_rows == 1
    assert completed_job.processed_rows == 4
    assert completed_job.total_rows == completed_job.processed_rows + completed_job.rejected_rows + completed_job.failed_processing_rows

    # Verify DECOUPLED BOUNDARY: Batch completion creates ZERO patterns or concentrations
    pattern_count_res = await db_session.execute(select(func.count(PrecursorPattern.id)))
    concentration_count_res = await db_session.execute(select(func.count(RiskConcentration.id)))
    assert pattern_count_res.scalar_one() == 0
    assert concentration_count_res.scalar_one() == 0

    # Explicitly trigger Phase 2B Pattern Discovery
    pat_res = await async_client.post("/api/v1/sif/patterns/discover")
    assert pat_res.status_code == 200
    pat_data = pat_res.json()
    assert pat_data["candidates_evaluated"] >= 0
    assert pat_data["patterns_created"] >= 0

    # Explicitly trigger Phase 3 Concentration Refresh
    conc_res = await async_client.post("/api/v1/sif/analytics/concentrations/refresh")
    assert conc_res.status_code == 200
    conc_data = conc_res.json()
    assert conc_data["total_active_concentrations"] >= 0
