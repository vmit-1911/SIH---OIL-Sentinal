"""Integration tests for GET /api/v1/health."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint_response_structure(async_client: AsyncClient):
    """Verify health check returns valid JSON structure and taxonomy info."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code in [200, 503]
    
    data = response.json()
    assert "status" in data
    assert "app_name" in data
    assert "version" in data
    assert "database" in data
    assert "active_taxonomies" in data
    assert isinstance(data["active_taxonomies"], list)
    assert len(data["active_taxonomies"]) > 0
    assert data["active_taxonomies"][0]["taxonomy_id"] == "IOGP_REPORT_459"
