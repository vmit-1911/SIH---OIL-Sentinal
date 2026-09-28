"""0005_phase4_batch_pipeline_tables

Revision ID: 0005_phase4_batch_pipeline_tables
Revises: 0004_phase3_risk_concentration_tables
Create Date: 2026-09-23 21:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005_phase4_batch_pipeline_tables"
down_revision: Union[str, None] = "0004_phase3_risk_concentration_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update batch_jobs table with operational counters and metadata
    op.add_column("batch_jobs", sa.Column("source_filename", sa.String(255), nullable=False, server_default=""))
    op.add_column("batch_jobs", sa.Column("import_schema_version", sa.String(50), nullable=False, server_default="OIL_SAFETY_REPORT_CSV_V1"))
    op.add_column("batch_jobs", sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("batch_jobs", sa.Column("accepted_rows", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("batch_jobs", sa.Column("rejected_rows", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("batch_jobs", sa.Column("duplicate_rows", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("batch_jobs", sa.Column("processed_rows", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("batch_jobs", sa.Column("failed_processing_rows", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("batch_jobs", sa.Column("error_summary", postgresql.JSONB(), nullable=True))
    op.add_column("batch_jobs", sa.Column("job_metadata", postgresql.JSONB(), nullable=True))

    # 2. Create batch_row_errors table
    op.create_table(
        "batch_row_errors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("batch_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(100), nullable=True),
        sa.Column("error_code", sa.String(50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_batch_row_errors_batch_id", "batch_row_errors", ["batch_id"])
    op.create_index("ix_batch_row_errors_error_code", "batch_row_errors", ["error_code"])
    op.create_index("ix_batch_row_errors_batch_row", "batch_row_errors", ["batch_id", "row_number"])

    # 3. Add batch traceability columns to safety_reports
    op.add_column("safety_reports", sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("batch_jobs.id", ondelete="SET NULL"), nullable=True))
    op.add_column("safety_reports", sa.Column("batch_row_number", sa.Integer(), nullable=True))
    op.create_index("ix_safety_reports_batch_id", "safety_reports", ["batch_id"])
    op.create_index("ix_safety_reports_batch_row", "safety_reports", ["batch_id", "batch_row_number"])


def downgrade() -> None:
    op.drop_index("ix_safety_reports_batch_row", table_name="safety_reports")
    op.drop_index("ix_safety_reports_batch_id", table_name="safety_reports")
    op.drop_column("safety_reports", "batch_row_number")
    op.drop_column("safety_reports", "batch_id")

    op.drop_index("ix_batch_row_errors_batch_row", table_name="batch_row_errors")
    op.drop_index("ix_batch_row_errors_error_code", table_name="batch_row_errors")
    op.drop_index("ix_batch_row_errors_batch_id", table_name="batch_row_errors")
    op.drop_table("batch_row_errors")

    op.drop_column("batch_jobs", "job_metadata")
    op.drop_column("batch_jobs", "error_summary")
    op.drop_column("batch_jobs", "failed_processing_rows")
    op.drop_column("batch_jobs", "processed_rows")
    op.drop_column("batch_jobs", "duplicate_rows")
    op.drop_column("batch_jobs", "rejected_rows")
    op.drop_column("batch_jobs", "accepted_rows")
    op.drop_column("batch_jobs", "total_rows")
    op.drop_column("batch_jobs", "import_schema_version")
    op.drop_column("batch_jobs", "source_filename")
