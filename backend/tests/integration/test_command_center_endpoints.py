"""Integration tests for Phase 10 HSE Command Center REST endpoints."""

from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
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
    ObservedTrend,
    PatternStatus,
    PotentialOutcome,
    ReviewDecision,
    ReviewFeedbackCategory,
    ReviewState,
    SIFClassification,
    SourceType,
)


@pytest.mark.asyncio
async def test_command_center_overview_endpoint(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/sif/command-center/overview returns high-level operational counts."""
    # Seed data
    rep = SafetyReport(report_ref="OIL-INT-CC-01", raw_text="Gas release during drilling", source_type=SourceType.NEAR_MISS, reported_location="Moran Rig-01")
    db_session.add(rep)
    await db_session.flush()

    asm = SIFAssessment(report_id=rep.id, sif_classification=SIFClassification.POTENTIAL_SIF, potential_severity=PotentialOutcome.FATALITY, evidence_score=0.95)
    db_session.add(asm)

    act = HSEActionRecommendation(
        action_key="ACT-INT-CC-01",
        source_type=ActionSourceType.ASSESSMENT,
        source_id=str(asm.id),
        action_category=ActionCategory.BARRIER_VERIFICATION,
        action_title="Action Title",
        action_description="Desc",
        priority=ActionPriority.HIGH,
        rationale="Rat",
        rule_id="ACT-R01",
        status=ActionStatus.OPEN,
    )
    db_session.add(act)

    case_obj = HSECase(
        case_key="CASE-INT-CC-01",
        title="Int Case",
        case_type=CaseType.SIF_INVESTIGATION,
        status=CaseStatus.INVESTIGATING,
        priority=CasePriority.HIGH,
        created_by="auditor_test",
    )
    db_session.add(case_obj)
    await db_session.commit()

    resp = await async_client.get("/api/v1/sif/command-center/overview")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_reports"] >= 1
    assert data["total_assessments"] >= 1
    assert data["potential_sif_count"] >= 1
    assert data["open_action_count"] >= 1
    assert data["active_case_count"] >= 1
    assert "summary_sources" in data


@pytest.mark.asyncio
async def test_command_center_sif_endpoint(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/sif/command-center/sif returns assessment, severity, and monthly distributions."""
    resp = await async_client.get("/api/v1/sif/command-center/sif")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_assessments" in data
    assert "classification_counts" in data
    assert "potential_severity_counts" in data
    assert "assessment_trend_by_month" in data


@pytest.mark.asyncio
async def test_command_center_precursors_endpoint(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/sif/command-center/precursors returns pattern summaries and dimension metrics."""
    pat = PrecursorPattern(
        pattern_code="PAT-INT-01",
        title="Crane Rigging Failure",
        description="Rigging failure under hook",
        hazard_category="SUSPENDED_LOAD",
        activity_type="LIFTING",
        failed_barrier_type="RIGGING",
        occurrence_count=4,
        status=PatternStatus.ACTIVE,
    )
    db_session.add(pat)
    await db_session.commit()

    resp = await async_client.get("/api/v1/sif/command-center/precursors?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_patterns"] >= 1
    assert len(data["top_patterns"]) >= 1
    assert "top_hazard_dimensions" in data


@pytest.mark.asyncio
async def test_command_center_concentrations_endpoint(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/sif/command-center/concentrations returns canonical dimension metrics and findings."""
    now = datetime.now(timezone.utc)
    conc = RiskConcentration(
        concentration_key="CONC|LOCATION|INT_SITE",
        dimension_type=ConcentrationDimension.LOCATION,
        dimension_value="Site A",
        occurrence_count=5,
        distinct_report_count=4,
        distinct_location_count=1,
        first_observed_at=now,
        last_observed_at=now,
        status=ConcentrationStatus.ACTIVE,
    )
    db_session.add(conc)
    await db_session.commit()

    resp = await async_client.get("/api/v1/sif/command-center/concentrations?limit=10&dimension=LOCATION")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_concentrations"] >= 1
    assert data["dimension_counts"]["LOCATION"] >= 1


@pytest.mark.asyncio
async def test_command_center_lsr_endpoint(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/sif/command-center/lsr returns LSR distribution statistics."""
    resp = await async_client.get("/api/v1/sif/command-center/lsr")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_lsr_rules" in data
    assert "rules" in data


@pytest.mark.asyncio
async def test_command_center_actions_endpoint(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/sif/command-center/actions returns action recommendation metrics and age breakdown."""
    resp = await async_client.get("/api/v1/sif/command-center/actions")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_actions" in data
    assert "status_counts" in data
    assert "open_actions_by_age" in data


@pytest.mark.asyncio
async def test_command_center_cases_endpoint(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/sif/command-center/cases returns case metrics and recent cases."""
    resp = await async_client.get("/api/v1/sif/command-center/cases")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_cases" in data
    assert "status_counts" in data
    assert "recently_updated_cases" in data


@pytest.mark.asyncio
async def test_command_center_reviews_endpoint(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/sif/command-center/reviews returns review queue workload."""
    resp = await async_client.get("/api/v1/sif/command-center/reviews")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_reviews" in data
    assert "pending_reviews" in data
    assert "age_of_pending_reviews" in data


@pytest.mark.asyncio
async def test_command_center_investigation_snapshot_endpoint(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/sif/command-center/investigation-snapshot returns multi-phase operational chain."""
    rep = SafetyReport(report_ref="OIL-SNAP-API-01", raw_text="Hydrocarbon line flange leak during hydrotest", source_type=SourceType.NEAR_MISS, reported_location="Digboi Field")
    db_session.add(rep)
    await db_session.flush()

    asm = SIFAssessment(report_id=rep.id, sif_classification=SIFClassification.POTENTIAL_SIF, potential_severity=PotentialOutcome.FATALITY, evidence_score=0.94)
    db_session.add(asm)
    await db_session.commit()

    resp = await async_client.get("/api/v1/sif/command-center/investigation-snapshot?report_ref=OIL-SNAP-API-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["report_count"] == 1
    assert data["summary"]["assessment_count"] == 1
    assert len(data["reports"]) == 1
    assert data["reports"][0]["report_ref"] == "OIL-SNAP-API-01"


@pytest.mark.asyncio
async def test_command_center_invalid_date_range_rejected(async_client: AsyncClient):
    """Invalid date range where from_date > to_date returns HTTP 400 Bad Request."""
    t_start = "2026-06-01T00:00:00Z"
    t_end = "2026-01-01T00:00:00Z"

    resp = await async_client.get(f"/api/v1/sif/command-center/overview?from_date={t_start}&to_date={t_end}")
    assert resp.status_code == 400
    data = resp.json()
    assert "cannot be greater than" in data["detail"]


@pytest.mark.asyncio
async def test_command_center_openapi_contract(async_client: AsyncClient):
    """Verify OpenAPI specification documents all 9 Command Center endpoints."""
    resp = await async_client.get("/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()
    paths = spec.get("paths", {})

    expected_endpoints = [
        "/api/v1/sif/command-center/overview",
        "/api/v1/sif/command-center/sif",
        "/api/v1/sif/command-center/precursors",
        "/api/v1/sif/command-center/concentrations",
        "/api/v1/sif/command-center/lsr",
        "/api/v1/sif/command-center/actions",
        "/api/v1/sif/command-center/cases",
        "/api/v1/sif/command-center/reviews",
        "/api/v1/sif/command-center/investigation-snapshot",
    ]

    for ep in expected_endpoints:
        assert ep in paths, f"Expected endpoint '{ep}' missing from OpenAPI specification"
        assert "get" in paths[ep], f"GET operation missing for '{ep}'"
