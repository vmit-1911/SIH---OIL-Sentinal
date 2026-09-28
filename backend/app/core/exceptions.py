"""Custom exception classes and error handlers for OIL SIF Sentinel."""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class SIFSentinelException(Exception):
    """Base exception for all application errors."""
    status_code: int = status.HTTP_400_BAD_REQUEST

    def __init__(self, message: Any, details: Optional[Dict[str, Any]] = None):
        super().__init__(str(message))
        self.message = str(message)
        self.details = details or {}


class TaxonomyNotFoundException(SIFSentinelException):
    """Raised when a requested LSR taxonomy is not found or cannot be loaded."""
    status_code = status.HTTP_404_NOT_FOUND


class ReportNotFoundException(SIFSentinelException):
    """Raised when a requested safety report is not found."""
    status_code = status.HTTP_404_NOT_FOUND


class AssessmentNotFoundException(SIFSentinelException):
    """Raised when a requested SIF assessment is not found."""
    status_code = status.HTTP_404_NOT_FOUND


class PatternNotFoundException(SIFSentinelException):
    """Raised when a requested precursor pattern is not found."""
    status_code = status.HTTP_404_NOT_FOUND


class ConcentrationNotFoundException(SIFSentinelException):
    """Raised when a requested risk concentration finding is not found."""
    status_code = status.HTTP_404_NOT_FOUND


class BatchJobNotFoundException(SIFSentinelException):
    """Raised when a requested batch processing job is not found."""
    status_code = status.HTTP_404_NOT_FOUND


class ReviewNotFoundException(SIFSentinelException):
    """Raised when a requested triage review item is not found."""
    status_code = status.HTTP_404_NOT_FOUND


class InvalidStateTransitionException(SIFSentinelException):
    """Raised when an invalid lifecycle state transition is attempted on a review."""
    status_code = status.HTTP_400_BAD_REQUEST


class ReviewConflictException(SIFSentinelException):
    """Raised when a concurrency conflict occurs while claiming or submitting a review."""
    status_code = status.HTTP_409_CONFLICT


class ActionNotFoundException(SIFSentinelException):
    """Raised when a requested HSE action recommendation is not found."""
    status_code = status.HTTP_404_NOT_FOUND


class CaseNotFoundException(SIFSentinelException):
    """Raised when a requested HSE case is not found."""
    status_code = status.HTTP_404_NOT_FOUND


class CaseSourceNotFoundException(SIFSentinelException):
    """Raised when a requested source association is not found in an HSE case."""
    status_code = status.HTTP_404_NOT_FOUND


class DuplicateSourceAssociationException(SIFSentinelException):
    """Raised when attempting to associate a duplicate source entity to a case."""
    status_code = status.HTTP_409_CONFLICT


class CaseClosureBlockedException(SIFSentinelException):
    """Raised when case closure is blocked due to uncompleted actions or missing rationale."""
    status_code = status.HTTP_400_BAD_REQUEST


class ReviewRationaleRequiredException(SIFSentinelException):
    """Raised when an AI assessment override or correction is submitted without required rationale."""
    status_code = status.HTTP_400_BAD_REQUEST


class DatabaseNotReadyException(SIFSentinelException):
    """Raised when database or vector extension connectivity check fails."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class WebhookNotFoundException(SIFSentinelException):
    """Raised when a requested webhook subscription cannot be located."""
    status_code = status.HTTP_404_NOT_FOUND


class FeatureNotImplementedException(HTTPException):
    """Explicit 501 exception for capabilities scheduled for future phases."""

    def __init__(self, feature_name: str, scheduled_phase: str = "Phase 1"):
        super().__init__(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "error": "Not Implemented",
                "feature": feature_name,
                "message": (
                    f"The feature '{feature_name}' is scheduled for implementation in {scheduled_phase}. "
                    "Phase 0 establishes the API contract and schema baseline only."
                ),
            },
        )
