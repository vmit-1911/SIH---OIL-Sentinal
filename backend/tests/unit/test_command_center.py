"""Unit tests for Phase 10 HSE Command Center / Operational Intelligence API.

Validates read-only aggregations, descriptive metrics, multi-dimensional filters,
investigation snapshot linking, pagination, and data integrity.
"""

import uuid
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.action import HSEActionRecommendation
from app.db.models.assessment import SIFAssessment
from app.db.models.case import HSECase, HSECaseSourceAssociation
from app.db.models.concentration import RiskConcentration
from app.db.models.pattern import PrecursorPattern
from app.db.models.report import SafetyReport
from app.db.models.review import TriageReview
from app.db.models.taxonomy import LSRReportMapping, LSRTaxonomy
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
    ConcentrationStatus,
    EvidenceStrength,
    ObservedTrend,
    PatternStatus,
    PotentialOutcome,
    ReviewDecision,
    ReviewFeedbackCategory,
    ReviewState,
    SIFClassification,
    SourceType,
)
from app.services.command_center_service import CommandCenterService


# ==============================================================================
# SCENARIOS A - T
# ==============================================================================


@pytest.mark.asyncio
async def test_scenario_a_empty_database(db_session: AsyncSession):
    """Scenario A: Empty database returns graceful zero/empty responses without errors or fabricated data."""
    service = CommandCenterService(db_session)

    # 1. Overview
    overview = await service.get_overview()
    assert overview.total_reports == 0
    assert overview.total_assessments == 0
    assert overview.potential_sif_count == 0
    assert overview.non_sif_count == 0
    assert overview.undetermined_count == 0
    assert overview.reviewed_count == 0
    assert overview.unreviewed_count == 0
    assert overview.open_action_count == 0
    assert overview.active_case_count == 0
    assert overview.recurring_pattern_count == 0
    assert overview.concentration_count == 0

    # 2. SIF Overview
    sif_ov = await service.get_sif_overview()
    assert sif_ov.total_assessments == 0
    assert sif_ov.classification_counts == {}
    assert sif_ov.actual_severity_counts == {}
    assert sif_ov.potential_severity_counts == {}
    assert sif_ov.reviewed_count == 0
    assert sif_ov.unreviewed_count == 0
    assert sif_ov.assessment_trend_by_month == []

    # 3. Precursors
    prec_ov = await service.get_precursor_overview()
    assert prec_ov.total_patterns == 0
    assert prec_ov.top_patterns == []
    assert prec_ov.top_hazard_dimensions == []

    # 4. Concentrations
    conc_ov = await service.get_concentration_overview()
    assert conc_ov.total_concentrations == 0
    assert conc_ov.items == []
    assert all(count == 0 for count in conc_ov.dimension_counts.values())

    # 5. Actions
    act_ov = await service.get_action_overview()
    assert act_ov.total_actions == 0
    assert all(count == 0 for count in act_ov.status_counts.values())

    # 6. Cases
    case_ov = await service.get_case_overview()
    assert case_ov.total_cases == 0
    assert case_ov.active_case_count == 0
    assert case_ov.recently_updated_cases == []

    # 7. Reviews
    rev_ov = await service.get_review_queue_overview()
    assert rev_ov.total_reviews == 0
    assert rev_ov.pending_reviews == 0
    assert rev_ov.in_review_count == 0
    assert rev_ov.reviewed_count == 0

    # 8. Investigation Snapshot
    snap = await service.get_investigation_snapshot(report_ref="NON-EXISTENT")
    assert snap.reports == []
    assert snap.assessments == []
    assert snap.summary["report_count"] == 0


@pytest.mark.asyncio
async def test_scenario_b_c_reports_and_sif_classifications(db_session: AsyncSession):
    """Scenarios B & C: Mixed SIF classifications, potential SIF counts, severities, and monthly trend."""
    now = datetime.now(timezone.utc)
    rep1 = SafetyReport(report_ref="OIL-CC-REP-01", raw_text="Gas leak detected near manifold", source_type=SourceType.NEAR_MISS, reported_location="Moran Rig-01", actual_severity=ActualOutcome.NO_INJURY, created_at=now - timedelta(days=40))
    rep2 = SafetyReport(report_ref="OIL-CC-REP-02", raw_text="Worker observed without safety glasses", source_type=SourceType.UA, reported_location="Duliajan Central Workshop", actual_severity=ActualOutcome.NO_INJURY, created_at=now - timedelta(days=10))
    rep3 = SafetyReport(report_ref="OIL-CC-REP-03", raw_text="Minor pump leakage with uncertain hazard", source_type=SourceType.UC, reported_location="Moran Facility", actual_severity=ActualOutcome.FIRST_AID, created_at=now - timedelta(days=5))

    db_session.add_all([rep1, rep2, rep3])
    await db_session.flush()

    asm1 = SIFAssessment(report_id=rep1.id, sif_classification=SIFClassification.POTENTIAL_SIF, potential_severity=PotentialOutcome.FATALITY, evidence_score=0.92)
    asm2 = SIFAssessment(report_id=rep2.id, sif_classification=SIFClassification.NON_SIF, potential_severity=PotentialOutcome.LOW_IMPACT, evidence_score=0.15)
    asm3 = SIFAssessment(report_id=rep3.id, sif_classification=SIFClassification.UNDETERMINED, potential_severity=PotentialOutcome.PERMANENT_DISABLING_INJURY, evidence_score=0.45)

    db_session.add_all([asm1, asm2, asm3])
    await db_session.commit()

    service = CommandCenterService(db_session)
    overview = await service.get_overview()

    assert overview.total_reports == 3
    assert overview.total_assessments == 3
    assert overview.potential_sif_count == 1
    assert overview.non_sif_count == 1
    assert overview.undetermined_count == 1

    sif_ov = await service.get_sif_overview()
    assert sif_ov.total_assessments == 3
    assert sif_ov.classification_counts[SIFClassification.POTENTIAL_SIF.value] == 1
    assert sif_ov.classification_counts[SIFClassification.NON_SIF.value] == 1
    assert sif_ov.classification_counts[SIFClassification.UNDETERMINED.value] == 1
    assert sif_ov.potential_severity_counts[PotentialOutcome.FATALITY.value] == 1
    assert len(sif_ov.assessment_trend_by_month) >= 1


@pytest.mark.asyncio
async def test_scenario_d_review_queue_counts(db_session: AsyncSession):
    """Scenario D: Review queue workloads, decision breakdowns, feedback categories, and age buckets."""
    now = datetime.now(timezone.utc)
    rep1 = SafetyReport(report_ref="OIL-REV-REP-01", raw_text="Report 1", source_type=SourceType.NEAR_MISS)
    rep2 = SafetyReport(report_ref="OIL-REV-REP-02", raw_text="Report 2", source_type=SourceType.UA)
    rep3 = SafetyReport(report_ref="OIL-REV-REP-03", raw_text="Report 3", source_type=SourceType.UC)
    db_session.add_all([rep1, rep2, rep3])
    await db_session.flush()

    rev1 = TriageReview(report_id=rep1.id, status=ReviewState.PENDING, created_at=now - timedelta(days=2))
    rev2 = TriageReview(report_id=rep2.id, status=ReviewState.IN_REVIEW, created_at=now - timedelta(days=15))
    rev3 = TriageReview(
        report_id=rep3.id,
        status=ReviewState.REVIEWED,
        decision=ReviewDecision.CONFIRM_AI,
        feedback_category=ReviewFeedbackCategory.CLASSIFICATION_ERROR,
        reviewer_id="auditor_lead",
        created_at=now - timedelta(days=45),
    )
    db_session.add_all([rev1, rev2, rev3])
    await db_session.commit()

    service = CommandCenterService(db_session)
    rev_ov = await service.get_review_queue_overview()

    assert rev_ov.total_reviews == 3
    assert rev_ov.pending_reviews == 1
    assert rev_ov.in_review_count == 1
    assert rev_ov.reviewed_count == 1
    assert rev_ov.decision_distribution[ReviewDecision.CONFIRM_AI.value] == 1
    assert rev_ov.feedback_category_distribution[ReviewFeedbackCategory.CLASSIFICATION_ERROR.value] == 1
    assert rev_ov.age_of_pending_reviews["< 7 days"] == 1


@pytest.mark.asyncio
async def test_scenario_e_pattern_counts_and_dimensions(db_session: AsyncSession):
    """Scenario E: Precursor patterns, top hazard, barrier failure, activity, and location dimensions."""
    pat1 = PrecursorPattern(
        pattern_code="PAT-01",
        title="Suspended Load Rigging Failure",
        description="Rigging failure under crane boom",
        hazard_category="SUSPENDED_LOAD",
        activity_type="CRANE_LIFTING",
        failed_barrier_type="RIGGING_INSPECTION",
        lsr_code="LSR_03_SAFE_MECHANICAL_LIFTING",
        occurrence_count=5,
        affected_locations=["Moran Rig-01", "Duliajan Workshop"],
        supporting_report_ids=["R1", "R2", "R3", "R4", "R5"],
        status=PatternStatus.ACTIVE,
    )
    pat2 = PrecursorPattern(
        pattern_code="PAT-02",
        title="High Pressure Line Flange Leak",
        description="Hydrocarbon release during well testing",
        hazard_category="HIGH_PRESSURE_HYDROCARBON",
        activity_type="WELL_TESTING",
        failed_barrier_type="ISOLATION_VALVE",
        lsr_code="LSR_02_ENERGY_ISOLATION",
        occurrence_count=3,
        affected_locations=["Digboi Production Site"],
        supporting_report_ids=["R6", "R7", "R8"],
        status=PatternStatus.ACTIVE,
    )
    db_session.add_all([pat1, pat2])
    await db_session.commit()

    service = CommandCenterService(db_session)
    prec_ov = await service.get_precursor_overview()

    assert prec_ov.total_patterns == 2
    assert len(prec_ov.top_patterns) == 2
    assert prec_ov.top_patterns[0].pattern_code == "PAT-01"
    assert prec_ov.top_patterns[0].occurrence_count == 5

    # Check dimension rankings
    assert any(d.name == "SUSPENDED_LOAD" and d.count == 5 for d in prec_ov.top_hazard_dimensions)
    assert any(d.name == "RIGGING_INSPECTION" and d.count == 5 for d in prec_ov.top_barrier_failure_dimensions)
    assert any(d.name == "CRANE_LIFTING" and d.count == 5 for d in prec_ov.top_activity_dimensions)


@pytest.mark.asyncio
async def test_scenario_f_concentration_canonical_dimensions(db_session: AsyncSession):
    """Scenario F: Risk concentrations exposed strictly across the 6 canonical dimensions."""
    now = datetime.now(timezone.utc)
    conc1 = RiskConcentration(
        concentration_key="CONC|LOCATION|MORAN",
        dimension_type=ConcentrationDimension.LOCATION,
        dimension_value="Moran Rig-01",
        occurrence_count=7,
        distinct_report_count=6,
        distinct_location_count=1,
        observed_trend=ObservedTrend.INCREASING,
        supporting_locations=["Moran Rig-01"],
        first_observed_at=now - timedelta(days=30),
        last_observed_at=now,
        status=ConcentrationStatus.ACTIVE,
    )
    conc2 = RiskConcentration(
        concentration_key="CONC|HAZARD|GAS_LEAK",
        dimension_type=ConcentrationDimension.HAZARD,
        dimension_value="TOXIC_GAS_RELEASE",
        occurrence_count=4,
        distinct_report_count=4,
        distinct_location_count=2,
        observed_trend=ObservedTrend.STABLE,
        supporting_locations=["Moran Rig-01", "Duliajan"],
        first_observed_at=now - timedelta(days=20),
        last_observed_at=now,
        status=ConcentrationStatus.ACTIVE,
    )
    db_session.add_all([conc1, conc2])
    await db_session.commit()

    service = CommandCenterService(db_session)
    conc_ov = await service.get_concentration_overview()

    assert conc_ov.total_concentrations == 2
    assert conc_ov.dimension_counts[ConcentrationDimension.LOCATION.value] == 1
    assert conc_ov.dimension_counts[ConcentrationDimension.HAZARD.value] == 1
    assert conc_ov.dimension_counts[ConcentrationDimension.BARRIER_FAILURE.value] == 0
    assert conc_ov.dimension_counts[ConcentrationDimension.ACTIVITY.value] == 0
    assert conc_ov.dimension_counts[ConcentrationDimension.LIFE_SAVING_RULE.value] == 0
    assert conc_ov.dimension_counts[ConcentrationDimension.PATTERN.value] == 0


@pytest.mark.asyncio
async def test_scenario_g_lsr_distribution(db_session: AsyncSession):
    """Scenario G: Descriptive LSR distributions across taxonomy rules, mappings, potential SIFs, and actions."""
    # Seed Taxonomy
    tax = LSRTaxonomy(
        taxonomy_id="IOGP_459",
        authority="IOGP",
        version="2018",
        name="IOGP Life-Saving Rules",
        description="Standard 9 rules",
        rules=[
            {"code": "LSR_01_BYPASSING_SAFETY_CONTROLS", "name": "Bypassing Safety Controls"},
            {"code": "LSR_02_ENERGY_ISOLATION", "name": "Energy Isolation"},
        ],
        active=True,
    )
    db_session.add(tax)
    await db_session.flush()

    rep = SafetyReport(report_ref="OIL-LSR-REP-01", raw_text="Lockout tagout ignored on main valve", source_type=SourceType.UA)
    db_session.add(rep)
    await db_session.flush()

    asm = SIFAssessment(report_id=rep.id, sif_classification=SIFClassification.POTENTIAL_SIF, potential_severity=PotentialOutcome.FATALITY, evidence_score=0.95)
    db_session.add(asm)

    map1 = LSRReportMapping(
        report_id=rep.id,
        taxonomy_id=tax.id,
        rule_code="LSR_02_ENERGY_ISOLATION",
        rule_name="Energy Isolation",
        confidence_score=0.9,
    )
    db_session.add(map1)

    act = HSEActionRecommendation(
        action_key="ACT-LSR-001",
        source_type=ActionSourceType.ASSESSMENT,
        source_id=str(asm.id),
        action_category=ActionCategory.ENERGY_ISOLATION_VERIFICATION,
        action_title="Conduct LOTO Standdown",
        action_description="Desc",
        priority=ActionPriority.HIGH,
        rationale="Isolation bypass",
        rule_id="LSR_02_ENERGY_ISOLATION",
        status=ActionStatus.OPEN,
    )
    db_session.add(act)
    await db_session.commit()

    service = CommandCenterService(db_session)
    lsr_ov = await service.get_lsr_overview()

    assert lsr_ov.total_lsr_rules >= 2
    rule2 = next(r for r in lsr_ov.rules if r.rule_code == "LSR_02_ENERGY_ISOLATION")
    assert rule2.assessment_count == 1
    assert rule2.potential_sif_count == 1
    assert rule2.open_action_count == 1


@pytest.mark.asyncio
async def test_scenario_h_i_action_and_case_distribution(db_session: AsyncSession):
    """Scenarios H & I: Action statuses, priorities, age distribution and Case statuses, priorities, types, owners."""
    now = datetime.now(timezone.utc)

    # Actions
    act1 = HSEActionRecommendation(
        action_key="ACT-TEST-01",
        source_type=ActionSourceType.ASSESSMENT,
        source_id="ASM-01",
        action_category=ActionCategory.BARRIER_VERIFICATION,
        action_title="Valve Pop Test",
        action_description="Desc",
        priority=ActionPriority.HIGH,
        rationale="Overpressure",
        rule_id="ACT-R01-BARRIER",
        status=ActionStatus.OPEN,
        created_at=now - timedelta(days=2),
    )
    act2 = HSEActionRecommendation(
        action_key="ACT-TEST-02",
        source_type=ActionSourceType.PATTERN,
        source_id="PAT-01",
        action_category=ActionCategory.PROCEDURE_REVIEW,
        action_title="Procedure Review",
        action_description="Desc",
        priority=ActionPriority.MEDIUM,
        rationale="Recurring pattern",
        rule_id="ACT-R10-PATTERN",
        status=ActionStatus.COMPLETED,
        created_at=now - timedelta(days=40),
    )
    db_session.add_all([act1, act2])

    # Cases
    case1 = HSECase(
        case_key="CASE-TEST-01",
        title="Well Control Investigation",
        case_type=CaseType.SIF_INVESTIGATION,
        status=CaseStatus.INVESTIGATING,
        priority=CasePriority.CRITICAL_REVIEW,
        owner="lead_inspector",
        created_by="auditor_test",
    )
    case2 = HSECase(
        case_key="CASE-TEST-02",
        title="Routine Rig Inspection",
        case_type=CaseType.ACTIVITY_REVIEW,
        status=CaseStatus.CLOSED,
        priority=CasePriority.INFORMATIONAL,
        owner="junior_engineer",
        created_by="auditor_test",
        closure_rationale="All tasks done",
    )
    db_session.add_all([case1, case2])
    await db_session.commit()

    service = CommandCenterService(db_session)

    act_ov = await service.get_action_overview()
    assert act_ov.total_actions == 2
    assert act_ov.status_counts[ActionStatus.OPEN.value] == 1
    assert act_ov.status_counts[ActionStatus.COMPLETED.value] == 1
    assert act_ov.open_actions_by_age["< 7 days"] == 1

    case_ov = await service.get_case_overview()
    assert case_ov.total_cases == 2
    assert case_ov.active_case_count == 1
    assert case_ov.status_counts[CaseStatus.INVESTIGATING.value] == 1
    assert case_ov.status_counts[CaseStatus.CLOSED.value] == 1
    assert case_ov.owner_distribution["lead_inspector"] == 1
    assert len(case_ov.recently_updated_cases) == 2


@pytest.mark.asyncio
async def test_scenario_j_k_l_m_filtering_and_combinations(db_session: AsyncSession):
    """Scenarios J, K, L, M: Date range, location, LSR, and combined filter criteria."""
    now = datetime.now(timezone.utc)
    t1 = now - timedelta(days=60)
    t2 = now - timedelta(days=10)

    rep_old = SafetyReport(report_ref="REP-OLD", raw_text="Old report text", reported_location="Moran Rig-01", created_at=t1)
    rep_new = SafetyReport(report_ref="REP-NEW", raw_text="New report text", reported_location="Duliajan Workshop", created_at=t2)
    db_session.add_all([rep_old, rep_new])
    await db_session.flush()

    asm_old = SIFAssessment(report_id=rep_old.id, sif_classification=SIFClassification.POTENTIAL_SIF)
    asm_new = SIFAssessment(report_id=rep_new.id, sif_classification=SIFClassification.NON_SIF)
    db_session.add_all([asm_old, asm_new])
    await db_session.commit()

    service = CommandCenterService(db_session)

    # Date filter: only recent 30 days
    recent_ov = await service.get_overview(from_date=now - timedelta(days=30), to_date=now)
    assert recent_ov.total_reports == 1
    assert recent_ov.potential_sif_count == 0
    assert recent_ov.non_sif_count == 1

    # Location filter: Moran only
    moran_ov = await service.get_overview(location="Moran")
    assert moran_ov.total_reports == 1
    assert moran_ov.potential_sif_count == 1

    # Combined filter: Moran AND recent 30 days -> 0 matches
    empty_ov = await service.get_overview(from_date=now - timedelta(days=30), to_date=now, location="Moran")
    assert empty_ov.total_reports == 0


@pytest.mark.asyncio
async def test_scenario_n_o_pagination_and_deterministic_ordering(db_session: AsyncSession):
    """Scenarios N & O: Pagination limits, offsets, and deterministic sorting."""
    for i in range(10):
        conc = RiskConcentration(
            concentration_key=f"CONC-PAGE-{i:02d}",
            dimension_type=ConcentrationDimension.LOCATION,
            dimension_value=f"Site-{i}",
            occurrence_count=10 - i,  # Decreasing count
            distinct_report_count=2,
            distinct_location_count=1,
            first_observed_at=datetime.now(timezone.utc),
            last_observed_at=datetime.now(timezone.utc),
            status=ConcentrationStatus.ACTIVE,
        )
        db_session.add(conc)
    await db_session.commit()

    service = CommandCenterService(db_session)

    page1 = await service.get_concentration_overview(limit=3, offset=0)
    assert page1.total_concentrations >= 10
    assert len(page1.items) == 3
    assert page1.items[0].occurrence_count == 10
    assert page1.items[1].occurrence_count == 9
    assert page1.items[2].occurrence_count == 8

    page2 = await service.get_concentration_overview(limit=3, offset=3)
    assert len(page2.items) == 3
    assert page2.items[0].occurrence_count == 7
    assert page2.items[1].occurrence_count == 6


@pytest.mark.asyncio
async def test_scenario_p_investigation_snapshot_chain(db_session: AsyncSession):
    """Scenario P: Compact operational chain linking reports, assessments, patterns, concentrations, reviews, actions, cases."""
    rep = SafetyReport(report_ref="OIL-SNAP-01", raw_text="High pressure hydrocarbon leak during hot work", source_type=SourceType.NEAR_MISS, reported_location="Moran Rig-08")
    db_session.add(rep)
    await db_session.flush()

    pat = PrecursorPattern(pattern_code="PAT-SNAP-01", title="Hydrocarbon Leak Pattern", description="Desc", occurrence_count=3, supporting_report_ids=[str(rep.id)], status=PatternStatus.ACTIVE)
    db_session.add(pat)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    conc = RiskConcentration(concentration_key="CONC-SNAP-01", dimension_type=ConcentrationDimension.HAZARD, dimension_value="GAS_RELEASE", pattern_id=pat.id, occurrence_count=3, distinct_report_count=1, distinct_location_count=1, first_observed_at=now, last_observed_at=now, supporting_report_ids=[str(rep.id)], status=ConcentrationStatus.ACTIVE)
    db_session.add(conc)
    await db_session.flush()

    asm = SIFAssessment(report_id=rep.id, sif_classification=SIFClassification.POTENTIAL_SIF, potential_severity=PotentialOutcome.FATALITY, evidence_score=0.91, precursor_signature="GAS_LEAK|HOT_WORK", pattern_id=pat.id)
    db_session.add(asm)
    await db_session.flush()

    rev = TriageReview(report_id=rep.id, assessment_id=asm.id, status=ReviewState.REVIEWED, decision=ReviewDecision.CONFIRM_AI, reviewer_id="auditor_raj")
    db_session.add(rev)
    await db_session.flush()

    act = HSEActionRecommendation(action_key="ACT-SNAP-01", source_type=ActionSourceType.ASSESSMENT, source_id=str(asm.id), action_category=ActionCategory.HOT_WORK_CONTROL_REVIEW, action_title="Hot Work Audit", action_description="Audit permit", priority=ActionPriority.HIGH, rationale="Near-miss", rule_id="ACT-R01", status=ActionStatus.OPEN)
    db_session.add(act)
    await db_session.flush()

    case_obj = HSECase(case_key="CASE-SNAP-01", title="Rig-08 Gas Leak Investigation", case_type=CaseType.SIF_INVESTIGATION, status=CaseStatus.INVESTIGATING, priority=CasePriority.CRITICAL_REVIEW, created_by="auditor_raj")
    db_session.add(case_obj)
    await db_session.flush()

    assoc = HSECaseSourceAssociation(case_id=case_obj.id, source_type=CaseSourceType.REPORT, source_id="OIL-SNAP-01", attached_by="auditor_raj")
    db_session.add(assoc)
    await db_session.commit()

    service = CommandCenterService(db_session)

    # 1. Query by report_ref
    snap_by_rep = await service.get_investigation_snapshot(report_ref="OIL-SNAP-01")
    assert snap_by_rep.summary["report_count"] == 1
    assert snap_by_rep.summary["assessment_count"] == 1
    assert snap_by_rep.summary["pattern_count"] == 1
    assert snap_by_rep.summary["review_count"] == 1
    assert snap_by_rep.summary["action_count"] == 1

    # 2. Query by case_key
    snap_by_case = await service.get_investigation_snapshot(case_key="CASE-SNAP-01")
    assert snap_by_case.summary["case_count"] == 1
    assert snap_by_case.summary["report_count"] == 1
    assert snap_by_case.cases[0].case_key == "CASE-SNAP-01"

    # 3. Query by pattern_code
    snap_by_pat = await service.get_investigation_snapshot(pattern_code="PAT-SNAP-01")
    assert snap_by_pat.summary["pattern_count"] == 1
    assert snap_by_pat.summary["report_count"] == 1


@pytest.mark.asyncio
async def test_scenario_q_r_s_read_only_and_source_integrity(db_session: AsyncSession):
    """Scenarios Q, R, S: Verify Command Center operations NEVER mutate underlying records and never fabricate data."""
    rep = SafetyReport(report_ref="OIL-IMMUT-01", raw_text="Original narrative text", source_type=SourceType.NEAR_MISS, reported_location="Moran")
    db_session.add(rep)
    await db_session.flush()

    asm = SIFAssessment(report_id=rep.id, sif_classification=SIFClassification.POTENTIAL_SIF, potential_severity=PotentialOutcome.FATALITY, evidence_score=0.89)
    db_session.add(asm)
    await db_session.commit()

    service = CommandCenterService(db_session)

    # Execute all read-only overview methods
    await service.get_overview()
    await service.get_sif_overview()
    await service.get_precursor_overview()
    await service.get_concentration_overview()
    await service.get_lsr_overview()
    await service.get_action_overview()
    await service.get_case_overview()
    await service.get_review_queue_overview()
    await service.get_investigation_snapshot(report_ref="OIL-IMMUT-01")

    # Assert underlying entity remains strictly unchanged
    refreshed_rep = await db_session.get(SafetyReport, rep.id)
    refreshed_asm = await db_session.get(SIFAssessment, asm.id)

    assert refreshed_rep.raw_text == "Original narrative text"
    assert refreshed_rep.reported_location == "Moran"
    assert refreshed_asm.sif_classification == SIFClassification.POTENTIAL_SIF
    assert refreshed_asm.evidence_score == 0.89
