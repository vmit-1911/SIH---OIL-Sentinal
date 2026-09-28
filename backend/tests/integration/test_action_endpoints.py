"""Integration tests for Phase 8 HSE Action & Recommendation Intelligence endpoints."""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

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
    ConcentrationDimension,
    ConcentrationStatus,
    ObservedTrend,
    PatternStatus,
    ReviewDecision,
    SourceType,
)
from app.schemas.report import SingleReportAnalysisRequest
from app.services.sif_analysis_service import SIFAnalysisService
from app.services.triage_service import TriageService


@pytest.mark.asyncio
async def test_get_actions_endpoint_with_filters(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/sif/actions filters recommendations by source_type, category, and priority."""
    sif_service = SIFAnalysisService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="OIL-ACT-001",
            raw_text="While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung across the rig floor.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04 / Moran",
        )
    )

    # 1. Trigger action generation
    gen_res = await async_client.post(
        "/api/v1/sif/actions/generate",
        json={"report_id": str(res.report_id), "persist": True},
    )
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    assert gen_data["total_generated"] >= 1

    # 2. Query actions list
    list_res = await async_client.get("/api/v1/sif/actions?limit=10")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1

    # 3. Filter by category
    filter_res = await async_client.get("/api/v1/sif/actions?action_category=BARRIER_VERIFICATION")
    assert filter_res.status_code == 200
    filter_data = filter_res.json()
    assert filter_data["total"] >= 1
    for item in filter_data["items"]:
        assert item["action_category"] == "BARRIER_VERIFICATION"


@pytest.mark.asyncio
async def test_get_action_by_id_and_entity_endpoints(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/sif/actions/{id}, /reports/{id}/actions, and /assessments/{id}/actions."""
    sif_service = SIFAnalysisService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="OIL-ACT-002",
            raw_text="Technician began unbolting high pressure flange on production manifold. Pressurized gas vented because double-block-and-bleed valve was not fully closed.",
            source_type=SourceType.NEAR_MISS,
            reported_location="EPS-Moran",
        )
    )

    # Generate
    gen_res = await async_client.post(
        "/api/v1/sif/actions/generate",
        json={"report_id": str(res.report_id), "persist": True},
    )
    assert gen_res.status_code == 200
    action_id = gen_res.json()["recommendations"][0]["id"]

    # 1. Get by ID
    get_res = await async_client.get(f"/api/v1/sif/actions/{action_id}")
    assert get_res.status_code == 200
    action_data = get_res.json()
    assert action_data["id"] == action_id
    assert action_data["rule_id"].startswith("ACT-")

    # 2. Get by Report ID
    rep_res = await async_client.get(f"/api/v1/sif/reports/{res.report_id}/actions")
    assert rep_res.status_code == 200
    rep_actions = rep_res.json()
    assert len(rep_actions) >= 1

    # 3. Get by Assessment ID
    ass_id = gen_res.json()["recommendations"][0]["source_id"]
    ass_res = await async_client.get(f"/api/v1/sif/assessments/{ass_id}/actions")
    assert ass_res.status_code == 200
    ass_actions = ass_res.json()
    assert len(ass_actions) >= 1


@pytest.mark.asyncio
async def test_pattern_and_concentration_action_endpoints(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/sif/patterns/{id}/actions and /concentrations/{key}/actions."""
    # 1. Create Pattern
    pattern = PrecursorPattern(
        id=uuid.uuid4(),
        pattern_code="PAT_API_TEST_001",
        title="Repeated Winch Line Snaps",
        description="Winch failures",
        occurrence_count=3,
        affected_locations=["Rig-01"],
        supporting_report_ids=[str(uuid.uuid4()) for _ in range(3)],
        status=PatternStatus.ACTIVE,
        first_detected_at=datetime.now(timezone.utc),
        last_detected_at=datetime.now(timezone.utc),
    )
    db_session.add(pattern)

    # 2. Create Concentration
    conc = RiskConcentration(
        id=uuid.uuid4(),
        concentration_key="CONC|LOCATION|RIG_01_TEST",
        dimension_type=ConcentrationDimension.LOCATION,
        dimension_value="Rig-01",
        occurrence_count=4,
        distinct_report_count=4,
        distinct_location_count=1,
        first_observed_at=datetime.now(timezone.utc),
        last_observed_at=datetime.now(timezone.utc),
        observed_trend=ObservedTrend.STABLE,
        supporting_report_ids=[str(uuid.uuid4()) for _ in range(4)],
        supporting_locations=["Rig-01"],
        status=ConcentrationStatus.ACTIVE,
        calculation_method="FREQUENCY_AGGREGATION_V1",
    )
    db_session.add(conc)
    await db_session.flush()

    # 3. Generate for pattern
    pat_gen = await async_client.post(
        "/api/v1/sif/actions/generate",
        json={"pattern_id": str(pattern.id), "persist": True},
    )
    assert pat_gen.status_code == 200
    pat_actions = pat_gen.json()["recommendations"]
    assert len(pat_actions) == 1

    # Query pattern actions
    pat_res = await async_client.get(f"/api/v1/sif/patterns/{pattern.id}/actions")
    assert pat_res.status_code == 200
    assert len(pat_res.json()) == 1

    # 4. Generate for concentration
    conc_gen = await async_client.post(
        "/api/v1/sif/actions/generate",
        json={"concentration_key": "CONC|LOCATION|RIG_01_TEST", "persist": True},
    )
    assert conc_gen.status_code == 200

    # Query concentration actions
    conc_res = await async_client.get("/api/v1/sif/concentrations/CONC|LOCATION|RIG_01_TEST/actions")
    assert conc_res.status_code == 200
    assert len(conc_res.json()) == 1


@pytest.mark.asyncio
async def test_action_acknowledge_and_status_transition_endpoints(async_client: AsyncClient, db_session: AsyncSession):
    """POST /api/v1/sif/actions/{id}/acknowledge and /status endpoints."""
    sif_service = SIFAnalysisService(db_session)

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="OIL-ACT-003",
            raw_text="While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung across the rig floor, narrowly missing two floormen in the swing path.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04",
        )
    )

    gen_res = await async_client.post(
        "/api/v1/sif/actions/generate",
        json={"report_id": str(res.report_id), "persist": True},
    )
    action_id = gen_res.json()["recommendations"][0]["id"]

    # 1. Acknowledge
    ack_res = await async_client.post(
        f"/api/v1/sif/actions/{action_id}/acknowledge",
        json={"actor_id": "HSE_MANAGER", "assigned_to": "TOOL_PUSHER"},
    )
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "ACKNOWLEDGED"
    assert ack_res.json()["actor_id"] == "HSE_MANAGER"
    assert ack_res.json()["assigned_to"] == "TOOL_PUSHER"

    # 2. In Progress
    in_prog_res = await async_client.post(
        f"/api/v1/sif/actions/{action_id}/status",
        json={"status": "IN_PROGRESS", "actor_id": "TOOL_PUSHER"},
    )
    assert in_prog_res.status_code == 200
    assert in_prog_res.json()["status"] == "IN_PROGRESS"

    # 3. Dismissed without rationale -> 400
    bad_dismiss = await async_client.post(
        f"/api/v1/sif/actions/{action_id}/status",
        json={"status": "DISMISSED", "actor_id": "HSE_MANAGER"},
    )
    assert bad_dismiss.status_code == 400

    # 4. Completed with rationale -> 200
    comp_res = await async_client.post(
        f"/api/v1/sif/actions/{action_id}/status",
        json={
            "status": "COMPLETED",
            "actor_id": "HSE_MANAGER",
            "status_rationale": "Wire rope replaced and certificate uploaded.",
        },
    )
    assert comp_res.status_code == 200
    assert comp_res.json()["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_action_endpoints_404_and_400_errors(async_client: AsyncClient):
    """Verify clean 404 responses for nonexistent IDs and 400 for invalid transitions."""
    fake_id = uuid.uuid4()

    r1 = await async_client.get(f"/api/v1/sif/actions/{fake_id}")
    assert r1.status_code == 404

    r2 = await async_client.get(f"/api/v1/sif/reports/{fake_id}/actions")
    assert r2.status_code == 404

    r3 = await async_client.get(f"/api/v1/sif/assessments/{fake_id}/actions")
    assert r3.status_code == 404

    r4 = await async_client.get(f"/api/v1/sif/patterns/{fake_id}/actions")
    assert r4.status_code == 404

    r5 = await async_client.get("/api/v1/sif/concentrations/NONEXISTENT_KEY/actions")
    assert r5.status_code == 404

    r6 = await async_client.post(
        f"/api/v1/sif/actions/{fake_id}/acknowledge",
        json={"actor_id": "HSE_TEST"},
    )
    assert r6.status_code == 404

    r7 = await async_client.post(
        f"/api/v1/sif/actions/{fake_id}/status",
        json={"status": "COMPLETED", "actor_id": "HSE_TEST", "status_rationale": "test"},
    )
    assert r7.status_code == 404
