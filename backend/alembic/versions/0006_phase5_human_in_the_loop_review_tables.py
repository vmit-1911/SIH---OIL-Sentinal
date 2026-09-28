"""0006_phase5_human_in_the_loop_review_tables

Revision ID: 0006_phase5_human_in_the_loop_review_tables
Revises: 0005_phase4_batch_pipeline_tables
Create Date: 2026-09-24 09:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006_phase5_human_in_the_loop_review_tables"
down_revision: Union[str, None] = "0005_phase4_batch_pipeline_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create new Enums if using postgres dialect
    review_state_enum = postgresql.ENUM("PENDING", "IN_REVIEW", "REVIEWED", name="review_state_enum", create_type=False)
    review_state_enum.create(op.get_bind(), checkfirst=True)

    review_decision_enum = postgresql.ENUM("CONFIRM_AI", "CORRECT", "REJECT_AI", "MARK_UNDETERMINED", name="review_decision_enum", create_type=False)
    review_decision_enum.create(op.get_bind(), checkfirst=True)

    review_audit_event_type_enum = postgresql.ENUM(
        "REVIEW_CREATED", "REVIEW_CLAIMED", "REVIEW_SUBMITTED",
        "CLASSIFICATION_CORRECTED", "PRECURSOR_CORRECTED", "LSR_CORRECTED",
        "REVIEW_REOPENED", "AUDITOR_OVERRIDE",
        name="review_audit_event_type_enum", create_type=False
    )
    review_audit_event_type_enum.create(op.get_bind(), checkfirst=True)

    review_feedback_category_enum = postgresql.ENUM(
        "CLASSIFICATION_ERROR", "EXTRACTION_ERROR", "LSR_MAPPING_ERROR",
        "PRECURSOR_ERROR", "MISSING_EVIDENCE", "INCORRECT_EVIDENCE", "OTHER",
        name="review_feedback_category_enum", create_type=False
    )
    review_feedback_category_enum.create(op.get_bind(), checkfirst=True)

    # 2. Add Phase 5 columns to triage_reviews table
    op.add_column("triage_reviews", sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sif_assessments.id", ondelete="CASCADE"), nullable=True))
    op.add_column("triage_reviews", sa.Column("status", sa.Enum("PENDING", "IN_REVIEW", "REVIEWED", name="review_state_enum"), nullable=False, server_default="PENDING"))
    op.add_column("triage_reviews", sa.Column("decision", sa.Enum("CONFIRM_AI", "CORRECT", "REJECT_AI", "MARK_UNDETERMINED", name="review_decision_enum"), nullable=True))
    op.add_column("triage_reviews", sa.Column("reviewer_role", sa.String(100), nullable=True))
    op.add_column("triage_reviews", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("triage_reviews", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("triage_reviews", sa.Column("original_classification", sa.Enum("POTENTIAL_SIF", "ACTUAL_SIF", "NON_SIF", "UNDETERMINED", name="sif_classification_enum"), nullable=False, server_default="UNDETERMINED"))
    op.add_column("triage_reviews", sa.Column("final_classification", sa.Enum("POTENTIAL_SIF", "ACTUAL_SIF", "NON_SIF", "UNDETERMINED", name="sif_classification_enum"), nullable=True))
    op.add_column("triage_reviews", sa.Column("original_structured_precursor", postgresql.JSONB(), nullable=True))
    op.add_column("triage_reviews", sa.Column("final_structured_precursor", postgresql.JSONB(), nullable=True))
    op.add_column("triage_reviews", sa.Column("original_lsr_code", sa.String(100), nullable=True))
    op.add_column("triage_reviews", sa.Column("final_lsr_code", sa.String(100), nullable=True))
    op.add_column("triage_reviews", sa.Column("reviewer_rationale", sa.Text(), nullable=True))
    op.add_column("triage_reviews", sa.Column("feedback_category", sa.Enum("CLASSIFICATION_ERROR", "EXTRACTION_ERROR", "LSR_MAPPING_ERROR", "PRECURSOR_ERROR", "MISSING_EVIDENCE", "INCORRECT_EVIDENCE", "OTHER", name="review_feedback_category_enum"), nullable=True))
    op.add_column("triage_reviews", sa.Column("feedback_details", postgresql.JSONB(), nullable=True))
    op.add_column("triage_reviews", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("triage_reviews", sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.add_column("triage_reviews", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))

    # Nullable reviewer_id (was non-nullable in initial migration)
    op.alter_column("triage_reviews", "reviewer_id", existing_type=sa.String(100), nullable=True)

    op.create_index("ix_triage_reviews_assessment_id", "triage_reviews", ["assessment_id"])
    op.create_index("ix_triage_reviews_status_created", "triage_reviews", ["status", "created_at"])
    op.create_index("ix_triage_reviews_reviewer_status", "triage_reviews", ["reviewer_id", "status"])
    op.create_index("ix_triage_reviews_report_status", "triage_reviews", ["report_id", "status"])

    # 3. Create review_audit_events table
    op.create_table(
        "review_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("review_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("triage_reviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.String(100), nullable=False),
        sa.Column("actor_role", sa.String(100), nullable=True),
        sa.Column("event_type", sa.Enum("REVIEW_CREATED", "REVIEW_CLAIMED", "REVIEW_SUBMITTED", "CLASSIFICATION_CORRECTED", "PRECURSOR_CORRECTED", "LSR_CORRECTED", "REVIEW_REOPENED", "AUDITOR_OVERRIDE", name="review_audit_event_type_enum"), nullable=False),
        sa.Column("before_state", postgresql.JSONB(), nullable=True),
        sa.Column("after_state", postgresql.JSONB(), nullable=True),
        sa.Column("changed_fields", postgresql.JSONB(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_review_audit_events_review_time", "review_audit_events", ["review_id", "created_at"])
    op.create_index("ix_review_audit_events_actor_time", "review_audit_events", ["actor_id", "created_at"])
    op.create_index("ix_review_audit_events_type_time", "review_audit_events", ["event_type", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_review_audit_events_type_time", table_name="review_audit_events")
    op.drop_index("ix_review_audit_events_actor_time", table_name="review_audit_events")
    op.drop_index("ix_review_audit_events_review_time", table_name="review_audit_events")
    op.drop_table("review_audit_events")

    op.drop_index("ix_triage_reviews_report_status", table_name="triage_reviews")
    op.drop_index("ix_triage_reviews_reviewer_status", table_name="triage_reviews")
    op.drop_index("ix_triage_reviews_status_created", table_name="triage_reviews")
    op.drop_index("ix_triage_reviews_assessment_id", table_name="triage_reviews")

    op.drop_column("triage_reviews", "updated_at")
    op.drop_column("triage_reviews", "created_at")
    op.drop_column("triage_reviews", "version")
    op.drop_column("triage_reviews", "feedback_details")
    op.drop_column("triage_reviews", "feedback_category")
    op.drop_column("triage_reviews", "reviewer_rationale")
    op.drop_column("triage_reviews", "final_lsr_code")
    op.drop_column("triage_reviews", "original_lsr_code")
    op.drop_column("triage_reviews", "final_structured_precursor")
    op.drop_column("triage_reviews", "original_structured_precursor")
    op.drop_column("triage_reviews", "final_classification")
    op.drop_column("triage_reviews", "original_classification")
    op.drop_column("triage_reviews", "completed_at")
    op.drop_column("triage_reviews", "started_at")
    op.drop_column("triage_reviews", "reviewer_role")
    op.drop_column("triage_reviews", "decision")
    op.drop_column("triage_reviews", "status")
    op.drop_column("triage_reviews", "assessment_id")

    op.execute("DROP TYPE IF EXISTS review_feedback_category_enum;")
    op.execute("DROP TYPE IF EXISTS review_audit_event_type_enum;")
    op.execute("DROP TYPE IF EXISTS review_decision_enum;")
    op.execute("DROP TYPE IF EXISTS review_state_enum;")
