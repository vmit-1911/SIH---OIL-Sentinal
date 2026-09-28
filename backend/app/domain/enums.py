"""Domain enumerations for OIL SIF Sentinel."""

from enum import Enum


class SourceType(str, Enum):
    """Source classification of the safety observation."""
    UA = "UA"  # Unsafe Act
    UC = "UC"  # Unsafe Condition
    NEAR_MISS = "NEAR_MISS"
    INCIDENT = "INCIDENT"


class ActualOutcome(str, Enum):
    """Actual physical outcome or injury resulting from the event."""
    NO_INJURY = "NO_INJURY"
    FIRST_AID = "FIRST_AID"
    MINOR_INJURY = "MINOR_INJURY"
    LOST_TIME_INJURY = "LOST_TIME_INJURY"
    EQUIPMENT_DAMAGE_ONLY = "EQUIPMENT_DAMAGE_ONLY"


class PotentialOutcome(str, Enum):
    """Plausible worst-case consequence if remaining defenses failed."""
    FATALITY = "FATALITY"
    PERMANENT_DISABLING_INJURY = "PERMANENT_DISABLING_INJURY"
    MAJOR_PROCESS_SAFETY_EVENT = "MAJOR_PROCESS_SAFETY_EVENT"
    LOW_IMPACT = "LOW_IMPACT"


class SIFClassification(str, Enum):
    """Core SIF categorization distinguishing potential from actual events.

    For automated heuristic screening (Phase 1B), the primary automated classifications are:
    - POTENTIAL_SIF: High-energy hazard exposure and/or critical barrier degradation present.
    - NON_SIF: Routine low-energy observations or conditions without critical barrier degradation.
    - UNDETERMINED: Inconclusive or insufficient narrative context.

    ACTUAL_SIF is NOT automatically inferred merely from injury severity. It is strictly reserved for:
    - Human HSE verification and triage review (TriageReview)
    - Authoritative source data / medical records
    - Future validated SIF classification logic
    """
    POTENTIAL_SIF = "POTENTIAL_SIF"
    ACTUAL_SIF = "ACTUAL_SIF"
    NON_SIF = "NON_SIF"
    UNDETERMINED = "UNDETERMINED"


class EvidenceStrength(str, Enum):
    """Categorical strength of evidence supporting the SIF classification."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TriageStatus(str, Enum):
    """Workflow status of the report in the HSE triage queue."""
    AUTO_SCREENED = "AUTO_SCREENED"
    PENDING_REVIEW = "PENDING_REVIEW"
    VALIDATED = "VALIDATED"
    OVERRIDDEN = "OVERRIDDEN"


class ReviewStatus(str, Enum):
    """HSE auditor decision status (backward-compatible alias)."""
    VALIDATED = "VALIDATED"
    OVERRIDDEN = "OVERRIDDEN"


class ReviewState(str, Enum):
    """Lifecycle state of an HSE human-in-the-loop review item."""
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    REVIEWED = "REVIEWED"


class ReviewDecision(str, Enum):
    """Authoritative HSE auditor decision on AI assessment."""
    CONFIRM_AI = "CONFIRM_AI"
    CORRECT = "CORRECT"
    REJECT_AI = "REJECT_AI"
    MARK_UNDETERMINED = "MARK_UNDETERMINED"


class ReviewAuditEventType(str, Enum):
    """Audit trail event type for tracking human review lifecycle actions."""
    REVIEW_CREATED = "REVIEW_CREATED"
    REVIEW_CLAIMED = "REVIEW_CLAIMED"
    REVIEW_SUBMITTED = "REVIEW_SUBMITTED"
    CLASSIFICATION_CORRECTED = "CLASSIFICATION_CORRECTED"
    PRECURSOR_CORRECTED = "PRECURSOR_CORRECTED"
    LSR_CORRECTED = "LSR_CORRECTED"
    REVIEW_REOPENED = "REVIEW_REOPENED"
    AUDITOR_OVERRIDE = "AUDITOR_OVERRIDE"


class ReviewFeedbackCategory(str, Enum):
    """Categorical classification of review feedback for model calibration."""
    CLASSIFICATION_ERROR = "CLASSIFICATION_ERROR"
    EXTRACTION_ERROR = "EXTRACTION_ERROR"
    LSR_MAPPING_ERROR = "LSR_MAPPING_ERROR"
    PRECURSOR_ERROR = "PRECURSOR_ERROR"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    INCORRECT_EVIDENCE = "INCORRECT_EVIDENCE"
    OTHER = "OTHER"


class BatchJobStatus(str, Enum):
    """Lifecycle status of asynchronous batch processing jobs."""
    PENDING = "PENDING"
    VALIDATING = "VALIDATING"
    INGESTING = "INGESTING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"


class BatchRowStatus(str, Enum):
    """Row-level evaluation outcome during batch ingestion."""
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"



class DerivationType(str, Enum):
    """Origin and provenance type for extracted or inferred safety concepts."""
    DIRECT_MATCH = "DIRECT_MATCH"  # Explicitly matched substring from narrative
    LEXICON_INFERENCE = "LEXICON_INFERENCE"  # Canonical concept mapped via domain lexicon
    RULE_INFERENCE = "RULE_INFERENCE"  # Derived via multi-factor domain evaluation rule
    METADATA = "METADATA"  # Sourced from structured report/request metadata


class PatternStatus(str, Enum):
    """Lifecycle status of a discovered recurring precursor pattern.
    
    Automatically discovered pattern candidates start in CANDIDATE state without
    implying automated risk prioritization or human validation.
    """
    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class ConcentrationDimension(str, Enum):
    """Operational aggregation dimension for SIF risk concentration findings."""
    PATTERN = "PATTERN"
    HAZARD = "HAZARD"
    BARRIER_FAILURE = "BARRIER_FAILURE"
    ACTIVITY = "ACTIVITY"
    LIFE_SAVING_RULE = "LIFE_SAVING_RULE"
    LOCATION = "LOCATION"


class ObservedTrend(str, Enum):
    """Descriptive classification of observed recurrence counts across chronological time periods.
    
    This is descriptive of observed historical reporting only. It is not a statistical forecast
    and does not represent probability of future injury.
    """
    STABLE = "STABLE"
    INCREASING = "INCREASING"
    DECREASING = "DECREASING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ConcentrationStatus(str, Enum):
    """Lifecycle status of a risk concentration finding."""
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class ActionCategory(str, Enum):
    """Controlled categorical classifications for HSE action recommendations."""
    IMMEDIATE_REVIEW = "IMMEDIATE_REVIEW"
    BARRIER_VERIFICATION = "BARRIER_VERIFICATION"
    PROCEDURE_REVIEW = "PROCEDURE_REVIEW"
    WORK_AUTHORIZATION_REVIEW = "WORK_AUTHORIZATION_REVIEW"
    ENERGY_ISOLATION_VERIFICATION = "ENERGY_ISOLATION_VERIFICATION"
    FALL_PROTECTION_VERIFICATION = "FALL_PROTECTION_VERIFICATION"
    LIFTING_CONTROL_VERIFICATION = "LIFTING_CONTROL_VERIFICATION"
    LINE_OF_FIRE_CONTROL_REVIEW = "LINE_OF_FIRE_CONTROL_REVIEW"
    CONFINED_SPACE_CONTROL_REVIEW = "CONFINED_SPACE_CONTROL_REVIEW"
    HOT_WORK_CONTROL_REVIEW = "HOT_WORK_CONTROL_REVIEW"
    DRIVING_CONTROL_REVIEW = "DRIVING_CONTROL_REVIEW"
    TREND_INVESTIGATION = "TREND_INVESTIGATION"
    PATTERN_INVESTIGATION = "PATTERN_INVESTIGATION"
    SITE_FOCUSED_REVIEW = "SITE_FOCUSED_REVIEW"
    MANAGEMENT_ATTENTION = "MANAGEMENT_ATTENTION"


class ActionPriority(str, Enum):
    """Deterministic priority levels for HSE action recommendations."""
    CRITICAL_REVIEW = "CRITICAL_REVIEW"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    INFORMATIONAL = "INFORMATIONAL"


class ActionStatus(str, Enum):
    """Controlled lifecycle status of an HSE action recommendation."""
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DISMISSED = "DISMISSED"


class ActionSourceType(str, Enum):
    """Originating intelligence entity for an HSE action recommendation."""
    ASSESSMENT = "ASSESSMENT"
    PATTERN = "PATTERN"
    CONCENTRATION = "CONCENTRATION"
    REVIEW = "REVIEW"


class CaseType(str, Enum):
    """Categorical classification of an HSE case/investigation."""
    SIF_INVESTIGATION = "SIF_INVESTIGATION"
    PATTERN_INVESTIGATION = "PATTERN_INVESTIGATION"
    LOCATION_REVIEW = "LOCATION_REVIEW"
    ACTIVITY_REVIEW = "ACTIVITY_REVIEW"
    BARRIER_REVIEW = "BARRIER_REVIEW"
    HSE_FOLLOW_UP = "HSE_FOLLOW_UP"


class CaseStatus(str, Enum):
    """Operational lifecycle status of an HSE case."""
    OPEN = "OPEN"
    TRIAGE = "TRIAGE"
    INVESTIGATING = "INVESTIGATING"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class CasePriority(str, Enum):
    """Operational review priority for an HSE case."""
    CRITICAL_REVIEW = "CRITICAL_REVIEW"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    INFORMATIONAL = "INFORMATIONAL"


class CaseEventType(str, Enum):
    """Append-only audit trail event type for tracking case lifecycle mutations."""
    CASE_CREATED = "CASE_CREATED"
    CASE_ASSIGNED = "CASE_ASSIGNED"
    CASE_STATUS_CHANGED = "CASE_STATUS_CHANGED"
    SOURCE_ATTACHED = "SOURCE_ATTACHED"
    SOURCE_DETACHED = "SOURCE_DETACHED"
    ACTION_ATTACHED = "ACTION_ATTACHED"
    ACTION_DETACHED = "ACTION_DETACHED"
    ACTION_STATUS_CHANGED = "ACTION_STATUS_CHANGED"
    REVIEW_ATTACHED = "REVIEW_ATTACHED"
    CASE_REOPENED = "CASE_REOPENED"
    CASE_CLOSED = "CASE_CLOSED"
    CASE_CANCELLED = "CASE_CANCELLED"


class CaseSourceType(str, Enum):
    """Source intelligence entity type attached to an HSE case."""
    REPORT = "REPORT"
    ASSESSMENT = "ASSESSMENT"
    PATTERN = "PATTERN"
    CONCENTRATION = "CONCENTRATION"
    REVIEW = "REVIEW"
    ACTION = "ACTION"


class WebhookEventType(str, Enum):
    """Event types that trigger webhook notifications and alerting pipelines."""
    SIF_DETECTED = "SIF_DETECTED"
    HIGH_CONCENTRATION_TRIGGERED = "HIGH_CONCENTRATION_TRIGGERED"
    ACTION_CRITICAL_ASSIGNED = "ACTION_CRITICAL_ASSIGNED"
    CASE_STATUS_CHANGED = "CASE_STATUS_CHANGED"
    EXPORT_GENERATED = "EXPORT_GENERATED"
    REVIEW_OVERRIDDEN = "REVIEW_OVERRIDDEN"
    TEST_PING = "TEST_PING"


class AlertChannel(str, Enum):
    """Delivery channels for HSE safety alerts."""
    WEBHOOK = "WEBHOOK"
    EMAIL = "EMAIL"
    IN_APP = "IN_APP"


class AlertSeverity(str, Enum):
    """Severity tier for dispatched safety alerts."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertDispatchStatus(str, Enum):
    """Delivery status of an alert notification."""
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
