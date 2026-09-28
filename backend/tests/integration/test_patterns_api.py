"""Integration tests for Pattern API endpoints (GET /sif/patterns, GET /sif/patterns/{id}, POST /sif/patterns/discover)."""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.assessment import SIFAssessment
from app.db.models.pattern import PrecursorPattern
from app.db.models.report import SafetyReport
from app.domain.enums import ActualOutcome, EvidenceStrength, PatternStatus, PotentialOutcome, SIFClassification, SourceType, TriageStatus


@pytest.mark.asyncio
async def test_get_patterns_empty(async_client: AsyncClient):
    """Verify GET /api/v1/sif/patterns returns empty list when no patterns exist."""
    response = await async_client.get("/api/v1/sif/patterns")
    assert response.status_code == 200
    data = response.json()
    assert data["total_patterns"] == 0
    assert data["patterns"] == []


@pytest.mark.asyncio
async def test_get_patterns_and_pattern_detail(async_client: AsyncClient, db_session: AsyncSession):
    """Verify GET /sif/patterns and GET /sif/patterns/{id} return expected DTOs."""
    pat_id = uuid.uuid4()
    rep_prec = {
        "hazard": "Suspended Load",
        "activity": "Crane Lifting",
        "barrier_failure": "Rigging Failure",
        "exposure": "Line of Fire",
        "potential_consequence": "FATALITY",
        "life_saving_rule": "LSR_03_MECHANICAL_LIFTING",
        "location": "Rig-04",
        "field_provenance": {},
    }

    pattern = PrecursorPattern(
        id=pat_id,
        pattern_code="PAT_LSR_03_SUSPENDED_LOAD_RIGGING_FAILURE",
        title="Recurring Suspended Load with Rigging Failure",
        description="3 reports were grouped due to suspended load failures.",
        hazard_category="Suspended Load",
        activity_type="Crane Lifting",
        failed_barrier_type="Rigging Failure",
        lsr_code="LSR_03_MECHANICAL_LIFTING",
        occurrence_count=3,
        affected_locations=["Rig-04"],
        supporting_report_ids=[str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())],
        supporting_lsr_codes=["LSR_03_MECHANICAL_LIFTING"],
        representative_precursor=rep_prec,
        similarity_summary={"avg_score": 0.88},
        evidence_summary={"member_count": 3},
        discovery_method="HYBRID_SIMILARITY_GROUPING_V1",
        status=PatternStatus.CANDIDATE,
        first_detected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        last_detected_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
    )
    db_session.add(pattern)
    await db_session.flush()

    # Test list endpoint
    res_list = await async_client.get("/api/v1/sif/patterns")
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["total_patterns"] >= 1
    found = next((p for p in list_data["patterns"] if p["id"] == str(pat_id)), None)
    assert found is not None
    assert found["pattern_code"] == "PAT_LSR_03_SUSPENDED_LOAD_RIGGING_FAILURE"
    assert found["occurrence_count"] == 3
    assert found["status"] == "CANDIDATE"

    # Test filter by status
    res_filtered = await async_client.get("/api/v1/sif/patterns?status=CANDIDATE")
    assert res_filtered.status_code == 200
    assert res_filtered.json()["total_patterns"] >= 1

    # Test filter by non-matching status
    res_empty = await async_client.get("/api/v1/sif/patterns?status=ARCHIVED")
    assert res_empty.status_code == 200
    assert res_empty.json()["total_patterns"] == 0

    # Test detail endpoint
    res_detail = await async_client.get(f"/api/v1/sif/patterns/{pat_id}")
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert detail_data["id"] == str(pat_id)
    assert detail_data["representative_precursor"]["hazard"] == "Suspended Load"
    assert detail_data["discovery_method"] == "HYBRID_SIMILARITY_GROUPING_V1"

    # Test detail 404
    non_existent = uuid.uuid4()
    res_404 = await async_client.get(f"/api/v1/sif/patterns/{non_existent}")
    assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_trigger_pattern_discovery_endpoint(async_client: AsyncClient, db_session: AsyncSession):
    """Verify POST /api/v1/sif/patterns/discover endpoint runs discovery successfully."""
    prec = {
        "hazard": "Hot Work",
        "activity": "Welding",
        "barrier_failure": "Gas Monitoring Failure",
        "exposure": "Flash Fire",
        "potential_consequence": "FATALITY",
        "life_saving_rule": "LSR_06_HOT_WORK",
        "location": "EPS Moran",
    }

    # Add 3 reports
    for i in range(3):
        rep = SafetyReport(
            report_ref=f"SR-DISC-{i}-{uuid.uuid4().hex[:6]}",
            source_type=SourceType.NEAR_MISS,
            raw_text=f"Hot work gas ignition incident {i}.",
            reported_location="EPS Moran",
            actual_severity=ActualOutcome.NO_INJURY,
            event_timestamp=datetime(2026, 1, 10 + i, 10, 0, tzinfo=timezone.utc),
        )
        db_session.add(rep)
        await db_session.flush()

        ass = SIFAssessment(
            report_id=rep.id,
            sif_classification=SIFClassification.POTENTIAL_SIF,
            evidence_score=0.85,
            evidence_strength=EvidenceStrength.HIGH,
            rule_based_screening_score=0.85,
            potential_severity=PotentialOutcome.FATALITY,
            evidence_spans=[],
            structured_precursor=prec,
            text_embedding=None,
            pattern_id=None,
            triage_status=TriageStatus.AUTO_SCREENED,
        )
        db_session.add(ass)
        await db_session.flush()

    response = await async_client.post("/api/v1/sif/patterns/discover")
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert data["qualifying_groups_found"] >= 1
    assert data["discovery_method"] == "HYBRID_SIMILARITY_GROUPING_V1"
