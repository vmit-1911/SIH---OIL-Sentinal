"""Pydantic schemas for Webhook Subscriptions, Delivery Logs, and HSE Alerts (Phase 15)."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    AlertChannel,
    AlertDispatchStatus,
    AlertSeverity,
    WebhookEventType,
)


class WebhookSubscriptionCreate(BaseModel):
    """Payload to register a new external webhook subscription."""
    name: str = Field(..., min_length=2, max_length=120, description="Subscriber name")
    target_url: str = Field(..., min_length=8, max_length=500, description="HTTP/HTTPS destination URL")
    secret_token: Optional[str] = Field(None, max_length=255, description="Optional shared secret for HMAC signature")
    subscribed_events: List[WebhookEventType] = Field(
        default_factory=lambda: [WebhookEventType.SIF_DETECTED, WebhookEventType.HIGH_CONCENTRATION_TRIGGERED],
        description="Events that trigger this webhook",
    )
    is_active: bool = Field(True, description="Whether webhook is active")
    description: Optional[str] = Field(None, max_length=255, description="Subscriber description")


class WebhookSubscriptionUpdate(BaseModel):
    """Payload to modify an existing webhook subscription."""
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    target_url: Optional[str] = Field(None, min_length=8, max_length=500)
    secret_token: Optional[str] = Field(None, max_length=255)
    subscribed_events: Optional[List[WebhookEventType]] = None
    is_active: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=255)


class WebhookSubscriptionDTO(BaseModel):
    """Representation of a registered webhook subscription."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    target_url: str
    secret_token: Optional[str] = None
    subscribed_events: List[WebhookEventType]
    is_active: bool
    description: Optional[str] = None
    failure_count: int = 0
    last_delivery_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class WebhookSubscriptionListResponse(BaseModel):
    """Paginated or listed webhook subscriptions."""
    items: List[WebhookSubscriptionDTO]
    total: int


class WebhookDeliveryLogDTO(BaseModel):
    """Log record of a webhook delivery attempt."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subscription_id: uuid.UUID
    event_type: WebhookEventType
    event_id: str
    payload: Dict[str, Any]
    status_code: Optional[int] = None
    response_preview: Optional[str] = None
    success: bool
    duration_ms: float
    attempt: int
    error_message: Optional[str] = None
    dispatched_at: datetime


class WebhookDeliveryLogListResponse(BaseModel):
    """List of webhook delivery log records."""
    items: List[WebhookDeliveryLogDTO]
    total: int


class AlertDispatchLogDTO(BaseModel):
    """Log record of an HSE alert dispatched across channels."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    channel: AlertChannel
    event_type: str
    severity: AlertSeverity
    recipient: str
    subject: str
    body_preview: str
    status: AlertDispatchStatus
    error_details: Optional[str] = None
    payload_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


class AlertDispatchLogListResponse(BaseModel):
    """List of alert notification log records."""
    items: List[AlertDispatchLogDTO]
    total: int


class AlertTestDispatchRequest(BaseModel):
    """Request payload to test dispatching alerts."""
    event_type: WebhookEventType = Field(WebhookEventType.TEST_PING, description="Event type to simulate")
    severity: AlertSeverity = Field(AlertSeverity.MEDIUM, description="Simulated severity")
    title: str = Field("Test HSE Safety Alert", min_length=3, max_length=255)
    summary: str = Field("This is a simulated safety notification from OIL SIF Sentinel.", min_length=5)
    recipients: Optional[List[str]] = Field(None, description="Optional recipient overrides")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Contextual payload metadata")


class AlertTestDispatchResponse(BaseModel):
    """Response returned upon test alert dispatch."""
    dispatched_channels: List[AlertChannel]
    webhook_deliveries_count: int
    email_deliveries_count: int
    status: str
    message: str
