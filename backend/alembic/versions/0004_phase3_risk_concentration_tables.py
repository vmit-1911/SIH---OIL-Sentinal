"""0004_phase3_risk_concentration_tables

Revision ID: 0004_phase3_risk_concentration_tables
Revises: 0003_phase2b_pattern_discovery_fields
Create Date: 2026-09-23 19:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_phase3_risk_concentration_tables"
down_revision: Union[str, None] = "0003_phase2b_pattern_discovery_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Enums if using postgres dialect
    concentration_dim_enum = postgresql.ENUM(
        "PATTERN", "HAZARD", "BARRIER_FAILURE", "ACTIVITY", "LIFE_SAVING_RULE", "LOCATION",
        name="concentration_dimension_enum",
        create_type=False,
    )
    concentration_dim_enum.create(op.get_bind(), checkfirst=True)

    observed_trend_enum = postgresql.ENUM(
        "STABLE", "INCREASING", "DECREASING", "INSUFFICIENT_DATA",
        name="observed_trend_enum",
        create_type=False,
    )
    observed_trend_enum.create(op.get_bind(), checkfirst=True)

    concentration_status_enum = postgresql.ENUM(
        "ACTIVE", "ARCHIVED",
        name="concentration_status_enum",
        create_type=False,
    )
    concentration_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create risk_concentrations table
    op.create_table(
        "risk_concentrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("concentration_key", sa.String(120), nullable=False, unique=True),
        sa.Column("dimension_type", sa.Enum("PATTERN", "HAZARD", "BARRIER_FAILURE", "ACTIVITY", "LIFE_SAVING_RULE", "LOCATION", name="concentration_dimension_enum"), nullable=False),
        sa.Column("dimension_value", sa.String(255), nullable=False),
        sa.Column("pattern_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("precursor_patterns.id", ondelete="SET NULL"), nullable=True),
        sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("distinct_report_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("distinct_location_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_trend", sa.Enum("STABLE", "INCREASING", "DECREASING", "INSUFFICIENT_DATA", name="observed_trend_enum"), nullable=False, server_default="INSUFFICIENT_DATA"),
        sa.Column("temporal_distribution", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("supporting_report_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("supporting_pattern_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("supporting_locations", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("supporting_lsr_codes", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("evidence_summary", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("calculation_method", sa.String(100), nullable=False, server_default="EXPLAINABLE_OBSERVED_CONCENTRATION_V1"),
        sa.Column("status", sa.Enum("ACTIVE", "ARCHIVED", name="concentration_status_enum"), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 3. Create indexes
    op.create_index("ix_risk_concentrations_key", "risk_concentrations", ["concentration_key"])
    op.create_index("ix_risk_concentrations_dim_type", "risk_concentrations", ["dimension_type"])
    op.create_index("ix_risk_concentrations_dim_val", "risk_concentrations", ["dimension_value"])
    op.create_index("ix_risk_concentrations_dim_type_val", "risk_concentrations", ["dimension_type", "dimension_value"])
    op.create_index("ix_risk_concentrations_trend", "risk_concentrations", ["observed_trend"])
    op.create_index("ix_risk_concentrations_status", "risk_concentrations", ["status"])
    op.create_index("ix_risk_concentrations_pattern_id", "risk_concentrations", ["pattern_id"])


def downgrade() -> None:
    op.drop_index("ix_risk_concentrations_pattern_id", table_name="risk_concentrations")
    op.drop_index("ix_risk_concentrations_status", table_name="risk_concentrations")
    op.drop_index("ix_risk_concentrations_trend", table_name="risk_concentrations")
    op.drop_index("ix_risk_concentrations_dim_type_val", table_name="risk_concentrations")
    op.drop_index("ix_risk_concentrations_dim_val", table_name="risk_concentrations")
    op.drop_index("ix_risk_concentrations_dim_type", table_name="risk_concentrations")
    op.drop_index("ix_risk_concentrations_key", table_name="risk_concentrations")
    op.drop_table("risk_concentrations")
    op.execute("DROP TYPE IF EXISTS concentration_status_enum;")
    op.execute("DROP TYPE IF EXISTS observed_trend_enum;")
    op.execute("DROP TYPE IF EXISTS concentration_dimension_enum;")
