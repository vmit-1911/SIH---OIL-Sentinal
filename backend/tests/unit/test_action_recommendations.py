"""Unit tests for Phase 8 Deterministic Action Recommendation Rule Engine & Service."""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ActionNotFoundException,
    AssessmentNotFoundException,
    ConcentrationNotFoundException,
    InvalidStateTransitionException,
    PatternNotFoundException,
    ReportNotFoundException,
)
from app.db.models.action import HSEActionRecommendation
from app.db.models.assessment import SIFAssessment
from app.db.models.concentration import RiskConcentration
from app.db.models.pattern import PrecursorPattern
from app.db.models.report import SafetyReport
from app.db.models.review import TriageReview
from app.db.models.taxonomy import LSRReportMapping, LSRTaxonomy
from app.domain.action.rule_engine import ActionRuleEngine
from app.domain.enums import (
    ActionCategory,
    ActionPriority,
    ActionSourceType,
    ActionStatus,
    ActualOutcome,
    ConcentrationDimension,
    ConcentrationStatus,
    EvidenceStrength,
    ObservedTrend,
    PatternStatus,
    PotentialOutcome,
    ReviewDecision,
    ReviewState,
    SIFClassification,
    SourceType,
    TriageStatus,
)
from app.schemas.action import (
    ActionAcknowledgeRequest,
    ActionGenerateRequest,
    ActionStatusUpdateRequest,
)
from app.schemas.report import SingleReportAnalysisRequest
from app.schemas.review import (
    PrecursorCorrectionRequest,
    ReviewClaimRequest,
    ReviewDecisionRequest,
)
from app.services.action_service import HSEActionRecommendationService
from app.services.sif_analysis_service import SIFAnalysisService
from app.services.triage_service import TriageService


@pytest.mark.asyncio
async def test_scenario_a_barrier_failure_action(db_session: AsyncSession):
    """Scenario A: Precursor with barrier failure generates BARRIER_VERIFICATION recommendation."""
    sif_service = SIFAnalysisService(db_session)
    action_service = HSEActionRecommendationService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-ACT-001",
            raw_text="While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung across the rig floor, narrowly missing two floormen in the swing path.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04 / Moran",
        )
    )

    actions = await action_service.generate_actions_for_report(res.report_id)
    assert len(actions) >= 1

    barrier_actions = [a for a in actions if a.action_category == ActionCategory.BARRIER_VERIFICATION]
    assert len(barrier_actions) == 1
    action = barrier_actions[0]
    assert action.rule_id == "ACT-R01-BARRIER"
    assert action.priority in (ActionPriority.HIGH, ActionPriority.CRITICAL_REVIEW)
    assert "Winch Line Parted" in action.action_description or "Rig-04" in action.action_description
    assert action.status == ActionStatus.OPEN


@pytest.mark.asyncio
async def test_scenario_b_energy_isolation_action(db_session: AsyncSession):
    """Scenario B: Pressurized gas release / LOTO failure generates ENERGY_ISOLATION_VERIFICATION."""
    sif_service = SIFAnalysisService(db_session)
    action_service = HSEActionRecommendationService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-ACT-002",
            raw_text="Technician began unbolting high pressure flange on production manifold. Pressurized gas vented because double-block-and-bleed valve was not fully closed.",
            source_type=SourceType.NEAR_MISS,
            reported_location="EPS-Moran",
        )
    )

    actions = await action_service.generate_actions_for_report(res.report_id)
    energy_actions = [a for a in actions if a.action_category == ActionCategory.ENERGY_ISOLATION_VERIFICATION]
    assert len(energy_actions) == 1
    action = energy_actions[0]
    assert action.rule_id == "ACT-R02-ENERGY-ISOLATION"
    assert action.priority in (ActionPriority.HIGH, ActionPriority.CRITICAL_REVIEW)
    assert "LSR_04_ENERGY_ISOLATION" in (action.lsr_code or "")


@pytest.mark.asyncio
async def test_scenario_c_working_at_height_fall_protection_action(db_session: AsyncSession):
    """Scenario C: Working at height without tie-off generates FALL_PROTECTION_VERIFICATION."""
    sif_service = SIFAnalysisService(db_session)
    action_service = HSEActionRecommendationService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-ACT-003",
            raw_text="During mast maintenance on monkey board at 25 meters height, derrickman unhooked his full body harness lanyard without 100% tie-off.",
            source_type=SourceType.INCIDENT,
            reported_location="Rig-01",
        )
    )

    actions = await action_service.generate_actions_for_report(res.report_id)
    fall_actions = [a for a in actions if a.action_category == ActionCategory.FALL_PROTECTION_VERIFICATION]
    assert len(fall_actions) == 1
    action = fall_actions[0]
    assert action.rule_id == "ACT-R03-HEIGHT-FALL"
    assert "WORKING_AT_HEIGHT" in (action.lsr_code or "")


@pytest.mark.asyncio
async def test_scenario_d_mechanical_lifting_and_line_of_fire_actions(db_session: AsyncSession):
    """Scenario D: Crane lift failure with floormen exposed generates LIFTING and LINE_OF_FIRE recommendations."""
    sif_service = SIFAnalysisService(db_session)
    action_service = HSEActionRecommendationService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-ACT-004",
            raw_text="While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung across the rig floor, narrowly missing two floormen in the swing path.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04 / Moran Field",
        )
    )

    actions = await action_service.generate_actions_for_report(res.report_id)
    categories = [a.action_category for a in actions]
    assert ActionCategory.LIFTING_CONTROL_VERIFICATION in categories
    assert ActionCategory.LINE_OF_FIRE_CONTROL_REVIEW in categories


@pytest.mark.asyncio
async def test_scenario_e_recurring_pattern_investigation_action(db_session: AsyncSession):
    """Scenario E: Multi-site recurring precursor pattern generates PATTERN_INVESTIGATION."""
    action_service = HSEActionRecommendationService(db_session)

    pattern = PrecursorPattern(
        id=uuid.uuid4(),
        pattern_code="PAT_TEST_WINCH_FAIL_001",
        title="Recurring Air Winch Line Failure",
        description="Repeated winch line failures during casing running operations across multiple rigs",
        hazard_category="Suspended Load",
        failed_barrier_type="Winch Line Parted",
        occurrence_count=4,
        affected_locations=["Rig-04", "Rig-07"],
        supporting_report_ids=[str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())],
        status=PatternStatus.ACTIVE,
        first_detected_at=datetime.now(timezone.utc),
        last_detected_at=datetime.now(timezone.utc),
    )
    db_session.add(pattern)
    await db_session.flush()

    actions = await action_service.generate_actions_for_pattern(pattern.id)
    assert len(actions) == 1
    action = actions[0]
    assert action.action_category == ActionCategory.PATTERN_INVESTIGATION
    assert action.rule_id == "ACT-R10-PATTERN-INVESTIGATION"
    assert action.priority == ActionPriority.CRITICAL_REVIEW
    assert action.pattern_key == "PAT_TEST_WINCH_FAIL_001"


@pytest.mark.asyncio
async def test_scenario_f_location_concentration_action(db_session: AsyncSession):
    """Scenario F: Location concentration generates SITE_FOCUSED_REVIEW recommendation."""
    action_service = HSEActionRecommendationService(db_session)

    conc = RiskConcentration(
        id=uuid.uuid4(),
        concentration_key="CONC|LOCATION|RIG_04",
        dimension_type=ConcentrationDimension.LOCATION,
        dimension_value="Rig-04",
        occurrence_count=5,
        distinct_report_count=5,
        distinct_location_count=1,
        first_observed_at=datetime.now(timezone.utc),
        last_observed_at=datetime.now(timezone.utc),
        observed_trend=ObservedTrend.INCREASING,
        supporting_report_ids=[str(uuid.uuid4()) for _ in range(5)],
        supporting_locations=["Rig-04"],
        status=ConcentrationStatus.ACTIVE,
        calculation_method="FREQUENCY_AGGREGATION_V1",
    )
    db_session.add(conc)
    await db_session.flush()

    actions = await action_service.generate_actions_for_concentration("CONC|LOCATION|RIG_04")
    assert len(actions) == 1
    action = actions[0]
    assert action.action_category == ActionCategory.SITE_FOCUSED_REVIEW
    assert action.rule_id == "ACT-R11-SITE-CONCENTRATION"
    assert action.priority == ActionPriority.HIGH
    assert action.concentration_key == "CONC|LOCATION|RIG_04"


@pytest.mark.asyncio
async def test_scenario_g_human_review_confirm_ai_preserves_recommendations(db_session: AsyncSession):
    """Scenario G: CONFIRM_AI preserves recommendations without arbitrary priority escalation."""
    sif_service = SIFAnalysisService(db_session)
    triage_service = TriageService(db_session)
    action_service = HSEActionRecommendationService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-ACT-REV-001",
            raw_text="While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung across the rig floor, narrowly missing two floormen in the swing path.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04",
        )
    )

    # Perform CONFIRM_AI review
    ass_res = await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == res.report_id))
    assessment = ass_res.scalar_one()

    review = await triage_service.ensure_review_for_assessment(assessment.id)
    await triage_service.claim_review(review.id, ReviewClaimRequest(reviewer_id="HSE_EXPERT"))
    await triage_service.submit_decision(
        review.id,
        ReviewDecisionRequest(
            reviewer_id="HSE_EXPERT",
            decision=ReviewDecision.CONFIRM_AI,
            reviewer_notes="Confirmed near miss.",
        ),
    )

    actions = await action_service.generate_actions_for_assessment(assessment.id)
    assert len(actions) >= 1
    assert any(a.priority == ActionPriority.HIGH for a in actions)


@pytest.mark.asyncio
async def test_scenario_h_human_review_correct_updates_action_targets(db_session: AsyncSession):
    """Scenario H: CORRECT review updates action targets to match corrected precursor and LSR."""
    sif_service = SIFAnalysisService(db_session)
    triage_service = TriageService(db_session)
    action_service = HSEActionRecommendationService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-ACT-REV-002",
            raw_text="Technician entered electrical switchgear room and touched uninsulated terminal.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Substation-01",
        )
    )

    ass_res = await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == res.report_id))
    assessment = ass_res.scalar_one()

    # Correct to ENERGY_ISOLATION
    review = await triage_service.ensure_review_for_assessment(assessment.id)
    await triage_service.claim_review(review.id, ReviewClaimRequest(reviewer_id="HSE_EXPERT"))
    await triage_service.submit_decision(
        review.id,
        ReviewDecisionRequest(
            reviewer_id="HSE_EXPERT",
            decision=ReviewDecision.CORRECT,
            final_classification=SIFClassification.POTENTIAL_SIF,
            final_lsr_code="LSR_04_ENERGY_ISOLATION",
            final_structured_precursor=PrecursorCorrectionRequest(
                hazard={"category": "High Voltage Electricity", "description": "High voltage electrical hazard"},
                barrier_failure={"failure_type": "Electrical Isolation Bypassed", "barrier_type": "ENERGY_ISOLATION"},
                life_saving_rule={"rule_code": "LSR_04_ENERGY_ISOLATION"},
            ),
            reviewer_rationale="Corrected to electrical energy isolation violation.",
        ),
    )

    actions = await action_service.generate_actions_for_assessment(assessment.id)
    energy_actions = [a for a in actions if a.action_category == ActionCategory.ENERGY_ISOLATION_VERIFICATION]
    assert len(energy_actions) == 1
    assert energy_actions[0].lsr_code == "LSR_04_ENERGY_ISOLATION"


@pytest.mark.asyncio
async def test_scenario_i_human_review_reject_ai_suppresses_actions(db_session: AsyncSession):
    """Scenario I: REJECT_AI suppresses SIF-driven action recommendations."""
    sif_service = SIFAnalysisService(db_session)
    triage_service = TriageService(db_session)
    action_service = HSEActionRecommendationService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-ACT-REV-003",
            raw_text="Worker dropped plastic water bottle from ground-level walkway.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-01",
        )
    )

    ass_res = await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == res.report_id))
    assessment = ass_res.scalar_one()

    review = await triage_service.ensure_review_for_assessment(assessment.id)
    await triage_service.claim_review(review.id, ReviewClaimRequest(reviewer_id="HSE_EXPERT"))
    await triage_service.submit_decision(
        review.id,
        ReviewDecisionRequest(
            reviewer_id="HSE_EXPERT",
            decision=ReviewDecision.REJECT_AI,
            final_classification=SIFClassification.NON_SIF,
            reviewer_rationale="Non-hazardous plastic bottle drop with zero SIF potential.",
        ),
    )

    actions = await action_service.generate_actions_for_assessment(assessment.id)
    assert len(actions) == 0


@pytest.mark.asyncio
async def test_scenario_j_mark_undetermined_suppresses_sif_actions(db_session: AsyncSession):
    """Scenario J: MARK_UNDETERMINED suppresses definitive SIF-driven action recommendations."""
    sif_service = SIFAnalysisService(db_session)
    triage_service = TriageService(db_session)
    action_service = HSEActionRecommendationService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-ACT-REV-004",
            raw_text="Noise observed near pump shed.",
            source_type=SourceType.UC,
            reported_location="Pump Shed",
        )
    )

    ass_res = await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == res.report_id))
    assessment = ass_res.scalar_one()

    review = await triage_service.ensure_review_for_assessment(assessment.id)
    await triage_service.claim_review(review.id, ReviewClaimRequest(reviewer_id="HSE_EXPERT"))
    await triage_service.submit_decision(
        review.id,
        ReviewDecisionRequest(
            reviewer_id="HSE_EXPERT",
            decision=ReviewDecision.MARK_UNDETERMINED,
            reviewer_rationale="Insufficient detail to confirm hazard or barrier condition.",
        ),
    )

    actions = await action_service.generate_actions_for_assessment(assessment.id)
    assert len(actions) == 0


@pytest.mark.asyncio
async def test_scenario_k_l_idempotency_and_no_duplicate_actions(db_session: AsyncSession):
    """Scenario K & L: Repeated action generation is idempotent and creates no duplicate records."""
    sif_service = SIFAnalysisService(db_session)
    action_service = HSEActionRecommendationService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-ACT-IDEMP",
            raw_text="While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung across the rig floor, narrowly missing two floormen in the swing path.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04 / Moran",
        )
    )

    # First run
    actions_1 = await action_service.generate_actions_for_report(res.report_id, persist=True)
    count_1 = len(actions_1)
    assert count_1 >= 1

    # Second run
    actions_2 = await action_service.generate_actions_for_report(res.report_id, persist=True)
    count_2 = len(actions_2)
    assert count_1 == count_2

    # Verify database total rows
    stmt = select(HSEActionRecommendation)
    db_rows = (await db_session.execute(stmt)).scalars().all()
    assert len(db_rows) == count_1


@pytest.mark.asyncio
async def test_scenario_m_missing_dimensions_have_no_placeholders(db_session: AsyncSession):
    """Scenario M: Actions generated from sparse precursors contain no placeholder values (*, UNKNOWN, OTHER)."""
    sif_service = SIFAnalysisService(db_session)
    action_service = HSEActionRecommendationService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-ACT-SPARSE",
            raw_text="Pressurized gas vented during maintenance.",
            source_type=SourceType.NEAR_MISS,
            reported_location=None,
        )
    )

    actions = await action_service.generate_actions_for_report(res.report_id)
    for act in actions:
        for k, v in (act.source_dimensions or {}).items():
            assert v not in ("*", "UNKNOWN", "OTHER", "N/A"), f"Dimension {k} must not contain placeholder: {v}"


@pytest.mark.asyncio
async def test_scenario_n_non_sif_generates_no_sif_actions(db_session: AsyncSession):
    """Scenario N: Low-risk housekeeping observation generates zero SIF actions."""
    sif_service = SIFAnalysisService(db_session)
    action_service = HSEActionRecommendationService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-ACT-NONSIF",
            raw_text="Empty cardboard boxes left on walkway creating minor trip hazard.",
            source_type=SourceType.UC,
            reported_location="Workshop",
        )
    )

    actions = await action_service.generate_actions_for_report(res.report_id)
    assert len(actions) == 0


@pytest.mark.asyncio
async def test_scenario_o_read_only_source_integrity(db_session: AsyncSession):
    """Scenario O: Action generation leaves source reports, assessments, and reviews strictly unmutated."""
    sif_service = SIFAnalysisService(db_session)
    action_service = HSEActionRecommendationService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-ACT-INTEG",
            raw_text="High pressure gas leak observed on production separator manifold.",
            source_type=SourceType.NEAR_MISS,
            reported_location="EPS-01",
        )
    )

    # Capture initial states
    rep_before = await db_session.get(SafetyReport, res.report_id)
    ass_before = (await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == res.report_id))).scalar_one()

    rep_text_before = rep_before.raw_text
    ass_score_before = ass_before.evidence_score
    ass_class_before = ass_before.sif_classification

    # Generate actions
    _ = await action_service.generate_actions_for_report(res.report_id, persist=True)

    # Re-fetch source records
    rep_after = await db_session.get(SafetyReport, res.report_id)
    ass_after = (await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == res.report_id))).scalar_one()

    assert rep_after.raw_text == rep_text_before
    assert ass_after.evidence_score == ass_score_before
    assert ass_after.sif_classification == ass_class_before


@pytest.mark.asyncio
async def test_scenario_p_action_lifecycle_and_transitions(db_session: AsyncSession):
    """Scenario P: Full lifecycle progression: OPEN -> ACKNOWLEDGED -> IN_PROGRESS -> COMPLETED."""
    sif_service = SIFAnalysisService(db_session)
    action_service = HSEActionRecommendationService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-ACT-LIFE",
            raw_text="While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung across the rig floor, narrowly missing two floormen in the swing path.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04 / Moran",
        )
    )

    actions = await action_service.generate_actions_for_report(res.report_id, persist=True)
    action_id = actions[0].id

    # 1. Acknowledge
    ack = await action_service.acknowledge_action(
        action_id,
        ActionAcknowledgeRequest(actor_id="HSE_OFFICER_1", assigned_to="RIG_SUPERVISOR"),
    )
    assert ack.status == ActionStatus.ACKNOWLEDGED
    assert ack.actor_id == "HSE_OFFICER_1"
    assert ack.assigned_to == "RIG_SUPERVISOR"
    assert ack.acknowledged_at is not None

    # 2. In Progress
    in_prog = await action_service.update_action_status(
        action_id,
        ActionStatusUpdateRequest(
            status=ActionStatus.IN_PROGRESS,
            actor_id="RIG_SUPERVISOR",
            assigned_to="RIG_SUPERVISOR",
        ),
    )
    assert in_prog.status == ActionStatus.IN_PROGRESS

    # 3. Completed (requires rationale)
    comp = await action_service.update_action_status(
        action_id,
        ActionStatusUpdateRequest(
            status=ActionStatus.COMPLETED,
            actor_id="HSE_OFFICER_1",
            status_rationale="Winch line replaced with certified wire rope and load test verified.",
        ),
    )
    assert comp.status == ActionStatus.COMPLETED
    assert comp.completed_at is not None
    assert comp.status_rationale == "Winch line replaced with certified wire rope and load test verified."


@pytest.mark.asyncio
async def test_scenario_q_invalid_status_transitions_rejected(db_session: AsyncSession):
    """Scenario Q: Invalid status transitions and missing rationale are rejected deterministically."""
    sif_service = SIFAnalysisService(db_session)
    action_service = HSEActionRecommendationService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-ACT-INV",
            raw_text="While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung across the rig floor, narrowly missing two floormen in the swing path.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04",
        )
    )

    actions = await action_service.generate_actions_for_report(res.report_id, persist=True)
    action_id = actions[0].id

    # 1. Missing rationale when completing
    with pytest.raises(InvalidStateTransitionException):
        await action_service.update_action_status(
            action_id,
            ActionStatusUpdateRequest(
                status=ActionStatus.COMPLETED,
                actor_id="HSE_OFFICER_1",
                status_rationale=None,
            ),
        )

    # 2. Complete with rationale
    await action_service.update_action_status(
        action_id,
        ActionStatusUpdateRequest(
            status=ActionStatus.COMPLETED,
            actor_id="HSE_OFFICER_1",
            status_rationale="Verified and completed.",
        ),
    )

    # 3. Transition from terminal state (COMPLETED -> IN_PROGRESS) must fail
    with pytest.raises(InvalidStateTransitionException):
        await action_service.update_action_status(
            action_id,
            ActionStatusUpdateRequest(
                status=ActionStatus.IN_PROGRESS,
                actor_id="HSE_OFFICER_1",
                status_rationale="Attempting to re-open",
            ),
        )


@pytest.mark.asyncio
async def test_multi_source_generation_and_dry_run(db_session: AsyncSession):
    """Test ActionGenerateRequest multi-source batch generation and persist=False preview."""
    sif_service = SIFAnalysisService(db_session)
    action_service = HSEActionRecommendationService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-ACT-MULTI",
            raw_text="While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung across the rig floor, narrowly missing two floormen in the swing path.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04",
        )
    )

    pattern = PrecursorPattern(
        id=uuid.uuid4(),
        pattern_code="PAT_TEST_MULTI_001",
        title="Winch Line Failure",
        description="Repeated winch line failures",
        occurrence_count=3,
        affected_locations=["Rig-04"],
        supporting_report_ids=[str(res.report_id)],
        status=PatternStatus.ACTIVE,
        first_detected_at=datetime.now(timezone.utc),
        last_detected_at=datetime.now(timezone.utc),
    )
    db_session.add(pattern)

    conc = RiskConcentration(
        id=uuid.uuid4(),
        concentration_key="CONC|LOCATION|RIG_04_MULTI",
        dimension_type=ConcentrationDimension.LOCATION,
        dimension_value="Rig-04",
        occurrence_count=3,
        distinct_report_count=3,
        distinct_location_count=1,
        first_observed_at=datetime.now(timezone.utc),
        last_observed_at=datetime.now(timezone.utc),
        observed_trend=ObservedTrend.STABLE,
        supporting_report_ids=[str(res.report_id)],
        supporting_locations=["Rig-04"],
        status=ConcentrationStatus.ACTIVE,
        calculation_method="FREQUENCY_AGGREGATION_V1",
    )
    db_session.add(conc)
    await db_session.flush()

    # Dry-run generation (persist=False)
    resp_dry = await action_service.generate_all_pending_actions(persist=False)
    assert resp_dry.total_generated >= 3

    # Verify nothing was persisted in DB
    db_count_dry = (await db_session.execute(select(HSEActionRecommendation))).scalars().all()
    assert len(db_count_dry) == 0

    # Persistent generation
    resp_persist = await action_service.generate_all_pending_actions(persist=True)
    assert resp_persist.total_generated >= 3

    # Re-run persistent generation (idempotent)
    resp_repeat = await action_service.generate_all_pending_actions(persist=True)
    assert resp_repeat.total_generated == resp_persist.total_generated


@pytest.mark.asyncio
async def test_action_query_filters(db_session: AsyncSession):
    """Test HSEActionRecommendationService.get_actions filtering capabilities."""
    sif_service = SIFAnalysisService(db_session)
    action_service = HSEActionRecommendationService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-ACT-FILTER",
            raw_text="While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung across the rig floor, narrowly missing two floormen in the swing path.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04",
        )
    )

    actions = await action_service.generate_actions_for_report(res.report_id, persist=True)
    assert len(actions) >= 1

    # Filter by status
    open_actions = await action_service.get_actions(status=ActionStatus.OPEN)
    assert open_actions.total >= 1

    # Filter by non-existent status
    comp_actions = await action_service.get_actions(status=ActionStatus.COMPLETED)
    assert comp_actions.total == 0

    # Filter by priority
    high_actions = await action_service.get_actions(priority=ActionPriority.HIGH)
    assert isinstance(high_actions.items, list)

    # Filter by rule_id
    rule_actions = await action_service.get_actions(rule_id="ACT-R01-BARRIER")
    assert rule_actions.total >= 1


def test_hot_work_and_confined_space_action_rules():
    """Test LSR_06_HOT_WORK and LSR_08_CONFINED_SPACE specific deterministic rules in ActionRuleEngine."""
    engine = ActionRuleEngine()

    # 1. Hot Work rule
    actions_hot = engine.evaluate_assessment(
        assessment_id=uuid.uuid4(),
        report_id=uuid.uuid4(),
        report_ref="SR-ACT-HOT",
        raw_text="Welder cutting pipe near manifold",
        sif_classification=SIFClassification.POTENTIAL_SIF,
        evidence_score=0.85,
        potential_severity=PotentialOutcome.FATALITY,
        structured_precursor={
            "hazard": "Flammable Gas",
            "activity": "Hot Work Welding",
            "barrier_failure": "Gas Testing Omitted",
        },
        primary_lsr_code="LSR_06_HOT_WORK",
        primary_lsr_name="Hot Work",
    )
    assert any(a["action_category"] == ActionCategory.HOT_WORK_CONTROL_REVIEW for a in actions_hot)

    # 2. Confined Space rule
    actions_cs = engine.evaluate_assessment(
        assessment_id=uuid.uuid4(),
        report_id=uuid.uuid4(),
        report_ref="SR-ACT-CS",
        raw_text="Vessel cleaner inside crude tank",
        sif_classification=SIFClassification.POTENTIAL_SIF,
        evidence_score=0.85,
        potential_severity=PotentialOutcome.FATALITY,
        structured_precursor={
            "hazard": "Toxic H2S",
            "activity": "Confined Space Entry",
            "barrier_failure": "Continuous Monitoring Omitted",
        },
        primary_lsr_code="LSR_08_CONFINED_SPACE",
        primary_lsr_name="Confined Space",
    )
    assert any(a["action_category"] == ActionCategory.CONFINED_SPACE_CONTROL_REVIEW for a in actions_cs)


@pytest.mark.asyncio
async def test_correction_1_pattern_investigation_requires_persisted_pattern(db_session: AsyncSession):
    """Correction 1: PATTERN_INVESTIGATION generated ONLY when persisted PrecursorPattern exists."""
    sif_service = SIFAnalysisService(db_session)
    action_service = HSEActionRecommendationService(db_session)

    # 1. 2 related reports without a persisted Phase 2B pattern
    r1 = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-PAT-R1",
            raw_text="While running 9-5/8 inch casing at Rig-04, the air winch line parted and the elevator swung.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04",
        )
    )
    r2 = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-PAT-R2",
            raw_text="During casing running at Rig-07, air winch line snapped under tension.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-07",
        )
    )

    actions_r1 = await action_service.generate_actions_for_report(r1.report_id)
    actions_r2 = await action_service.generate_actions_for_report(r2.report_id)
    assert not any(a.action_category == ActionCategory.PATTERN_INVESTIGATION for a in actions_r1)
    assert not any(a.action_category == ActionCategory.PATTERN_INVESTIGATION for a in actions_r2)

    # 2. Persist valid Phase 2B pattern -> PATTERN_INVESTIGATION is generated
    pattern = PrecursorPattern(
        id=uuid.uuid4(),
        pattern_code="PAT_PHASE2B_TEST_001",
        title="Winch Line Snap Pattern",
        description="Phase 2B recurring pattern across rigs",
        occurrence_count=3,
        affected_locations=["Rig-04", "Rig-07"],
        supporting_report_ids=[str(r1.report_id), str(r2.report_id), str(uuid.uuid4())],
        status=PatternStatus.ACTIVE,
        first_detected_at=datetime.now(timezone.utc),
        last_detected_at=datetime.now(timezone.utc),
    )
    db_session.add(pattern)
    await db_session.flush()

    pat_actions = await action_service.generate_actions_for_pattern(pattern.id)
    assert len(pat_actions) == 1
    assert pat_actions[0].action_category == ActionCategory.PATTERN_INVESTIGATION
    assert pat_actions[0].rule_id == "ACT-R10-PATTERN-INVESTIGATION"


@pytest.mark.asyncio
async def test_correction_2_no_unsupported_operational_mandates(db_session: AsyncSession):
    """Correction 2: Verify generated action texts contain no unsupported operational mandates."""
    sif_service = SIFAnalysisService(db_session)
    action_service = HSEActionRecommendationService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-MANDATE-TEST",
            raw_text="While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung across the rig floor, narrowly missing two floormen in the swing path.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04",
        )
    )

    actions = await action_service.generate_actions_for_report(res.report_id)
    assert len(actions) >= 1

    unsupported_terms = [
        "double block & bleed",
        "100% tie-off",
        "full-body harnesses",
        "anchor points",
        "ivms telemetry",
        "journey management",
        "continuous lel monitoring",
        "standby rescue watch",
        "site stand-down",
    ]

    for action in actions:
        full_text = f"{action.action_title} {action.action_description} {action.rationale}".lower()
        for term in unsupported_terms:
            assert term not in full_text, f"Unsupported mandate '{term}' found in action {action.action_key}"


@pytest.mark.asyncio
async def test_correction_3_concentration_consumes_persisted_record_without_new_threshold(db_session: AsyncSession):
    """Correction 3: Phase 8 generates site recommendation from persisted concentration without inventing thresholds."""
    action_service = HSEActionRecommendationService(db_session)

    conc = RiskConcentration(
        id=uuid.uuid4(),
        concentration_key="CONC|LOCATION|RIG_TEST_01",
        dimension_type=ConcentrationDimension.LOCATION,
        dimension_value="Rig-Test-01",
        occurrence_count=2,
        distinct_report_count=2,
        distinct_location_count=1,
        first_observed_at=datetime.now(timezone.utc),
        last_observed_at=datetime.now(timezone.utc),
        observed_trend=ObservedTrend.STABLE,
        supporting_report_ids=[str(uuid.uuid4()), str(uuid.uuid4())],
        supporting_locations=["Rig-Test-01"],
        status=ConcentrationStatus.ACTIVE,
        calculation_method="FREQUENCY_AGGREGATION_V1",
    )
    db_session.add(conc)
    await db_session.flush()

    actions = await action_service.generate_actions_for_concentration("CONC|LOCATION|RIG_TEST_01")
    assert len(actions) == 1
    assert actions[0].action_category == ActionCategory.SITE_FOCUSED_REVIEW
    assert actions[0].rule_id == "ACT-R11-SITE-CONCENTRATION"
    assert "Rig-Test-01" in actions[0].rationale


@pytest.mark.asyncio
async def test_correction_4_actual_sif_requires_authoritative_or_reviewed_state(db_session: AsyncSession):
    """Correction 4: AI POTENTIAL_SIF+FATALITY does NOT trigger ACT-R13; authoritative ACTUAL_SIF triggers ACT-R13."""
    sif_service = SIFAnalysisService(db_session)
    triage_service = TriageService(db_session)
    action_service = HSEActionRecommendationService(db_session)

    # 1. AI POTENTIAL_SIF report
    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-ACTUAL-SIF-TEST",
            raw_text="While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung across the rig floor, narrowly missing two floormen in the swing path.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04",
        )
    )
    ass_res = await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == res.report_id))
    assessment = ass_res.scalar_one()

    # AI assessment must NOT produce MANAGEMENT_ATTENTION (ACT-R13)
    ai_actions = await action_service.generate_actions_for_assessment(assessment.id)
    assert not any(a.action_category == ActionCategory.MANAGEMENT_ATTENTION for a in ai_actions)
    assert not any(a.rule_id == "ACT-R13-CRITICAL-REVIEW" for a in ai_actions)

    # 2. Human expert reviews and records authoritative ACTUAL_SIF
    review = await triage_service.ensure_review_for_assessment(assessment.id)
    await triage_service.claim_review(review.id, ReviewClaimRequest(reviewer_id="HSE_EXPERT"))
    await triage_service.submit_decision(
        review.id,
        ReviewDecisionRequest(
            reviewer_id="HSE_EXPERT",
            decision=ReviewDecision.CORRECT,
            final_classification=SIFClassification.ACTUAL_SIF,
            reviewer_rationale="Authoritatively confirmed as an actual SIF event with lost time injury.",
        ),
    )

    # Now authoritative reviewed state produces MANAGEMENT_ATTENTION (ACT-R13)
    reviewed_actions = await action_service.generate_actions_for_assessment(assessment.id)
    mgmt_actions = [a for a in reviewed_actions if a.action_category == ActionCategory.MANAGEMENT_ATTENTION]
    assert len(mgmt_actions) == 1
    assert mgmt_actions[0].rule_id == "ACT-R13-CRITICAL-REVIEW"
    assert mgmt_actions[0].priority == ActionPriority.CRITICAL_REVIEW


@pytest.mark.asyncio
async def test_correction_5_confirm_ai_does_not_arbitrarily_escalate_priority(db_session: AsyncSession):
    """Correction 5: CONFIRM_AI does not automatically transform every recommendation into CRITICAL_REVIEW."""
    sif_service = SIFAnalysisService(db_session)
    triage_service = TriageService(db_session)
    action_service = HSEActionRecommendationService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-CONFIRM-AI-PRIO",
            raw_text="While running 9-5/8 inch casing at Rig-04, the air winch line parted and the elevator swung across the rig floor.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04",
        )
    )
    ass_res = await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == res.report_id))
    assessment = ass_res.scalar_one()

    # Before review
    actions_before = await action_service.generate_actions_for_assessment(assessment.id)

    # Perform CONFIRM_AI
    review = await triage_service.ensure_review_for_assessment(assessment.id)
    await triage_service.claim_review(review.id, ReviewClaimRequest(reviewer_id="HSE_EXPERT"))
    await triage_service.submit_decision(
        review.id,
        ReviewDecisionRequest(
            reviewer_id="HSE_EXPERT",
            decision=ReviewDecision.CONFIRM_AI,
            reviewer_notes="Confirmed near miss assessment.",
        ),
    )

    # After CONFIRM_AI
    actions_after = await action_service.generate_actions_for_assessment(assessment.id)
    assert len(actions_before) == len(actions_after)
    for a_before, a_after in zip(actions_before, actions_after):
        assert a_before.priority == a_after.priority
        assert a_after.priority != ActionPriority.CRITICAL_REVIEW



