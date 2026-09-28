"""Unit tests for SQLAlchemy ORM models metadata."""

from app.db.base import Base
from app.db.models import (
    BatchJob,
    LSRReportMapping,
    LSRTaxonomy,
    PrecursorPattern,
    SafetyReport,
    SIFAssessment,
    TriageReview,
)


def test_models_registered_in_metadata():
    """Verify all 7 models are registered in Base.metadata."""
    table_names = set(Base.metadata.tables.keys())
    expected_tables = {
        "safety_reports",
        "sif_assessments",
        "lsr_taxonomies",
        "lsr_report_mappings",
        "precursor_patterns",
        "triage_reviews",
        "batch_jobs",
    }
    assert expected_tables.issubset(table_names)


def test_safety_report_columns():
    """Verify safety_reports table columns."""
    table = Base.metadata.tables["safety_reports"]
    columns = {c.name for c in table.columns}
    assert {"id", "report_ref", "source_type", "raw_text", "actual_severity", "created_at"}.issubset(columns)


def test_sif_assessment_columns_and_vector():
    """Verify sif_assessments table has pgvector embedding and jsonb precursor."""
    table = Base.metadata.tables["sif_assessments"]
    columns = {c.name for c in table.columns}
    assert {
        "id",
        "report_id",
        "sif_classification",
        "evidence_score",
        "evidence_strength",
        "rule_based_screening_score",
        "potential_severity",
        "structured_precursor",
        "text_embedding",
        "triage_status",
    }.issubset(columns)
    # Check that text_embedding is nullable in Phase 0
    assert table.columns["text_embedding"].nullable is True


def test_triage_review_and_audit_event_columns():
    """Verify triage_reviews and review_audit_events table columns."""
    review_table = Base.metadata.tables["triage_reviews"]
    review_cols = {c.name for c in review_table.columns}
    assert {
        "id",
        "report_id",
        "assessment_id",
        "status",
        "decision",
        "reviewer_id",
        "reviewer_role",
        "original_classification",
        "final_classification",
        "original_structured_precursor",
        "final_structured_precursor",
        "original_lsr_code",
        "final_lsr_code",
        "reviewer_rationale",
        "reviewer_notes",
        "feedback_category",
        "feedback_details",
        "version",
        "created_at",
        "updated_at",
    }.issubset(review_cols)

    audit_table = Base.metadata.tables["review_audit_events"]
    audit_cols = {c.name for c in audit_table.columns}
    assert {
        "id",
        "review_id",
        "actor_id",
        "actor_role",
        "event_type",
        "before_state",
        "after_state",
        "changed_fields",
        "rationale",
        "created_at",
    }.issubset(audit_cols)

