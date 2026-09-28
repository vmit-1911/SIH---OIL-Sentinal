"""0007_phase8_hse_action_recommendations

Revision ID: 0007_phase8_hse_action_recommendations
Revises: 0006_phase5_human_in_the_loop_review_tables
Create Date: 2026-09-24 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0007_phase8_hse_action_recommendations"
down_revision: Union[str, None] = "0006_phase5_human_in_the_loop_review_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create new Enums if using postgresql dialect
    action_category_enum = postgresql.ENUM(
        "IMMEDIATE_REVIEW", "BARRIER_VERIFICATION", "PROCEDURE_REVIEW",
        "WORK_AUTHORIZATION_REVIEW", "ENERGY_ISOLATION_VERIFICATION",
        "FALL_PROTECTION_VERIFICATION", "LIFTING_CONTROL_VERIFICATION",
        "LINE_OF_FIRE_CONTROL_REVIEW", "CONFINED_SPACE_CONTROL_REVIEW",
        "HOT_WORK_CONTROL_REVIEW", "DRIVING_CONTROL_REVIEW",
        "TREND_INVESTIGATION", "PATTERN_INVESTIGATION",
        "SITE_FOCUSED_REVIEW", "MANAGEMENT_ATTENTION",
        name="action_category_enum", create_type=False
    )
    action_category_enum.create(op.get_bind(), checkfirst=True)

    action_priority_enum = postgresql.ENUM(
        "CRITICAL_REVIEW", "HIGH", "MEDIUM", "INFORMATIONAL",
        name="action_priority_enum", create_type=False
    )
    action_priority_enum.create(op.get_bind(), checkfirst=True)

    action_status_enum = postgresql.ENUM(
        "OPEN", "ACKNOWLEDGED", "IN_PROGRESS", "COMPLETED", "DISMISSED",
        name="action_status_enum", create_type=False
    )
    action_status_enum.create(op.get_bind(), checkfirst=True)

    action_source_type_enum = postgresql.ENUM(
        "ASSESSMENT", "PATTERN", "CONCENTRATION", "REVIEW",
        name="action_source_type_enum", create_type=False
    )
    action_source_type_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create hse_action_recommendations table
    op.create_table(
        "hse_action_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("action_key", sa.String(255), nullable=False),
        sa.Column("source_type", sa.Enum("ASSESSMENT", "PATTERN", "CONCENTRATION", "REVIEW", name="action_source_type_enum"), nullable=False),
        sa.Column("source_id", sa.String(120), nullable=False),
        sa.Column("action_category", sa.Enum(
            "IMMEDIATE_REVIEW", "BARRIER_VERIFICATION", "PROCEDURE_REVIEW",
            "WORK_AUTHORIZATION_REVIEW", "ENERGY_ISOLATION_VERIFICATION",
            "FALL_PROTECTION_VERIFICATION", "LIFTING_CONTROL_VERIFICATION",
            "LINE_OF_FIRE_CONTROL_REVIEW", "CONFINED_SPACE_CONTROL_REVIEW",
            "HOT_WORK_CONTROL_REVIEW", "DRIVING_CONTROL_REVIEW",
            "TREND_INVESTIGATION", "PATTERN_INVESTIGATION",
            "SITE_FOCUSED_REVIEW", "MANAGEMENT_ATTENTION",
            name="action_category_enum"
        ), nullable=False),
        sa.Column("action_title", sa.String(255), nullable=False),
        sa.Column("action_description", sa.Text(), nullable=False),
        sa.Column("priority", sa.Enum("CRITICAL_REVIEW", "HIGH", "MEDIUM", "INFORMATIONAL", name="action_priority_enum"), nullable=False, server_default="MEDIUM"),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("evidence_refs", postgresql.JSONB(), nullable=True),
        sa.Column("source_dimensions", postgresql.JSONB(), nullable=True),
        sa.Column("lsr_code", sa.String(100), nullable=True),
        sa.Column("precursor_signature", sa.String(255), nullable=True),
        sa.Column("pattern_key", sa.String(120), nullable=True),
        sa.Column("concentration_key", sa.String(120), nullable=True),
        sa.Column("rule_id", sa.String(100), nullable=False),
        sa.Column("rule_version", sa.String(50), nullable=False, server_default="1.0.0"),
        sa.Column("status", sa.Enum("OPEN", "ACKNOWLEDGED", "IN_PROGRESS", "COMPLETED", "DISMISSED", name="action_status_enum"), nullable=False, server_default="OPEN"),
        sa.Column("assigned_to", sa.String(100), nullable=True),
        sa.Column("actor_id", sa.String(100), nullable=True),
        sa.Column("status_rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 3. Indexes
    op.create_index("ix_hse_action_recommendations_action_key", "hse_action_recommendations", ["action_key"], unique=True)
    op.create_index("ix_hse_action_recommendations_source_type", "hse_action_recommendations", ["source_type"])
    op.create_index("ix_hse_action_recommendations_source_id", "hse_action_recommendations", ["source_id"])
    op.create_index("ix_hse_action_recommendations_action_category", "hse_action_recommendations", ["action_category"])
    op.create_index("ix_hse_action_recommendations_priority", "hse_action_recommendations", ["priority"])
    op.create_index("ix_hse_action_recommendations_status", "hse_action_recommendations", ["status"])
    op.create_index("ix_hse_action_recommendations_rule_id", "hse_action_recommendations", ["rule_id"])
    op.create_index("idx_hse_actions_source", "hse_action_recommendations", ["source_type", "source_id"])
    op.create_index("idx_hse_actions_status_priority", "hse_action_recommendations", ["status", "priority"])


def downgrade() -> None:
    op.drop_table("hse_action_recommendations")
    bind = op.get_bind()
    sa.Enum(name="action_source_type_enum").drop(bind, checkfirst=True)
    sa.Enum(name="action_status_enum").drop(bind, checkfirst=True)
    sa.Enum(name="action_priority_enum").drop(bind, checkfirst=True)
    sa.Enum(name="action_category_enum").drop(bind, checkfirst=True)
