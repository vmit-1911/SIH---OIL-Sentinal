"""Unit tests for CSVExportService (Phase 15)."""

import csv
import io
import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.action import HSEActionRecommendation
from app.db.models.assessment import SIFAssessment
from app.db.models.case import HSECase
from app.db.models.concentration import RiskConcentration
from app.db.models.report import SafetyReport
from app.domain.enums import (
    ActionCategory,
    ActionPriority,
    ActionSourceType,
    ActionStatus,
    ActualOutcome,
    CasePriority,
    CaseStatus,
    CaseType,
    ConcentrationDimension,
    ConcentrationStatus,
    EvidenceStrength,
    ObservedTrend,
    PotentialOutcome,
    SIFClassification,
    SourceType,
)
from app.schemas.command_center import CommandCenterOverview
from app.services.csv_export_service import CSVExportService


@pytest.mark.asyncio
async def test_export_assessments_csv(db_session: AsyncSession):
    """Verify CSV export for reports and SIF assessments."""
    now = datetime.now(timezone.utc)
    rep_id = uuid.uuid4()
    report = SafetyReport(
        id=rep_id,
        report_ref="REP-CSV-01",
        event_timestamp=now,
        reported_location="DULIAJAN_FIELD",
        source_type=SourceType.INCIDENT,
        actual_severity=ActualOutcome.MINOR_INJURY,
        raw_text="Worker tripped over unshielded drilling pipe.",
        created_at=now,
    )
    assessment = SIFAssessment(
        id=uuid.uuid4(),
        report_id=rep_id,
        sif_classification=SIFClassification.POTENTIAL_SIF,
        evidence_score=0.85,
        evidence_strength=EvidenceStrength.HIGH,
        rule_based_screening_score=0.90,
        potential_severity=PotentialOutcome.FATALITY,
        primary_reasoning="Heavy rotating equipment nearby.",
        structured_precursor={"hazard_source": "ROTATING_EQUIPMENT", "barrier_failure": "GUARD_MISSING"},
    )
    db_session.add(report)
    db_session.add(assessment)
    await db_session.commit()

    csv_service = CSVExportService(db_session)
    csv_str = await csv_service.export_assessments_csv()

    reader = list(csv.reader(io.StringIO(csv_str)))
    assert len(reader) == 2  # Header + 1 row
    header = reader[0]
    row = reader[1]

    assert "Report Reference" in header
    assert "SIF Classification" in header
    assert row[1] == "REP-CSV-01"
    assert row[6] == "POTENTIAL_SIF"


@pytest.mark.asyncio
async def test_export_actions_csv(db_session: AsyncSession):
    """Verify CSV export for HSE actions."""
    now = datetime.now(timezone.utc)
    action = HSEActionRecommendation(
        id=uuid.uuid4(),
        action_key="ACT-CSV-01",
        source_type=ActionSourceType.ASSESSMENT,
        source_id="SRC-1",
        action_category=ActionCategory.BARRIER_VERIFICATION,
        priority=ActionPriority.HIGH,
        status=ActionStatus.OPEN,
        action_title="Replace safety barrier",
        action_description="Install physical guard rail around drilling pit.",
        assigned_to="RIG_SUPERVISOR",
        rule_id="RULE-BARRIER-01",
        rationale="Missing guard rail hazard",
        created_at=now,
    )
    db_session.add(action)
    await db_session.commit()

    csv_service = CSVExportService(db_session)
    csv_str = await csv_service.export_actions_csv(status="OPEN")

    reader = list(csv.reader(io.StringIO(csv_str)))
    assert len(reader) == 2
    assert reader[1][1] == "ACT-CSV-01"
    assert reader[1][5] == "HIGH"


@pytest.mark.asyncio
async def test_export_concentrations_csv(db_session: AsyncSession):
    """Verify CSV export for Risk Concentrations."""
    now = datetime.now(timezone.utc)
    conc = RiskConcentration(
        id=uuid.uuid4(),
        concentration_key="CONC|LOC|MORAN_OIL_FIELD",
        dimension_type=ConcentrationDimension.LOCATION,
        dimension_value="MORAN_OIL_FIELD",
        occurrence_count=8,
        distinct_report_count=5,
        distinct_location_count=1,
        observed_trend=ObservedTrend.INCREASING,
        status=ConcentrationStatus.ACTIVE,
        first_observed_at=now,
        last_observed_at=now,
    )
    db_session.add(conc)
    await db_session.commit()

    csv_service = CSVExportService(db_session)
    csv_str = await csv_service.export_concentrations_csv(dimension="LOCATION")

    reader = list(csv.reader(io.StringIO(csv_str)))
    assert len(reader) == 2
    assert reader[1][2] == "LOCATION"
    assert reader[1][3] == "MORAN_OIL_FIELD"
    assert reader[1][7] == "INCREASING"


def test_export_command_center_summary_csv():
    """Verify Command Center KPI summary CSV generation."""
    now = datetime.now(timezone.utc)
    overview = CommandCenterOverview(
        total_reports=50,
        total_assessments=50,
        potential_sif_count=8,
        non_sif_count=40,
        undetermined_count=2,
        open_action_count=5,
        active_case_count=2,
        unreviewed_count=1,
        recurring_pattern_count=3,
        concentration_count=2,
        generated_at=now,
        data_as_of=now,
    )

    csv_str = CSVExportService.export_command_center_summary_csv(overview)
    reader = list(csv.reader(io.StringIO(csv_str)))

    assert len(reader) > 5
    metric_names = [r[0] for r in reader]
    assert "Total Reports" in metric_names
    assert "Potential SIF Count" in metric_names
