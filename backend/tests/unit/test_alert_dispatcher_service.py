"""Unit tests for AlertDispatcherService (Phase 15)."""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AlertSeverity, WebhookEventType
from app.schemas.alert import WebhookSubscriptionCreate, WebhookSubscriptionUpdate
from app.services.alert_dispatcher_service import (
    AlertDispatcherService,
    WebhookNotFoundException,
)


@pytest.mark.asyncio
async def test_webhook_subscription_lifecycle(db_session: AsyncSession):
    """Verify create, list, update, and delete for webhook subscriptions."""
    dispatcher = AlertDispatcherService(db_session)

    # 1. Create
    payload = WebhookSubscriptionCreate(
        name="Enterprise Safety Gateway",
        target_url="https://siem.oilindia.in/api/v1/sif-events",
        secret_token="custom_secret_key_123",
        subscribed_events=[WebhookEventType.SIF_DETECTED, WebhookEventType.HIGH_CONCENTRATION_TRIGGERED],
        description="Corporate SIEM real-time event pipeline",
    )
    sub = await dispatcher.create_subscription(payload)
    assert sub.id is not None
    assert sub.name == "Enterprise Safety Gateway"
    assert "SIF_DETECTED" in sub.subscribed_events

    # 2. Get
    fetched = await dispatcher.get_subscription(sub.id)
    assert fetched.id == sub.id
    assert fetched.target_url == "https://siem.oilindia.in/api/v1/sif-events"

    # 3. List
    subs, total = await dispatcher.list_subscriptions()
    assert total >= 1
    assert any(s.id == sub.id for s in subs)

    # 4. Update
    updated = await dispatcher.update_subscription(
        sub.id,
        WebhookSubscriptionUpdate(name="Updated Safety Gateway", is_active=False),
    )
    assert updated.name == "Updated Safety Gateway"
    assert updated.is_active is False

    # 5. Delete
    deleted = await dispatcher.delete_subscription(sub.id)
    assert deleted is True

    # 6. Verify 404
    with pytest.raises(WebhookNotFoundException):
        await dispatcher.get_subscription(sub.id)


@pytest.mark.asyncio
async def test_dispatch_event_and_logs(db_session: AsyncSession):
    """Verify event dispatch triggers webhook delivery and records audit logs."""
    dispatcher = AlertDispatcherService(db_session)

    # Create active subscription
    sub = await dispatcher.create_subscription(
        WebhookSubscriptionCreate(
            name="Test Listener",
            target_url="http://test-listener.local/webhook",
            subscribed_events=[WebhookEventType.SIF_DETECTED],
        )
    )

    # Dispatch event
    res = await dispatcher.dispatch_event(
        event_type=WebhookEventType.SIF_DETECTED,
        severity=AlertSeverity.HIGH,
        title="High Potential SIF Incident Detected",
        summary="High-pressure gas line barrier degradation identified at Rig 04.",
        payload_data={"report_id": str(uuid.uuid4()), "score": 0.95},
        recipients=["test-hse@oilindia.in"],
    )

    assert res["status"] == "COMPLETED"
    assert res["webhook_deliveries"] >= 1
    assert res["email_deliveries"] >= 1

    # Check webhook delivery logs
    logs, total = await dispatcher.list_webhook_logs(subscription_id=sub.id)
    assert total >= 1
    assert logs[0].success is True
    assert logs[0].event_type == WebhookEventType.SIF_DETECTED

    # Check alert dispatch logs
    alert_logs, a_total = await dispatcher.list_alert_logs()
    assert a_total >= 1
    assert alert_logs[0].severity == AlertSeverity.HIGH


@pytest.mark.asyncio
async def test_test_webhook_subscription(db_session: AsyncSession):
    """Verify test webhook ping functionality."""
    dispatcher = AlertDispatcherService(db_session)
    sub = await dispatcher.create_subscription(
        WebhookSubscriptionCreate(
            name="Ping Endpoint",
            target_url="http://ping-target.local/webhook",
            subscribed_events=[WebhookEventType.TEST_PING],
        )
    )

    delivery = await dispatcher.test_webhook_subscription(sub.id)
    assert delivery.success is True
    assert delivery.event_type == WebhookEventType.TEST_PING
    assert delivery.status_code == 200
