"""Integration tests for PDF & CSV Intelligence Export Endpoints (Phase 15)."""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
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


@pytest.mark.asyncio
async def test_export_executive_brief_pdf(async_client: AsyncClient, db_session: AsyncSession):
    """Verify GET /api/v1/sif/export/executive-brief/pdf returns valid PDF stream."""
    response = await async_client.get("/api/v1/sif/export/executive-brief/pdf")
    assert response.status_code == 200
    assert "application/pdf" in response.headers["content-type"]
    assert response.content.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_export_incident_dossier_pdf(async_client: AsyncClient, db_session: AsyncSession):
    """Verify GET /api/v1/sif/export/dossier/{report_id}/pdf."""
    now = datetime.now(timezone.utc)
    report_id = uuid.uuid4()
    report = SafetyReport(
        id=report_id,
        report_ref="REP-EXPORT-01",
        event_timestamp=now,
        reported_location="DULIAJAN_DRILLING_RIG",
        source_type=SourceType.INCIDENT,
        actual_severity=ActualOutcome.NO_INJURY,
        raw_text="Near miss during high pressure manifold test.",
        created_at=now,
    )
    assessment = SIFAssessment(
        id=uuid.uuid4(),
        report_id=report_id,
        sif_classification=SIFClassification.POTENTIAL_SIF,
        evidence_score=0.91,
        evidence_strength=EvidenceStrength.HIGH,
        rule_based_screening_score=0.94,
        potential_severity=PotentialOutcome.FATALITY,
        primary_reasoning="High energy manifold pressurized beyond test threshold.",
    )
    db_session.add(report)
    db_session.add(assessment)
    await db_session.commit()

    # Success case
    resp = await async_client.get(f"/api/v1/sif/export/dossier/{report_id}/pdf")
    assert resp.status_code == 200
    assert "application/pdf" in resp.headers["content-type"]
    assert resp.content.startswith(b"%PDF-")

    # 404 case
    bad_id = uuid.uuid4()
    resp_404 = await async_client.get(f"/api/v1/sif/export/dossier/{bad_id}/pdf")
    assert resp_404.status_code == 404


@pytest.mark.asyncio
async def test_export_case_dossier_pdf(async_client: AsyncClient, db_session: AsyncSession):
    """Verify GET /api/v1/sif/export/case/{case_id}/pdf."""
    now = datetime.now(timezone.utc)
    case_id = uuid.uuid4()
    case = HSECase(
        id=case_id,
        case_key="CASE-2026-EXP",
        title="High Pressure Testing Investigation",
        case_type=CaseType.SIF_INVESTIGATION,
        status=CaseStatus.INVESTIGATING,
        priority=CasePriority.CRITICAL_REVIEW,
        owner="HSE_DIRECTOR",
        created_by="SYSTEM",
        description="Formal root-cause inquiry into manifold barrier degradation.",
        created_at=now,
    )
    db_session.add(case)
    await db_session.commit()

    resp = await async_client.get(f"/api/v1/sif/export/case/{case_id}/pdf")
    assert resp.status_code == 200
    assert "application/pdf" in resp.headers["content-type"]
    assert resp.content.startswith(b"%PDF-")

    # 404 case
    bad_id = uuid.uuid4()
    resp_404 = await async_client.get(f"/api/v1/sif/export/case/{bad_id}/pdf")
    assert resp_404.status_code == 404


@pytest.mark.asyncio
async def test_export_csv_endpoints(async_client: AsyncClient, db_session: AsyncSession):
    """Verify CSV export endpoints for assessments, actions, concentrations, and cases."""
    now = datetime.now(timezone.utc)
    rep_id = uuid.uuid4()
    report = SafetyReport(
        id=rep_id,
        report_ref="REP-INT-CSV",
        event_timestamp=now,
        reported_location="DULIAJAN_HUB",
        source_type=SourceType.INCIDENT,
        actual_severity=ActualOutcome.NO_INJURY,
        raw_text="Routine line inspection observation.",
        created_at=now,
    )
    action = HSEActionRecommendation(
        id=uuid.uuid4(),
        action_key="ACT-INT-CSV",
        source_type=ActionSourceType.ASSESSMENT,
        source_id=str(rep_id),
        action_category=ActionCategory.BARRIER_VERIFICATION,
        priority=ActionPriority.HIGH,
        status=ActionStatus.OPEN,
        action_title="Sample Action",
        action_description="Action description",
        assigned_to="SAFETY_OFFICER",
        rule_id="RULE-SAMPLE-01",
        rationale="Sample action rationale",
        created_at=now,
    )
    conc = RiskConcentration(
        id=uuid.uuid4(),
        concentration_key="CONC|LOC|DULIAJAN_HUB",
        dimension_type=ConcentrationDimension.LOCATION,
        dimension_value="DULIAJAN_HUB",
        occurrence_count=5,
        distinct_report_count=2,
        distinct_location_count=1,
        observed_trend=ObservedTrend.STABLE,
        status=ConcentrationStatus.ACTIVE,
        first_observed_at=now,
        last_observed_at=now,
    )
    case = HSECase(
        id=uuid.uuid4(),
        case_key="CASE-CSV-01",
        title="Sample CSV Case",
        case_type=CaseType.SIF_INVESTIGATION,
        status=CaseStatus.OPEN,
        priority=CasePriority.HIGH,
        owner="HSE_OFFICER",
        created_by="SYSTEM",
        created_at=now,
    )

    db_session.add(report)
    db_session.add(action)
    db_session.add(conc)
    db_session.add(case)
    await db_session.commit()

    # 1. Assessments CSV
    resp_ass = await async_client.get("/api/v1/sif/export/assessments/csv")
    assert resp_ass.status_code == 200
    assert "text/csv" in resp_ass.headers["content-type"]
    assert "Report Reference" in resp_ass.text

    # 2. Actions CSV
    resp_act = await async_client.get("/api/v1/sif/export/actions/csv")
    assert resp_act.status_code == 200
    assert "text/csv" in resp_act.headers["content-type"]
    assert "Action Key" in resp_act.text

    # 3. Concentrations CSV
    resp_conc = await async_client.get("/api/v1/sif/export/concentrations/csv")
    assert resp_conc.status_code == 200
    assert "text/csv" in resp_conc.headers["content-type"]
    assert "Concentration ID" in resp_conc.text

    # 4. Cases CSV
    resp_case = await async_client.get("/api/v1/sif/export/cases/csv")
    assert resp_case.status_code == 200
    assert "text/csv" in resp_case.headers["content-type"]
    assert "Case ID" in resp_case.text
