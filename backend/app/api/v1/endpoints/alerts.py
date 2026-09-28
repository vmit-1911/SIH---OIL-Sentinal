"""REST API Endpoints for Webhooks, Delivery Logs, and HSE Alerts (Phase 15)."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.domain.enums import AlertChannel, WebhookEventType
from app.schemas.alert import (
    AlertDispatchLogDTO,
    AlertDispatchLogListResponse,
    AlertTestDispatchRequest,
    AlertTestDispatchResponse,
    WebhookDeliveryLogDTO,
    WebhookDeliveryLogListResponse,
    WebhookSubscriptionCreate,
    WebhookSubscriptionDTO,
    WebhookSubscriptionListResponse,
    WebhookSubscriptionUpdate,
)
from app.services.alert_dispatcher_service import AlertDispatcherService

router = APIRouter(prefix="/sif", tags=["Alerts & Webhooks"])


# -----------------------------------------------------------------------------
# 1. ALERT DISPATCH & LOGS
# -----------------------------------------------------------------------------
@router.post(
    "/alerts/dispatch-test",
    response_model=AlertTestDispatchResponse,
    summary="Dispatch Test Alert",
    description="Simulates a multi-channel safety notification dispatch to configured webhooks and email recipients.",
)
async def dispatch_test_alert(
    payload: AlertTestDispatchRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Test dispatching safety alert notification."""
    dispatcher = AlertDispatcherService(session)
    result = await dispatcher.dispatch_event(
        event_type=payload.event_type,
        severity=payload.severity,
        title=payload.title,
        summary=payload.summary,
        payload_data=payload.metadata or {},
        recipients=payload.recipients,
    )
    return AlertTestDispatchResponse(
        dispatched_channels=[AlertChannel.WEBHOOK, AlertChannel.EMAIL],
        webhook_deliveries_count=result["webhook_deliveries"],
        email_deliveries_count=result["email_deliveries"],
        status="DELIVERED",
        message=f"Dispatched test alert {result['event_id']} across channels",
    )


@router.get(
    "/alerts/logs",
    response_model=AlertDispatchLogListResponse,
    summary="List Alert Dispatch Logs",
    description="Retrieves audit history of safety notifications dispatched by the system.",
)
async def list_alert_logs(
    channel: Optional[AlertChannel] = Query(None, description="Filter by delivery channel"),
    limit: int = Query(50, ge=1, le=200, description="Max logs to return"),
    session: AsyncSession = Depends(get_db_session),
):
    """List recent alert dispatch logs."""
    dispatcher = AlertDispatcherService(session)
    logs, total = await dispatcher.list_alert_logs(channel=channel, limit=limit)
    return AlertDispatchLogListResponse(
        items=[AlertDispatchLogDTO.model_validate(l) for l in logs],
        total=total,
    )


# -----------------------------------------------------------------------------
# 2. WEBHOOK SUBSCRIPTION MANAGEMENT
# -----------------------------------------------------------------------------
@router.post(
    "/webhooks/subscribe",
    response_model=WebhookSubscriptionDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Register Webhook Subscription",
    description="Subscribes an external destination URL to receive real-time SIF Sentinel events with HMAC signatures.",
)
async def subscribe_webhook(
    payload: WebhookSubscriptionCreate,
    session: AsyncSession = Depends(get_db_session),
):
    """Register new webhook subscription."""
    dispatcher = AlertDispatcherService(session)
    sub = await dispatcher.create_subscription(payload)
    return WebhookSubscriptionDTO.model_validate(sub)


@router.get(
    "/webhooks",
    response_model=WebhookSubscriptionListResponse,
    summary="List Webhook Subscriptions",
    description="Lists all registered external webhook subscriptions.",
)
async def list_webhooks(
    active_only: bool = Query(False, description="Filter to active subscriptions only"),
    session: AsyncSession = Depends(get_db_session),
):
    """List webhook subscriptions."""
    dispatcher = AlertDispatcherService(session)
    subs, total = await dispatcher.list_subscriptions(active_only=active_only)
    return WebhookSubscriptionListResponse(
        items=[WebhookSubscriptionDTO.model_validate(s) for s in subs],
        total=total,
    )


@router.get(
    "/webhooks/logs",
    response_model=WebhookDeliveryLogListResponse,
    summary="List Webhook Delivery Logs",
    description="Queries recent webhook delivery attempts, HTTP response codes, latencies, and error messages.",
)
async def list_webhook_logs(
    subscription_id: Optional[uuid.UUID] = Query(None, description="Filter by subscription ID"),
    limit: int = Query(50, ge=1, le=200, description="Max logs to return"),
    session: AsyncSession = Depends(get_db_session),
):
    """List webhook delivery logs."""
    dispatcher = AlertDispatcherService(session)
    logs, total = await dispatcher.list_webhook_logs(subscription_id=subscription_id, limit=limit)
    return WebhookDeliveryLogListResponse(
        items=[WebhookDeliveryLogDTO.model_validate(l) for l in logs],
        total=total,
    )


@router.get(
    "/webhooks/{subscription_id}",
    response_model=WebhookSubscriptionDTO,
    summary="Get Webhook Subscription",
    description="Fetches details for a specific webhook subscription.",
)
async def get_webhook_subscription(
    subscription_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """Get single webhook subscription."""
    dispatcher = AlertDispatcherService(session)
    sub = await dispatcher.get_subscription(subscription_id)
    return WebhookSubscriptionDTO.model_validate(sub)


@router.patch(
    "/webhooks/{subscription_id}",
    response_model=WebhookSubscriptionDTO,
    summary="Update Webhook Subscription",
    description="Updates settings or active status for a webhook subscription.",
)
async def update_webhook_subscription(
    subscription_id: uuid.UUID,
    payload: WebhookSubscriptionUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    """Update webhook subscription."""
    dispatcher = AlertDispatcherService(session)
    sub = await dispatcher.update_subscription(subscription_id, payload)
    return WebhookSubscriptionDTO.model_validate(sub)


@router.delete(
    "/webhooks/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Webhook Subscription",
    description="Deletes a webhook subscription and its delivery logs.",
)
async def delete_webhook_subscription(
    subscription_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """Delete webhook subscription."""
    dispatcher = AlertDispatcherService(session)
    await dispatcher.delete_subscription(subscription_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/webhooks/{subscription_id}/test",
    response_model=WebhookDeliveryLogDTO,
    summary="Test Webhook Endpoint",
    description="Dispatches a test ping event to the specified webhook endpoint and records response code/latency.",
)
async def test_webhook_endpoint(
    subscription_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """Trigger test delivery to a webhook."""
    dispatcher = AlertDispatcherService(session)
    delivery = await dispatcher.test_webhook_subscription(subscription_id)
    return WebhookDeliveryLogDTO.model_validate(delivery)
