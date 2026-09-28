"""Unit tests for PDFExportService (Phase 15)."""

import uuid
from datetime import datetime, timezone
import pytest

from app.db.models.action import HSEActionRecommendation
from app.db.models.assessment import SIFAssessment
from app.db.models.case import HSECase, HSECaseEvent, HSECaseSourceAssociation
from app.db.models.report import SafetyReport
from app.db.models.taxonomy import LSRReportMapping
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
    EvidenceStrength,
    ObservedTrend,
    PotentialOutcome,
    SIFClassification,
    SourceType,
)
from app.schemas.command_center import (
    ActionOverviewDTO,
    CommandCenterOverview,
    ConcentrationOverviewDTO,
    ConcentrationSummaryDTO,
    LSROverviewDTO,
    PatternSummaryDTO,
    PrecursorOverviewDTO,
    SIFOverviewDTO,
)
from app.services.pdf_export_service import PDFExportService


@pytest.fixture
def pdf_service() -> PDFExportService:
    return PDFExportService()


def test_generate_executive_safety_brief_pdf(pdf_service):
    """Verify executive brief PDF builds valid bytes with complete metadata."""
    now = datetime.now(timezone.utc)
    overview = CommandCenterOverview(
        total_reports=100,
        total_assessments=100,
        potential_sif_count=15,
        non_sif_count=80,
        undetermined_count=5,
        open_action_count=10,
        active_case_count=3,
        unreviewed_count=4,
        recurring_pattern_count=2,
        concentration_count=4,
        generated_at=now,
        data_as_of=now,
    )
    sif_overview = SIFOverviewDTO(
        generated_at=now,
        total_assessments=100,
        classification_counts={"POTENTIAL_SIF": 15, "NON_SIF": 80, "UNDETERMINED": 5},
        potential_severity_counts={"FATALITY": 5, "PERMANENT_DISABLING_INJURY": 10, "LOW_IMPACT": 85},
        assessment_trend_by_month=[],
        lsr_distribution={"LSR-01": 10, "LSR-02": 5},
    )
    precursor_overview = PrecursorOverviewDTO(
        generated_at=now,
        total_patterns=2,
        top_patterns=[
            PatternSummaryDTO(
                id=uuid.uuid4(),
                pattern_code="PAT-HAZ-01",
                title="Hydraulic Line Leakage Pattern",
                description="Recurring high pressure line failure",
                occurrence_count=5,
                hazard_category="PRESSURE_HAZARD",
                failed_barrier_type="PRESSURE_RELIEF_VALVE",
                first_detected_at=now,
            )
        ],
        top_hazard_dimensions=[],
        top_barrier_failure_dimensions=[],
        top_activity_dimensions=[],
    )
    concentration_overview = ConcentrationOverviewDTO(
        generated_at=now,
        total_concentrations=1,
        limit=50,
        offset=0,
        items=[
            ConcentrationSummaryDTO(
                id=uuid.uuid4(),
                concentration_key="CONC|LOC|DULIAJAN_RIG_07",
                dimension_type=ConcentrationDimension.LOCATION,
                dimension_value="DULIAJAN_RIG_07",
                occurrence_count=12,
                distinct_report_count=8,
                distinct_location_count=1,
                observed_trend=ObservedTrend.INCREASING,
                first_observed_at=now,
                last_observed_at=now,
            )
        ],
    )
    action_overview = ActionOverviewDTO(
        generated_at=now,
        total_actions=15,
        status_counts={"OPEN": 6, "IN_PROGRESS": 4, "COMPLETED": 5},
        priority_distribution={"CRITICAL_REVIEW": 2, "HIGH": 5, "MEDIUM": 5, "INFORMATIONAL": 3},
        category_distribution={},
        open_actions_by_age={},
    )
    lsr_overview = LSROverviewDTO(
        generated_at=now,
        total_lsr_rules=9,
        rules=[],
    )

    pdf_bytes = pdf_service.generate_executive_safety_brief_pdf(
        overview=overview,
        sif_overview=sif_overview,
        precursor_overview=precursor_overview,
        concentration_overview=concentration_overview,
        action_overview=action_overview,
        lsr_overview=lsr_overview,
        filter_params={"location": "DULIAJAN", "from_date": "2026-01-01"},
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")


def test_generate_incident_dossier_pdf(pdf_service):
    """Verify Incident Dossier PDF generates valid stream with full entities."""
    now = datetime.now(timezone.utc)
    rep_id = uuid.uuid4()
    tax_id = uuid.uuid4()
    report = SafetyReport(
        id=rep_id,
        report_ref="REP-2026-001",
        event_timestamp=now,
        reported_location="DIGBOI_PLANT_A",
        source_type=SourceType.INCIDENT,
        actual_severity=ActualOutcome.FIRST_AID,
        raw_text="Worker observed pressurized hydraulic line leaking near hot turbine manifold.",
        created_at=now,
    )
    assessment = SIFAssessment(
        id=uuid.uuid4(),
        report_id=rep_id,
        sif_classification=SIFClassification.POTENTIAL_SIF,
        evidence_score=0.88,
        evidence_strength=EvidenceStrength.HIGH,
        rule_based_screening_score=0.92,
        potential_severity=PotentialOutcome.FATALITY,
        primary_reasoning="High energy hydraulic fluid in close proximity to ignition source.",
        structured_precursor={
            "hazard_source": "PRESSURIZED_HYDRAULIC_LINE",
            "barrier_failure": "HOSE_INTEGRITY_DEGRADED",
            "activity": "ROUTINE_DRILLING_OPERATION",
            "equipment": "HYDRAULIC_POWER_PACK",
        },
    )
    lsr_mapping = LSRReportMapping(
        id=uuid.uuid4(),
        report_id=rep_id,
        taxonomy_id=tax_id,
        rule_code="LSR_05_BYPASS_SAFETY_CONTROLS",
        rule_name="Bypass Safety Controls",
        confidence_score=0.95,
        trigger_evidence=["hydraulic line leak"],
        is_primary=True,
    )
    action = HSEActionRecommendation(
        id=uuid.uuid4(),
        action_key="ACT-001",
        source_type=ActionSourceType.ASSESSMENT,
        source_id=str(rep_id),
        action_category=ActionCategory.BARRIER_VERIFICATION,
        priority=ActionPriority.CRITICAL_REVIEW,
        status=ActionStatus.OPEN,
        action_title="Inspect hydraulic hose manifold",
        action_description="Perform immediate pressure test and replace degraded hose sections.",
        assigned_to="MAINTENANCE_SUPERVISOR",
        rule_id="RULE-HYD-01",
        rationale="High energy hydraulic line failure identified",
        created_at=now,
    )
    case = HSECase(
        id=uuid.uuid4(),
        case_key="CASE-2026-001",
        title="Hydraulic Line Integrity Investigation",
        case_type=CaseType.SIF_INVESTIGATION,
        status=CaseStatus.INVESTIGATING,
        priority=CasePriority.HIGH,
        owner="HSE_LEAD_01",
        created_by="SYSTEM",
        created_at=now,
    )

    pdf_bytes = pdf_service.generate_incident_dossier_pdf(
        report=report,
        assessment=assessment,
        lsr_mappings=[lsr_mapping],
        related_actions=[action],
        related_case=case,
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")


def test_generate_case_dossier_pdf(pdf_service):
    """Verify HSE Case Dossier PDF generation."""
    now = datetime.now(timezone.utc)
    case_id = uuid.uuid4()
    case = HSECase(
        id=case_id,
        case_key="CASE-2026-002",
        title="High Pressure Line Failure Formal Investigation",
        case_type=CaseType.SIF_INVESTIGATION,
        status=CaseStatus.INVESTIGATING,
        priority=CasePriority.CRITICAL_REVIEW,
        owner="SR_HSE_MANAGER",
        created_by="SYSTEM",
        description="Comprehensive investigation into recurring hydraulic seal failures across rig fleet.",
        created_at=now,
    )
    event = HSECaseEvent(
        id=uuid.uuid4(),
        case_id=case_id,
        event_type=CaseEventType.CASE_CREATED,
        actor_id="SYSTEM",
        rationale="Automated case created following SIF precursor discovery.",
        created_at=now,
    )
    action = HSEActionRecommendation(
        id=uuid.uuid4(),
        action_key="ACT-002",
        source_type=ActionSourceType.ASSESSMENT,
        source_id="SRC-1",
        action_category=ActionCategory.PROCEDURE_REVIEW,
        priority=ActionPriority.HIGH,
        status=ActionStatus.IN_PROGRESS,
        action_title="Update pressure relief valve SOP",
        action_description="Standardize valve inspection frequencies.",
        rule_id="RULE-SOP-02",
        rationale="Standardize SOP across operations",
        created_at=now,
    )
    source = HSECaseSourceAssociation(
        id=uuid.uuid4(),
        case_id=case_id,
        source_type=CaseSourceType.REPORT,
        source_id="REP-101",
        attached_by="SYSTEM",
        attached_at=now,
    )

    pdf_bytes = pdf_service.generate_case_dossier_pdf(
        case=case,
        events=[event],
        actions=[action],
        sources=[source],
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")
