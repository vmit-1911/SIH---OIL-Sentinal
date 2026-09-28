"""Unit tests for Phase 9 HSE Case Management & Operational Follow-up."""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ActionNotFoundException,
    AssessmentNotFoundException,
    CaseClosureBlockedException,
    CaseNotFoundException,
    CaseSourceNotFoundException,
    ConcentrationNotFoundException,
    DuplicateSourceAssociationException,
    InvalidStateTransitionException,
    PatternNotFoundException,
    ReportNotFoundException,
    ReviewNotFoundException,
)
from app.db.models.action import HSEActionRecommendation
from app.db.models.assessment import SIFAssessment
from app.db.models.case import HSECase, HSECaseEvent, HSECaseSourceAssociation
from app.db.models.concentration import RiskConcentration
from app.db.models.pattern import PrecursorPattern
from app.db.models.report import SafetyReport
from app.db.models.review import TriageReview
from app.domain.enums import (
    ActionCategory,
    ActionPriority,
    ActionSourceType,
    ActionStatus,
    ActualOutcome,
    CaseEventType,
    CasePriority,
    CaseSourceType,
    CaseStatus,
    CaseType,
    ConcentrationDimension,
    ConcentrationStatus,
    ObservedTrend,
    PatternStatus,
    PotentialOutcome,
    ReviewDecision,
    ReviewState,
    SIFClassification,
    SourceType,
)
from app.schemas.action import ActionStatusUpdateRequest
from app.schemas.case import (
    HSECaseAssignRequest,
    HSECaseCreateRequest,
    HSECaseReopenRequest,
    HSECaseSourceAttachRequest,
    HSECaseStatusUpdateRequest,
    HSECaseUpdateRequest,
    SourceReferenceInput,
)
from app.schemas.report import SingleReportAnalysisRequest
from app.services.action_service import HSEActionRecommendationService
from app.services.case_service import HSECaseManagementService
from app.services.sif_analysis_service import SIFAnalysisService
from app.services.triage_service import TriageService


@pytest.mark.asyncio
async def test_scenario_a_create_case_from_report(db_session: AsyncSession):
    """Scenario A: Create an HSE case referencing a safety report."""
    sif_service = SIFAnalysisService(db_session)
    analysis = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="OIL-CASE-REP-001",
            raw_text="Driller observed high gas influx during tripping out of hole at Rig-08.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-08 / Moran",
        )
    )

    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="Rig-08 Gas Influx Tripping Investigation",
            description="Detailed operational investigation into high gas influx near-miss.",
            case_type=CaseType.SIF_INVESTIGATION,
            priority=CasePriority.HIGH,
            created_by="auditor_rajesh",
            sources=[
                SourceReferenceInput(
                    source_type=CaseSourceType.REPORT,
                    source_id=str(analysis.report_id),
                    source_metadata={"report_ref": "OIL-CASE-REP-001", "location": "Rig-08 / Moran"},
                )
            ],
        )
    )

    assert case_dto.id is not None
    assert case_dto.case_key.startswith("CASE-")
    assert case_dto.title == "Rig-08 Gas Influx Tripping Investigation"
    assert case_dto.status == CaseStatus.OPEN
    assert case_dto.priority == CasePriority.HIGH
    assert len(case_dto.sources) == 1
    assert case_dto.sources[0].source_type == CaseSourceType.REPORT
    assert case_dto.sources[0].source_id == str(analysis.report_id)


@pytest.mark.asyncio
async def test_scenario_b_create_case_from_assessment(db_session: AsyncSession):
    """Scenario B: Create an HSE case referencing a SIF assessment."""
    sif_service = SIFAnalysisService(db_session)
    analysis = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="OIL-CASE-ASM-001",
            raw_text="Scaffolder unclipped safety harness while working on 15-meter derrick monkey board.",
            source_type=SourceType.UA,
            reported_location="Derrick Monkey Board",
        )
    )

    asm_res = await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == analysis.report_id))
    assessment = asm_res.scalar_one()

    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="Working at Height Unclipped Harness Investigation",
            case_type=CaseType.SIF_INVESTIGATION,
            priority=CasePriority.CRITICAL_REVIEW,
            created_by="auditor_priya",
            sources=[
                SourceReferenceInput(
                    source_type=CaseSourceType.ASSESSMENT,
                    source_id=str(assessment.id),
                    source_metadata={"classification": assessment.sif_classification.value},
                )
            ],
        )
    )

    assert case_dto.status == CaseStatus.OPEN
    assert case_dto.priority == CasePriority.CRITICAL_REVIEW
    assert len(case_dto.sources) == 1
    assert case_dto.sources[0].source_type == CaseSourceType.ASSESSMENT
    assert case_dto.sources[0].source_id == str(assessment.id)


@pytest.mark.asyncio
async def test_scenario_c_create_case_from_pattern(db_session: AsyncSession):
    """Scenario C: Create an HSE case referencing a recurring precursor pattern."""
    pattern = PrecursorPattern(
        pattern_code="PAT-H2S-VALVE-FAIL-01",
        title="Recurring H2S Gland Packing Leakage Pattern",
        description="Repeated H2S gas release during wellhead valve maintenance.",
        status=PatternStatus.ACTIVE,
    )
    db_session.add(pattern)
    await db_session.commit()

    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="H2S Valve Packing Recurring Failure Case",
            case_type=CaseType.PATTERN_INVESTIGATION,
            priority=CasePriority.HIGH,
            created_by="hse_manager_anand",
            sources=[
                SourceReferenceInput(
                    source_type=CaseSourceType.PATTERN,
                    source_id=str(pattern.pattern_code),
                    source_metadata={"pattern_code": pattern.pattern_code},
                )
            ],
        )
    )

    assert case_dto.case_type == CaseType.PATTERN_INVESTIGATION
    assert len(case_dto.sources) == 1
    assert case_dto.sources[0].source_type == CaseSourceType.PATTERN
    assert case_dto.sources[0].source_id == "PAT-H2S-VALVE-FAIL-01"


@pytest.mark.asyncio
async def test_scenario_d_create_case_from_concentration(db_session: AsyncSession):
    """Scenario D: Create an HSE case referencing a risk concentration finding."""
    now = datetime.now(timezone.utc)
    conc = RiskConcentration(
        concentration_key="CONC-FALL_PROTECTION-BARRIER_FAILURE",
        dimension_type=ConcentrationDimension.BARRIER_FAILURE,
        dimension_value="FALL_PROTECTION_FAILURE",
        status=ConcentrationStatus.ACTIVE,
        occurrence_count=8,
        first_observed_at=now,
        last_observed_at=now,
        observed_trend=ObservedTrend.INCREASING,
    )
    db_session.add(conc)
    await db_session.commit()

    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="Fall Protection Barrier Degradation Review",
            case_type=CaseType.BARRIER_REVIEW,
            priority=CasePriority.HIGH,
            created_by="barrier_lead_kavita",
            sources=[
                SourceReferenceInput(
                    source_type=CaseSourceType.CONCENTRATION,
                    source_id=str(conc.concentration_key),
                    source_metadata={"occurrence_count": 8, "trend": "INCREASING"},
                )
            ],
        )
    )

    assert case_dto.case_type == CaseType.BARRIER_REVIEW
    assert len(case_dto.sources) == 1
    assert case_dto.sources[0].source_type == CaseSourceType.CONCENTRATION
    assert case_dto.sources[0].source_id == "CONC-FALL_PROTECTION-BARRIER_FAILURE"


@pytest.mark.asyncio
async def test_scenario_e_attach_multiple_source_types(db_session: AsyncSession):
    """Scenario E: Create case and attach all 6 supported source intelligence types."""
    sif_service = SIFAnalysisService(db_session)
    analysis = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="OIL-CASE-MULTI-001",
            raw_text="During crane lifting at Central Tank Farm, the wire rope sling snapped dropping a 4-ton manifold.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Central Tank Farm",
        )
    )

    # 1. Action recommendation
    action_rec = HSEActionRecommendation(
        action_key="ACT-CASE-MULTI-001",
        source_type=ActionSourceType.ASSESSMENT,
        source_id=str(analysis.report_id),
        action_category=ActionCategory.BARRIER_VERIFICATION,
        action_title="Conduct Rigging Gear Inspection",
        action_description="Operational verification of all wire slings.",
        priority=ActionPriority.HIGH,
        rationale="Wire rope sling parted during lifting operation.",
        rule_id="ACT-R01-BARRIER",
        status=ActionStatus.OPEN,
    )
    db_session.add(action_rec)

    # 2. Assessment
    asm_res = await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == analysis.report_id))
    assessment = asm_res.scalar_one()

    # 3. Human Review
    triage_service = TriageService(db_session)
    triage = await triage_service.ensure_review_for_assessment(assessment.id)


    # 4. Pattern
    pattern = PrecursorPattern(
        pattern_code="PAT-LIFTING-SLING-SNAP",
        title="Lifting Rigging Equipment Failure Pattern",
        description="Crane sling failure during lift",
        status=PatternStatus.ACTIVE,
    )
    db_session.add(pattern)

    # 5. Concentration
    now = datetime.now(timezone.utc)
    conc = RiskConcentration(
        concentration_key="CONC-LIFTING-OPS-LOC",
        dimension_type=ConcentrationDimension.LOCATION,
        dimension_value="Central Tank Farm",
        status=ConcentrationStatus.ACTIVE,
        occurrence_count=5,
        first_observed_at=now,
        last_observed_at=now,
    )
    db_session.add(conc)
    await db_session.commit()

    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="CTF Rigging Failure Comprehensive Investigation",
            case_type=CaseType.SIF_INVESTIGATION,
            priority=CasePriority.CRITICAL_REVIEW,
            created_by="lead_investigator_neha",
            sources=[
                SourceReferenceInput(source_type=CaseSourceType.REPORT, source_id=str(analysis.report_id)),
                SourceReferenceInput(source_type=CaseSourceType.ASSESSMENT, source_id=str(assessment.id)),
                SourceReferenceInput(source_type=CaseSourceType.PATTERN, source_id=pattern.pattern_code),
                SourceReferenceInput(source_type=CaseSourceType.CONCENTRATION, source_id=conc.concentration_key),
                SourceReferenceInput(source_type=CaseSourceType.REVIEW, source_id=str(triage.id)),
                SourceReferenceInput(source_type=CaseSourceType.ACTION, source_id=str(action_rec.id)),
            ],
        )
    )

    assert len(case_dto.sources) == 6
    attached_types = {s.source_type for s in case_dto.sources}
    assert attached_types == {
        CaseSourceType.REPORT,
        CaseSourceType.ASSESSMENT,
        CaseSourceType.PATTERN,
        CaseSourceType.CONCENTRATION,
        CaseSourceType.REVIEW,
        CaseSourceType.ACTION,
    }




@pytest.mark.asyncio
async def test_scenario_f_duplicate_source_attachment_rejected(db_session: AsyncSession):
    """Scenario F: Duplicate source attachment to the same case is rejected."""
    report = SafetyReport(
        report_ref="REP-DUP-001",
        raw_text="Worker observed missing valve cap during pre-shift tour.",
        source_type=SourceType.UC,
    )
    db_session.add(report)
    await db_session.commit()

    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="Duplicate Source Attachment Test Case",
            created_by="auditor_test",
            sources=[
                SourceReferenceInput(source_type=CaseSourceType.REPORT, source_id="REP-DUP-001"),
            ],
        )
    )

    # Attempting to attach the exact same source to the case must raise DuplicateSourceAssociationException
    with pytest.raises(DuplicateSourceAssociationException):
        await case_service.attach_source(
            case_id=case_dto.id,
            request=HSECaseSourceAttachRequest(
                source_type=CaseSourceType.REPORT,
                source_id="REP-DUP-001",
                actor_id="auditor_test",
            ),
        )


@pytest.mark.asyncio
async def test_scenario_g_valid_lifecycle_transitions(db_session: AsyncSession):
    """Scenario G: Case follows deterministic lifecycle: OPEN -> TRIAGE -> INVESTIGATING -> ACTION_REQUIRED -> PENDING_VERIFICATION -> CLOSED."""
    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="Lifecycle Progression Test Case",
            created_by="auditor_progress",
        )
    )
    assert case_dto.status == CaseStatus.OPEN

    # 1. OPEN -> TRIAGE
    case_dto = await case_service.update_case_status(
        case_id=case_dto.id,
        request=HSECaseStatusUpdateRequest(status=CaseStatus.TRIAGE, actor_id="auditor_progress"),
    )
    assert case_dto.status == CaseStatus.TRIAGE

    # 2. TRIAGE -> INVESTIGATING
    case_dto = await case_service.update_case_status(
        case_id=case_dto.id,
        request=HSECaseStatusUpdateRequest(status=CaseStatus.INVESTIGATING, actor_id="investigator_lead"),
    )
    assert case_dto.status == CaseStatus.INVESTIGATING

    # 3. INVESTIGATING -> ACTION_REQUIRED
    case_dto = await case_service.update_case_status(
        case_id=case_dto.id,
        request=HSECaseStatusUpdateRequest(status=CaseStatus.ACTION_REQUIRED, actor_id="investigator_lead"),
    )
    assert case_dto.status == CaseStatus.ACTION_REQUIRED

    # 4. ACTION_REQUIRED -> PENDING_VERIFICATION
    case_dto = await case_service.update_case_status(
        case_id=case_dto.id,
        request=HSECaseStatusUpdateRequest(status=CaseStatus.PENDING_VERIFICATION, actor_id="verifier_raj"),
    )
    assert case_dto.status == CaseStatus.PENDING_VERIFICATION

    # 5. PENDING_VERIFICATION -> CLOSED
    case_dto = await case_service.update_case_status(
        case_id=case_dto.id,
        request=HSECaseStatusUpdateRequest(
            status=CaseStatus.CLOSED,
            actor_id="hse_head",
            rationale="All physical barrier verification tests passed and site personnel trained.",
        ),
    )
    assert case_dto.status == CaseStatus.CLOSED
    assert case_dto.closed_at is not None
    assert case_dto.closure_rationale == "All physical barrier verification tests passed and site personnel trained."


@pytest.mark.asyncio
async def test_scenario_h_invalid_lifecycle_transition_rejected(db_session: AsyncSession):
    """Scenario H: Invalid lifecycle transitions are rejected with 400 error."""
    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="Invalid Transition Test Case",
            created_by="auditor_test",
        )
    )
    assert case_dto.status == CaseStatus.OPEN

    # Attempting to jump directly from OPEN to CLOSED must fail
    with pytest.raises(InvalidStateTransitionException):
        await case_service.update_case_status(
            case_id=case_dto.id,
            request=HSECaseStatusUpdateRequest(
                status=CaseStatus.CLOSED,
                actor_id="auditor_test",
                rationale="Premature closure attempt",
            ),
        )

    # Attempting to jump directly from OPEN to PENDING_VERIFICATION must fail
    with pytest.raises(InvalidStateTransitionException):
        await case_service.update_case_status(
            case_id=case_dto.id,
            request=HSECaseStatusUpdateRequest(
                status=CaseStatus.PENDING_VERIFICATION,
                actor_id="auditor_test",
            ),
        )


@pytest.mark.asyncio
async def test_scenario_i_assign_owner(db_session: AsyncSession):
    """Scenario I: Assigning an owner updates case ownership, assigned_at, and creates an audit event."""
    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="Unassigned Case",
            created_by="intake_officer",
        )
    )
    assert case_dto.owner is None
    assert case_dto.assigned_at is None

    case_dto = await case_service.assign_case(
        case_id=case_dto.id,
        request=HSECaseAssignRequest(
            owner="inspector_vikram",
            actor_id="hse_lead",
            rationale="Assigned to Vikram due to domain expertise in well control.",
        ),
    )
    assert case_dto.owner == "inspector_vikram"
    assert case_dto.assigned_at is not None


@pytest.mark.asyncio
async def test_scenario_j_case_timeline_generated(db_session: AsyncSession):
    """Scenario J: Append-only case timeline logs every lifecycle and source mutation in order."""
    report = SafetyReport(
        report_ref="REP-TL-001",
        raw_text="Worker stepped over open grating without barricade.",
        source_type=SourceType.UA,
    )
    db_session.add(report)
    await db_session.commit()

    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="Timeline Validation Case",
            created_by="user_a",
        )
    )

    await case_service.assign_case(
        case_id=case_dto.id,
        request=HSECaseAssignRequest(owner="user_b", actor_id="user_a", rationale="Initial assignment"),
    )

    await case_service.attach_source(
        case_id=case_dto.id,
        request=HSECaseSourceAttachRequest(
            source_type=CaseSourceType.REPORT,
            source_id="REP-TL-001",
            actor_id="user_b",
        ),
    )

    await case_service.update_case_status(
        case_id=case_dto.id,
        request=HSECaseStatusUpdateRequest(status=CaseStatus.INVESTIGATING, actor_id="user_b"),
    )

    timeline = await case_service.get_case_timeline(case_dto.id)
    assert len(timeline) >= 4

    event_types = [e.event_type for e in timeline]
    assert event_types[0] == CaseEventType.CASE_CREATED
    assert CaseEventType.CASE_ASSIGNED in event_types
    assert CaseEventType.SOURCE_ATTACHED in event_types
    assert CaseEventType.CASE_STATUS_CHANGED in event_types


@pytest.mark.asyncio
async def test_scenario_k_action_attachment_and_events(db_session: AsyncSession):
    """Scenario K: Attaching and detaching actions emit ACTION_ATTACHED and ACTION_DETACHED events."""
    action_rec = HSEActionRecommendation(
        action_key="ACT-TEST-ATTACH-001",
        source_type=ActionSourceType.ASSESSMENT,
        source_id="ASM-UUID-001",
        action_category=ActionCategory.BARRIER_VERIFICATION,
        action_title="Verify BOP Pressure Test Records",
        action_description="Check third-party calibration logs.",
        priority=ActionPriority.HIGH,
        rationale="Pressure test log indicated potential delay.",
        rule_id="ACT-R01-BARRIER",
        status=ActionStatus.OPEN,
    )
    db_session.add(action_rec)
    await db_session.commit()

    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(title="Action Event Test Case", created_by="auditor_test")
    )

    # Attach action
    case_dto = await case_service.attach_source(
        case_id=case_dto.id,
        request=HSECaseSourceAttachRequest(
            source_type=CaseSourceType.ACTION,
            source_id=str(action_rec.id),
            actor_id="auditor_test",
        ),
    )
    assert len(case_dto.sources) == 1

    # Check timeline for ACTION_ATTACHED event
    timeline = await case_service.get_case_timeline(case_dto.id)
    assert any(e.event_type == CaseEventType.ACTION_ATTACHED for e in timeline)

    # Detach action
    case_dto = await case_service.detach_source(
        case_id=case_dto.id,
        source_id_or_assoc_id=str(action_rec.id),
        actor_id="auditor_test",
        rationale="Action reassigned to another case",
    )
    assert len(case_dto.sources) == 0

    # Check timeline for ACTION_DETACHED event
    timeline = await case_service.get_case_timeline(case_dto.id)
    assert any(e.event_type == CaseEventType.ACTION_DETACHED for e in timeline)


@pytest.mark.asyncio
async def test_scenario_l_existing_action_status_remains_authoritative(db_session: AsyncSession):
    """Scenario L: Phase 8 action recommendations are authoritative; case attachment does not alter action status."""
    action_rec = HSEActionRecommendation(
        action_key="ACT-AUTH-TEST-001",
        source_type=ActionSourceType.ASSESSMENT,
        source_id="ASM-AUTH-001",
        action_category=ActionCategory.LINE_OF_FIRE_CONTROL_REVIEW,
        action_title="Conduct Line of Fire Stand-down",
        action_description="Operational standdown on rig floor.",
        priority=ActionPriority.HIGH,
        rationale="Line of fire precursor identified.",
        rule_id="ACT-R03-LSR",
        status=ActionStatus.IN_PROGRESS,
    )
    db_session.add(action_rec)
    await db_session.commit()

    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="Authoritative Action Integrity Case",
            created_by="auditor_test",
            sources=[
                SourceReferenceInput(source_type=CaseSourceType.ACTION, source_id=str(action_rec.id))
            ],
        )
    )

    # Advance case status
    await case_service.update_case_status(
        case_id=case_dto.id,
        request=HSECaseStatusUpdateRequest(status=CaseStatus.INVESTIGATING, actor_id="auditor_test"),
    )

    # Verify action record remains strictly IN_PROGRESS
    refreshed_act = await db_session.get(HSEActionRecommendation, action_rec.id)
    assert refreshed_act.status == ActionStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_scenario_m_human_review_remains_unchanged(db_session: AsyncSession):
    """Scenario M: Attaching a human review to a case does not alter the Phase 5 review audit record."""
    sif_service = SIFAnalysisService(db_session)
    analysis = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="OIL-REV-AUTH-001",
            raw_text="Worker stepped over open grating without barricade.",
            source_type=SourceType.UA,
        )
    )

    asm_res = await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == analysis.report_id))
    asm = asm_res.scalar_one()

    triage_service = TriageService(db_session)
    triage = await triage_service.ensure_review_for_assessment(asm.id)


    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="Review Integrity Case",
            created_by="auditor_test",
            sources=[
                SourceReferenceInput(source_type=CaseSourceType.REVIEW, source_id=str(triage.id))
            ],
        )
    )

    # Case updates
    await case_service.update_case(
        case_id=case_dto.id,
        request=HSECaseUpdateRequest(title="Updated Review Integrity Case", priority=CasePriority.CRITICAL_REVIEW),
    )

    # Verify review record remains strictly intact
    refreshed_review = await db_session.get(TriageReview, triage.id)
    assert refreshed_review.id == triage.id
    assert refreshed_review.report_id == analysis.report_id


@pytest.mark.asyncio
async def test_scenario_n_evidence_remains_unchanged(db_session: AsyncSession):
    """Scenario N: Underlying safety reports and SIF assessments are read-only and unmutated by case operations."""
    sif_service = SIFAnalysisService(db_session)
    analysis = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="OIL-EVID-AUTH-001",
            raw_text="Hot work commenced without combustible gas detection test.",
            source_type=SourceType.UA,
        )
    )

    rep = await db_session.get(SafetyReport, analysis.report_id)
    asm_res = await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == analysis.report_id))
    asm = asm_res.scalar_one()

    original_report_text = rep.raw_text
    original_sif_class = asm.sif_classification

    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="Evidence Immutability Case",
            created_by="auditor_test",
            sources=[
                SourceReferenceInput(source_type=CaseSourceType.REPORT, source_id=str(rep.id)),
                SourceReferenceInput(source_type=CaseSourceType.ASSESSMENT, source_id=str(asm.id)),
            ],
        )
    )

    # Check report and assessment in db
    refreshed_rep = await db_session.get(SafetyReport, analysis.report_id)
    refreshed_asm = await db_session.get(SIFAssessment, asm.id)

    assert refreshed_rep.raw_text == original_report_text
    assert refreshed_asm.sif_classification == original_sif_class


@pytest.mark.asyncio
async def test_scenario_o_close_with_rationale_and_action_resolution(db_session: AsyncSession):
    """Scenario O: Case closure enforces rationale and blocks closure if open actions remain."""
    # 1. Action that is still OPEN
    action_rec = HSEActionRecommendation(
        action_key="ACT-CLOSE-TEST-001",
        source_type=ActionSourceType.ASSESSMENT,
        source_id="ASM-CLOSE-001",
        action_category=ActionCategory.BARRIER_VERIFICATION,
        action_title="Perform Safety Valve Pop Test",
        action_description="Test pop pressure on PSV-102.",
        priority=ActionPriority.HIGH,
        rationale="PSV inspection overdue.",
        rule_id="ACT-R01-BARRIER",
        status=ActionStatus.OPEN,
    )
    db_session.add(action_rec)
    await db_session.commit()

    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="Closure Check Case",
            created_by="auditor_test",
            sources=[
                SourceReferenceInput(source_type=CaseSourceType.ACTION, source_id=str(action_rec.id))
            ],
        )
    )

    # Transition to INVESTIGATING
    await case_service.update_case_status(
        case_id=case_dto.id,
        request=HSECaseStatusUpdateRequest(status=CaseStatus.INVESTIGATING, actor_id="auditor_test"),
    )

    # Attempting to close without rationale must fail
    with pytest.raises(CaseClosureBlockedException):
        await case_service.update_case_status(
            case_id=case_dto.id,
            request=HSECaseStatusUpdateRequest(status=CaseStatus.CLOSED, actor_id="auditor_test", rationale=""),
        )

    # Attempting to close with open action must fail
    with pytest.raises(CaseClosureBlockedException):
        await case_service.update_case_status(
            case_id=case_dto.id,
            request=HSECaseStatusUpdateRequest(
                status=CaseStatus.CLOSED,
                actor_id="auditor_test",
                rationale="Attempting closure with open action",
            ),
            require_actions_resolved=True,
        )

    # Now complete the action in Phase 8
    action_rec.status = ActionStatus.COMPLETED
    action_rec.completed_at = datetime.now(timezone.utc)
    action_rec.status_rationale = "Pop test executed successfully at 150 psi."
    await db_session.commit()

    # Now closing should succeed
    closed_case = await case_service.update_case_status(
        case_id=case_dto.id,
        request=HSECaseStatusUpdateRequest(
            status=CaseStatus.CLOSED,
            actor_id="hse_lead",
            rationale="PSV-102 pop test completed and certified.",
        ),
        require_actions_resolved=True,
    )
    assert closed_case.status == CaseStatus.CLOSED
    assert closed_case.closed_at is not None


@pytest.mark.asyncio
async def test_scenario_p_reopen_with_rationale(db_session: AsyncSession):
    """Scenario P: Closed case can be reopened to INVESTIGATING with mandatory rationale."""
    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="Reopen Test Case",
            created_by="auditor_test",
        )
    )

    # Reopening an OPEN case must fail
    with pytest.raises(InvalidStateTransitionException):
        await case_service.reopen_case(
            case_id=case_dto.id,
            request=HSECaseReopenRequest(actor_id="hse_lead", rationale="Attempting reopen on open case"),
        )

    # Progress and close
    await case_service.update_case_status(
        case_id=case_dto.id,
        request=HSECaseStatusUpdateRequest(status=CaseStatus.INVESTIGATING, actor_id="auditor_test"),
    )
    await case_service.update_case_status(
        case_id=case_dto.id,
        request=HSECaseStatusUpdateRequest(
            status=CaseStatus.CLOSED,
            actor_id="auditor_test",
            rationale="Initial findings verified.",
        ),
    )

    # Empty rationale fails schema/validation
    with pytest.raises(Exception):
        await case_service.reopen_case(
            case_id=case_dto.id,
            request=HSECaseReopenRequest(actor_id="hse_lead", rationale=""),
        )

    # Valid reopen
    reopened = await case_service.reopen_case(
        case_id=case_dto.id,
        request=HSECaseReopenRequest(
            actor_id="hse_lead",
            rationale="New recurring incident reported at adjacent manifold requires reopening.",
        ),
    )
    assert reopened.status == CaseStatus.INVESTIGATING
    assert reopened.closed_at is None

    # Check timeline contains CASE_REOPENED event
    timeline = await case_service.get_case_timeline(case_dto.id)
    assert any(e.event_type == CaseEventType.CASE_REOPENED for e in timeline)



@pytest.mark.asyncio
async def test_scenario_q_cancellation(db_session: AsyncSession):
    """Scenario Q: Open/triage/investigating case can be cancelled with rationale."""
    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="Cancellation Test Case",
            created_by="auditor_test",
        )
    )

    # Cancel without rationale must fail
    with pytest.raises(CaseClosureBlockedException):
        await case_service.update_case_status(
            case_id=case_dto.id,
            request=HSECaseStatusUpdateRequest(
                status=CaseStatus.CANCELLED,
                actor_id="auditor_test",
                rationale="",
            ),
        )

    # Cancel with rationale succeeds
    cancelled_dto = await case_service.update_case_status(
        case_id=case_dto.id,
        request=HSECaseStatusUpdateRequest(
            status=CaseStatus.CANCELLED,
            actor_id="auditor_test",
            rationale="Duplicate case logged in error by trainee.",
        ),
    )
    assert cancelled_dto.status == CaseStatus.CANCELLED
    assert cancelled_dto.closure_rationale == "Duplicate case logged in error by trainee."


@pytest.mark.asyncio
async def test_scenario_r_case_filtering(db_session: AsyncSession):
    """Scenario R: Query cases with deterministic filters."""
    case_service = HSECaseManagementService(db_session)
    await case_service.create_case(
        HSECaseCreateRequest(
            title="Critical Barrier Case",
            case_type=CaseType.BARRIER_REVIEW,
            priority=CasePriority.CRITICAL_REVIEW,
            owner="investigator_sam",
            created_by="auditor_test",
        )
    )
    await case_service.create_case(
        HSECaseCreateRequest(
            title="Routine Activity Case",
            case_type=CaseType.ACTIVITY_REVIEW,
            priority=CasePriority.MEDIUM,
            owner="investigator_john",
            created_by="auditor_test",
        )
    )

    # Filter by priority
    res_crit = await case_service.list_cases(priority=CasePriority.CRITICAL_REVIEW)
    assert any(c.title == "Critical Barrier Case" for c in res_crit.items)
    assert all(c.priority == CasePriority.CRITICAL_REVIEW for c in res_crit.items)

    # Filter by case_type
    res_bar = await case_service.list_cases(case_type=CaseType.BARRIER_REVIEW)
    assert any(c.title == "Critical Barrier Case" for c in res_bar.items)

    # Filter by owner
    res_sam = await case_service.list_cases(owner="investigator_sam")
    assert any(c.title == "Critical Barrier Case" for c in res_sam.items)


@pytest.mark.asyncio
async def test_scenario_s_case_pagination(db_session: AsyncSession):
    """Scenario S: Case listing adheres to pagination contracts."""
    case_service = HSECaseManagementService(db_session)
    for i in range(5):
        await case_service.create_case(
            HSECaseCreateRequest(
                title=f"Pagination Test Case {i+1}",
                created_by="auditor_page",
            )
        )

    res_page_1 = await case_service.list_cases(page=1, page_size=2)
    assert res_page_1.page == 1
    assert res_page_1.page_size == 2
    assert len(res_page_1.items) == 2
    assert res_page_1.total >= 5
    assert res_page_1.total_pages >= 3


@pytest.mark.asyncio
async def test_scenario_t_deterministic_case_summary(db_session: AsyncSession):
    """Scenario T: Case summary computes deterministic aggregate metrics."""
    # Seed reports, assessment, pattern, action
    rep1 = SafetyReport(report_ref="REP-001", raw_text="Report 1 text", source_type=SourceType.UA)
    rep2 = SafetyReport(report_ref="REP-002", raw_text="Report 2 text", source_type=SourceType.NEAR_MISS)
    db_session.add_all([rep1, rep2])
    await db_session.flush()

    asm = SIFAssessment(
        report_id=rep1.id,
        sif_classification=SIFClassification.POTENTIAL_SIF,
        potential_severity=PotentialOutcome.FATALITY,
        primary_reasoning="Bypassing interlock",
        evidence_score=0.9,
    )
    db_session.add(asm)

    pat = PrecursorPattern(
        pattern_code="PAT-001",
        title="Summary Test Pattern",
        description="Pattern description",
        status=PatternStatus.ACTIVE,
    )
    db_session.add(pat)

    # 1. Create action
    action_rec = HSEActionRecommendation(
        action_key="ACT-SUM-TEST-001",
        source_type=ActionSourceType.ASSESSMENT,
        source_id=str(rep1.id),
        action_category=ActionCategory.BARRIER_VERIFICATION,
        action_title="Summary Action 1",
        action_description="Desc",
        priority=ActionPriority.HIGH,
        rationale="Rat",
        rule_id="ACT-R01-BARRIER",
        status=ActionStatus.OPEN,
    )
    db_session.add(action_rec)
    await db_session.commit()

    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="Summary Test Case",
            case_type=CaseType.SIF_INVESTIGATION,
            priority=CasePriority.HIGH,
            created_by="auditor_test",
            sources=[
                SourceReferenceInput(source_type=CaseSourceType.REPORT, source_id="REP-001"),
                SourceReferenceInput(source_type=CaseSourceType.REPORT, source_id="REP-002"),
                SourceReferenceInput(source_type=CaseSourceType.ASSESSMENT, source_id=str(asm.id)),
                SourceReferenceInput(source_type=CaseSourceType.PATTERN, source_id="PAT-001"),
                SourceReferenceInput(source_type=CaseSourceType.ACTION, source_id=str(action_rec.id)),
            ],
        )
    )

    summary = await case_service.get_case_summary(case_dto.id)
    assert summary.case_id == case_dto.id
    assert summary.case_key == case_dto.case_key
    assert summary.report_count == 2
    assert summary.assessment_count == 1
    assert summary.pattern_count == 1
    assert summary.concentration_count == 0
    assert summary.action_count == 1
    assert summary.open_action_count == 1
    assert summary.completed_action_count == 0


@pytest.mark.asyncio
async def test_scenario_u_idempotency_key(db_session: AsyncSession):
    """Scenario U: Supplying an idempotency key returns the existing case without duplicate creation."""
    case_service = HSECaseManagementService(db_session)
    key = "CASE-IDEMPOTENT-UNIQUE-999"

    case_1 = await case_service.create_case(
        HSECaseCreateRequest(
            title="First Case Submission",
            case_type=CaseType.SIF_INVESTIGATION,
            idempotency_key=key,
            created_by="auditor_idem",
        )
    )
    assert case_1.case_key == key

    # Submit again with same idempotency key
    case_2 = await case_service.create_case(
        HSECaseCreateRequest(
            title="First Case Submission",
            case_type=CaseType.SIF_INVESTIGATION,
            idempotency_key=key,
            created_by="auditor_idem",
        )
    )
    assert case_2.id == case_1.id
    assert case_2.case_key == key
    assert case_2.title == "First Case Submission"


@pytest.mark.asyncio
async def test_scenario_v_audit_event_immutability(db_session: AsyncSession):
    """Scenario V: Case events are append-only; historical events retain before/after states."""
    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="Audit Immutability Case",
            created_by="auditor_audit",
        )
    )

    await case_service.update_case_status(
        case_id=case_dto.id,
        request=HSECaseStatusUpdateRequest(status=CaseStatus.INVESTIGATING, actor_id="investigator_1"),
    )

    await case_service.update_case_status(
        case_id=case_dto.id,
        request=HSECaseStatusUpdateRequest(status=CaseStatus.ACTION_REQUIRED, actor_id="investigator_2"),
    )

    events = await case_service.get_case_timeline(case_dto.id)
    assert len(events) == 3

    # First event
    assert events[0].event_type == CaseEventType.CASE_CREATED
    assert events[0].after_state["status"] == CaseStatus.OPEN.value

    # Second event
    assert events[1].event_type == CaseEventType.CASE_STATUS_CHANGED
    assert events[1].before_state["status"] == CaseStatus.OPEN.value
    assert events[1].after_state["status"] == CaseStatus.INVESTIGATING.value

    # Third event
    assert events[2].event_type == CaseEventType.CASE_STATUS_CHANGED
    assert events[2].before_state["status"] == CaseStatus.INVESTIGATING.value
    assert events[2].after_state["status"] == CaseStatus.ACTION_REQUIRED.value


# ==============================================================================
# PHASE 9 CONTRACT CORRECTION REGRESSION TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_correction_1_configurable_case_closure_policy(db_session: AsyncSession):
    """Correction 1: Verify configurable case closure policy when require_actions_resolved is enabled vs disabled."""
    action_rec = HSEActionRecommendation(
        action_key="ACT-CLOSURE-POLICY-01",
        source_type=ActionSourceType.ASSESSMENT,
        source_id="ASM-CP-01",
        action_category=ActionCategory.BARRIER_VERIFICATION,
        action_title="Closure Policy Verification Action",
        action_description="Verify valve sealing",
        priority=ActionPriority.HIGH,
        rationale="Overpressure risk",
        rule_id="ACT-R01-BARRIER",
        status=ActionStatus.OPEN,
    )
    db_session.add(action_rec)
    await db_session.commit()

    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="Closure Policy Test Case",
            created_by="auditor_test",
            sources=[SourceReferenceInput(source_type=CaseSourceType.ACTION, source_id=str(action_rec.id))],
        )
    )

    await case_service.update_case_status(
        case_id=case_dto.id,
        request=HSECaseStatusUpdateRequest(status=CaseStatus.INVESTIGATING, actor_id="auditor_test"),
    )

    # 1. Closure blocked when require_actions_resolved=True
    with pytest.raises(CaseClosureBlockedException):
        await case_service.update_case_status(
            case_id=case_dto.id,
            request=HSECaseStatusUpdateRequest(
                status=CaseStatus.CLOSED,
                actor_id="auditor_test",
                rationale="Attempting closure with open action under strict policy",
            ),
            require_actions_resolved=True,
        )

    # 2. Closure allowed when require_actions_resolved=False (provided rationale is present)
    closed_case = await case_service.update_case_status(
        case_id=case_dto.id,
        request=HSECaseStatusUpdateRequest(
            status=CaseStatus.CLOSED,
            actor_id="auditor_test",
            rationale="Operational sign-off granted by asset manager with separate action tracking",
        ),
        require_actions_resolved=False,
    )
    assert closed_case.status == CaseStatus.CLOSED
    assert closed_case.closure_rationale is not None

    # 3. Closure without rationale is always blocked regardless of require_actions_resolved
    reopened = await case_service.reopen_case(
        case_id=case_dto.id,
        request=HSECaseReopenRequest(actor_id="auditor_test", rationale="Reopening for rationale test"),
    )
    with pytest.raises(CaseClosureBlockedException):
        await case_service.update_case_status(
            case_id=reopened.id,
            request=HSECaseStatusUpdateRequest(
                status=CaseStatus.CLOSED,
                actor_id="auditor_test",
                rationale="",
            ),
            require_actions_resolved=False,
        )


@pytest.mark.asyncio
async def test_correction_2_cancelled_case_reopening_rejected(db_session: AsyncSession):
    """Correction 2: CLOSED cases can reopen, but CANCELLED cases are terminal and cannot reopen."""
    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="Cancelled Reopen Test Case",
            created_by="auditor_test",
        )
    )

    # Cancel case with mandatory rationale
    cancelled = await case_service.update_case_status(
        case_id=case_dto.id,
        request=HSECaseStatusUpdateRequest(
            status=CaseStatus.CANCELLED,
            actor_id="auditor_test",
            rationale="Duplicate case logged in error",
        ),
    )
    assert cancelled.status == CaseStatus.CANCELLED

    # Attempting to reopen a CANCELLED case must fail with InvalidStateTransitionException
    with pytest.raises(InvalidStateTransitionException) as exc_info:
        await case_service.reopen_case(
            case_id=cancelled.id,
            request=HSECaseReopenRequest(actor_id="auditor_test", rationale="Attempting to reopen cancelled case"),
        )
    assert "only CLOSED cases can be reopened" in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_correction_3_action_status_source_of_truth_immutability(db_session: AsyncSession):
    """Correction 3: Phase 8 owns action status; Phase 9 case lifecycle operations never mutate action status."""
    action_rec = HSEActionRecommendation(
        action_key="ACT-INTEGRITY-01",
        source_type=ActionSourceType.ASSESSMENT,
        source_id="ASM-INT-01",
        action_category=ActionCategory.ENERGY_ISOLATION_VERIFICATION,
        action_title="Conduct Energy Isolation Standdown",
        action_description="Site-wide standdown",
        priority=ActionPriority.HIGH,
        rationale="Isolation bypass reported",
        rule_id="ACT-R02-BARRIER",
        status=ActionStatus.OPEN,
    )
    db_session.add(action_rec)
    await db_session.commit()

    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="Action Source of Truth Test Case",
            created_by="auditor_test",
            sources=[SourceReferenceInput(source_type=CaseSourceType.ACTION, source_id=str(action_rec.id))],
        )
    )

    # Perform multiple case mutations
    await case_service.update_case_status(
        case_id=case_dto.id,
        request=HSECaseStatusUpdateRequest(status=CaseStatus.TRIAGE, actor_id="auditor_test"),
    )
    await case_service.update_case_status(
        case_id=case_dto.id,
        request=HSECaseStatusUpdateRequest(status=CaseStatus.INVESTIGATING, actor_id="auditor_test"),
    )
    await case_service.assign_case(
        case_id=case_dto.id,
        request=HSECaseAssignRequest(owner="investigator_sam", actor_id="auditor_test"),
    )
    await case_service.get_case_summary(case_dto.id)

    # Verify action status in DB is strictly OPEN (unmutated by case service)
    refreshed_action = await db_session.get(HSEActionRecommendation, action_rec.id)
    assert refreshed_action.status == ActionStatus.OPEN

    # Status mutations can only occur via Phase 8 action service
    act_service = HSEActionRecommendationService(db_session)
    updated_action = await act_service.update_action_status(
        action_id=action_rec.id,
        request=ActionStatusUpdateRequest(
            status=ActionStatus.IN_PROGRESS,
            actor_id="hse_engineer",
            status_rationale="Standdown session scheduled with rig team",
        ),
    )
    assert updated_action.status == ActionStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_correction_4_polymorphic_source_validation_all_types(db_session: AsyncSession):
    """Correction 4: Deterministically validate existence for REPORT, ASSESSMENT, PATTERN, CONCENTRATION, REVIEW, ACTION."""
    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(title="Polymorphic Validation Host Case", created_by="auditor_test")
    )

    # 1. REPORT: invalid reference rejected, valid accepted
    with pytest.raises(ReportNotFoundException):
        await case_service.attach_source(
            case_id=case_dto.id,
            request=HSECaseSourceAttachRequest(
                source_type=CaseSourceType.REPORT,
                source_id="NON-EXISTENT-REPORT-REF",
                actor_id="auditor_test",
            ),
        )
    valid_rep = SafetyReport(report_ref="OIL-VAL-REP-01", raw_text="Valid report text", source_type=SourceType.UA)
    db_session.add(valid_rep)
    await db_session.commit()
    res = await case_service.attach_source(
        case_id=case_dto.id,
        request=HSECaseSourceAttachRequest(
            source_type=CaseSourceType.REPORT,
            source_id="OIL-VAL-REP-01",
            actor_id="auditor_test",
        ),
    )
    assert any(s.source_id == "OIL-VAL-REP-01" for s in res.sources)

    # 2. ASSESSMENT: invalid UUID/missing rejected, valid accepted
    with pytest.raises(AssessmentNotFoundException):
        await case_service.attach_source(
            case_id=case_dto.id,
            request=HSECaseSourceAttachRequest(
                source_type=CaseSourceType.ASSESSMENT,
                source_id=str(uuid.uuid4()),
                actor_id="auditor_test",
            ),
        )
    valid_asm = SIFAssessment(
        report_id=valid_rep.id,
        sif_classification=SIFClassification.POTENTIAL_SIF,
        potential_severity=PotentialOutcome.PERMANENT_DISABLING_INJURY,
        evidence_score=0.88,
    )
    db_session.add(valid_asm)
    await db_session.commit()
    res = await case_service.attach_source(
        case_id=case_dto.id,
        request=HSECaseSourceAttachRequest(
            source_type=CaseSourceType.ASSESSMENT,
            source_id=str(valid_asm.id),
            actor_id="auditor_test",
        ),
    )
    assert any(s.source_id == str(valid_asm.id) for s in res.sources)

    # 3. PATTERN: invalid rejected, valid accepted
    with pytest.raises(PatternNotFoundException):
        await case_service.attach_source(
            case_id=case_dto.id,
            request=HSECaseSourceAttachRequest(
                source_type=CaseSourceType.PATTERN,
                source_id="NON-EXISTENT-PAT",
                actor_id="auditor_test",
            ),
        )
    valid_pat = PrecursorPattern(
        pattern_code="PAT-VAL-01",
        title="Valid Test Pattern",
        description="Valid pattern description",
        status=PatternStatus.ACTIVE,
    )
    db_session.add(valid_pat)
    await db_session.commit()
    res = await case_service.attach_source(
        case_id=case_dto.id,
        request=HSECaseSourceAttachRequest(
            source_type=CaseSourceType.PATTERN,
            source_id="PAT-VAL-01",
            actor_id="auditor_test",
        ),
    )
    assert any(s.source_id == "PAT-VAL-01" for s in res.sources)

    # 4. CONCENTRATION: invalid rejected, valid accepted
    with pytest.raises(ConcentrationNotFoundException):
        await case_service.attach_source(
            case_id=case_dto.id,
            request=HSECaseSourceAttachRequest(
                source_type=CaseSourceType.CONCENTRATION,
                source_id="NON-EXISTENT-CONC",
                actor_id="auditor_test",
            ),
        )
    now = datetime.now(timezone.utc)
    valid_conc = RiskConcentration(
        concentration_key="CONC-VAL-01",
        dimension_type=ConcentrationDimension.LOCATION,
        dimension_value="Moran Asset",
        status=ConcentrationStatus.ACTIVE,
        occurrence_count=3,
        first_observed_at=now,
        last_observed_at=now,
    )
    db_session.add(valid_conc)
    await db_session.commit()
    res = await case_service.attach_source(
        case_id=case_dto.id,
        request=HSECaseSourceAttachRequest(
            source_type=CaseSourceType.CONCENTRATION,
            source_id="CONC-VAL-01",
            actor_id="auditor_test",
        ),
    )
    assert any(s.source_id == "CONC-VAL-01" for s in res.sources)

    # 5. REVIEW: invalid rejected, valid accepted
    with pytest.raises(ReviewNotFoundException):
        await case_service.attach_source(
            case_id=case_dto.id,
            request=HSECaseSourceAttachRequest(
                source_type=CaseSourceType.REVIEW,
                source_id=str(uuid.uuid4()),
                actor_id="auditor_test",
            ),
        )
    triage_service = TriageService(db_session)
    valid_review = await triage_service.ensure_review_for_assessment(valid_asm.id)
    res = await case_service.attach_source(
        case_id=case_dto.id,
        request=HSECaseSourceAttachRequest(
            source_type=CaseSourceType.REVIEW,
            source_id=str(valid_review.id),
            actor_id="auditor_test",
        ),
    )
    assert any(s.source_id == str(valid_review.id) for s in res.sources)

    # 6. ACTION: invalid rejected, valid accepted
    with pytest.raises(ActionNotFoundException):
        await case_service.attach_source(
            case_id=case_dto.id,
            request=HSECaseSourceAttachRequest(
                source_type=CaseSourceType.ACTION,
                source_id="NON-EXISTENT-ACT",
                actor_id="auditor_test",
            ),
        )
    valid_act = HSEActionRecommendation(
        action_key="ACT-VAL-01",
        source_type=ActionSourceType.ASSESSMENT,
        source_id=str(valid_rep.id),
        action_category=ActionCategory.BARRIER_VERIFICATION,
        action_title="Valid Action",
        action_description="Desc",
        priority=ActionPriority.MEDIUM,
        rationale="Rat",
        rule_id="ACT-R01-BARRIER",
        status=ActionStatus.OPEN,
    )
    db_session.add(valid_act)
    await db_session.commit()
    res = await case_service.attach_source(
        case_id=case_dto.id,
        request=HSECaseSourceAttachRequest(
            source_type=CaseSourceType.ACTION,
            source_id="ACT-VAL-01",
            actor_id="auditor_test",
        ),
    )
    assert any(s.source_id == "ACT-VAL-01" for s in res.sources)


@pytest.mark.asyncio
async def test_correction_5_source_detach_lifecycle_restrictions(db_session: AsyncSession):
    """Correction 5: Detachment allowed in active states; rejected in CLOSED or CANCELLED."""
    report = SafetyReport(report_ref="REP-DETACH-01", raw_text="Worker observed damaged sling.", source_type=SourceType.UC)
    db_session.add(report)
    await db_session.commit()

    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="Detach Lifecycle Case",
            created_by="auditor_test",
            sources=[SourceReferenceInput(source_type=CaseSourceType.REPORT, source_id="REP-DETACH-01")],
        )
    )
    assert len(case_dto.sources) == 1

    # 1. Detach allowed in OPEN state
    case_dto = await case_service.detach_source(
        case_id=case_dto.id,
        source_id_or_assoc_id="REP-DETACH-01",
        actor_id="auditor_test",
        rationale="Detached in OPEN state",
    )
    assert len(case_dto.sources) == 0

    # Verify timeline event created
    timeline = await case_service.get_case_timeline(case_dto.id)
    detach_events = [e for e in timeline if e.event_type == CaseEventType.SOURCE_DETACHED]
    assert len(detach_events) == 1
    assert detach_events[0].actor_id == "auditor_test"
    assert detach_events[0].rationale == "Detached in OPEN state"

    # Re-attach and progress to CLOSED
    await case_service.attach_source(
        case_id=case_dto.id,
        request=HSECaseSourceAttachRequest(
            source_type=CaseSourceType.REPORT,
            source_id="REP-DETACH-01",
            actor_id="auditor_test",
        ),
    )
    await case_service.update_case_status(
        case_id=case_dto.id,
        request=HSECaseStatusUpdateRequest(status=CaseStatus.INVESTIGATING, actor_id="auditor_test"),
    )
    await case_service.update_case_status(
        case_id=case_dto.id,
        request=HSECaseStatusUpdateRequest(
            status=CaseStatus.CLOSED,
            actor_id="auditor_test",
            rationale="Investigation concluded",
        ),
    )

    # Detach from CLOSED must fail with InvalidStateTransitionException
    with pytest.raises(InvalidStateTransitionException):
        await case_service.detach_source(
            case_id=case_dto.id,
            source_id_or_assoc_id="REP-DETACH-01",
            actor_id="auditor_test",
        )


@pytest.mark.asyncio
async def test_correction_6_case_priority_immutability(db_session: AsyncSession):
    """Correction 6: Case priority is explicitly supplied/inherited; adding sources never mutates priority."""
    # Seed 3 reports and 1 action
    rep1 = SafetyReport(report_ref="REP-PRIO-01", raw_text="Report 1", source_type=SourceType.UA)
    rep2 = SafetyReport(report_ref="REP-PRIO-02", raw_text="Report 2", source_type=SourceType.UA)
    rep3 = SafetyReport(report_ref="REP-PRIO-03", raw_text="Report 3", source_type=SourceType.UA)
    act1 = HSEActionRecommendation(
        action_key="ACT-PRIO-01",
        source_type=ActionSourceType.ASSESSMENT,
        source_id="ASM-P-01",
        action_category=ActionCategory.BARRIER_VERIFICATION,
        action_title="Prio Action",
        action_description="Desc",
        priority=ActionPriority.CRITICAL_REVIEW,
        rationale="Rat",
        rule_id="ACT-R01-BARRIER",
        status=ActionStatus.OPEN,
    )
    db_session.add_all([rep1, rep2, rep3, act1])
    await db_session.commit()

    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="Priority Source of Truth Case",
            priority=CasePriority.MEDIUM,
            created_by="auditor_test",
            sources=[SourceReferenceInput(source_type=CaseSourceType.REPORT, source_id="REP-PRIO-01")],
        )
    )
    assert case_dto.priority == CasePriority.MEDIUM

    # Attach more reports and critical action
    await case_service.attach_source(
        case_id=case_dto.id,
        request=HSECaseSourceAttachRequest(source_type=CaseSourceType.REPORT, source_id="REP-PRIO-02", actor_id="auditor_test"),
    )
    await case_service.attach_source(
        case_id=case_dto.id,
        request=HSECaseSourceAttachRequest(source_type=CaseSourceType.REPORT, source_id="REP-PRIO-03", actor_id="auditor_test"),
    )
    updated_case = await case_service.attach_source(
        case_id=case_dto.id,
        request=HSECaseSourceAttachRequest(source_type=CaseSourceType.ACTION, source_id="ACT-PRIO-01", actor_id="auditor_test"),
    )

    # Priority remains strictly MEDIUM (not auto-calculated or changed by attached sources)
    assert updated_case.priority == CasePriority.MEDIUM


@pytest.mark.asyncio
async def test_correction_7_source_of_truth_integrity(db_session: AsyncSession):
    """Correction 7: Phase 9 case operations never mutate Phase 1-8 authoritative records."""
    sif_service = SIFAnalysisService(db_session)
    analysis = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="OIL-SOT-REP-01",
            raw_text="Hot work commenced without combustible gas detection test.",
            source_type=SourceType.UA,
        )
    )

    asm_res = await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == analysis.report_id))
    asm = asm_res.scalar_one()

    pattern = PrecursorPattern(
        pattern_code="PAT-SOT-01",
        title="SOT Pattern",
        description="Pattern",
        status=PatternStatus.ACTIVE,
    )
    now = datetime.now(timezone.utc)
    conc = RiskConcentration(
        concentration_key="CONC-SOT-01",
        dimension_type=ConcentrationDimension.LOCATION,
        dimension_value="Moran",
        status=ConcentrationStatus.ACTIVE,
        occurrence_count=4,
        first_observed_at=now,
        last_observed_at=now,
    )
    action_rec = HSEActionRecommendation(
        action_key="ACT-SOT-01",
        source_type=ActionSourceType.ASSESSMENT,
        source_id=str(analysis.report_id),
        action_category=ActionCategory.BARRIER_VERIFICATION,
        action_title="SOT Action",
        action_description="Desc",
        priority=ActionPriority.HIGH,
        rationale="Rat",
        rule_id="ACT-R01-BARRIER",
        status=ActionStatus.OPEN,
    )
    db_session.add_all([pattern, conc, action_rec])
    await db_session.commit()

    triage_service = TriageService(db_session)
    review = await triage_service.ensure_review_for_assessment(asm.id)

    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="SOT Integrity Verification Case",
            created_by="auditor_test",
            sources=[
                SourceReferenceInput(source_type=CaseSourceType.REPORT, source_id=str(analysis.report_id)),
                SourceReferenceInput(source_type=CaseSourceType.ASSESSMENT, source_id=str(asm.id)),
                SourceReferenceInput(source_type=CaseSourceType.PATTERN, source_id="PAT-SOT-01"),
                SourceReferenceInput(source_type=CaseSourceType.CONCENTRATION, source_id="CONC-SOT-01"),
                SourceReferenceInput(source_type=CaseSourceType.REVIEW, source_id=str(review.id)),
                SourceReferenceInput(source_type=CaseSourceType.ACTION, source_id="ACT-SOT-01"),
            ],
        )
    )

    # Perform extensive case operations
    await case_service.update_case_status(
        case_id=case_dto.id,
        request=HSECaseStatusUpdateRequest(status=CaseStatus.INVESTIGATING, actor_id="auditor_test"),
    )
    await case_service.assign_case(
        case_id=case_dto.id,
        request=HSECaseAssignRequest(owner="inspector_vikram", actor_id="auditor_test"),
    )
    await case_service.get_case_summary(case_dto.id)

    # Verify all Phase 1-8 entities remain strictly unchanged
    refreshed_asm = await db_session.get(SIFAssessment, asm.id)
    refreshed_pat = await db_session.get(PrecursorPattern, pattern.id)
    refreshed_conc = await db_session.get(RiskConcentration, conc.id)
    refreshed_rev = await db_session.get(TriageReview, review.id)
    refreshed_act = await db_session.get(HSEActionRecommendation, action_rec.id)

    assert refreshed_asm.sif_classification == asm.sif_classification
    assert refreshed_pat.status == PatternStatus.ACTIVE
    assert refreshed_conc.occurrence_count == 4
    assert refreshed_rev.status == review.status
    assert refreshed_act.status == ActionStatus.OPEN


@pytest.mark.asyncio
async def test_correction_8_case_audit_integrity_failed_mutations(db_session: AsyncSession):
    """Correction 8: Failed mutations rollback cleanly without creating false audit events."""
    case_service = HSECaseManagementService(db_session)
    case_dto = await case_service.create_case(
        HSECaseCreateRequest(
            title="Audit Integrity Host Case",
            created_by="auditor_test",
        )
    )

    # Check baseline event count
    timeline_before = await case_service.get_case_timeline(case_dto.id)
    assert len(timeline_before) == 1  # Only CASE_CREATED

    # 1. Failed transition (OPEN -> CLOSED without intermediate steps)
    with pytest.raises(InvalidStateTransitionException):
        await case_service.update_case_status(
            case_id=case_dto.id,
            request=HSECaseStatusUpdateRequest(status=CaseStatus.CLOSED, actor_id="auditor_test", rationale="Premature"),
        )

    # 2. Failed source attachment (non-existent source)
    with pytest.raises(ReportNotFoundException):
        await case_service.attach_source(
            case_id=case_dto.id,
            request=HSECaseSourceAttachRequest(
                source_type=CaseSourceType.REPORT,
                source_id="DOES-NOT-EXIST-999",
                actor_id="auditor_test",
            ),
        )

    # Check timeline after failures: no false events were recorded
    timeline_after = await case_service.get_case_timeline(case_dto.id)
    assert len(timeline_after) == 1


@pytest.mark.asyncio
async def test_correction_9_idempotency_key_conflict(db_session: AsyncSession):
    """Correction 9: Reusing an idempotency key with materially conflicting case metadata raises 409 error."""
    case_service = HSECaseManagementService(db_session)
    key = "CASE-IDEM-CONFLICT-KEY-01"

    # First request
    case_1 = await case_service.create_case(
        HSECaseCreateRequest(
            title="Original Well Control Case",
            case_type=CaseType.SIF_INVESTIGATION,
            idempotency_key=key,
            created_by="auditor_test",
        )
    )
    assert case_1.case_key == key

    # Repeated request with same key but different title -> 409 DuplicateSourceAssociationException
    with pytest.raises(DuplicateSourceAssociationException) as exc_info:
        await case_service.create_case(
            HSECaseCreateRequest(
                title="Materially Conflicting Title With Same Key",
                case_type=CaseType.SIF_INVESTIGATION,
                idempotency_key=key,
                created_by="auditor_test",
            )
        )
    assert "conflicts with an existing case" in str(exc_info.value.message)
