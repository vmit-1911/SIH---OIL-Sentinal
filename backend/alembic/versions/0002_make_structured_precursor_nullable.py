"""0002_make_structured_precursor_nullable

Revision ID: 0002_make_structured_precursor_nullable
Revises: 0001_initial_schema
Create Date: 2026-09-23 13:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_make_structured_precursor_nullable"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make structured_precursor column nullable so Phase 1C can store NULL
    op.alter_column(
        "sif_assessments",
        "structured_precursor",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
    )


def downgrade() -> None:
    # Revert structured_precursor column to non-nullable
    op.alter_column(
        "sif_assessments",
        "structured_precursor",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
    )
