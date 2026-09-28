"""Integration tests for Webhook and Alert REST Endpoints (Phase 15)."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AlertChannel, AlertSeverity, WebhookEventType


@pytest.mark.asyncio
async def test_webhook_endpoints_flow(async_client: AsyncClient, db_session: AsyncSession):
    """Verify full CRUD and test execution on Webhook endpoints."""
    # 1. Subscribe Webhook
    sub_payload = {
        "name": "Integration SIEM Webhook",
        "target_url": "https://siem-integration.oilindia.in/webhook",
        "secret_token": "secret_12345",
        "subscribed_events": ["SIF_DETECTED", "HIGH_CONCENTRATION_TRIGGERED"],
        "is_active": True,
        "description": "Real-time SIEM integration",
    }
    resp_create = await async_client.post("/api/v1/sif/webhooks/subscribe", json=sub_payload)
    assert resp_create.status_code == 201
    created_data = resp_create.json()
    sub_id = created_data["id"]
    assert created_data["name"] == "Integration SIEM Webhook"

    # 2. Get Webhook
    resp_get = await async_client.get(f"/api/v1/sif/webhooks/{sub_id}")
    assert resp_get.status_code == 200
    assert resp_get.json()["id"] == sub_id

    # 3. List Webhooks
    resp_list = await async_client.get("/api/v1/sif/webhooks")
    assert resp_list.status_code == 200
    list_data = resp_list.json()
    assert list_data["total"] >= 1
    assert any(item["id"] == sub_id for item in list_data["items"])

    # 4. Patch Webhook
    patch_payload = {"name": "Updated SIEM Webhook", "is_active": False}
    resp_patch = await async_client.patch(f"/api/v1/sif/webhooks/{sub_id}", json=patch_payload)
    assert resp_patch.status_code == 200
    assert resp_patch.json()["name"] == "Updated SIEM Webhook"
    assert resp_patch.json()["is_active"] is False

    # 5. Test Webhook Ping
    resp_test = await async_client.post(f"/api/v1/sif/webhooks/{sub_id}/test")
    assert resp_test.status_code == 200
    test_log = resp_test.json()
    assert test_log["subscription_id"] == sub_id
    assert test_log["success"] is True

    # 6. List Webhook Logs
    resp_logs = await async_client.get(f"/api/v1/sif/webhooks/logs?subscription_id={sub_id}")
    assert resp_logs.status_code == 200
    assert resp_logs.json()["total"] >= 1

    # 7. Delete Webhook
    resp_del = await async_client.delete(f"/api/v1/sif/webhooks/{sub_id}")
    assert resp_del.status_code == 204

    # 8. Verify Deleted
    resp_get_del = await async_client.get(f"/api/v1/sif/webhooks/{sub_id}")
    assert resp_get_del.status_code == 404


@pytest.mark.asyncio
async def test_alerts_dispatch_and_logs(async_client: AsyncClient, db_session: AsyncSession):
    """Verify test alert dispatch and retrieving alert logs."""
    dispatch_payload = {
        "event_type": "HIGH_CONCENTRATION_TRIGGERED",
        "severity": "CRITICAL",
        "title": "Severe Gas Leak Precursor Concentration Triggered",
        "summary": "Multiple high-pressure gas barrier failures observed at Duliajan Hub.",
        "recipients": ["hse-director@oilindia.in"],
        "metadata": {"concentration_id": str(uuid.uuid4()), "affected_count": 7},
    }
    resp_dispatch = await async_client.post("/api/v1/sif/alerts/dispatch-test", json=dispatch_payload)
    assert resp_dispatch.status_code == 200
    data = resp_dispatch.json()
    assert data["status"] == "DELIVERED"
    assert data["email_deliveries_count"] >= 1

    # Query alert logs
    resp_logs = await async_client.get("/api/v1/sif/alerts/logs")
    assert resp_logs.status_code == 200
    logs_data = resp_logs.json()
    assert logs_data["total"] >= 1
    assert any(log["severity"] == "CRITICAL" for log in logs_data["items"])
