import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.action import HSEActionRecommendation
from app.db.models.assessment import SIFAssessment
from app.db.models.report import SafetyReport
from app.domain.enums import (
    ActionCategory,
    ActionPriority,
    ActionSourceType,
    ActionStatus,
    CaseEventType,
    CasePriority,
    CaseSourceType,
    CaseStatus,
    CaseType,
    SourceType,
)
from app.schemas.report import SingleReportAnalysisRequest
from app.services.sif_analysis_service import SIFAnalysisService


@pytest.mark.asyncio
async def test_create_and_get_case_endpoint(async_client: AsyncClient, db_session: AsyncSession):
    """POST /api/v1/sif/cases creates an HSE case and GET /api/v1/sif/cases/{case_id} retrieves it."""
    # Seed SafetyReport for source reference validation
    report = SafetyReport(
        report_ref="OIL-API-REP-01",
        raw_text="Driller observed unexpected pressure rise at Rig-02 wellhead.",
        source_type=SourceType.NEAR_MISS,
        reported_location="Rig-02",
    )
    db_session.add(report)
    await db_session.commit()

    payload = {
        "title": "API Rig Floor Near-Miss Case",
        "description": "Investigating high potential near miss on rig floor.",
        "case_type": "SIF_INVESTIGATION",
        "priority": "HIGH",
        "owner": "investigator_rahul",
        "created_by": "auditor_api",
        "sources": [
            {
                "source_type": "REPORT",
                "source_id": "OIL-API-REP-01",
                "source_metadata": {"facility": "Rig-02"},
            }
        ],
    }

    create_res = await async_client.post("/api/v1/sif/cases", json=payload)
    assert create_res.status_code == 201
    data = create_res.json()
    assert data["title"] == "API Rig Floor Near-Miss Case"
    assert data["status"] == "OPEN"
    assert data["priority"] == "HIGH"
    assert data["owner"] == "investigator_rahul"
    assert len(data["sources"]) == 1
    assert data["sources"][0]["source_id"] == "OIL-API-REP-01"

    case_id = data["id"]

    # Retrieve by ID
    get_res = await async_client.get(f"/api/v1/sif/cases/{case_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["id"] == case_id
    assert get_data["case_key"] == data["case_key"]


@pytest.mark.asyncio
async def test_list_cases_with_filtering_and_pagination(async_client: AsyncClient):
    """GET /api/v1/sif/cases supports filtering by priority, type, owner and pagination."""
    # Create 2 cases
    await async_client.post(
        "/api/v1/sif/cases",
        json={
            "title": "Case Priority Filter 1",
            "case_type": "BARRIER_REVIEW",
            "priority": "CRITICAL_REVIEW",
            "owner": "filter_user_1",
            "created_by": "test_user",
        },
    )
    await async_client.post(
        "/api/v1/sif/cases",
        json={
            "title": "Case Priority Filter 2",
            "case_type": "LOCATION_REVIEW",
            "priority": "MEDIUM",
            "owner": "filter_user_2",
            "created_by": "test_user",
        },
    )

    # Filter by priority
    res_crit = await async_client.get("/api/v1/sif/cases?priority=CRITICAL_REVIEW")
    assert res_crit.status_code == 200
    crit_data = res_crit.json()
    assert crit_data["total"] >= 1
    assert all(c["priority"] == "CRITICAL_REVIEW" for c in crit_data["items"])

    # Filter by owner
    res_owner = await async_client.get("/api/v1/sif/cases?owner=filter_user_1")
    assert res_owner.status_code == 200
    owner_data = res_owner.json()
    assert any(c["owner"] == "filter_user_1" for c in owner_data["items"])

    # Pagination
    res_page = await async_client.get("/api/v1/sif/cases?page=1&page_size=1")
    assert res_page.status_code == 200
    page_data = res_page.json()
    assert page_data["page"] == 1
    assert page_data["page_size"] == 1
    assert len(page_data["items"]) == 1


@pytest.mark.asyncio
async def test_update_and_assign_case_endpoints(async_client: AsyncClient):
    """PATCH /api/v1/sif/cases/{case_id} and POST /api/v1/sif/cases/{case_id}/assign update metadata."""
    create_res = await async_client.post(
        "/api/v1/sif/cases",
        json={"title": "Original Case Title", "created_by": "test_user"},
    )
    case_id = create_res.json()["id"]

    # PATCH
    patch_res = await async_client.patch(
        f"/api/v1/sif/cases/{case_id}",
        json={"title": "Updated Case Title", "priority": "HIGH"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Updated Case Title"
    assert patch_res.json()["priority"] == "HIGH"

    # ASSIGN
    assign_res = await async_client.post(
        f"/api/v1/sif/cases/{case_id}/assign",
        json={"owner": "investigator_alok", "rationale": "Specialized in gas leaks"},
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["owner"] == "investigator_alok"
    assert assign_res.json()["assigned_at"] is not None


@pytest.mark.asyncio
async def test_case_lifecycle_and_closure_endpoints(async_client: AsyncClient, db_session: AsyncSession):
    """POST /api/v1/sif/cases/{case_id}/status transitions case lifecycle and validates closure."""
    create_res = await async_client.post(
        "/api/v1/sif/cases",
        json={"title": "Lifecycle Endpoints Case", "created_by": "test_user"},
    )
    case_id = create_res.json()["id"]

    # Transition to TRIAGE
    res_triage = await async_client.post(
        f"/api/v1/sif/cases/{case_id}/status",
        json={"status": "TRIAGE", "actor_id": "test_user"},
    )
    assert res_triage.status_code == 200
    assert res_triage.json()["status"] == "TRIAGE"

    # Transition to INVESTIGATING
    res_inv = await async_client.post(
        f"/api/v1/sif/cases/{case_id}/status",
        json={"status": "INVESTIGATING", "actor_id": "test_user"},
    )
    assert res_inv.status_code == 200
    assert res_inv.json()["status"] == "INVESTIGATING"

    # Attempt closure without rationale -> 400
    res_err_close = await async_client.post(
        f"/api/v1/sif/cases/{case_id}/status",
        json={"status": "CLOSED", "actor_id": "test_user", "rationale": ""},
    )
    assert res_err_close.status_code == 400

    # Successful closure
    res_close = await async_client.post(
        f"/api/v1/sif/cases/{case_id}/status",
        json={"status": "CLOSED", "actor_id": "test_user", "rationale": "Investigation complete and controls verified."},
    )
    assert res_close.status_code == 200
    assert res_close.json()["status"] == "CLOSED"
    assert res_close.json()["closed_at"] is not None

    # Reopen
    res_reopen = await async_client.post(
        f"/api/v1/sif/cases/{case_id}/reopen",
        json={"actor_id": "test_user", "rationale": "Follow-up inspection revealed recurring deficiency."},
    )
    assert res_reopen.status_code == 200
    assert res_reopen.json()["status"] == "INVESTIGATING"
    assert res_reopen.json()["closed_at"] is None


@pytest.mark.asyncio
async def test_cancelled_case_reopening_is_rejected(async_client: AsyncClient):
    """CANCELLED cases cannot be reopened; returns deterministic 400 error."""
    create_res = await async_client.post(
        "/api/v1/sif/cases",
        json={"title": "Cancelled Reopen Rejection Case", "created_by": "test_user"},
    )
    case_id = create_res.json()["id"]

    # Cancel case
    res_cancel = await async_client.post(
        f"/api/v1/sif/cases/{case_id}/status",
        json={"status": "CANCELLED", "actor_id": "test_user", "rationale": "Logged erroneously."},
    )
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "CANCELLED"

    # Attempt to reopen -> 400 Bad Request
    res_reopen = await async_client.post(
        f"/api/v1/sif/cases/{case_id}/reopen",
        json={"actor_id": "test_user", "rationale": "Attempting to revive cancelled case."},
    )
    assert res_reopen.status_code == 400


@pytest.mark.asyncio
async def test_attach_and_detach_source_endpoints(async_client: AsyncClient, db_session: AsyncSession):
    """POST /api/v1/sif/cases/{case_id}/sources and DELETE /api/v1/sif/cases/{case_id}/sources/{source_id}."""
    # Seed report
    report = SafetyReport(
        report_ref="OIL-REP-ATTACH-01",
        raw_text="Hot work commenced without combustible gas detection test.",
        source_type=SourceType.UA,
    )
    db_session.add(report)
    await db_session.commit()

    create_res = await async_client.post(
        "/api/v1/sif/cases",
        json={"title": "Source Endpoints Case", "created_by": "test_user"},
    )
    case_id = create_res.json()["id"]

    # Attach Source
    attach_res = await async_client.post(
        f"/api/v1/sif/cases/{case_id}/sources",
        json={
            "source_type": "REPORT",
            "source_id": "OIL-REP-ATTACH-01",
            "source_metadata": {"rig": "Rig-01"},
            "actor_id": "test_user",
        },
    )
    assert attach_res.status_code == 200
    assert len(attach_res.json()["sources"]) == 1

    # Attach duplicate source -> 409
    dup_res = await async_client.post(
        f"/api/v1/sif/cases/{case_id}/sources",
        json={
            "source_type": "REPORT",
            "source_id": "OIL-REP-ATTACH-01",
            "actor_id": "test_user",
        },
    )
    assert dup_res.status_code == 409

    # Detach Source
    detach_res = await async_client.delete(
        f"/api/v1/sif/cases/{case_id}/sources/OIL-REP-ATTACH-01?actor_id=test_user&rationale=Removed"
    )
    assert detach_res.status_code == 200
    assert len(detach_res.json()["sources"]) == 0


@pytest.mark.asyncio
async def test_case_timeline_and_summary_endpoints(async_client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/sif/cases/{case_id}/timeline and GET /api/v1/sif/cases/{case_id}/summary."""
    sif_service = SIFAnalysisService(db_session)
    analysis = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="REP-TS-01",
            raw_text="Worker observed gas leak during valve maintenance.",
            source_type=SourceType.NEAR_MISS,
        )
    )

    asm_res = await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == analysis.report_id))
    assessment = asm_res.scalar_one()

    create_res = await async_client.post(
        "/api/v1/sif/cases",
        json={
            "title": "Timeline & Summary Case",
            "case_type": "SIF_INVESTIGATION",
            "priority": "HIGH",
            "created_by": "test_user",
            "sources": [
                {"source_type": "REPORT", "source_id": str(analysis.report_id)},
                {"source_type": "ASSESSMENT", "source_id": str(assessment.id)},
            ],
        },
    )
    case_id = create_res.json()["id"]

    # Timeline
    tl_res = await async_client.get(f"/api/v1/sif/cases/{case_id}/timeline")
    assert tl_res.status_code == 200
    events = tl_res.json()
    assert len(events) >= 3  # CASE_CREATED + 2 SOURCE_ATTACHED

    # Summary
    sum_res = await async_client.get(f"/api/v1/sif/cases/{case_id}/summary")
    assert sum_res.status_code == 200
    summary = sum_res.json()
    assert summary["case_id"] == case_id
    assert summary["report_count"] == 1
    assert summary["assessment_count"] == 1


@pytest.mark.asyncio
async def test_case_not_found_errors(async_client: AsyncClient):
    """Endpoints return 404 for nonexistent case UUID."""
    fake_id = str(uuid.uuid4())
    assert (await async_client.get(f"/api/v1/sif/cases/{fake_id}")).status_code == 404
    assert (await async_client.patch(f"/api/v1/sif/cases/{fake_id}", json={"title": "new"})).status_code == 404
    assert (await async_client.post(f"/api/v1/sif/cases/{fake_id}/assign", json={"owner": "me"})).status_code == 404
    assert (await async_client.post(f"/api/v1/sif/cases/{fake_id}/status", json={"status": "CLOSED"})).status_code == 404
    assert (await async_client.get(f"/api/v1/sif/cases/{fake_id}/timeline")).status_code == 404
    assert (await async_client.get(f"/api/v1/sif/cases/{fake_id}/summary")).status_code == 404
    assert (await async_client.post(f"/api/v1/sif/cases/{fake_id}/reopen", json={"rationale": "Valid reopen rationale"})).status_code == 404
