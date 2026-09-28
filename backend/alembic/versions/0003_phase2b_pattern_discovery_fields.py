"""0003_phase2b_pattern_discovery_fields

Revision ID: 0003_phase2b_pattern_discovery_fields
Revises: 0002_make_structured_precursor_nullable
Create Date: 2026-09-23 18:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003_phase2b_pattern_discovery_fields"
down_revision: Union[str, None] = "0002_make_structured_precursor_nullable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create pattern_status_enum if using postgres dialect
    pattern_status_enum = postgresql.ENUM("CANDIDATE", "ACTIVE", "ARCHIVED", name="pattern_status_enum", create_type=False)
    pattern_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Add columns to precursor_patterns table
    op.add_column("precursor_patterns", sa.Column("status", sa.Enum("CANDIDATE", "ACTIVE", "ARCHIVED", name="pattern_status_enum"), nullable=False, server_default="CANDIDATE"))
    op.add_column("precursor_patterns", sa.Column("discovery_method", sa.String(100), nullable=False, server_default="HYBRID_SIMILARITY_GROUPING_V1"))
    op.add_column("precursor_patterns", sa.Column("representative_precursor", postgresql.JSONB(), nullable=True))
    op.add_column("precursor_patterns", sa.Column("similarity_summary", postgresql.JSONB(), nullable=True))
    op.add_column("precursor_patterns", sa.Column("evidence_summary", postgresql.JSONB(), nullable=True))
    op.add_column("precursor_patterns", sa.Column("supporting_report_ids", postgresql.JSONB(), nullable=False, server_default="[]"))
    op.add_column("precursor_patterns", sa.Column("supporting_lsr_codes", postgresql.JSONB(), nullable=False, server_default="[]"))

    # 3. Create index for status
    op.create_index("ix_precursor_patterns_status", "precursor_patterns", ["status"])


def downgrade() -> None:
    op.drop_index("ix_precursor_patterns_status", table_name="precursor_patterns")
    op.drop_column("precursor_patterns", "supporting_lsr_codes")
    op.drop_column("precursor_patterns", "supporting_report_ids")
    op.drop_column("precursor_patterns", "evidence_summary")
    op.drop_column("precursor_patterns", "similarity_summary")
    op.drop_column("precursor_patterns", "representative_precursor")
    op.drop_column("precursor_patterns", "discovery_method")
    op.drop_column("precursor_patterns", "status")
    op.execute("DROP TYPE IF EXISTS pattern_status_enum;")
