"""Integration tests for Phase 3 analytics and risk concentration API endpoints."""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.assessment import SIFAssessment
from app.db.models.report import SafetyReport
from app.domain.enums import ActualOutcome, EvidenceStrength, PotentialOutcome, SIFClassification, SourceType, TriageStatus


@pytest.mark.asyncio
async def test_analytics_api_endpoints_full_cycle(async_client: AsyncClient, db_session: AsyncSession):
    """Verify full REST API cycle for concentrations, refresh, trends, distribution, and summary."""
    # 1. Initially check /summary on empty DB
    res_sum = await async_client.get("/api/v1/sif/analytics/summary")
    assert res_sum.status_code == 200
    sum_data = res_sum.json()
    assert sum_data["total_reports_analyzed"] == 0
    assert sum_data["sif_potential_percentage"] == 0.0

    # 2. Check /concentrations empty list
    res_list = await async_client.get("/api/v1/sif/analytics/concentrations")
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["total_concentrations"] == 0
    assert list_data["concentrations"] == []

    # 3. Insert 3 SIF assessments into DB
    prec = {
        "hazard": "Suspended Load",
        "activity": "Crane Lifting",
        "barrier_failure": "Rigging Failure",
        "exposure": "Line of Fire",
        "potential_consequence": "FATALITY",
        "life_saving_rule": "LSR_03_MECHANICAL_LIFTING",
    }
    for i in range(3):
        rep = SafetyReport(
            report_ref=f"SR-API-{i}",
            source_type=SourceType.NEAR_MISS,
            raw_text=f"Crane hoist line failure event {i}.",
            reported_location="Rig-04 Moran",
            actual_severity=ActualOutcome.NO_INJURY,
            event_timestamp=datetime(2026, 1 + i, 10, 10, 0, tzinfo=timezone.utc),
        )
        db_session.add(rep)
        await db_session.flush()

        ass = SIFAssessment(
            report_id=rep.id,
            sif_classification=SIFClassification.POTENTIAL_SIF,
            evidence_score=0.9,
            evidence_strength=EvidenceStrength.HIGH,
            rule_based_screening_score=0.9,
            potential_severity=PotentialOutcome.FATALITY,
            evidence_spans=[],
            structured_precursor=prec,
            triage_status=TriageStatus.AUTO_SCREENED,
        )
        db_session.add(ass)

    await db_session.commit()

    # 4. Trigger POST /refresh
    res_refresh = await async_client.post("/api/v1/sif/analytics/concentrations/refresh")
    assert res_refresh.status_code == 200
    ref_data = res_refresh.json()
    assert ref_data["assessments_evaluated"] == 3
    assert ref_data["concentrations_created"] >= 4
    assert ref_data["total_active_concentrations"] >= 4

    # 5. GET /concentrations with dimension filter
    res_haz = await async_client.get("/api/v1/sif/analytics/concentrations?dimension=HAZARD")
    assert res_haz.status_code == 200
    haz_data = res_haz.json()
    assert haz_data["total_concentrations"] == 1
    conc_item = haz_data["concentrations"][0]
    assert conc_item["dimension_value"] == "Suspended Load"
    assert conc_item["occurrence_count"] == 3
    conc_id = conc_item["id"]

    # 6. GET /concentrations/{id}
    res_detail = await async_client.get(f"/api/v1/sif/analytics/concentrations/{conc_id}")
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert detail_data["id"] == conc_id
    assert detail_data["dimension_type"] == "HAZARD"
    assert "evidence_summary" in detail_data

    # 7. GET /concentrations/nonexistent -> 404
    fake_id = uuid.uuid4()
    res_404 = await async_client.get(f"/api/v1/sif/analytics/concentrations/{fake_id}")
    assert res_404.status_code == 404

    # 8. GET /trends
    res_trends = await async_client.get("/api/v1/sif/analytics/trends?dimension=HAZARD")
    assert res_trends.status_code == 200
    trends_data = res_trends.json()
    assert "trends" in trends_data
    assert len(trends_data["trends"]) >= 1

    # 9. GET /distribution
    res_dist = await async_client.get("/api/v1/sif/analytics/distribution?dimension=HAZARD")
    assert res_dist.status_code == 200
    dist_data = res_dist.json()
    assert dist_data["dimension_type"] == "HAZARD"
    assert dist_data["total_occurrences"] >= 3
    assert len(dist_data["items"]) >= 1

    # 10. GET /summary after refresh
    res_sum2 = await async_client.get("/api/v1/sif/analytics/summary")
    assert res_sum2.status_code == 200
    sum_data2 = res_sum2.json()
    assert sum_data2["total_reports_analyzed"] == 3
    assert sum_data2["total_sif_potential_count"] == 3
    assert sum_data2["sif_potential_percentage"] == 100.0
    assert sum_data2["active_risk_concentrations_count"] >= 4
