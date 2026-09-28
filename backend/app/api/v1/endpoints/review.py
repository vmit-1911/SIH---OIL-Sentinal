"""HSE officer audit review, triage queue, state machine, and audit trail endpoints."""

import math
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ReviewNotFoundException
from app.db.models.review import TriageReview
from app.db.session import get_db_session
from app.domain.enums import ReviewState, SIFClassification
from app.schemas.common import ErrorResponse
from app.schemas.review import (
    HumanReviewRequest,
    HumanReviewResponse,
    ReviewAnalyticsSummary,
    ReviewAuditEventResponse,
    ReviewClaimRequest,
    ReviewDecisionRequest,
    ReviewDetailResponse,
    ReviewFeedbackResponse,
    ReviewReopenRequest,
    TriageQueueItem,
    TriageQueueResponse,
)
from app.services.report_service import ReportService
from app.services.triage_service import TriageService

router = APIRouter()


def _map_review_to_detail(review: TriageReview) -> ReviewDetailResponse:
    """Helper to convert TriageReview ORM instance into ReviewDetailResponse DTO."""
    feedback_dto = None
    if review.feedback_category:
        fb_notes = None
        fb_details = None
        if isinstance(review.feedback_details, dict):
            fb_notes = review.feedback_details.get("notes")
            fb_details = review.feedback_details.get("specific_error_details")
        feedback_dto = ReviewFeedbackResponse(
            category=review.feedback_category,
            notes=fb_notes,
            specific_error_details=fb_details,
        )

    audit_events_dto = [
        ReviewAuditEventResponse(
            id=ev.id,
            review_id=ev.review_id,
            actor_id=ev.actor_id,
            actor_role=ev.actor_role,
            event_type=ev.event_type,
            before_state=ev.before_state,
            after_state=ev.after_state,
            changed_fields=ev.changed_fields,
            rationale=ev.rationale,
            created_at=ev.created_at,
        )
        for ev in (review.audit_events or [])
    ]

    return ReviewDetailResponse(
        id=review.id,
        report_id=review.report_id,
        assessment_id=review.assessment_id,
        status=review.status,
        decision=review.decision,
        reviewer_id=review.reviewer_id,
        reviewer_role=review.reviewer_role,
        started_at=review.started_at,
        completed_at=review.completed_at,
        original_classification=review.original_classification,
        final_classification=review.final_classification,
        original_structured_precursor=review.original_structured_precursor,
        final_structured_precursor=review.final_structured_precursor,
        original_lsr_code=review.original_lsr_code,
        final_lsr_code=review.final_lsr_code,
        reviewer_rationale=review.reviewer_rationale,
        reviewer_notes=review.reviewer_notes,
        feedback=feedback_dto,
        version=review.version,
        created_at=review.created_at,
        updated_at=review.updated_at,
        report_narrative=review.report.raw_text if review.report else None,
        reported_location=review.report.reported_location if review.report else None,
        source_type=review.report.source_type.value if review.report else None,
        event_timestamp=review.report.event_timestamp if review.report else None,
        recent_audit_events=audit_events_dto,
    )


@router.get(
    "/sif/reviews/queue",
    response_model=TriageQueueResponse,
    status_code=status.HTTP_200_OK,
    summary="List Triage Review Queue",
    description="Retrieve paginated review items with deterministic multi-attribute filtering (status, classification, location, LSR, batch, dates).",
)
async def get_triage_queue(
    status: Optional[ReviewState] = Query(None, description="Filter by review lifecycle status: PENDING, IN_REVIEW, REVIEWED"),
    classification: Optional[SIFClassification] = Query(None, description="Filter by SIF classification"),
    location: Optional[str] = Query(None, description="Case-insensitive location search"),
    life_saving_rule: Optional[str] = Query(None, description="Filter by Life-Saving Rule code"),
    batch_id: Optional[UUID] = Query(None, description="Filter by batch ingestion job ID"),
    date_from: Optional[datetime] = Query(None, description="Filter from event or creation date"),
    date_to: Optional[datetime] = Query(None, description="Filter to event or creation date"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db_session),
) -> TriageQueueResponse:
    """Retrieve filtered triage review queue."""
    service = TriageService(db)
    items, total_count = await service.get_triage_queue(
        status=status,
        classification=classification,
        location=location,
        life_saving_rule=life_saving_rule,
        batch_id=batch_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )

    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0

    queue_items = [
        TriageQueueItem(
            review_id=r.id,
            report_id=r.report_id,
            assessment_id=r.assessment_id,
            status=r.status,
            decision=r.decision,
            reviewer_id=r.reviewer_id,
            classification=r.final_classification or r.original_classification,
            life_saving_rule=r.final_lsr_code or r.original_lsr_code,
            reported_location=r.report.reported_location if r.report else None,
            source_type=r.report.source_type.value if r.report else "UNKNOWN",
            event_timestamp=r.report.event_timestamp if r.report else None,
            created_at=r.created_at,
            batch_id=r.report.batch_id if r.report else None,
        )
        for r in items
    ]

    return TriageQueueResponse(
        items=queue_items,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/sif/reviews/analytics/summary",
    response_model=ReviewAnalyticsSummary,
    status_code=status.HTTP_200_OK,
    summary="Get Review Audit Analytics Summary",
    description="Returns descriptive audit statistics of HSE human-in-the-loop actions, override counts, and calibration feedback breakdown.",
)
async def get_review_analytics_summary(
    db: AsyncSession = Depends(get_db_session),
) -> ReviewAnalyticsSummary:
    """Retrieve descriptive review audit statistics."""
    service = TriageService(db)
    return await service.get_analytics_summary()


@router.get(
    "/sif/reviews/{review_id}",
    response_model=ReviewDetailResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Review item not found"},
    },
    summary="Get Triage Review Details",
    description="Retrieve full details for a review item, including report narrative, original AI values, human corrections, and audit history.",
)
async def get_review_detail(
    review_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> ReviewDetailResponse:
    """Fetch complete review item details."""
    service = TriageService(db)
    review = await service.get_review_by_id(review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Triage review item with ID '{review_id}' not found",
        )
    return _map_review_to_detail(review)


@router.post(
    "/sif/reviews/{review_id}/claim",
    response_model=ReviewDetailResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Review item not found"},
        409: {"model": ErrorResponse, "description": "Review item already claimed by another officer"},
        400: {"model": ErrorResponse, "description": "Invalid state transition"},
    },
    summary="Claim Review Item",
    description="Claims a PENDING review item for an HSE officer, transitioning it to IN_REVIEW.",
)
async def claim_review(
    review_id: UUID,
    request: ReviewClaimRequest,
    db: AsyncSession = Depends(get_db_session),
) -> ReviewDetailResponse:
    """Claim a review item from the triage queue."""
    service = TriageService(db)
    review = await service.claim_review(review_id, request)
    return _map_review_to_detail(review)


@router.post(
    "/sif/reviews/{review_id}/decision",
    response_model=ReviewDetailResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Review item not found"},
        409: {"model": ErrorResponse, "description": "Concurrency conflict"},
        400: {"model": ErrorResponse, "description": "Missing rationale or invalid state transition"},
    },
    summary="Submit Human Review Decision",
    description="Submit an authoritative decision (CONFIRM_AI, CORRECT, REJECT_AI, MARK_UNDETERMINED) with optional corrections and rationale.",
)
async def submit_review_decision(
    review_id: UUID,
    request: ReviewDecisionRequest,
    db: AsyncSession = Depends(get_db_session),
) -> ReviewDetailResponse:
    """Submit decision and corrections for a review item."""
    service = TriageService(db)
    review = await service.submit_decision(review_id, request)
    return _map_review_to_detail(review)


@router.get(
    "/sif/reviews/{review_id}/history",
    response_model=List[ReviewAuditEventResponse],
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Review item not found"},
    },
    summary="Get Append-Only Review Audit History",
    description="Returns the full chronological append-only audit trail of events for this review.",
)
async def get_review_history(
    review_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> List[ReviewAuditEventResponse]:
    """Retrieve full append-only audit trail for a review item."""
    service = TriageService(db)
    events = await service.get_review_history(review_id)
    return [
        ReviewAuditEventResponse(
            id=ev.id,
            review_id=ev.review_id,
            actor_id=ev.actor_id,
            actor_role=ev.actor_role,
            event_type=ev.event_type,
            before_state=ev.before_state,
            after_state=ev.after_state,
            changed_fields=ev.changed_fields,
            rationale=ev.rationale,
            created_at=ev.created_at,
        )
        for ev in events
    ]


@router.post(
    "/sif/reviews/{review_id}/reopen",
    response_model=ReviewDetailResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Review item not found"},
        400: {"model": ErrorResponse, "description": "Cannot reopen unreviewed item or missing rationale"},
    },
    summary="Reopen Completed Review",
    description="Transitions a REVIEWED item back to IN_REVIEW with mandatory justification.",
)
async def reopen_review(
    review_id: UUID,
    request: ReviewReopenRequest,
    db: AsyncSession = Depends(get_db_session),
) -> ReviewDetailResponse:
    """Reopen a previously completed review."""
    service = TriageService(db)
    review = await service.reopen_review(review_id, request)
    return _map_review_to_detail(review)


# Legacy review endpoint for backward compatibility
@router.post(
    "/sif/reports/{report_id}/review",
    response_model=HumanReviewResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Report not found"},
    },
    summary="Submit HSE Auditor Review (Legacy)",
    description="Allows HSE officers to confirm or override automated SIF potential decisions (backward-compatible legacy endpoint).",
)
async def review_report_legacy(
    report_id: UUID,
    request: HumanReviewRequest,
    db: AsyncSession = Depends(get_db_session),
) -> HumanReviewResponse:
    """Submit human review decision for a safety report via legacy endpoint."""
    report_service = ReportService(db)
    report = await report_service.get_report_by_id(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Safety report with ID '{report_id}' not found",
        )

    triage_service = TriageService(db)
    review = await triage_service.record_review(report_id, request)

    return HumanReviewResponse(
        report_id=report_id,
        review_id=review.id,
        status=review.review_status,
        updated_at=datetime.now(timezone.utc),
    )
