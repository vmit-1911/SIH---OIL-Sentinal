"""Application service for managing HSE cases, investigations, source links, and audit timelines."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import (
    ActionNotFoundException,
    AssessmentNotFoundException,
    CaseClosureBlockedException,
    CaseNotFoundException,
    CaseSourceNotFoundException,
    ConcentrationNotFoundException,
    DuplicateSourceAssociationException,
    InvalidStateTransitionException,
    PatternNotFoundException,
    ReportNotFoundException,
    ReviewNotFoundException,
)
from app.core.logging import get_logger
from app.db.models.action import HSEActionRecommendation
from app.db.models.assessment import SIFAssessment
from app.db.models.case import HSECase, HSECaseEvent, HSECaseSourceAssociation
from app.db.models.concentration import RiskConcentration
from app.db.models.pattern import PrecursorPattern
from app.db.models.report import SafetyReport
from app.db.models.review import TriageReview
from app.domain.enums import (
    ActionStatus,
    CaseEventType,
    CasePriority,
    CaseSourceType,
    CaseStatus,
    CaseType,
)
from app.schemas.case import (
    CaseListResponse,
    HSECaseAssignRequest,
    HSECaseCreateRequest,
    HSECaseDTO,
    HSECaseEventDTO,
    HSECaseReopenRequest,
    HSECaseSourceAttachRequest,
    HSECaseSourceDTO,
    HSECaseStatusUpdateRequest,
    HSECaseSummaryDTO,
    HSECaseUpdateRequest,
)

logger = get_logger(__name__)


class HSECaseManagementService:
    """Orchestrates deterministic HSE case lifecycle, source associations, and audit trail."""

    ALLOWED_TRANSITIONS: Dict[CaseStatus, List[CaseStatus]] = {
        CaseStatus.OPEN: [CaseStatus.TRIAGE, CaseStatus.INVESTIGATING, CaseStatus.CANCELLED],
        CaseStatus.TRIAGE: [CaseStatus.INVESTIGATING, CaseStatus.ACTION_REQUIRED, CaseStatus.CANCELLED],
        CaseStatus.INVESTIGATING: [
            CaseStatus.ACTION_REQUIRED,
            CaseStatus.PENDING_VERIFICATION,
            CaseStatus.CLOSED,
            CaseStatus.CANCELLED,
        ],
        CaseStatus.ACTION_REQUIRED: [
            CaseStatus.PENDING_VERIFICATION,
            CaseStatus.INVESTIGATING,
            CaseStatus.CLOSED,
            CaseStatus.CANCELLED,
        ],
        CaseStatus.PENDING_VERIFICATION: [
            CaseStatus.CLOSED,
            CaseStatus.INVESTIGATING,
            CaseStatus.ACTION_REQUIRED,
            CaseStatus.CANCELLED,
        ],
        CaseStatus.CLOSED: [CaseStatus.INVESTIGATING],
        CaseStatus.CANCELLED: [],  # CANCELLED remains strictly terminal
    }

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _to_source_dto(m: HSECaseSourceAssociation) -> HSECaseSourceDTO:
        return HSECaseSourceDTO(
            id=m.id,
            case_id=m.case_id,
            source_type=m.source_type,
            source_id=m.source_id,
            source_metadata=m.source_metadata or {},
            attached_by=m.attached_by,
            attached_at=m.attached_at,
        )

    @staticmethod
    def _to_event_dto(m: HSECaseEvent) -> HSECaseEventDTO:
        return HSECaseEventDTO(
            id=m.id,
            case_id=m.case_id,
            event_type=m.event_type,
            actor_id=m.actor_id,
            before_state=m.before_state,
            after_state=m.after_state,
            source_reference=m.source_reference,
            rationale=m.rationale,
            created_at=m.created_at,
        )

    def _to_case_dto(self, m: HSECase, sources: Optional[List[HSECaseSourceAssociation]] = None) -> HSECaseDTO:
        if sources is None:
            sources = m.__dict__.get("sources") or []
        return HSECaseDTO(
            id=m.id,
            case_key=m.case_key,
            title=m.title,
            description=m.description,
            case_type=m.case_type,
            status=m.status,
            priority=m.priority,
            owner=m.owner,
            created_by=m.created_by,
            assigned_at=m.assigned_at,
            opened_at=m.opened_at,
            closed_at=m.closed_at,
            closure_rationale=m.closure_rationale,
            created_at=m.created_at,
            updated_at=m.updated_at,
            sources=[self._to_source_dto(s) for s in sources],
        )

    async def _fetch_sources_for_case(self, case_id: uuid.UUID) -> List[HSECaseSourceAssociation]:
        stmt = (
            select(HSECaseSourceAssociation)
            .where(HSECaseSourceAssociation.case_id == case_id)
            .order_by(HSECaseSourceAssociation.attached_at.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def _validate_source_existence(self, source_type: CaseSourceType, source_id: str) -> None:
        """Validate deterministically that the referenced polymorphic source entity exists in the database."""
        sid = str(source_id).strip()
        if source_type == CaseSourceType.REPORT:
            try:
                uid = uuid.UUID(sid)
                stmt = select(SafetyReport).where((SafetyReport.id == uid) | (SafetyReport.report_ref == sid))
            except ValueError:
                stmt = select(SafetyReport).where(SafetyReport.report_ref == sid)
            res = await self.session.execute(stmt)
            if not res.scalar_one_or_none():
                raise ReportNotFoundException(f"Referenced safety report '{sid}' does not exist.")

        elif source_type == CaseSourceType.ASSESSMENT:
            try:
                uid = uuid.UUID(sid)
                stmt = select(SIFAssessment).where(SIFAssessment.id == uid)
            except ValueError:
                raise AssessmentNotFoundException(f"Referenced SIF assessment ID '{sid}' is not a valid UUID.")
            res = await self.session.execute(stmt)
            if not res.scalar_one_or_none():
                raise AssessmentNotFoundException(f"Referenced SIF assessment '{sid}' does not exist.")

        elif source_type == CaseSourceType.PATTERN:
            try:
                uid = uuid.UUID(sid)
                stmt = select(PrecursorPattern).where((PrecursorPattern.id == uid) | (PrecursorPattern.pattern_code == sid))
            except ValueError:
                stmt = select(PrecursorPattern).where(PrecursorPattern.pattern_code == sid)
            res = await self.session.execute(stmt)
            if not res.scalar_one_or_none():
                raise PatternNotFoundException(f"Referenced precursor pattern '{sid}' does not exist.")

        elif source_type == CaseSourceType.CONCENTRATION:
            try:
                uid = uuid.UUID(sid)
                stmt = select(RiskConcentration).where((RiskConcentration.id == uid) | (RiskConcentration.concentration_key == sid))
            except ValueError:
                stmt = select(RiskConcentration).where(RiskConcentration.concentration_key == sid)
            res = await self.session.execute(stmt)
            if not res.scalar_one_or_none():
                raise ConcentrationNotFoundException(f"Referenced risk concentration '{sid}' does not exist.")

        elif source_type == CaseSourceType.REVIEW:
            try:
                uid = uuid.UUID(sid)
                stmt = select(TriageReview).where(TriageReview.id == uid)
            except ValueError:
                raise ReviewNotFoundException(f"Referenced triage review ID '{sid}' is not a valid UUID.")
            res = await self.session.execute(stmt)
            if not res.scalar_one_or_none():
                raise ReviewNotFoundException(f"Referenced triage review '{sid}' does not exist.")

        elif source_type == CaseSourceType.ACTION:
            try:
                uid = uuid.UUID(sid)
                stmt = select(HSEActionRecommendation).where((HSEActionRecommendation.id == uid) | (HSEActionRecommendation.action_key == sid))
            except ValueError:
                stmt = select(HSEActionRecommendation).where(HSEActionRecommendation.action_key == sid)
            res = await self.session.execute(stmt)
            if not res.scalar_one_or_none():
                raise ActionNotFoundException(f"Referenced action recommendation '{sid}' does not exist.")

        else:
            raise InvalidStateTransitionException(f"Unsupported source type: '{source_type}'.")

    async def create_case(self, request: HSECaseCreateRequest) -> HSECaseDTO:
        """Create an HSE case with optional idempotency, initial sources, and audit event."""
        target_key = request.idempotency_key
        if target_key:
            stmt = select(HSECase).where(HSECase.case_key == target_key)
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                if existing.title != request.title or existing.case_type != request.case_type:
                    raise DuplicateSourceAssociationException(
                        f"Idempotency key '{target_key}' conflicts with an existing case of different title/type."
                    )
                logger.info(f"Returning existing HSE case with key '{target_key}' (idempotency hit)")
                sources = await self._fetch_sources_for_case(existing.id)
                return self._to_case_dto(existing, sources=sources)

        # Validate existence of all initial sources before persisting case
        for src in (request.sources or []):
            await self._validate_source_existence(src.source_type, str(src.source_id))

        case_key = target_key or f"CASE-{uuid.uuid4().hex[:12].upper()}"
        now = datetime.now(timezone.utc)

        case = HSECase(
            case_key=case_key,
            title=request.title,
            description=request.description,
            case_type=request.case_type,
            status=CaseStatus.OPEN,
            priority=request.priority,
            owner=request.owner,
            created_by=request.created_by,
            assigned_at=now if request.owner else None,
            opened_at=now,
            created_at=now,
            updated_at=now,
        )
        self.session.add(case)
        await self.session.flush()

        # 2. Append creation audit event
        created_event = HSECaseEvent(
            case_id=case.id,
            event_type=CaseEventType.CASE_CREATED,
            actor_id=request.created_by,
            before_state=None,
            after_state={
                "case_key": case.case_key,
                "title": case.title,
                "case_type": case.case_type.value,
                "status": case.status.value,
                "priority": case.priority.value,
                "owner": case.owner,
            },
            rationale=f"HSE Case created by {request.created_by}",
            created_at=now,
        )
        self.session.add(created_event)

        # 3. Attach initial sources
        attached_keys = set()
        for src in (request.sources or []):
            combo = (src.source_type, str(src.source_id))
            if combo in attached_keys:
                continue
            attached_keys.add(combo)

            assoc = HSECaseSourceAssociation(
                case_id=case.id,
                source_type=src.source_type,
                source_id=str(src.source_id),
                source_metadata=src.source_metadata or {},
                attached_by=request.created_by,
                attached_at=now,
            )
            self.session.add(assoc)

            event_type = CaseEventType.SOURCE_ATTACHED
            if src.source_type == CaseSourceType.ACTION:
                event_type = CaseEventType.ACTION_ATTACHED
            elif src.source_type == CaseSourceType.REVIEW:
                event_type = CaseEventType.REVIEW_ATTACHED

            src_event = HSECaseEvent(
                case_id=case.id,
                event_type=event_type,
                actor_id=request.created_by,
                source_reference={
                    "source_type": src.source_type.value,
                    "source_id": str(src.source_id),
                    "metadata": src.source_metadata or {},
                },
                rationale=f"Initial source {src.source_type.value}:{src.source_id} attached upon case creation",
                created_at=now,
            )
            self.session.add(src_event)

        await self.session.commit()
        return await self.get_case(case.id)

    async def get_case(self, case_id: uuid.UUID) -> HSECaseDTO:
        """Fetch HSE case by UUID."""
        stmt = select(HSECase).where(HSECase.id == case_id)
        result = await self.session.execute(stmt)
        case = result.scalar_one_or_none()
        if not case:
            raise CaseNotFoundException(f"HSE Case with ID '{case_id}' was not found.")
        sources = await self._fetch_sources_for_case(case.id)
        return self._to_case_dto(case, sources=sources)

    async def get_case_by_key(self, case_key: str) -> HSECaseDTO:
        """Fetch HSE case by stable case key."""
        stmt = select(HSECase).where(HSECase.case_key == case_key)
        result = await self.session.execute(stmt)
        case = result.scalar_one_or_none()
        if not case:
            raise CaseNotFoundException(f"HSE Case with key '{case_key}' was not found.")
        sources = await self._fetch_sources_for_case(case.id)
        return self._to_case_dto(case, sources=sources)

    async def update_case(self, case_id: uuid.UUID, request: HSECaseUpdateRequest) -> HSECaseDTO:
        """Update mutable metadata of an HSE case."""
        stmt = select(HSECase).where(HSECase.id == case_id)
        result = await self.session.execute(stmt)
        case = result.scalar_one_or_none()
        if not case:
            raise CaseNotFoundException(f"HSE Case with ID '{case_id}' was not found.")

        now = datetime.now(timezone.utc)
        if request.title is not None:
            case.title = request.title
        if request.description is not None:
            case.description = request.description
        if request.priority is not None:
            case.priority = request.priority

        case.updated_at = now
        await self.session.commit()
        sources = await self._fetch_sources_for_case(case.id)
        return self._to_case_dto(case, sources=sources)

    async def assign_case(self, case_id: uuid.UUID, request: HSECaseAssignRequest) -> HSECaseDTO:
        """Assign an HSE case to a responsible investigator or owner."""
        stmt = select(HSECase).where(HSECase.id == case_id)
        result = await self.session.execute(stmt)
        case = result.scalar_one_or_none()
        if not case:
            raise CaseNotFoundException(f"HSE Case with ID '{case_id}' was not found.")

        now = datetime.now(timezone.utc)
        before_owner = case.owner
        case.owner = request.owner
        case.assigned_at = now
        case.updated_at = now

        assign_event = HSECaseEvent(
            case_id=case.id,
            event_type=CaseEventType.CASE_ASSIGNED,
            actor_id=request.actor_id,
            before_state={"owner": before_owner},
            after_state={"owner": request.owner},
            rationale=request.rationale or f"Case assigned to '{request.owner}'",
            created_at=now,
        )
        self.session.add(assign_event)
        await self.session.commit()
        sources = await self._fetch_sources_for_case(case.id)
        return self._to_case_dto(case, sources=sources)

    async def update_case_status(
        self,
        case_id: uuid.UUID,
        request: HSECaseStatusUpdateRequest,
        require_actions_resolved: Optional[bool] = None,
    ) -> HSECaseDTO:
        """Transition the operational lifecycle status of an HSE case."""
        if require_actions_resolved is None:
            require_actions_resolved = get_settings().CASE_CLOSURE_REQUIRES_ACTION_RESOLUTION

        stmt = select(HSECase).where(HSECase.id == case_id)
        result = await self.session.execute(stmt)
        case = result.scalar_one_or_none()
        if not case:
            raise CaseNotFoundException(f"HSE Case with ID '{case_id}' was not found.")

        if request.status == case.status:
            sources = await self._fetch_sources_for_case(case.id)
            return self._to_case_dto(case, sources=sources)

        allowed = self.ALLOWED_TRANSITIONS.get(case.status, [])
        if request.status not in allowed:
            raise InvalidStateTransitionException(
                f"Invalid case lifecycle transition from '{case.status.value}' to '{request.status.value}'. "
                f"Allowed target states: {[s.value for s in allowed]}."
            )

        now = datetime.now(timezone.utc)
        before_status = case.status

        # Closure validation
        if request.status == CaseStatus.CLOSED:
            if not request.rationale or not request.rationale.strip():
                raise CaseClosureBlockedException("Case closure requires an explicit closure rationale.")

            if require_actions_resolved:
                sources = await self._fetch_sources_for_case(case.id)
                action_sources = [s for s in sources if s.source_type == CaseSourceType.ACTION]
                if action_sources:
                    action_ids_or_keys = [s.source_id for s in action_sources]
                    action_uuids = []
                    action_keys = []
                    for ak in action_ids_or_keys:
                        try:
                            action_uuids.append(uuid.UUID(ak))
                        except ValueError:
                            action_keys.append(ak)

                    act_stmt = select(HSEActionRecommendation).where(
                        (HSEActionRecommendation.id.in_(action_uuids)) | (HSEActionRecommendation.action_key.in_(action_keys))
                    )
                    act_res = await self.session.execute(act_stmt)
                    actions = act_res.scalars().all()
                    unresolved = [
                        a for a in actions
                        if a.status in (ActionStatus.OPEN, ActionStatus.ACKNOWLEDGED, ActionStatus.IN_PROGRESS)
                    ]
                    if unresolved:
                        raise CaseClosureBlockedException(
                            f"Cannot close case: {len(unresolved)} attached HSE action(s) remain unresolved "
                            f"(must be COMPLETED or DISMISSED as configured by application closure policy)."
                        )

            case.closed_at = now
            case.closure_rationale = request.rationale.strip()
            event_type = CaseEventType.CASE_CLOSED

        elif request.status == CaseStatus.CANCELLED:
            if not request.rationale or not request.rationale.strip():
                raise CaseClosureBlockedException("Case cancellation requires an explicit cancellation rationale.")
            case.closed_at = now
            case.closure_rationale = request.rationale.strip()
            event_type = CaseEventType.CASE_CANCELLED

        else:
            event_type = CaseEventType.CASE_STATUS_CHANGED

        case.status = request.status
        case.updated_at = now

        status_event = HSECaseEvent(
            case_id=case.id,
            event_type=event_type,
            actor_id=request.actor_id,
            before_state={"status": before_status.value},
            after_state={"status": request.status.value},
            rationale=request.rationale,
            created_at=now,
        )
        self.session.add(status_event)
        await self.session.commit()
        sources = await self._fetch_sources_for_case(case.id)
        return self._to_case_dto(case, sources=sources)

    async def reopen_case(self, case_id: uuid.UUID, request: HSECaseReopenRequest) -> HSECaseDTO:
        """Reopen a previously CLOSED HSE case with mandatory rationale."""
        stmt = select(HSECase).where(HSECase.id == case_id)
        result = await self.session.execute(stmt)
        case = result.scalar_one_or_none()
        if not case:
            raise CaseNotFoundException(f"HSE Case with ID '{case_id}' was not found.")

        if case.status != CaseStatus.CLOSED:
            raise InvalidStateTransitionException(
                f"Cannot reopen case: only CLOSED cases can be reopened. Current status: '{case.status.value}'."
            )

        if not request.rationale or len(request.rationale.strip()) < 3:
            raise InvalidStateTransitionException("Reopening a case requires a valid rationale (minimum 3 characters).")

        now = datetime.now(timezone.utc)
        before_status = case.status
        before_closed_at = case.closed_at

        case.status = CaseStatus.INVESTIGATING
        case.closed_at = None
        case.closure_rationale = None
        case.updated_at = now

        reopen_event = HSECaseEvent(
            case_id=case.id,
            event_type=CaseEventType.CASE_REOPENED,
            actor_id=request.actor_id,
            before_state={
                "status": before_status.value,
                "closed_at": before_closed_at.isoformat() if before_closed_at else None,
            },
            after_state={
                "status": CaseStatus.INVESTIGATING.value,
                "closed_at": None,
            },
            rationale=request.rationale.strip(),
            created_at=now,
        )
        self.session.add(reopen_event)
        await self.session.commit()
        sources = await self._fetch_sources_for_case(case.id)
        return self._to_case_dto(case, sources=sources)

    async def attach_source(self, case_id: uuid.UUID, request: HSECaseSourceAttachRequest) -> HSECaseDTO:
        """Attach a source intelligence reference to an HSE case."""
        stmt = select(HSECase).where(HSECase.id == case_id)
        result = await self.session.execute(stmt)
        case = result.scalar_one_or_none()
        if not case:
            raise CaseNotFoundException(f"HSE Case with ID '{case_id}' was not found.")

        if case.status in (CaseStatus.CLOSED, CaseStatus.CANCELLED):
            raise InvalidStateTransitionException(
                f"Cannot attach sources to a case in terminal state '{case.status.value}'."
            )

        target_source_id = str(request.source_id).strip()
        await self._validate_source_existence(request.source_type, target_source_id)

        existing_sources = await self._fetch_sources_for_case(case.id)
        for existing_src in existing_sources:
            if existing_src.source_type == request.source_type and existing_src.source_id == target_source_id:
                raise DuplicateSourceAssociationException(
                    f"Source '{request.source_type.value}:{target_source_id}' is already attached to case '{case.case_key}'."
                )

        now = datetime.now(timezone.utc)
        assoc = HSECaseSourceAssociation(
            case_id=case.id,
            source_type=request.source_type,
            source_id=target_source_id,
            source_metadata=request.source_metadata or {},
            attached_by=request.actor_id,
            attached_at=now,
        )
        self.session.add(assoc)
        case.updated_at = now

        event_type = CaseEventType.SOURCE_ATTACHED
        if request.source_type == CaseSourceType.ACTION:
            event_type = CaseEventType.ACTION_ATTACHED
        elif request.source_type == CaseSourceType.REVIEW:
            event_type = CaseEventType.REVIEW_ATTACHED

        attach_event = HSECaseEvent(
            case_id=case.id,
            event_type=event_type,
            actor_id=request.actor_id,
            source_reference={
                "source_type": request.source_type.value,
                "source_id": target_source_id,
                "metadata": request.source_metadata or {},
            },
            rationale=f"Attached source {request.source_type.value}:{target_source_id}",
            created_at=now,
        )
        self.session.add(attach_event)
        await self.session.commit()
        return await self.get_case(case.id)

    async def detach_source(
        self,
        case_id: uuid.UUID,
        source_id_or_assoc_id: str,
        actor_id: str = "system_auditor",
        rationale: Optional[str] = None,
    ) -> HSECaseDTO:
        """Detach a source intelligence reference from an HSE case."""
        stmt = select(HSECase).where(HSECase.id == case_id)
        result = await self.session.execute(stmt)
        case = result.scalar_one_or_none()
        if not case:
            raise CaseNotFoundException(f"HSE Case with ID '{case_id}' was not found.")

        if case.status in (CaseStatus.CLOSED, CaseStatus.CANCELLED):
            raise InvalidStateTransitionException(
                f"Cannot detach sources from a case in terminal state '{case.status.value}'."
            )

        existing_sources = await self._fetch_sources_for_case(case.id)
        target = None
        target_str = str(source_id_or_assoc_id).strip()
        for src in existing_sources:
            if str(src.id) == target_str or src.source_id == target_str:
                target = src
                break

        if not target:
            raise CaseSourceNotFoundException(
                f"Source reference '{source_id_or_assoc_id}' was not found in case '{case.case_key}'."
            )

        now = datetime.now(timezone.utc)
        src_type = target.source_type
        src_id = target.source_id
        src_meta = target.source_metadata or {}

        await self.session.delete(target)
        case.updated_at = now

        event_type = CaseEventType.ACTION_DETACHED if src_type == CaseSourceType.ACTION else CaseEventType.SOURCE_DETACHED
        detach_event = HSECaseEvent(
            case_id=case.id,
            event_type=event_type,
            actor_id=actor_id,
            source_reference={
                "source_type": src_type.value,
                "source_id": src_id,
                "metadata": src_meta,
            },
            rationale=rationale or f"Detached source {src_type.value}:{src_id}",
            created_at=now,
        )
        self.session.add(detach_event)
        await self.session.commit()
        return await self.get_case(case.id)

    async def get_case_timeline(self, case_id: uuid.UUID) -> List[HSECaseEventDTO]:
        """Fetch chronologically ordered append-only audit events for a case."""
        stmt = select(HSECase).where(HSECase.id == case_id)
        result = await self.session.execute(stmt)
        case = result.scalar_one_or_none()
        if not case:
            raise CaseNotFoundException(f"HSE Case with ID '{case_id}' was not found.")

        event_stmt = select(HSECaseEvent).where(HSECaseEvent.case_id == case_id).order_by(HSECaseEvent.created_at.asc())
        event_res = await self.session.execute(event_stmt)
        events = event_res.scalars().all()
        return [self._to_event_dto(e) for e in events]

    async def get_case_summary(self, case_id: uuid.UUID) -> HSECaseSummaryDTO:
        """Calculate deterministic aggregate metrics and statistics for an HSE case."""
        stmt = select(HSECase).where(HSECase.id == case_id)
        result = await self.session.execute(stmt)
        case = result.scalar_one_or_none()
        if not case:
            raise CaseNotFoundException(f"HSE Case with ID '{case_id}' was not found.")

        sources = await self._fetch_sources_for_case(case.id)

        report_count = 0
        assessment_count = 0
        pattern_count = 0
        concentration_count = 0
        review_count = 0
        action_count = 0
        open_action_count = 0
        completed_action_count = 0
        evidence_count = 0

        action_ids_or_keys = []
        for src in sources:
            if src.source_type == CaseSourceType.REPORT:
                report_count += 1
            elif src.source_type == CaseSourceType.ASSESSMENT:
                assessment_count += 1
                evidence_count += 1
            elif src.source_type == CaseSourceType.PATTERN:
                pattern_count += 1
            elif src.source_type == CaseSourceType.CONCENTRATION:
                concentration_count += 1
            elif src.source_type == CaseSourceType.REVIEW:
                review_count += 1
            elif src.source_type == CaseSourceType.ACTION:
                action_count += 1
                action_ids_or_keys.append(src.source_id)

        if action_ids_or_keys:
            action_uuids = []
            action_keys = []
            for ak in action_ids_or_keys:
                try:
                    action_uuids.append(uuid.UUID(ak))
                except ValueError:
                    action_keys.append(ak)

            act_stmt = select(HSEActionRecommendation).where(
                (HSEActionRecommendation.id.in_(action_uuids)) | (HSEActionRecommendation.action_key.in_(action_keys))
            )
            act_res = await self.session.execute(act_stmt)
            actions = act_res.scalars().all()

            for a in actions:
                if a.status in (ActionStatus.OPEN, ActionStatus.ACKNOWLEDGED, ActionStatus.IN_PROGRESS):
                    open_action_count += 1
                elif a.status == ActionStatus.COMPLETED:
                    completed_action_count += 1

        return HSECaseSummaryDTO(
            case_id=case.id,
            case_key=case.case_key,
            title=case.title,
            case_type=case.case_type,
            status=case.status,
            priority=case.priority,
            owner=case.owner,
            report_count=report_count,
            assessment_count=assessment_count,
            pattern_count=pattern_count,
            concentration_count=concentration_count,
            review_count=review_count,
            action_count=action_count,
            open_action_count=open_action_count,
            completed_action_count=completed_action_count,
            evidence_count=evidence_count,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )

    async def list_cases(
        self,
        status: Optional[CaseStatus] = None,
        priority: Optional[CasePriority] = None,
        case_type: Optional[CaseType] = None,
        owner: Optional[str] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        updated_after: Optional[datetime] = None,
        updated_before: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> CaseListResponse:
        """Query and filter HSE cases with deterministic pagination."""
        query = select(HSECase)

        if status:
            query = query.where(HSECase.status == status)
        if priority:
            query = query.where(HSECase.priority == priority)
        if case_type:
            query = query.where(HSECase.case_type == case_type)
        if owner:
            query = query.where(HSECase.owner == owner)
        if created_after:
            query = query.where(HSECase.created_at >= created_after)
        if created_before:
            query = query.where(HSECase.created_at <= created_before)
        if updated_after:
            query = query.where(HSECase.updated_at >= updated_after)
        if updated_before:
            query = query.where(HSECase.updated_at <= updated_before)

        count_stmt = select(func.count()).select_from(query.subquery())
        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        offset = (page - 1) * page_size
        query = query.order_by(HSECase.created_at.desc()).offset(offset).limit(page_size)
        res = await self.session.execute(query)
        cases = list(res.scalars().all())

        case_ids = [c.id for c in cases]
        sources_by_case: Dict[uuid.UUID, List[HSECaseSourceAssociation]] = {cid: [] for cid in case_ids}
        if case_ids:
            src_stmt = (
                select(HSECaseSourceAssociation)
                .where(HSECaseSourceAssociation.case_id.in_(case_ids))
                .order_by(HSECaseSourceAssociation.attached_at.asc())
            )
            src_res = await self.session.execute(src_stmt)
            for s in src_res.scalars().all():
                sources_by_case[s.case_id].append(s)

        total_pages = max(1, (total + page_size - 1) // page_size)

        return CaseListResponse(
            total=total,
            items=[self._to_case_dto(c, sources=sources_by_case.get(c.id, [])) for c in cases],
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
