"""Integration tests for skeleton endpoints returning explicit 501 Not Implemented."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_batch_upload_returns_202(async_client: AsyncClient):
    """Verify POST /api/v1/sif/batch-upload returns 202 Accepted with valid CSV upload."""
    csv_content = b"source_report_id,raw_text,reported_location\nSR-SKEL-1,Worker observed standing under suspended pipe load on drilling floor,Rig-04\n"
    files = {"file": ("reports.csv", csv_content, "text/csv")}
    response = await async_client.post("/api/v1/sif/batch-upload", files=files)
    assert response.status_code == 202
    data = response.json()
    assert "batch_id" in data
    assert data["status"] in ("PENDING", "VALIDATING", "INGESTING", "PROCESSING", "COMPLETED")



@pytest.mark.asyncio
async def test_analytics_summary_returns_200(async_client: AsyncClient):
    """Verify GET /api/v1/sif/analytics/summary returns 200 now that Phase 3 analytics is implemented."""
    response = await async_client.get("/api/v1/sif/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_reports_analyzed" in data
    assert "active_risk_concentrations_count" in data
    assert "top_life_saving_rules" in data
    assert "location_concentrations" in data

