"""Integration test for OpenAPI specification generation."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_openapi_schema_generated(async_client: AsyncClient):
    """Verify that the OpenAPI JSON schema generates with all expected paths."""
    response = await async_client.get("/openapi.json")
    assert response.status_code == 200
    
    schema = response.json()
    assert "openapi" in schema
    assert "paths" in schema
    
    paths = schema["paths"]
    assert "/api/v1/health" in paths
    assert "/api/v1/taxonomies" in paths
    assert "/api/v1/sif/analyze" in paths
    assert "/api/v1/sif/batch-upload" in paths
    assert "/api/v1/sif/batch/{batch_id}" in paths
    assert "/api/v1/sif/reports" in paths
    assert "/api/v1/sif/reports/{report_id}" in paths
    assert "/api/v1/sif/reports/{report_id}/review" in paths
    assert "/api/v1/sif/reviews/queue" in paths
    assert "/api/v1/sif/reviews/analytics/summary" in paths
    assert "/api/v1/sif/reviews/{review_id}" in paths
    assert "/api/v1/sif/reviews/{review_id}/claim" in paths
    assert "/api/v1/sif/reviews/{review_id}/decision" in paths
    assert "/api/v1/sif/reviews/{review_id}/history" in paths
    assert "/api/v1/sif/reviews/{review_id}/reopen" in paths
    assert "/api/v1/patterns" not in paths  # ensure prefix
    assert "/api/v1/sif/patterns" in paths
    assert "/api/v1/sif/analytics/summary" in paths
    assert "/api/v1/sif/reports/{report_id}/evidence" in paths
    assert "/api/v1/sif/reports/{report_id}/explanation" in paths
    assert "/api/v1/sif/reports/{report_id}/investigation-context" in paths
    assert "/api/v1/sif/assessments/{assessment_id}/evidence" in paths
    assert "/api/v1/sif/assessments/{assessment_id}/similarity" in paths
    assert "/api/v1/sif/patterns/{pattern_id}/evidence" in paths
    assert "/api/v1/sif/concentrations/{concentration_key}/evidence" in paths
    assert "/api/v1/sif/actions" in paths
    assert "/api/v1/sif/actions/{action_id}" in paths
    assert "/api/v1/sif/reports/{report_id}/actions" in paths
    assert "/api/v1/sif/assessments/{assessment_id}/actions" in paths
    assert "/api/v1/sif/patterns/{pattern_id}/actions" in paths
    assert "/api/v1/sif/actions/generate" in paths
    assert "/api/v1/sif/actions/{action_id}/acknowledge" in paths
    assert "/api/v1/sif/actions/{action_id}/status" in paths
    assert "/api/v1/sif/cases" in paths
    assert "/api/v1/sif/cases/{case_id}" in paths
    assert "/api/v1/sif/cases/{case_id}/assign" in paths
    assert "/api/v1/sif/cases/{case_id}/status" in paths
    assert "/api/v1/sif/cases/{case_id}/sources" in paths
    assert "/api/v1/sif/cases/{case_id}/sources/{source_id}" in paths
    assert "/api/v1/sif/cases/{case_id}/timeline" in paths
    assert "/api/v1/sif/cases/{case_id}/summary" in paths
    assert "/api/v1/sif/cases/{case_id}/reopen" in paths


