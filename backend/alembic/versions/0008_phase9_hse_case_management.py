"""0008_phase9_hse_case_management

Revision ID: 0008_phase9_hse_case_management
Revises: 0007_phase8_hse_action_recommendations
Create Date: 2026-09-24 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0008_phase9_hse_case_management"
down_revision: Union[str, None] = "0007_phase8_hse_action_recommendations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create new Enums if using postgresql dialect
    case_type_enum = postgresql.ENUM(
        "SIF_INVESTIGATION", "PATTERN_INVESTIGATION", "LOCATION_REVIEW",
        "ACTIVITY_REVIEW", "BARRIER_REVIEW", "HSE_FOLLOW_UP",
        name="case_type_enum", create_type=False
    )
    case_type_enum.create(op.get_bind(), checkfirst=True)

    case_status_enum = postgresql.ENUM(
        "OPEN", "TRIAGE", "INVESTIGATING", "ACTION_REQUIRED",
        "PENDING_VERIFICATION", "CLOSED", "CANCELLED",
        name="case_status_enum", create_type=False
    )
    case_status_enum.create(op.get_bind(), checkfirst=True)

    case_priority_enum = postgresql.ENUM(
        "CRITICAL_REVIEW", "HIGH", "MEDIUM", "INFORMATIONAL",
        name="case_priority_enum", create_type=False
    )
    case_priority_enum.create(op.get_bind(), checkfirst=True)

    case_event_type_enum = postgresql.ENUM(
        "CASE_CREATED", "CASE_ASSIGNED", "CASE_STATUS_CHANGED",
        "SOURCE_ATTACHED", "SOURCE_DETACHED", "ACTION_ATTACHED",
        "ACTION_DETACHED", "ACTION_STATUS_CHANGED", "REVIEW_ATTACHED",
        "CASE_REOPENED", "CASE_CLOSED", "CASE_CANCELLED",
        name="case_event_type_enum", create_type=False
    )
    case_event_type_enum.create(op.get_bind(), checkfirst=True)

    case_source_type_enum = postgresql.ENUM(
        "REPORT", "ASSESSMENT", "PATTERN", "CONCENTRATION", "REVIEW", "ACTION",
        name="case_source_type_enum", create_type=False
    )
    case_source_type_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create hse_cases table
    op.create_table(
        "hse_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("case_key", sa.String(100), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("case_type", sa.Enum("SIF_INVESTIGATION", "PATTERN_INVESTIGATION", "LOCATION_REVIEW", "ACTIVITY_REVIEW", "BARRIER_REVIEW", "HSE_FOLLOW_UP", name="case_type_enum"), nullable=False),
        sa.Column("status", sa.Enum("OPEN", "TRIAGE", "INVESTIGATING", "ACTION_REQUIRED", "PENDING_VERIFICATION", "CLOSED", "CANCELLED", name="case_status_enum"), nullable=False, server_default="OPEN"),
        sa.Column("priority", sa.Enum("CRITICAL_REVIEW", "HIGH", "MEDIUM", "INFORMATIONAL", name="case_priority_enum"), nullable=False, server_default="MEDIUM"),
        sa.Column("owner", sa.String(100), nullable=True),
        sa.Column("created_by", sa.String(100), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closure_rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_hse_cases_case_key", "hse_cases", ["case_key"], unique=True)
    op.create_index("idx_hse_cases_status_priority", "hse_cases", ["status", "priority"])
    op.create_index("idx_hse_cases_owner_status", "hse_cases", ["owner", "status"])
    op.create_index("idx_hse_cases_type_status", "hse_cases", ["case_type", "status"])

    # 3. Create hse_case_source_associations table
    op.create_table(
        "hse_case_source_associations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hse_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.Enum("REPORT", "ASSESSMENT", "PATTERN", "CONCENTRATION", "REVIEW", "ACTION", name="case_source_type_enum"), nullable=False),
        sa.Column("source_id", sa.String(120), nullable=False),
        sa.Column("source_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("attached_by", sa.String(100), nullable=False),
        sa.Column("attached_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("case_id", "source_type", "source_id", name="uq_hse_case_source"),
    )
    op.create_index("idx_hse_case_sources_lookup", "hse_case_source_associations", ["source_type", "source_id"])
    op.create_index("idx_hse_case_sources_case_id", "hse_case_source_associations", ["case_id"])

    # 4. Create hse_case_events table
    op.create_table(
        "hse_case_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hse_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.Enum("CASE_CREATED", "CASE_ASSIGNED", "CASE_STATUS_CHANGED", "SOURCE_ATTACHED", "SOURCE_DETACHED", "ACTION_ATTACHED", "ACTION_DETACHED", "ACTION_STATUS_CHANGED", "REVIEW_ATTACHED", "CASE_REOPENED", "CASE_CLOSED", "CASE_CANCELLED", name="case_event_type_enum"), nullable=False),
        sa.Column("actor_id", sa.String(100), nullable=False),
        sa.Column("before_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_reference", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_hse_case_events_case_created", "hse_case_events", ["case_id", "created_at"])


def downgrade() -> None:
    op.drop_table("hse_case_events")
    op.drop_table("hse_case_source_associations")
    op.drop_table("hse_cases")

    op.execute("DROP TYPE IF EXISTS case_source_type_enum")
    op.execute("DROP TYPE IF EXISTS case_event_type_enum")
    op.execute("DROP TYPE IF EXISTS case_priority_enum")
    op.execute("DROP TYPE IF EXISTS case_status_enum")
    op.execute("DROP TYPE IF EXISTS case_type_enum")
