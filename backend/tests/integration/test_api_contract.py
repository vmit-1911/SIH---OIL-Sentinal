"""Phase 11 API Contract, Verification, and Frontend Compatibility Test Suite.

Verifies:
- Scenarios A-T across all 9 Command Center endpoints.
- Consistent error structures, request traceability, pagination, and empty states.
- Read-only guarantees and non-mutation of underlying Phase 1-10 source tables.
- OpenAPI schema registration and compatibility.
"""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    HSEActionRecommendation,
    HSECase,
    HSECaseEvent,
    LSRReportMapping,
    LSRTaxonomy,
    PrecursorPattern,
    RiskConcentration,
    SafetyReport,
    SIFAssessment,
    TriageReview,
)
from app.domain.enums import (
    ActionCategory,
    ActionPriority,
    ActionSourceType,
    ActionStatus,
    CasePriority,
    CaseStatus,
    CaseType,
    ConcentrationDimension,
    ConcentrationStatus,
    ObservedTrend,
    PatternStatus,
    PotentialOutcome,
    ReviewState,
    SIFClassification,
    SourceType,
)
from app.schemas.api_contract import API_VERSION, ApiError, ApiErrorResponse, ApiMetadata, PaginationMetadata
from app.schemas.command_center import (
    ActionOverviewDTO,
    CaseOverviewDTO,
    CommandCenterOverview,
    ConcentrationOverviewDTO,
    InvestigationSnapshotDTO,
    LSROverviewDTO,
    PrecursorOverviewDTO,
    ReviewQueueOverviewDTO,
    SIFOverviewDTO,
)


@pytest.mark.asyncio
async def test_scenario_a_all_command_center_endpoints_exist(async_client: AsyncClient):
    """Scenario A: All 9 Command Center endpoints exist and respond with HTTP 200."""
    endpoints = [
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
    for ep in endpoints:
        res = await async_client.get(ep)
        assert res.status_code == 200, f"Endpoint {ep} failed with status {res.status_code}: {res.text}"


@pytest.mark.asyncio
async def test_scenario_b_empty_state_responses(async_client: AsyncClient):
    """Scenario B: Empty-state responses return 0 counts, empty lists, and valid timestamps."""
    # Overview empty state
    res_ov = await async_client.get("/api/v1/sif/command-center/overview")
    assert res_ov.status_code == 200
    ov_data = res_ov.json()
    assert ov_data["total_reports"] >= 0
    assert ov_data["total_assessments"] >= 0
    assert ov_data["potential_sif_count"] >= 0
    assert ov_data["open_action_count"] >= 0
    assert ov_data["active_case_count"] >= 0
    assert "generated_at" in ov_data
    assert "data_as_of" in ov_data

    # Precursors empty state
    res_prec = await async_client.get("/api/v1/sif/command-center/precursors?location=NON_EXISTENT_FACILITY_XYZ")
    assert res_prec.status_code == 200
    prec_data = res_prec.json()
    assert prec_data["total_patterns"] == 0
    assert prec_data["top_patterns"] == []

    # Concentrations empty state
    res_conc = await async_client.get("/api/v1/sif/command-center/concentrations?location=NON_EXISTENT_FACILITY_XYZ")
    assert res_conc.status_code == 200
    conc_data = res_conc.json()
    assert conc_data["total_concentrations"] == 0
    assert conc_data["items"] == []


@pytest.mark.asyncio
async def test_scenario_c_populated_responses_and_dto_validation(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Scenario C: Valid populated responses parse into validated DTO models."""
    now = datetime.now(timezone.utc)
    rep = SafetyReport(
        report_ref="API-POP-01",
        raw_text="Worker observed scaffold without toe-boards at Rig-09.",
        reported_location="Rig-09",
        source_type=SourceType.UC,
        created_at=now,
    )
    db_session.add(rep)
    await db_session.flush()

    asm = SIFAssessment(
        report_id=rep.id,
        sif_classification=SIFClassification.POTENTIAL_SIF,
        potential_severity=PotentialOutcome.PERMANENT_DISABLING_INJURY,
        evidence_score=0.88,
        precursor_signature="FALL_PROTECTION",
        assessed_at=now,
    )
    db_session.add(asm)

    pat = PrecursorPattern(
        pattern_code=f"PAT-{uuid.uuid4().hex[:8].upper()}",
        title="Scaffolding and Fall Protection Deficiencies",
        description="Recurrent issues with missing scaffold toe-boards",
        occurrence_count=4,
        supporting_report_ids=[str(rep.id)],
        affected_locations=["Rig-09"],
        hazard_category="WORKING_AT_HEIGHT",
        activity_type="MAINTENANCE",
        failed_barrier_type="PHYSICAL_GUARD",
        status=PatternStatus.ACTIVE,
        first_detected_at=now,
        last_detected_at=now,
    )
    db_session.add(pat)

    conc = RiskConcentration(
        concentration_key=f"CONC-{uuid.uuid4().hex[:8].upper()}",
        dimension_type=ConcentrationDimension.LOCATION,
        dimension_value="Rig-09",
        occurrence_count=5,
        distinct_report_count=4,
        distinct_location_count=1,
        observed_trend=ObservedTrend.INCREASING,
        supporting_locations=["Rig-09"],
        status=ConcentrationStatus.ACTIVE,
        first_observed_at=now,
        last_observed_at=now,
    )
    db_session.add(conc)

    act = HSEActionRecommendation(
        action_key=f"ACT-{uuid.uuid4().hex[:8].upper()}",
        rule_id="ACT-R01-SCAFFOLD",
        source_type=ActionSourceType.ASSESSMENT,
        source_id=str(asm.id),
        action_title="Inspect Rig-09 Scaffolding Guards",
        action_description="Conduct physical audit of toe-boards and guardrails",
        action_category=ActionCategory.FALL_PROTECTION_VERIFICATION,
        priority=ActionPriority.HIGH,
        rationale="Action generated from SIF assessment",
        status=ActionStatus.OPEN,
        created_at=now,
        updated_at=now,
    )
    db_session.add(act)

    hse_case = HSECase(
        case_key=f"CASE-{uuid.uuid4().hex[:8].upper()}",
        title="Rig-09 Fall Protection Investigation",
        description="Investigation into recurring scaffold defects",
        case_type=CaseType.SIF_INVESTIGATION,
        status=CaseStatus.INVESTIGATING,
        priority=CasePriority.HIGH,
        owner="safety_lead@oil.in",
        created_by="system",
        created_at=now,
        updated_at=now,
    )
    db_session.add(hse_case)
    await db_session.commit()

    # Validate DTO parsing across all endpoints
    res_ov = await async_client.get("/api/v1/sif/command-center/overview")
    assert res_ov.status_code == 200
    ov_dto = CommandCenterOverview.model_validate(res_ov.json())
    assert ov_dto.potential_sif_count >= 1

    res_sif = await async_client.get("/api/v1/sif/command-center/sif")
    assert res_sif.status_code == 200
    sif_dto = SIFOverviewDTO.model_validate(res_sif.json())
    assert sif_dto.total_assessments >= 1

    res_prec = await async_client.get("/api/v1/sif/command-center/precursors")
    assert res_prec.status_code == 200
    prec_dto = PrecursorOverviewDTO.model_validate(res_prec.json())
    assert prec_dto.total_patterns >= 1

    res_conc = await async_client.get("/api/v1/sif/command-center/concentrations")
    assert res_conc.status_code == 200
    conc_dto = ConcentrationOverviewDTO.model_validate(res_conc.json())
    assert conc_dto.total_concentrations >= 1

    res_lsr = await async_client.get("/api/v1/sif/command-center/lsr")
    assert res_lsr.status_code == 200
    lsr_dto = LSROverviewDTO.model_validate(res_lsr.json())
    assert isinstance(lsr_dto.rules, list)

    res_act = await async_client.get("/api/v1/sif/command-center/actions")
    assert res_act.status_code == 200
    act_dto = ActionOverviewDTO.model_validate(res_act.json())
    assert act_dto.total_actions >= 1

    res_case = await async_client.get("/api/v1/sif/command-center/cases")
    assert res_case.status_code == 200
    case_dto = CaseOverviewDTO.model_validate(res_case.json())
    assert case_dto.total_cases >= 1

    res_rev = await async_client.get("/api/v1/sif/command-center/reviews")
    assert res_rev.status_code == 200
    rev_dto = ReviewQueueOverviewDTO.model_validate(res_rev.json())
    assert isinstance(rev_dto.total_reviews, int)


@pytest.mark.asyncio
async def test_scenario_d_date_filtering(async_client: AsyncClient):
    """Scenario D: Date filtering with from_date and to_date filters metrics."""
    t_start = "2020-01-01T00:00:00Z"
    t_end = "2020-12-31T23:59:59Z"

    res = await async_client.get(f"/api/v1/sif/command-center/overview?from_date={t_start}&to_date={t_end}")
    assert res.status_code == 200
    data = res.json()
    assert data["reporting_period"]["from_date"] is not None
    assert data["reporting_period"]["to_date"] is not None
    assert data["total_reports"] == 0


@pytest.mark.asyncio
async def test_scenario_e_location_filtering(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Scenario E: Location filtering restricts metrics to matching location."""
    now = datetime.now(timezone.utc)
    rep = SafetyReport(
        report_ref="API-LOC-01",
        raw_text="Overhead crane hydraulic line leak.",
        reported_location="Rig-09",
        source_type=SourceType.UC,
        created_at=now,
    )
    db_session.add(rep)
    await db_session.commit()

    res_match = await async_client.get("/api/v1/sif/command-center/overview?location=Rig-09")
    assert res_match.status_code == 200
    data_match = res_match.json()
    assert data_match["total_reports"] >= 1

    res_nomatch = await async_client.get("/api/v1/sif/command-center/overview?location=UNMATCHED_LOC_999")
    assert res_nomatch.status_code == 200
    data_nomatch = res_nomatch.json()
    assert data_nomatch["total_reports"] == 0


@pytest.mark.asyncio
async def test_scenario_f_lsr_filtering(async_client: AsyncClient):
    """Scenario F: Life-Saving Rule code filtering."""
    res = await async_client.get("/api/v1/sif/command-center/lsr?lsr_code=WORK_AT_HEIGHT")
    assert res.status_code == 200
    data = res.json()
    assert "rules" in data


@pytest.mark.asyncio
async def test_scenario_g_concentration_filters(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Scenario G: Concentration filtering by canonical dimension and observed trend."""
    now = datetime.now(timezone.utc)
    conc = RiskConcentration(
        concentration_key=f"CONC-{uuid.uuid4().hex[:8].upper()}",
        dimension_type=ConcentrationDimension.LOCATION,
        dimension_value="Rig-12",
        occurrence_count=7,
        distinct_report_count=5,
        distinct_location_count=1,
        observed_trend=ObservedTrend.INCREASING,
        supporting_locations=["Rig-12"],
        status=ConcentrationStatus.ACTIVE,
        first_observed_at=now,
        last_observed_at=now,
    )
    db_session.add(conc)
    await db_session.commit()

    res = await async_client.get(
        "/api/v1/sif/command-center/concentrations?dimension=LOCATION&trend=INCREASING"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_concentrations"] >= 1
    for item in data["items"]:
        assert item["dimension_type"] == "LOCATION"
        assert item["observed_trend"] == "INCREASING"


@pytest.mark.asyncio
async def test_scenario_h_action_filters(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Scenario H: HSE action recommendations filtering by status, priority, category, and source."""
    now = datetime.now(timezone.utc)
    act = HSEActionRecommendation(
        action_key=f"ACT-{uuid.uuid4().hex[:8].upper()}",
        rule_id="ACT-R02-FALL",
        source_type=ActionSourceType.ASSESSMENT,
        source_id=str(uuid.uuid4()),
        action_title="Conduct fall protection harness audit",
        action_description="Check expiration dates and anchor points",
        action_category=ActionCategory.FALL_PROTECTION_VERIFICATION,
        priority=ActionPriority.HIGH,
        rationale="Action generated for fall audit",
        status=ActionStatus.OPEN,
        created_at=now,
        updated_at=now,
    )
    db_session.add(act)
    await db_session.commit()

    res = await async_client.get(
        "/api/v1/sif/command-center/actions?status=OPEN&priority=HIGH&category=FALL_PROTECTION_VERIFICATION"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_actions"] >= 1
    assert data["status_counts"].get("OPEN", 0) >= 1


@pytest.mark.asyncio
async def test_scenario_i_case_filters(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Scenario I: Case filtering by status, priority, case_type, and owner."""
    now = datetime.now(timezone.utc)
    hse_case = HSECase(
        case_key=f"CASE-{uuid.uuid4().hex[:8].upper()}",
        title="Rig-15 Rigging Failure Investigation",
        description="Formal investigation into hoist slip",
        case_type=CaseType.SIF_INVESTIGATION,
        status=CaseStatus.INVESTIGATING,
        priority=CasePriority.HIGH,
        owner="safety_lead@oil.in",
        created_by="system",
        created_at=now,
        updated_at=now,
    )
    db_session.add(hse_case)
    await db_session.commit()

    res = await async_client.get(
        "/api/v1/sif/command-center/cases?status=INVESTIGATING&priority=HIGH&case_type=SIF_INVESTIGATION&owner=safety_lead@oil.in"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_cases"] >= 1
    assert data["status_counts"].get("INVESTIGATING", 0) >= 1


@pytest.mark.asyncio
async def test_scenario_j_pagination_invariants(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Scenario J: Pagination invariants (limit, offset, non-mutation of aggregate total)."""
    now = datetime.now(timezone.utc)
    for i in range(3):
        conc = RiskConcentration(
            concentration_key=f"CONC-PAG-{i}-{uuid.uuid4().hex[:6].upper()}",
            dimension_type=ConcentrationDimension.HAZARD,
            dimension_value=f"Hazard-{i}",
            occurrence_count=i + 3,
            distinct_report_count=i + 2,
            distinct_location_count=1,
            observed_trend=ObservedTrend.STABLE,
            supporting_locations=["Rig-01"],
            status=ConcentrationStatus.ACTIVE,
            first_observed_at=now,
            last_observed_at=now,
        )
        db_session.add(conc)
    await db_session.commit()

    res1 = await async_client.get("/api/v1/sif/command-center/concentrations?limit=1&offset=0")
    assert res1.status_code == 200
    data1 = res1.json()
    total = data1["total_concentrations"]

    res2 = await async_client.get("/api/v1/sif/command-center/concentrations?limit=1&offset=1")
    assert res2.status_code == 200
    data2 = res2.json()

    # Total must remain identical regardless of offset
    assert data2["total_concentrations"] == total
    assert data1["limit"] == 1
    assert data1["offset"] == 0
    assert data2["offset"] == 1


@pytest.mark.asyncio
async def test_scenario_k_invalid_date_range(async_client: AsyncClient):
    """Scenario K: Invalid date range (from_date > to_date) returns HTTP 400 with INVALID_DATE_RANGE."""
    t_start = "2026-12-31T00:00:00Z"
    t_end = "2026-01-01T00:00:00Z"
    res = await async_client.get(f"/api/v1/sif/command-center/overview?from_date={t_start}&to_date={t_end}")
    assert res.status_code == 400
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_DATE_RANGE"
    assert "cannot be greater than" in data["error"]["message"]
    assert "request_id" in data["error"]


@pytest.mark.asyncio
async def test_scenario_l_invalid_enum_validation(async_client: AsyncClient):
    """Scenario L: Invalid enum query parameters return HTTP 422 with VALIDATION_ERROR."""
    res = await async_client.get("/api/v1/sif/command-center/concentrations?dimension=INVALID_DIMENSION_TYPE")
    assert res.status_code == 422
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "request_id" in data["error"]


@pytest.mark.asyncio
async def test_scenario_m_missing_resource_error(async_client: AsyncClient):
    """Scenario M: Non-existent UUIDs return HTTP 404 with structured RESOURCE_NOT_FOUND error."""
    fake_id = str(uuid.uuid4())
    res = await async_client.get(f"/api/v1/sif/reports/{fake_id}")
    assert res.status_code == 404
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] in ("REPORT_NOT_FOUND", "RESOURCE_NOT_FOUND")
    assert "request_id" in data["error"]


@pytest.mark.asyncio
async def test_scenario_n_consistent_error_schema(async_client: AsyncClient):
    """Scenario N: Structured ApiError schema validation on errors."""
    res = await async_client.get("/api/v1/sif/cases/INVALID-UUID-1234")
    assert res.status_code in (404, 422)
    data = res.json()
    assert "error" in data
    err_obj = data["error"]
    assert "code" in err_obj
    assert "message" in err_obj
    assert "request_id" in err_obj
    ApiError.model_validate(err_obj)


@pytest.mark.asyncio
async def test_scenario_o_request_id_traceability(async_client: AsyncClient):
    """Scenario O: Deterministic request-level traceability header handling."""
    # Auto-generated request_id
    res1 = await async_client.get("/api/v1/sif/command-center/overview")
    assert res1.status_code == 200
    assert "X-Request-ID" in res1.headers
    assert len(res1.headers["X-Request-ID"]) > 0

    # Preserved client-supplied request_id
    custom_id = "test-custom-trace-id-98765"
    res2 = await async_client.get(
        "/api/v1/sif/command-center/overview",
        headers={"X-Request-ID": custom_id},
    )
    assert res2.status_code == 200
    assert res2.headers["X-Request-ID"] == custom_id


@pytest.mark.asyncio
async def test_scenario_p_r_read_only_and_no_source_mutation(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Scenarios P & R: Read-only invariant and zero mutation of Phase 1-10 source tables."""
    # Count rows across all source tables
    count_rep_before = (await db_session.execute(select(func.count(SafetyReport.id)))).scalar()
    count_asm_before = (await db_session.execute(select(func.count(SIFAssessment.id)))).scalar()
    count_pat_before = (await db_session.execute(select(func.count(PrecursorPattern.id)))).scalar()
    count_conc_before = (await db_session.execute(select(func.count(RiskConcentration.id)))).scalar()
    count_rev_before = (await db_session.execute(select(func.count(TriageReview.id)))).scalar()
    count_act_before = (await db_session.execute(select(func.count(HSEActionRecommendation.id)))).scalar()
    count_case_before = (await db_session.execute(select(func.count(HSECase.id)))).scalar()
    count_event_before = (await db_session.execute(select(func.count(HSECaseEvent.id)))).scalar()

    # Invoke all 9 endpoints repeatedly
    for _ in range(2):
        await async_client.get("/api/v1/sif/command-center/overview")
        await async_client.get("/api/v1/sif/command-center/sif")
        await async_client.get("/api/v1/sif/command-center/precursors")
        await async_client.get("/api/v1/sif/command-center/concentrations")
        await async_client.get("/api/v1/sif/command-center/lsr")
        await async_client.get("/api/v1/sif/command-center/actions")
        await async_client.get("/api/v1/sif/command-center/cases")
        await async_client.get("/api/v1/sif/command-center/reviews")
        await async_client.get("/api/v1/sif/command-center/investigation-snapshot?report_ref=API-POP-01")

    # Re-verify row counts
    count_rep_after = (await db_session.execute(select(func.count(SafetyReport.id)))).scalar()
    count_asm_after = (await db_session.execute(select(func.count(SIFAssessment.id)))).scalar()
    count_pat_after = (await db_session.execute(select(func.count(PrecursorPattern.id)))).scalar()
    count_conc_after = (await db_session.execute(select(func.count(RiskConcentration.id)))).scalar()
    count_rev_after = (await db_session.execute(select(func.count(TriageReview.id)))).scalar()
    count_act_after = (await db_session.execute(select(func.count(HSEActionRecommendation.id)))).scalar()
    count_case_after = (await db_session.execute(select(func.count(HSECase.id)))).scalar()
    count_event_after = (await db_session.execute(select(func.count(HSECaseEvent.id)))).scalar()

    assert count_rep_before == count_rep_after
    assert count_asm_before == count_asm_after
    assert count_pat_before == count_pat_after
    assert count_conc_before == count_conc_after
    assert count_rev_before == count_rev_after
    assert count_act_before == count_act_after
    assert count_case_before == count_case_after
    assert count_event_before == count_event_after


@pytest.mark.asyncio
async def test_scenario_q_openapi_registration(async_client: AsyncClient):
    """Scenario Q: OpenAPI schema contains all 9 Command Center endpoints and schemas."""
    res = await async_client.get("/openapi.json")
    assert res.status_code == 200
    schema = res.json()
    paths = schema.get("paths", {})

    expected = [
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
    for ep in expected:
        assert ep in paths, f"OpenAPI missing path: {ep}"
        assert "get" in paths[ep], f"Path {ep} missing GET method"


@pytest.mark.asyncio
async def test_scenario_s_investigation_snapshot_contract(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Scenario S: Investigation snapshot operational graph contract."""
    now = datetime.now(timezone.utc)
    rep = SafetyReport(
        report_ref="API-SNAP-01",
        raw_text="Worker observed electrical hazard in MCC room.",
        reported_location="Rig-01",
        source_type=SourceType.UC,
        created_at=now,
    )
    db_session.add(rep)
    await db_session.commit()

    res = await async_client.get("/api/v1/sif/command-center/investigation-snapshot?report_ref=API-SNAP-01")
    assert res.status_code == 200
    dto = InvestigationSnapshotDTO.model_validate(res.json())
    assert dto.query_target.get("report_ref") == "API-SNAP-01"
    assert "summary" in res.json()
    assert len(dto.reports) >= 1
    assert dto.reports[0].report_ref == "API-SNAP-01"


@pytest.mark.asyncio
async def test_scenario_t_metadata_models_and_version():
    """Scenario T: API metadata and version constants integrity."""
    assert API_VERSION == "1.0"
    meta = ApiMetadata(request_id="req-12345")
    assert meta.request_id == "req-12345"
    assert meta.api_version == "1.0"
    assert isinstance(meta.generated_at, datetime)

    pag = PaginationMetadata(limit=10, offset=0, returned=5, total=25, has_next=True)
    assert pag.has_next is True
    assert pag.total == 25
