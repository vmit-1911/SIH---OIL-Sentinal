"""SQLAlchemy models for Webhooks, Delivery Logs, and Alert Notifications (Phase 15)."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import (
    AlertChannel,
    AlertDispatchStatus,
    AlertSeverity,
    WebhookEventType,
)


class WebhookSubscription(Base):
    """Represents an external webhook endpoint configured to receive SIF Sentinel event streams."""

    __tablename__ = "webhook_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        doc="Human-readable name for the webhook subscriber (e.g., 'Enterprise SIEM Webhook')",
    )
    target_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="HTTP or HTTPS target destination URL",
    )
    secret_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Shared secret token used to generate HMAC-SHA256 request signatures",
    )
    subscribed_events: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        doc="List of WebhookEventType values subscribed to (e.g., ['SIF_DETECTED', 'HIGH_CONCENTRATION_TRIGGERED'])",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Whether this webhook endpoint is active and should receive events",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Optional description of the subscriber system or owner",
    )
    failure_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Consecutive delivery failure count",
    )
    last_delivery_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of the most recent delivery attempt",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    deliveries: Mapped[List["WebhookDeliveryLog"]] = relationship(
        "WebhookDeliveryLog",
        back_populates="subscription",
        cascade="all, delete-orphan",
        order_by="desc(WebhookDeliveryLog.dispatched_at)",
    )


class WebhookDeliveryLog(Base):
    """Audit log of an individual webhook HTTP dispatch attempt and result."""

    __tablename__ = "webhook_delivery_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[WebhookEventType] = mapped_column(
        Enum(WebhookEventType, name="webhook_event_type_enum", native_enum=False),
        nullable=False,
        index=True,
    )
    event_id: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
        doc="Unique identifier for the triggering domain event",
    )
    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        doc="Full JSON payload dispatched to the webhook target",
    )
    status_code: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="HTTP status code received from target server (e.g. 200, 500)",
    )
    response_preview: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="First 500 characters of remote response body",
    )
    success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        index=True,
        doc="Whether delivery succeeded (status 2xx)",
    )
    duration_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        doc="Roundtrip HTTP latency in milliseconds",
    )
    attempt: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        doc="Attempt number (1 for initial, 2+ for retries)",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Exception message or network failure description",
    )
    dispatched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    subscription: Mapped["WebhookSubscription"] = relationship(
        "WebhookSubscription",
        back_populates="deliveries",
    )


class AlertDispatchLog(Base):
    """Audit log of high-priority HSE safety notifications dispatched across channels."""

    __tablename__ = "alert_dispatch_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    channel: Mapped[AlertChannel] = mapped_column(
        Enum(AlertChannel, name="alert_channel_enum", native_enum=False),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, name="alert_severity_enum", native_enum=False),
        nullable=False,
        index=True,
    )
    recipient: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Email address, webhook URL, or internal user identifier",
    )
    subject: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Subject line or brief title of the alert",
    )
    body_preview: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Text summary or preview of the alert contents",
    )
    status: Mapped[AlertDispatchStatus] = mapped_column(
        Enum(AlertDispatchStatus, name="alert_dispatch_status_enum", native_enum=False),
        nullable=False,
        default=AlertDispatchStatus.PENDING,
        index=True,
    )
    error_details: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    payload_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Supporting metadata or contextual parameters",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )


Index("ix_webhook_delivery_sub_time", WebhookDeliveryLog.subscription_id, WebhookDeliveryLog.dispatched_at)
Index("ix_alert_dispatch_channel_time", AlertDispatchLog.channel, AlertDispatchLog.created_at)
