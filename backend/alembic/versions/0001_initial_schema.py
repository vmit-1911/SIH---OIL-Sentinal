"""0001_initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-23 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector extension if supported on PostgreSQL
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Create Enums if using postgres dialect
    source_type_enum = postgresql.ENUM("UA", "UC", "NEAR_MISS", "INCIDENT", name="source_type_enum", create_type=False)
    source_type_enum.create(op.get_bind(), checkfirst=True)

    actual_outcome_enum = postgresql.ENUM(
        "NO_INJURY", "FIRST_AID", "MINOR_INJURY", "LOST_TIME_INJURY", "EQUIPMENT_DAMAGE_ONLY",
        name="actual_outcome_enum", create_type=False
    )
    actual_outcome_enum.create(op.get_bind(), checkfirst=True)

    potential_outcome_enum = postgresql.ENUM(
        "FATALITY", "PERMANENT_DISABLING_INJURY", "MAJOR_PROCESS_SAFETY_EVENT", "LOW_IMPACT",
        name="potential_outcome_enum", create_type=False
    )
    potential_outcome_enum.create(op.get_bind(), checkfirst=True)

    sif_classification_enum = postgresql.ENUM(
        "POTENTIAL_SIF", "ACTUAL_SIF", "NON_SIF", "UNDETERMINED",
        name="sif_classification_enum", create_type=False
    )
    sif_classification_enum.create(op.get_bind(), checkfirst=True)

    evidence_strength_enum = postgresql.ENUM("LOW", "MEDIUM", "HIGH", name="evidence_strength_enum", create_type=False)
    evidence_strength_enum.create(op.get_bind(), checkfirst=True)

    triage_status_enum = postgresql.ENUM(
        "AUTO_SCREENED", "PENDING_REVIEW", "VALIDATED", "OVERRIDDEN",
        name="triage_status_enum", create_type=False
    )
    triage_status_enum.create(op.get_bind(), checkfirst=True)

    review_status_enum = postgresql.ENUM("VALIDATED", "OVERRIDDEN", name="review_status_enum", create_type=False)
    review_status_enum.create(op.get_bind(), checkfirst=True)

    batch_job_status_enum = postgresql.ENUM(
        "PENDING", "PROCESSING", "COMPLETED", "FAILED",
        name="batch_job_status_enum", create_type=False
    )
    batch_job_status_enum.create(op.get_bind(), checkfirst=True)

    # 3. Create safety_reports table
    op.create_table(
        "safety_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_ref", sa.String(100), unique=True, nullable=False),
        sa.Column("source_type", sa.Enum("UA", "UC", "NEAR_MISS", "INCIDENT", name="source_type_enum"), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("reported_location", sa.String(255), nullable=True),
        sa.Column("reported_department", sa.String(255), nullable=True),
        sa.Column("actual_severity", sa.Enum("NO_INJURY", "FIRST_AID", "MINOR_INJURY", "LOST_TIME_INJURY", "EQUIPMENT_DAMAGE_ONLY", name="actual_outcome_enum"), nullable=False),
        sa.Column("actual_outcome_details", sa.Text(), nullable=True),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_safety_reports_report_ref", "safety_reports", ["report_ref"])
    op.create_index("ix_safety_reports_source_type", "safety_reports", ["source_type"])
    op.create_index("ix_safety_reports_location", "safety_reports", ["reported_location"])
    op.create_index("ix_safety_reports_actual_severity", "safety_reports", ["actual_severity"])
    op.create_index("ix_safety_reports_event_timestamp", "safety_reports", ["event_timestamp"])
    op.create_index("ix_safety_reports_created_at", "safety_reports", ["created_at"])
    op.create_index("ix_safety_reports_source_created", "safety_reports", ["source_type", "created_at"])
    op.create_index("ix_safety_reports_loc_time", "safety_reports", ["reported_location", "event_timestamp"])

    # 4. Create lsr_taxonomies table
    op.create_table(
        "lsr_taxonomies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("taxonomy_id", sa.String(100), unique=True, nullable=False),
        sa.Column("authority", sa.String(100), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("rules", postgresql.JSONB(), nullable=False),
        sa.Column("active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_lsr_taxonomies_taxonomy_id", "lsr_taxonomies", ["taxonomy_id"])
    op.create_index("ix_lsr_taxonomies_active", "lsr_taxonomies", ["active"])

    # 5. Create precursor_patterns table
    op.create_table(
        "precursor_patterns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pattern_code", sa.String(100), unique=True, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("hazard_category", sa.String(100), nullable=True),
        sa.Column("activity_type", sa.String(100), nullable=True),
        sa.Column("failed_barrier_type", sa.String(100), nullable=True),
        sa.Column("lsr_code", sa.String(100), nullable=True),
        sa.Column("occurrence_count", sa.Integer(), default=1, nullable=False),
        sa.Column("affected_locations", postgresql.JSONB(), nullable=False),
        sa.Column("similarity_weights", postgresql.JSONB(), nullable=True),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_detected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_precursor_patterns_pattern_code", "precursor_patterns", ["pattern_code"])
    op.create_index("ix_precursor_patterns_hazard", "precursor_patterns", ["hazard_category"])
    op.create_index("ix_precursor_patterns_activity", "precursor_patterns", ["activity_type"])
    op.create_index("ix_precursor_patterns_barrier", "precursor_patterns", ["failed_barrier_type"])
    op.create_index("ix_precursor_patterns_lsr", "precursor_patterns", ["lsr_code"])
    op.create_index("ix_precursor_patterns_first_detected", "precursor_patterns", ["first_detected_at"])
    op.create_index("ix_precursor_patterns_last_detected", "precursor_patterns", ["last_detected_at"])
    op.create_index("ix_precursor_patterns_hazard_act", "precursor_patterns", ["hazard_category", "activity_type"])

    # 6. Create sif_assessments table
    op.create_table(
        "sif_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("safety_reports.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("sif_classification", sa.Enum("POTENTIAL_SIF", "ACTUAL_SIF", "NON_SIF", "UNDETERMINED", name="sif_classification_enum"), nullable=False),
        sa.Column("evidence_score", sa.Float(), nullable=False, default=0.0),
        sa.Column("evidence_strength", sa.Enum("LOW", "MEDIUM", "HIGH", name="evidence_strength_enum"), nullable=False),
        sa.Column("rule_based_screening_score", sa.Float(), nullable=False, default=0.0),
        sa.Column("potential_severity", sa.Enum("FATALITY", "PERMANENT_DISABLING_INJURY", "MAJOR_PROCESS_SAFETY_EVENT", "LOW_IMPACT", name="potential_outcome_enum"), nullable=False),
        sa.Column("potential_outcome_details", sa.Text(), nullable=True),
        sa.Column("primary_reasoning", sa.Text(), nullable=True),
        sa.Column("evidence_spans", postgresql.JSONB(), nullable=False),
        sa.Column("structured_precursor", postgresql.JSONB(), nullable=False),
        sa.Column("text_embedding", Vector(384), nullable=True),
        sa.Column("precursor_signature", sa.String(255), nullable=True),
        sa.Column("pattern_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("precursor_patterns.id", ondelete="SET NULL"), nullable=True),
        sa.Column("triage_status", sa.Enum("AUTO_SCREENED", "PENDING_REVIEW", "VALIDATED", "OVERRIDDEN", name="triage_status_enum"), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sif_assessments_report_id", "sif_assessments", ["report_id"])
    op.create_index("ix_sif_assessments_classification", "sif_assessments", ["sif_classification"])
    op.create_index("ix_sif_assessments_strength", "sif_assessments", ["evidence_strength"])
    op.create_index("ix_sif_assessments_potential_severity", "sif_assessments", ["potential_severity"])
    op.create_index("ix_sif_assessments_pattern_id", "sif_assessments", ["pattern_id"])
    op.create_index("ix_sif_assessments_triage_status", "sif_assessments", ["triage_status"])
    op.create_index("ix_sif_assessments_assessed_at", "sif_assessments", ["assessed_at"])
    op.create_index("ix_sif_assessments_signature", "sif_assessments", ["precursor_signature"])
    op.create_index("ix_sif_assessments_sif_triage", "sif_assessments", ["sif_classification", "triage_status"])
    op.create_index("ix_sif_assessments_score", "sif_assessments", ["evidence_score"])

    # 7. Create lsr_report_mappings table
    op.create_table(
        "lsr_report_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("safety_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("taxonomy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lsr_taxonomies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_code", sa.String(100), nullable=False),
        sa.Column("rule_name", sa.String(255), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("trigger_evidence", postgresql.JSONB(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), default=True, nullable=False),
    )
    op.create_index("ix_lsr_report_mappings_report_id", "lsr_report_mappings", ["report_id"])
    op.create_index("ix_lsr_report_mappings_taxonomy_id", "lsr_report_mappings", ["taxonomy_id"])
    op.create_index("ix_lsr_report_mappings_rule_code", "lsr_report_mappings", ["rule_code"])
    op.create_index("ix_lsr_report_mappings_rule_report", "lsr_report_mappings", ["rule_code", "report_id"])

    # 8. Create triage_reviews table
    op.create_table(
        "triage_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("safety_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_id", sa.String(100), nullable=False),
        sa.Column("verified_sif_classification", sa.Enum("POTENTIAL_SIF", "ACTUAL_SIF", "NON_SIF", "UNDETERMINED", name="sif_classification_enum"), nullable=False),
        sa.Column("verified_potential_severity", sa.Enum("FATALITY", "PERMANENT_DISABLING_INJURY", "MAJOR_PROCESS_SAFETY_EVENT", "LOW_IMPACT", name="potential_outcome_enum"), nullable=True),
        sa.Column("verified_lsr_code", sa.String(100), nullable=True),
        sa.Column("review_status", sa.Enum("VALIDATED", "OVERRIDDEN", name="review_status_enum"), nullable=False),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_triage_reviews_report_id", "triage_reviews", ["report_id"])
    op.create_index("ix_triage_reviews_reviewer_id", "triage_reviews", ["reviewer_id"])
    op.create_index("ix_triage_reviews_status", "triage_reviews", ["review_status"])
    op.create_index("ix_triage_reviews_reviewed_at", "triage_reviews", ["reviewed_at"])
    op.create_index("ix_triage_reviews_reviewer_time", "triage_reviews", ["reviewer_id", "reviewed_at"])

    # 9. Create batch_jobs table
    op.create_table(
        "batch_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.Enum("PENDING", "PROCESSING", "COMPLETED", "FAILED", name="batch_job_status_enum"), nullable=False),
        sa.Column("total_records", sa.Integer(), nullable=False, default=0),
        sa.Column("processed_records", sa.Integer(), nullable=False, default=0),
        sa.Column("sif_count", sa.Integer(), nullable=False, default=0),
        sa.Column("error_count", sa.Integer(), nullable=False, default=0),
        sa.Column("error_details", postgresql.JSONB(), nullable=True),
        sa.Column("results_summary", postgresql.JSONB(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_batch_jobs_status", "batch_jobs", ["status"])
    op.create_index("ix_batch_jobs_created_at", "batch_jobs", ["created_at"])


def downgrade() -> None:
    op.drop_table("batch_jobs")
    op.drop_table("triage_reviews")
    op.drop_table("lsr_report_mappings")
    op.drop_table("sif_assessments")
    op.drop_table("precursor_patterns")
    op.drop_table("lsr_taxonomies")
    op.drop_table("safety_reports")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS batch_job_status_enum;")
    op.execute("DROP TYPE IF EXISTS review_status_enum;")
    op.execute("DROP TYPE IF EXISTS triage_status_enum;")
    op.execute("DROP TYPE IF EXISTS evidence_strength_enum;")
    op.execute("DROP TYPE IF EXISTS sif_classification_enum;")
    op.execute("DROP TYPE IF EXISTS potential_outcome_enum;")
    op.execute("DROP TYPE IF EXISTS actual_outcome_enum;")
    op.execute("DROP TYPE IF EXISTS source_type_enum;")
