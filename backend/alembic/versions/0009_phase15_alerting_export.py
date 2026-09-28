"""0009_phase15_alerting_export

Revision ID: 0009_phase15_alerting_export
Revises: 0008_phase9_hse_case_management
Create Date: 2026-09-25 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0009_phase15_alerting_export"
down_revision: Union[str, None] = "0008_phase9_hse_case_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create PostgreSQL Enums if supported
    webhook_event_type_enum = postgresql.ENUM(
        "SIF_DETECTED", "HIGH_CONCENTRATION_TRIGGERED", "ACTION_CRITICAL_ASSIGNED",
        "CASE_STATUS_CHANGED", "EXPORT_GENERATED", "REVIEW_OVERRIDDEN", "TEST_PING",
        name="webhook_event_type_enum", create_type=False
    )
    webhook_event_type_enum.create(op.get_bind(), checkfirst=True)

    alert_channel_enum = postgresql.ENUM(
        "WEBHOOK", "EMAIL", "IN_APP",
        name="alert_channel_enum", create_type=False
    )
    alert_channel_enum.create(op.get_bind(), checkfirst=True)

    alert_severity_enum = postgresql.ENUM(
        "LOW", "MEDIUM", "HIGH", "CRITICAL",
        name="alert_severity_enum", create_type=False
    )
    alert_severity_enum.create(op.get_bind(), checkfirst=True)

    alert_dispatch_status_enum = postgresql.ENUM(
        "PENDING", "DELIVERED", "FAILED", "SKIPPED",
        name="alert_dispatch_status_enum", create_type=False
    )
    alert_dispatch_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create webhook_subscriptions table
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("target_url", sa.String(500), nullable=False),
        sa.Column("secret_token", sa.String(255), nullable=True),
        sa.Column("subscribed_events", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_delivery_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_webhook_subscriptions_is_active", "webhook_subscriptions", ["is_active"])

    # 3. Create webhook_delivery_logs table
    op.create_table(
        "webhook_delivery_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_id", sa.String(120), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("response_preview", sa.String(500), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_webhook_delivery_logs_subscription_id", "webhook_delivery_logs", ["subscription_id"])
    op.create_index("ix_webhook_delivery_logs_event_type", "webhook_delivery_logs", ["event_type"])
    op.create_index("ix_webhook_delivery_logs_event_id", "webhook_delivery_logs", ["event_id"])
    op.create_index("ix_webhook_delivery_logs_success", "webhook_delivery_logs", ["success"])
    op.create_index("ix_webhook_delivery_logs_dispatched_at", "webhook_delivery_logs", ["dispatched_at"])
    op.create_index("ix_webhook_delivery_sub_time", "webhook_delivery_logs", ["subscription_id", "dispatched_at"])

    # 4. Create alert_dispatch_logs table
    op.create_table(
        "alert_dispatch_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("body_preview", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("payload_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_alert_dispatch_logs_channel", "alert_dispatch_logs", ["channel"])
    op.create_index("ix_alert_dispatch_logs_event_type", "alert_dispatch_logs", ["event_type"])
    op.create_index("ix_alert_dispatch_logs_severity", "alert_dispatch_logs", ["severity"])
    op.create_index("ix_alert_dispatch_logs_recipient", "alert_dispatch_logs", ["recipient"])
    op.create_index("ix_alert_dispatch_logs_status", "alert_dispatch_logs", ["status"])
    op.create_index("ix_alert_dispatch_logs_created_at", "alert_dispatch_logs", ["created_at"])
    op.create_index("ix_alert_dispatch_channel_time", "alert_dispatch_logs", ["channel", "created_at"])


def downgrade() -> None:
    op.drop_table("alert_dispatch_logs")
    op.drop_table("webhook_delivery_logs")
    op.drop_table("webhook_subscriptions")

    bind = op.get_bind()
    for enum_name in [
        "alert_dispatch_status_enum",
        "alert_severity_enum",
        "alert_channel_enum",
        "webhook_event_type_enum",
    ]:
        sa.Enum(name=enum_name).drop(bind, checkfirst=True)
