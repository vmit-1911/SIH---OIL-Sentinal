"""Unit tests for domain enums."""

import pytest
from app.domain.enums import (
    ActualOutcome,
    EvidenceStrength,
    PotentialOutcome,
    SIFClassification,
    SourceType,
    TriageStatus,
)


def test_actual_outcome_values():
    """Verify all required actual outcome enums are present."""
    expected = {"NO_INJURY", "FIRST_AID", "MINOR_INJURY", "LOST_TIME_INJURY", "EQUIPMENT_DAMAGE_ONLY"}
    actual = {e.value for e in ActualOutcome}
    assert expected == actual


def test_potential_outcome_values():
    """Verify all required potential outcome enums are present."""
    expected = {"FATALITY", "PERMANENT_DISABLING_INJURY", "MAJOR_PROCESS_SAFETY_EVENT", "LOW_IMPACT"}
    actual = {e.value for e in PotentialOutcome}
    assert expected == actual


def test_sif_classification_values():
    """Verify all required SIF classification enums are present."""
    expected = {"POTENTIAL_SIF", "ACTUAL_SIF", "NON_SIF", "UNDETERMINED"}
    actual = {e.value for e in SIFClassification}
    assert expected == actual


def test_evidence_strength_values():
    """Verify evidence strength enums."""
    expected = {"LOW", "MEDIUM", "HIGH"}
    actual = {e.value for e in EvidenceStrength}
    assert expected == actual


def test_pattern_status_values():
    """Verify pattern status enums."""
    from app.domain.enums import PatternStatus
    expected = {"CANDIDATE", "ACTIVE", "ARCHIVED"}
    actual = {e.value for e in PatternStatus}
    assert expected == actual


def test_batch_enums():
    """Verify BatchJobStatus and BatchRowStatus enum values."""
    from app.domain.enums import BatchJobStatus, BatchRowStatus
    expected_job = {
        "PENDING",
        "VALIDATING",
        "INGESTING",
        "PROCESSING",
        "COMPLETED",
        "COMPLETED_WITH_ERRORS",
        "FAILED",
    }
    assert expected_job == {e.value for e in BatchJobStatus}

    expected_row = {"ACCEPTED", "REJECTED", "DUPLICATE"}
    assert expected_row == {e.value for e in BatchRowStatus}


def test_review_enums():
    """Verify ReviewState, ReviewDecision, ReviewAuditEventType, and ReviewFeedbackCategory values."""
    from app.domain.enums import (
        ReviewAuditEventType,
        ReviewDecision,
        ReviewFeedbackCategory,
        ReviewState,
    )
    expected_states = {"PENDING", "IN_REVIEW", "REVIEWED"}
    assert expected_states == {e.value for e in ReviewState}

    expected_decisions = {"CONFIRM_AI", "CORRECT", "REJECT_AI", "MARK_UNDETERMINED"}
    assert expected_decisions == {e.value for e in ReviewDecision}

    expected_events = {
        "REVIEW_CREATED",
        "REVIEW_CLAIMED",
        "REVIEW_SUBMITTED",
        "CLASSIFICATION_CORRECTED",
        "PRECURSOR_CORRECTED",
        "LSR_CORRECTED",
        "REVIEW_REOPENED",
        "AUDITOR_OVERRIDE",
    }
    assert expected_events == {e.value for e in ReviewAuditEventType}

    expected_feedback = {
        "CLASSIFICATION_ERROR",
        "EXTRACTION_ERROR",
        "LSR_MAPPING_ERROR",
        "PRECURSOR_ERROR",
        "MISSING_EVIDENCE",
        "INCORRECT_EVIDENCE",
        "OTHER",
    }
    assert expected_feedback == {e.value for e in ReviewFeedbackCategory}


