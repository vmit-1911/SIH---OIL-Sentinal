"""Integration tests for GET /api/v1/taxonomies."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_taxonomies_returns_iogp_459(async_client: AsyncClient):
    """Verify taxonomies endpoint returns the 9 IOGP rules."""
    response = await async_client.get("/api/v1/taxonomies")
    assert response.status_code == 200
    
    data = response.json()
    assert "taxonomies" in data
    assert len(data["taxonomies"]) == 1
    
    tax = data["taxonomies"][0]
    assert tax["taxonomy_id"] == "IOGP_REPORT_459"
    assert tax["authority"] == "IOGP"
    assert tax["version"] == "2018"
    assert len(tax["rules"]) == 9
    
    codes = [r["code"] for r in tax["rules"]]
    assert "LSR_01_BYPASS_SAFETY_CONTROLS" in codes
    assert "LSR_07_SAFE_MECHANICAL_LIFTING" in codes
    assert "LSR_09_WORKING_AT_HEIGHT" in codes
