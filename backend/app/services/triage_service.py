"""HSE auditor review, triage queue, state machine, and audit trail service."""

import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    InvalidStateTransitionException,
    ReportNotFoundException,
    ReviewConflictException,
    ReviewNotFoundException,
    ReviewRationaleRequiredException,
)
from app.db.models.assessment import SIFAssessment
from app.db.models.report import SafetyReport
from app.db.models.review import ReviewAuditEvent, TriageReview
from app.domain.enums import (
    ReviewAuditEventType,
    ReviewDecision,
    ReviewFeedbackCategory,
    ReviewState,
    ReviewStatus,
    SIFClassification,
    TriageStatus,
)
from app.schemas.review import (
    HumanReviewRequest,
    ReviewAnalyticsSummary,
    ReviewClaimRequest,
    ReviewDecisionRequest,
    ReviewReopenRequest,
)


class TriageService:
    """Service handling HSE officer audit review, lifecycle state machine, and audit trail."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def ensure_review_for_assessment(self, assessment_id: uuid.UUID) -> TriageReview:
        """Create or return existing PENDING review for an AI assessment with initial audit snapshot."""
        stmt = (
            select(TriageReview)
            .where(TriageReview.assessment_id == assessment_id)
            .options(selectinload(TriageReview.report), selectinload(TriageReview.audit_events))
        )
        res = await self.session.execute(stmt)
        review = res.scalars().first()
        if review:
            return review

        # Fetch assessment details
        assessment_stmt = (
            select(SIFAssessment)
            .where(SIFAssessment.id == assessment_id)
            .options(selectinload(SIFAssessment.report))
        )
        res = await self.session.execute(assessment_stmt)
        assessment = res.scalars().first()
        if not assessment:
            raise ReviewNotFoundException(f"SIFAssessment with ID '{assessment_id}' not found")

        # Determine original primary LSR code
        original_lsr = None
        if assessment.structured_precursor and isinstance(assessment.structured_precursor, dict):
            lsr_dict = assessment.structured_precursor.get("life_saving_rule")
            if isinstance(lsr_dict, dict):
                original_lsr = lsr_dict.get("rule_code")

        review = TriageReview(
            id=uuid.uuid4(),
            report_id=assessment.report_id,
            assessment_id=assessment.id,
            status=ReviewState.PENDING,
            decision=None,
            reviewer_id=None,
            reviewer_role=None,
            original_classification=assessment.sif_classification,
            final_classification=assessment.sif_classification,
            original_structured_precursor=assessment.structured_precursor,
            final_structured_precursor=assessment.structured_precursor,
            original_lsr_code=original_lsr,
            final_lsr_code=original_lsr,
            version=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(review)

        # Initial append-only audit event
        audit_event = ReviewAuditEvent(
            id=uuid.uuid4(),
            review_id=review.id,
            actor_id="system",
            actor_role="SYSTEM",
            event_type=ReviewAuditEventType.REVIEW_CREATED,
            before_state=None,
            after_state={
                "status": ReviewState.PENDING.value,
                "original_classification": assessment.sif_classification.value,
                "original_lsr_code": original_lsr,
            },
            changed_fields=["status", "original_classification", "original_lsr_code"],
            rationale="Initial AI assessment ingested and staged for HSE expert review",
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(audit_event)
        await self.session.flush()
        return review

    async def get_review_by_id(self, review_id: uuid.UUID) -> Optional[TriageReview]:
        """Fetch review with report, assessment, and audit history loaded."""
        stmt = (
            select(TriageReview)
            .where(TriageReview.id == review_id)
            .options(
                selectinload(TriageReview.report),
                selectinload(TriageReview.assessment),
                selectinload(TriageReview.audit_events),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def claim_review(
        self,
        review_id: uuid.UUID,
        request: ReviewClaimRequest,
    ) -> TriageReview:
        """Claim a review item from the queue, transitioning PENDING -> IN_REVIEW."""
        review = await self.get_review_by_id(review_id)
        if not review:
            raise ReviewNotFoundException(f"Triage review item with ID '{review_id}' not found")

        # State transition & Concurrency validations
        if review.status == ReviewState.IN_REVIEW:
            if review.reviewer_id == request.reviewer_id:
                # Idempotent re-claim by same active reviewer
                return review
            raise ReviewConflictException(
                f"Review item '{review_id}' is already claimed by reviewer '{review.reviewer_id}'"
            )

        if review.status == ReviewState.REVIEWED:
            raise InvalidStateTransitionException(
                f"Cannot claim review '{review_id}' because it has already been completed (REVIEWED). "
                "Reopen the review before re-claiming."
            )

        if review.status != ReviewState.PENDING:
            raise InvalidStateTransitionException(
                f"Invalid state transition from '{review.status.value}' to 'IN_REVIEW'"
            )

        before_state = {
            "status": review.status.value,
            "reviewer_id": review.reviewer_id,
            "reviewer_role": review.reviewer_role,
        }

        # Apply transition
        now = datetime.now(timezone.utc)
        review.status = ReviewState.IN_REVIEW
        review.reviewer_id = request.reviewer_id
        review.reviewer_role = request.reviewer_role
        review.started_at = now
        review.updated_at = now
        review.version += 1

        after_state = {
            "status": ReviewState.IN_REVIEW.value,
            "reviewer_id": request.reviewer_id,
            "reviewer_role": request.reviewer_role,
            "started_at": now.isoformat(),
        }

        audit_event = ReviewAuditEvent(
            id=uuid.uuid4(),
            review_id=review.id,
            actor_id=request.reviewer_id,
            actor_role=request.reviewer_role,
            event_type=ReviewAuditEventType.REVIEW_CLAIMED,
            before_state=before_state,
            after_state=after_state,
            changed_fields=["status", "reviewer_id", "reviewer_role", "started_at"],
            rationale=f"Review claimed by HSE officer {request.reviewer_id}",
            created_at=now,
        )
        self.session.add(audit_event)
        await self.session.flush()
        return review

    async def submit_decision(
        self,
        review_id: uuid.UUID,
        request: ReviewDecisionRequest,
    ) -> TriageReview:
        """Submit an authoritative HSE review decision, corrections, and feedback."""
        review = await self.get_review_by_id(review_id)
        if not review:
            raise ReviewNotFoundException(f"Triage review item with ID '{review_id}' not found")

        # Concurrency check
        if review.status == ReviewState.IN_REVIEW and review.reviewer_id and review.reviewer_id != request.reviewer_id:
            raise ReviewConflictException(
                f"Review item '{review_id}' is locked by reviewer '{review.reviewer_id}'"
            )

        # Idempotency check for already reviewed items
        if review.status == ReviewState.REVIEWED:
            if (
                review.decision == request.decision
                and review.reviewer_id == request.reviewer_id
                and (request.final_classification is None or review.final_classification == request.final_classification)
                and (request.final_lsr_code is None or review.final_lsr_code == request.final_lsr_code)
            ):
                return review
            raise InvalidStateTransitionException(
                f"Review item '{review_id}' is already REVIEWED. Reopen the review before submitting modifications."
            )

        # Compute final classification and fields
        if request.decision == ReviewDecision.CONFIRM_AI:
            final_class = request.final_classification or review.original_classification
            final_lsr = request.final_lsr_code or review.original_lsr_code
            if request.final_structured_precursor:
                merged_prec = dict(review.original_structured_precursor or {})
                merged_prec.update(request.final_structured_precursor.model_dump(exclude_unset=True, exclude_none=True))
                final_prec = merged_prec
            else:
                final_prec = review.original_structured_precursor
        else:
            final_class = request.final_classification or review.final_classification or review.original_classification
            final_lsr = request.final_lsr_code or review.final_lsr_code or review.original_lsr_code
            if request.final_structured_precursor:
                merged_prec = dict(review.original_structured_precursor or {})
                merged_prec.update(request.final_structured_precursor.model_dump(exclude_unset=True, exclude_none=True))
                final_prec = merged_prec
            else:
                final_prec = review.final_structured_precursor or review.original_structured_precursor

        # Validate mandatory rationale when overriding or correcting
        is_classification_corrected = (final_class != review.original_classification)
        is_lsr_corrected = (final_lsr != review.original_lsr_code)
        is_precursor_corrected = (final_prec != review.original_structured_precursor)
        is_override = request.decision in (ReviewDecision.CORRECT, ReviewDecision.REJECT_AI, ReviewDecision.MARK_UNDETERMINED)

        if (is_classification_corrected or is_lsr_corrected or is_precursor_corrected or is_override):
            if not request.reviewer_rationale or not request.reviewer_rationale.strip():
                raise ReviewRationaleRequiredException(
                    "Reviewer rationale is mandatory when correcting, rejecting, or overriding AI assessments."
                )

        now = datetime.now(timezone.utc)
        before_state = {
            "status": review.status.value,
            "decision": review.decision.value if review.decision else None,
            "final_classification": review.final_classification.value if review.final_classification else None,
            "final_lsr_code": review.final_lsr_code,
        }

        # Apply review changes
        review.status = ReviewState.REVIEWED
        review.decision = request.decision
        review.reviewer_id = request.reviewer_id
        review.reviewer_role = request.reviewer_role or review.reviewer_role
        review.final_classification = final_class
        review.final_lsr_code = final_lsr
        review.final_structured_precursor = final_prec
        review.reviewer_rationale = request.reviewer_rationale
        review.reviewer_notes = request.reviewer_notes
        review.completed_at = now
        if not review.started_at:
            review.started_at = now
        review.updated_at = now
        review.version += 1

        if request.feedback:
            review.feedback_category = request.feedback.category
            review.feedback_details = request.feedback.model_dump()

        # Update SIFAssessment triage_status preserving original AI scores and classification
        if review.assessment:
            if request.decision == ReviewDecision.CONFIRM_AI:
                review.assessment.triage_status = TriageStatus.VALIDATED
            else:
                review.assessment.triage_status = TriageStatus.OVERRIDDEN

        after_state = {
            "status": ReviewState.REVIEWED.value,
            "decision": request.decision.value,
            "final_classification": final_class.value,
            "final_lsr_code": final_lsr,
            "completed_at": now.isoformat(),
        }

        # Append audit events
        submitted_event = ReviewAuditEvent(
            id=uuid.uuid4(),
            review_id=review.id,
            actor_id=request.reviewer_id,
            actor_role=request.reviewer_role,
            event_type=ReviewAuditEventType.REVIEW_SUBMITTED,
            before_state=before_state,
            after_state=after_state,
            changed_fields=["status", "decision", "completed_at"],
            rationale=request.reviewer_rationale,
            created_at=now,
        )
        self.session.add(submitted_event)

        if is_classification_corrected:
            self.session.add(
                ReviewAuditEvent(
                    id=uuid.uuid4(),
                    review_id=review.id,
                    actor_id=request.reviewer_id,
                    actor_role=request.reviewer_role,
                    event_type=ReviewAuditEventType.CLASSIFICATION_CORRECTED,
                    before_state={"classification": review.original_classification.value},
                    after_state={"classification": final_class.value},
                    changed_fields=["final_classification"],
                    rationale=request.reviewer_rationale,
                    created_at=now,
                )
            )

        if is_lsr_corrected:
            self.session.add(
                ReviewAuditEvent(
                    id=uuid.uuid4(),
                    review_id=review.id,
                    actor_id=request.reviewer_id,
                    actor_role=request.reviewer_role,
                    event_type=ReviewAuditEventType.LSR_CORRECTED,
                    before_state={"lsr_code": review.original_lsr_code},
                    after_state={"lsr_code": final_lsr},
                    changed_fields=["final_lsr_code"],
                    rationale=request.reviewer_rationale,
                    created_at=now,
                )
            )

        if is_precursor_corrected:
            self.session.add(
                ReviewAuditEvent(
                    id=uuid.uuid4(),
                    review_id=review.id,
                    actor_id=request.reviewer_id,
                    actor_role=request.reviewer_role,
                    event_type=ReviewAuditEventType.PRECURSOR_CORRECTED,
                    before_state={"structured_precursor": review.original_structured_precursor},
                    after_state={"structured_precursor": final_prec},
                    changed_fields=["final_structured_precursor"],
                    rationale=request.reviewer_rationale,
                    created_at=now,
                )
            )

        if is_override:
            self.session.add(
                ReviewAuditEvent(
                    id=uuid.uuid4(),
                    review_id=review.id,
                    actor_id=request.reviewer_id,
                    actor_role=request.reviewer_role,
                    event_type=ReviewAuditEventType.AUDITOR_OVERRIDE,
                    before_state={"decision": None},
                    after_state={"decision": request.decision.value},
                    changed_fields=["decision"],
                    rationale=request.reviewer_rationale,
                    created_at=now,
                )
            )

        await self.session.flush()
        return review

    async def reopen_review(
        self,
        review_id: uuid.UUID,
        request: ReviewReopenRequest,
    ) -> TriageReview:
        """Reopen a completed review, transitioning REVIEWED -> IN_REVIEW."""
        review = await self.get_review_by_id(review_id)
        if not review:
            raise ReviewNotFoundException(f"Triage review item with ID '{review_id}' not found")

        if review.status != ReviewState.REVIEWED:
            raise InvalidStateTransitionException(
                f"Cannot reopen review '{review_id}' because its status is '{review.status.value}'. "
                "Only REVIEWED items can be reopened."
            )

        if not request.reopen_rationale or not request.reopen_rationale.strip():
            raise ReviewRationaleRequiredException("Mandatory reopen rationale is required when reopening a review.")

        now = datetime.now(timezone.utc)
        before_state = {
            "status": review.status.value,
            "decision": review.decision.value if review.decision else None,
            "completed_at": review.completed_at.isoformat() if review.completed_at else None,
        }

        review.status = ReviewState.IN_REVIEW
        review.completed_at = None
        review.reviewer_id = request.reviewer_id
        review.reviewer_role = request.reviewer_role or review.reviewer_role
        review.updated_at = now
        review.version += 1

        if review.assessment:
            review.assessment.triage_status = TriageStatus.PENDING_REVIEW

        after_state = {
            "status": ReviewState.IN_REVIEW.value,
            "reviewer_id": request.reviewer_id,
        }

        audit_event = ReviewAuditEvent(
            id=uuid.uuid4(),
            review_id=review.id,
            actor_id=request.reviewer_id,
            actor_role=request.reviewer_role,
            event_type=ReviewAuditEventType.REVIEW_REOPENED,
            before_state=before_state,
            after_state=after_state,
            changed_fields=["status", "completed_at", "reviewer_id"],
            rationale=request.reopen_rationale,
            created_at=now,
        )
        self.session.add(audit_event)
        await self.session.flush()
        return review

    async def get_review_history(self, review_id: uuid.UUID) -> List[ReviewAuditEvent]:
        """Fetch complete chronological append-only audit trail for a review."""
        review = await self.get_review_by_id(review_id)
        if not review:
            raise ReviewNotFoundException(f"Triage review item with ID '{review_id}' not found")

        stmt = (
            select(ReviewAuditEvent)
            .where(ReviewAuditEvent.review_id == review_id)
            .order_by(ReviewAuditEvent.created_at.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_triage_queue(
        self,
        status: Optional[ReviewState] = None,
        classification: Optional[SIFClassification] = None,
        location: Optional[str] = None,
        life_saving_rule: Optional[str] = None,
        batch_id: Optional[uuid.UUID] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[TriageReview], int]:
        """Deterministic triage queue listing with multi-attribute filtering and pagination."""
        query = (
            select(TriageReview)
            .join(SafetyReport, TriageReview.report_id == SafetyReport.id)
            .options(
                selectinload(TriageReview.report),
                selectinload(TriageReview.assessment),
                selectinload(TriageReview.audit_events),
            )
        )

        filters = []
        if status:
            filters.append(TriageReview.status == status)
        if classification:
            filters.append(
                or_(
                    TriageReview.final_classification == classification,
                    TriageReview.original_classification == classification,
                )
            )
        if location:
            filters.append(SafetyReport.reported_location.ilike(f"%{location}%"))
        if life_saving_rule:
            filters.append(
                or_(
                    TriageReview.final_lsr_code == life_saving_rule,
                    TriageReview.original_lsr_code == life_saving_rule,
                )
            )
        if batch_id:
            filters.append(SafetyReport.batch_id == batch_id)
        if date_from:
            filters.append(
                or_(
                    SafetyReport.event_timestamp >= date_from,
                    TriageReview.created_at >= date_from,
                )
            )
        if date_to:
            filters.append(
                or_(
                    SafetyReport.event_timestamp <= date_to,
                    TriageReview.created_at <= date_to,
                )
            )

        if filters:
            query = query.where(*filters)

        # Count total matching records
        count_query = (
            select(func.count(TriageReview.id))
            .join(SafetyReport, TriageReview.report_id == SafetyReport.id)
        )
        if filters:
            count_query = count_query.where(*filters)

        total_res = await self.session.execute(count_query)
        total_count = total_res.scalar_one()

        # Deterministic ordering
        query = query.order_by(TriageReview.created_at.desc(), TriageReview.id.asc())
        offset = max(0, (page - 1) * page_size)
        query = query.offset(offset).limit(page_size)

        res = await self.session.execute(query)
        items = list(res.scalars().all())
        return items, total_count

    async def get_analytics_summary(self) -> ReviewAnalyticsSummary:
        """Compute descriptive audit statistics of HSE human-in-the-loop review actions."""
        # Total counts by status
        status_stmt = select(TriageReview.status, func.count(TriageReview.id)).group_by(TriageReview.status)
        status_res = await self.session.execute(status_stmt)
        status_map = {row[0]: row[1] for row in status_res.all()}

        pending_count = status_map.get(ReviewState.PENDING, 0)
        in_review_count = status_map.get(ReviewState.IN_REVIEW, 0)
        reviewed_count = status_map.get(ReviewState.REVIEWED, 0)
        total_reviews = pending_count + in_review_count + reviewed_count

        # Total counts by decision
        decision_stmt = select(TriageReview.decision, func.count(TriageReview.id)).where(TriageReview.decision.is_not(None)).group_by(TriageReview.decision)
        decision_res = await self.session.execute(decision_stmt)
        decision_map = {row[0]: row[1] for row in decision_res.all()}

        confirmations_count = decision_map.get(ReviewDecision.CONFIRM_AI, 0)
        corrections_count = decision_map.get(ReviewDecision.CORRECT, 0)
        rejections_count = decision_map.get(ReviewDecision.REJECT_AI, 0)
        undetermined_count = decision_map.get(ReviewDecision.MARK_UNDETERMINED, 0)

        # Classification corrections count
        class_corr_stmt = select(func.count(TriageReview.id)).where(
            TriageReview.status == ReviewState.REVIEWED,
            TriageReview.final_classification != TriageReview.original_classification,
        )
        class_corr_res = await self.session.execute(class_corr_stmt)
        classification_corrections_count = class_corr_res.scalar_one()

        # LSR corrections count
        lsr_corr_stmt = select(func.count(TriageReview.id)).where(
            TriageReview.status == ReviewState.REVIEWED,
            TriageReview.final_lsr_code != TriageReview.original_lsr_code,
        )
        lsr_corr_res = await self.session.execute(lsr_corr_stmt)
        lsr_corrections_count = lsr_corr_res.scalar_one()

        # Precursor corrections count (via audit events)
        prec_corr_stmt = select(func.count(func.distinct(ReviewAuditEvent.review_id))).where(
            ReviewAuditEvent.event_type == ReviewAuditEventType.PRECURSOR_CORRECTED
        )
        prec_corr_res = await self.session.execute(prec_corr_stmt)
        precursor_corrections_count = prec_corr_res.scalar_one()

        # Feedback breakdown
        fb_stmt = select(TriageReview.feedback_category, func.count(TriageReview.id)).where(TriageReview.feedback_category.is_not(None)).group_by(TriageReview.feedback_category)
        fb_res = await self.session.execute(fb_stmt)
        feedback_breakdown = {row[0].value: row[1] for row in fb_res.all() if row[0]}

        return ReviewAnalyticsSummary(
            total_reviews=total_reviews,
            pending_count=pending_count,
            in_review_count=in_review_count,
            reviewed_count=reviewed_count,
            confirmations_count=confirmations_count,
            corrections_count=corrections_count,
            rejections_count=rejections_count,
            undetermined_count=undetermined_count,
            classification_corrections_count=classification_corrections_count,
            lsr_corrections_count=lsr_corrections_count,
            precursor_corrections_count=precursor_corrections_count,
            feedback_breakdown=feedback_breakdown,
        )

    # Legacy method for backward compatibility
    async def record_review(
        self,
        report_id: uuid.UUID,
        review_in: HumanReviewRequest,
    ) -> TriageReview:
        """Persist auditor review (legacy backward-compatible method)."""
        # Check if review exists for report
        stmt = (
            select(TriageReview)
            .where(TriageReview.report_id == report_id)
            .options(selectinload(TriageReview.audit_events))
        )
        res = await self.session.execute(stmt)
        review = res.scalars().first()

        decision = ReviewDecision.CONFIRM_AI if review_in.review_status == ReviewStatus.VALIDATED else ReviewDecision.CORRECT

        if not review:
            # Query report to find assessment if available
            rep_stmt = select(SafetyReport).where(SafetyReport.id == report_id).options(selectinload(SafetyReport.assessment))
            rep_res = await self.session.execute(rep_stmt)
            rep = rep_res.scalars().first()
            if not rep:
                raise ReportNotFoundException(f"Safety report '{report_id}' not found")

            assessment_id = rep.assessment.id if rep.assessment else None
            orig_class = rep.assessment.sif_classification if rep.assessment else review_in.verified_sif_classification
            orig_prec = rep.assessment.structured_precursor if rep.assessment else None

            review = TriageReview(
                id=uuid.uuid4(),
                report_id=report_id,
                assessment_id=assessment_id,
                status=ReviewState.REVIEWED,
                decision=decision,
                reviewer_id=review_in.reviewer_id,
                reviewer_role="HSE_AUDITOR",
                original_classification=orig_class,
                final_classification=review_in.verified_sif_classification,
                original_structured_precursor=orig_prec,
                final_structured_precursor=orig_prec,
                original_lsr_code=review_in.verified_life_saving_rule,
                final_lsr_code=review_in.verified_life_saving_rule,
                reviewer_rationale=review_in.override_reason,
                reviewer_notes=review_in.reviewer_notes,
                completed_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            self.session.add(review)
        else:
            review.status = ReviewState.REVIEWED
            review.decision = decision
            review.reviewer_id = review_in.reviewer_id
            review.final_classification = review_in.verified_sif_classification
            review.final_lsr_code = review_in.verified_life_saving_rule
            review.reviewer_rationale = review_in.override_reason
            review.reviewer_notes = review_in.reviewer_notes
            review.completed_at = datetime.now(timezone.utc)
            review.version += 1

        self.session.add(
            ReviewAuditEvent(
                id=uuid.uuid4(),
                review_id=review.id,
                actor_id=review_in.reviewer_id,
                actor_role="HSE_AUDITOR",
                event_type=ReviewAuditEventType.REVIEW_SUBMITTED,
                before_state=None,
                after_state={"status": "REVIEWED", "classification": review_in.verified_sif_classification.value},
                changed_fields=["status", "final_classification"],
                rationale=review_in.override_reason,
                created_at=datetime.now(timezone.utc),
            )
        )
        await self.session.flush()
        return review
