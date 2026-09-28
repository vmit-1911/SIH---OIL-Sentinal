"""Application service for generating, querying, and managing HSE Action Recommendations."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ActionNotFoundException,
    AssessmentNotFoundException,
    ConcentrationNotFoundException,
    InvalidStateTransitionException,
    PatternNotFoundException,
    ReportNotFoundException,
)
from app.core.logging import get_logger
from app.db.models.action import HSEActionRecommendation
from app.db.models.assessment import SIFAssessment
from app.db.models.concentration import RiskConcentration
from app.db.models.pattern import PrecursorPattern
from app.db.models.report import SafetyReport
from app.db.models.review import TriageReview
from app.db.models.taxonomy import LSRReportMapping
from app.domain.action.rule_engine import ActionRuleEngine
from app.domain.enums import (
    ActionCategory,
    ActionPriority,
    ActionSourceType,
    ActionStatus,
)
from app.schemas.action import (
    ActionAcknowledgeRequest,
    ActionGenerateResponse,
    ActionListResponse,
    ActionStatusUpdateRequest,
    HSEActionRecommendationDTO,
)

logger = get_logger(__name__)


class HSEActionRecommendationService:
    """Orchestrates deterministic HSE action generation, idempotency, and lifecycle management."""

    def __init__(
        self,
        session: AsyncSession,
        rule_engine: Optional[ActionRuleEngine] = None,
    ):
        self.session = session
        self.rule_engine = rule_engine or ActionRuleEngine()

    @staticmethod
    def _to_dto(m: HSEActionRecommendation) -> HSEActionRecommendationDTO:
        """Convert ORM model instance to Pydantic DTO."""
        return HSEActionRecommendationDTO(
            id=m.id,
            action_key=m.action_key,
            source_type=m.source_type,
            source_id=m.source_id,
            action_category=m.action_category,
            action_title=m.action_title,
            action_description=m.action_description,
            priority=m.priority,
            rationale=m.rationale,
            evidence_refs=m.evidence_refs or [],
            source_dimensions=m.source_dimensions or {},
            lsr_code=m.lsr_code,
            precursor_signature=m.precursor_signature,
            pattern_key=m.pattern_key,
            concentration_key=m.concentration_key,
            rule_id=m.rule_id,
            rule_version=m.rule_version,
            status=m.status,
            assigned_to=m.assigned_to,
            actor_id=m.actor_id,
            status_rationale=m.status_rationale,
            created_at=m.created_at,
            updated_at=m.updated_at,
            acknowledged_at=m.acknowledged_at,
            completed_at=m.completed_at,
            dismissed_at=m.dismissed_at,
        )

    async def _persist_actions(
        self,
        action_dicts: List[Dict[str, Any]],
        persist: bool = True,
    ) -> Tuple[List[HSEActionRecommendationDTO], int, int]:
        """Idempotently persist generated action dictionaries into the database."""
        if not action_dicts:
            return [], 0, 0

        dtos: List[HSEActionRecommendationDTO] = []
        new_count = 0
        existing_count = 0

        for item in action_dicts:
            action_key = item["action_key"]
            stmt = select(HSEActionRecommendation).where(HSEActionRecommendation.action_key == action_key)
            res = await self.session.execute(stmt)
            existing = res.scalar_one_or_none()

            if existing:
                existing_count += 1
                dtos.append(self._to_dto(existing))
            else:
                new_count += 1
                if persist:
                    new_model = HSEActionRecommendation(
                        id=uuid.uuid4(),
                        action_key=action_key,
                        source_type=item["source_type"],
                        source_id=item["source_id"],
                        action_category=item["action_category"],
                        action_title=item["action_title"],
                        action_description=item["action_description"],
                        priority=item["priority"],
                        rationale=item["rationale"],
                        evidence_refs=item.get("evidence_refs"),
                        source_dimensions=item.get("source_dimensions"),
                        lsr_code=item.get("lsr_code"),
                        precursor_signature=item.get("precursor_signature"),
                        pattern_key=item.get("pattern_key"),
                        concentration_key=item.get("concentration_key"),
                        rule_id=item["rule_id"],
                        rule_version=item.get("rule_version", "1.0.0"),
                        status=ActionStatus.OPEN,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    self.session.add(new_model)
                    await self.session.flush()
                    dtos.append(self._to_dto(new_model))
                else:
                    mock_model = HSEActionRecommendation(
                        id=uuid.uuid4(),
                        action_key=action_key,
                        source_type=item["source_type"],
                        source_id=item["source_id"],
                        action_category=item["action_category"],
                        action_title=item["action_title"],
                        action_description=item["action_description"],
                        priority=item["priority"],
                        rationale=item["rationale"],
                        evidence_refs=item.get("evidence_refs"),
                        source_dimensions=item.get("source_dimensions"),
                        lsr_code=item.get("lsr_code"),
                        precursor_signature=item.get("precursor_signature"),
                        pattern_key=item.get("pattern_key"),
                        concentration_key=item.get("concentration_key"),
                        rule_id=item["rule_id"],
                        rule_version=item.get("rule_version", "1.0.0"),
                        status=ActionStatus.OPEN,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    dtos.append(self._to_dto(mock_model))

        return dtos, new_count, existing_count

    # --------------------------------------------------------------------------
    # Generation Methods
    # --------------------------------------------------------------------------
    async def generate_actions_for_assessment(
        self,
        assessment_id: uuid.UUID,
        persist: bool = True,
    ) -> List[HSEActionRecommendationDTO]:
        """Generate deterministic HSE actions for a single SIF assessment."""
        ass = await self.session.get(SIFAssessment, assessment_id)
        if not ass:
            raise AssessmentNotFoundException(f"SIF assessment '{assessment_id}' was not found.")

        rep = await self.session.get(SafetyReport, ass.report_id)
        if not rep:
            raise ReportNotFoundException(f"Safety report '{ass.report_id}' was not found.")

        # Load primary LSR mapping
        stmt_lsr = (
            select(LSRReportMapping)
            .where(LSRReportMapping.report_id == rep.id)
            .order_by(LSRReportMapping.is_primary.desc())
        )
        res_lsr = await self.session.execute(stmt_lsr)
        primary_lsr = res_lsr.scalars().first()

        # Load human review if present
        stmt_rev = select(TriageReview).where(TriageReview.assessment_id == assessment_id)
        res_rev = await self.session.execute(stmt_rev)
        review = res_rev.scalars().first()

        raw_actions = self.rule_engine.evaluate_assessment(
            assessment_id=ass.id,
            report_id=rep.id,
            report_ref=rep.report_ref,
            raw_text=rep.raw_text,
            sif_classification=ass.sif_classification,
            evidence_score=ass.evidence_score,
            potential_severity=ass.potential_severity,
            structured_precursor=ass.structured_precursor,
            primary_lsr_code=primary_lsr.rule_code if primary_lsr else None,
            primary_lsr_name=primary_lsr.rule_name if primary_lsr else None,
            review_decision=review.decision if review else None,
            final_classification=review.final_classification if review else None,
            final_structured_precursor=review.final_structured_precursor if review else None,
            final_lsr_code=review.final_lsr_code if review else None,
            evidence_spans=ass.evidence_spans,
        )

        dtos, _, _ = await self._persist_actions(raw_actions, persist=persist)
        return dtos

    async def generate_actions_for_pattern(
        self,
        pattern_id: uuid.UUID,
        persist: bool = True,
    ) -> List[HSEActionRecommendationDTO]:
        """Generate deterministic HSE actions for a recurring precursor pattern."""
        pattern = await self.session.get(PrecursorPattern, pattern_id)
        if not pattern:
            raise PatternNotFoundException(f"Precursor pattern '{pattern_id}' was not found.")

        raw_actions = self.rule_engine.evaluate_pattern(
            pattern_id=pattern.id,
            pattern_code=pattern.pattern_code,
            title=pattern.title,
            hazard_category=pattern.hazard_category,
            failed_barrier_type=pattern.failed_barrier_type,
            occurrence_count=pattern.occurrence_count,
            affected_locations=pattern.affected_locations or [],
            supporting_report_ids=pattern.supporting_report_ids or [],
            lsr_code=pattern.lsr_code,
        )

        dtos, _, _ = await self._persist_actions(raw_actions, persist=persist)
        return dtos

    async def generate_actions_for_concentration(
        self,
        concentration_key: str,
        persist: bool = True,
    ) -> List[HSEActionRecommendationDTO]:
        """Generate deterministic HSE actions for a risk concentration finding."""
        stmt = select(RiskConcentration).where(RiskConcentration.concentration_key == concentration_key)
        res = await self.session.execute(stmt)
        conc = res.scalar_one_or_none()
        if not conc:
            raise ConcentrationNotFoundException(f"Risk concentration '{concentration_key}' was not found.")

        raw_actions = self.rule_engine.evaluate_concentration(
            concentration_key=conc.concentration_key,
            dimension_type=conc.dimension_type,
            dimension_value=conc.dimension_value,
            occurrence_count=conc.occurrence_count,
            distinct_report_count=conc.distinct_report_count,
            distinct_location_count=conc.distinct_location_count,
            observed_trend=conc.observed_trend,
            supporting_report_ids=conc.supporting_report_ids or [],
            supporting_locations=conc.supporting_locations or [],
        )

        dtos, _, _ = await self._persist_actions(raw_actions, persist=persist)
        return dtos

    async def generate_actions_for_report(
        self,
        report_id: uuid.UUID,
        persist: bool = True,
    ) -> List[HSEActionRecommendationDTO]:
        """Generate deterministic HSE actions for a safety report by finding its assessment."""
        rep = await self.session.get(SafetyReport, report_id)
        if not rep:
            raise ReportNotFoundException(f"Safety report '{report_id}' was not found.")

        stmt = select(SIFAssessment).where(SIFAssessment.report_id == report_id)
        res = await self.session.execute(stmt)
        ass = res.scalar_one_or_none()
        if not ass:
            return []

        return await self.generate_actions_for_assessment(ass.id, persist=persist)

    async def generate_all_pending_actions(
        self,
        persist: bool = True,
    ) -> ActionGenerateResponse:
        """Scan all active assessments, patterns, and concentrations to generate pending actions."""
        all_dtos: List[HSEActionRecommendationDTO] = []
        total_new = 0
        total_existing = 0

        # 1. Assessments
        stmt_ass = select(SIFAssessment)
        res_ass = await self.session.execute(stmt_ass)
        assessments = res_ass.scalars().all()
        for ass in assessments:
            dtos = await self.generate_actions_for_assessment(ass.id, persist=persist)
            all_dtos.extend(dtos)

        # 2. Patterns
        stmt_pat = select(PrecursorPattern)
        res_pat = await self.session.execute(stmt_pat)
        patterns = res_pat.scalars().all()
        for pat in patterns:
            dtos = await self.generate_actions_for_pattern(pat.id, persist=persist)
            all_dtos.extend(dtos)

        # 3. Concentrations
        stmt_conc = select(RiskConcentration)
        res_conc = await self.session.execute(stmt_conc)
        concentrations = res_conc.scalars().all()
        for conc in concentrations:
            dtos = await self.generate_actions_for_concentration(conc.concentration_key, persist=persist)
            all_dtos.extend(dtos)

        # Unique by action_key
        unique_dtos: Dict[str, HSEActionRecommendationDTO] = {d.action_key: d for d in all_dtos}
        final_list = list(unique_dtos.values())

        return ActionGenerateResponse(
            total_generated=len(final_list),
            new_actions=total_new,
            existing_actions=total_existing,
            recommendations=final_list,
        )

    # --------------------------------------------------------------------------
    # Query & Retrieval Methods
    # --------------------------------------------------------------------------
    async def get_actions(
        self,
        source_type: Optional[ActionSourceType] = None,
        source_id: Optional[str] = None,
        status: Optional[ActionStatus] = None,
        priority: Optional[ActionPriority] = None,
        action_category: Optional[ActionCategory] = None,
        rule_id: Optional[str] = None,
        lsr_code: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
    ) -> ActionListResponse:
        """Query and filter HSE action recommendations with pagination."""
        offset = (page - 1) * limit

        query = select(HSEActionRecommendation)
        count_query = select(func.count(HSEActionRecommendation.id))

        if source_type:
            query = query.where(HSEActionRecommendation.source_type == source_type)
            count_query = count_query.where(HSEActionRecommendation.source_type == source_type)
        if source_id:
            query = query.where(HSEActionRecommendation.source_id == source_id)
            count_query = count_query.where(HSEActionRecommendation.source_id == source_id)
        if status:
            query = query.where(HSEActionRecommendation.status == status)
            count_query = count_query.where(HSEActionRecommendation.status == status)
        if priority:
            query = query.where(HSEActionRecommendation.priority == priority)
            count_query = count_query.where(HSEActionRecommendation.priority == priority)
        if action_category:
            query = query.where(HSEActionRecommendation.action_category == action_category)
            count_query = count_query.where(HSEActionRecommendation.action_category == action_category)
        if rule_id:
            query = query.where(HSEActionRecommendation.rule_id == rule_id)
            count_query = count_query.where(HSEActionRecommendation.rule_id == rule_id)
        if lsr_code:
            query = query.where(HSEActionRecommendation.lsr_code == lsr_code)
            count_query = count_query.where(HSEActionRecommendation.lsr_code == lsr_code)

        # Count total
        count_res = await self.session.execute(count_query)
        total = count_res.scalar() or 0

        # Order by created_at desc
        query = query.order_by(HSEActionRecommendation.created_at.desc()).offset(offset).limit(limit)
        res = await self.session.execute(query)
        rows = res.scalars().all()

        return ActionListResponse(
            total=total,
            items=[self._to_dto(r) for r in rows],
            page=page,
            limit=limit,
        )

    async def get_action_by_id(self, action_id: uuid.UUID) -> HSEActionRecommendationDTO:
        """Retrieve an action recommendation by its unique ID."""
        action = await self.session.get(HSEActionRecommendation, action_id)
        if not action:
            raise ActionNotFoundException(f"HSE action recommendation '{action_id}' was not found.")
        return self._to_dto(action)

    async def get_actions_for_report(self, report_id: uuid.UUID) -> List[HSEActionRecommendationDTO]:
        """Retrieve all actions associated with a report or its assessment."""
        rep = await self.session.get(SafetyReport, report_id)
        if not rep:
            raise ReportNotFoundException(f"Safety report '{report_id}' was not found.")

        # Query actions for this assessment
        stmt_ass = select(SIFAssessment).where(SIFAssessment.report_id == report_id)
        res_ass = await self.session.execute(stmt_ass)
        ass = res_ass.scalar_one_or_none()

        actions: List[HSEActionRecommendation] = []
        if ass:
            stmt = select(HSEActionRecommendation).where(
                (HSEActionRecommendation.source_type == ActionSourceType.ASSESSMENT)
                & (HSEActionRecommendation.source_id == str(ass.id))
            )
            res = await self.session.execute(stmt)
            actions = res.scalars().all()

        return [self._to_dto(a) for a in actions]

    async def get_actions_for_assessment(self, assessment_id: uuid.UUID) -> List[HSEActionRecommendationDTO]:
        """Retrieve all actions generated for a specific SIF assessment."""
        ass = await self.session.get(SIFAssessment, assessment_id)
        if not ass:
            raise AssessmentNotFoundException(f"SIF assessment '{assessment_id}' was not found.")

        stmt = select(HSEActionRecommendation).where(
            (HSEActionRecommendation.source_type == ActionSourceType.ASSESSMENT)
            & (HSEActionRecommendation.source_id == str(assessment_id))
        )
        res = await self.session.execute(stmt)
        rows = res.scalars().all()
        return [self._to_dto(a) for a in rows]

    async def get_actions_for_pattern(self, pattern_id: uuid.UUID) -> List[HSEActionRecommendationDTO]:
        """Retrieve all actions generated for a recurring precursor pattern."""
        pat = await self.session.get(PrecursorPattern, pattern_id)
        if not pat:
            raise PatternNotFoundException(f"Precursor pattern '{pattern_id}' was not found.")

        stmt = select(HSEActionRecommendation).where(
            (HSEActionRecommendation.source_type == ActionSourceType.PATTERN)
            & (HSEActionRecommendation.source_id == str(pattern_id))
        )
        res = await self.session.execute(stmt)
        rows = res.scalars().all()
        return [self._to_dto(a) for a in rows]

    async def get_actions_for_concentration(self, concentration_key: str) -> List[HSEActionRecommendationDTO]:
        """Retrieve all actions generated for a risk concentration finding."""
        stmt_conc = select(RiskConcentration).where(RiskConcentration.concentration_key == concentration_key)
        res_conc = await self.session.execute(stmt_conc)
        conc = res_conc.scalar_one_or_none()
        if not conc:
            raise ConcentrationNotFoundException(f"Risk concentration '{concentration_key}' was not found.")

        stmt = select(HSEActionRecommendation).where(
            (HSEActionRecommendation.source_type == ActionSourceType.CONCENTRATION)
            & (HSEActionRecommendation.source_id == concentration_key)
        )
        res = await self.session.execute(stmt)
        rows = res.scalars().all()
        return [self._to_dto(a) for a in rows]

    # --------------------------------------------------------------------------
    # Lifecycle Management Methods
    # --------------------------------------------------------------------------
    async def acknowledge_action(
        self,
        action_id: uuid.UUID,
        request: ActionAcknowledgeRequest,
    ) -> HSEActionRecommendationDTO:
        """Acknowledge an HSE action recommendation."""
        action = await self.session.get(HSEActionRecommendation, action_id)
        if not action:
            raise ActionNotFoundException(f"HSE action recommendation '{action_id}' was not found.")

        if action.status == ActionStatus.OPEN:
            action.status = ActionStatus.ACKNOWLEDGED
            action.acknowledged_at = datetime.now(timezone.utc)
            action.actor_id = request.actor_id
            if request.assigned_to:
                action.assigned_to = request.assigned_to
            action.updated_at = datetime.now(timezone.utc)
            await self.session.flush()

        return self._to_dto(action)

    async def update_action_status(
        self,
        action_id: uuid.UUID,
        request: ActionStatusUpdateRequest,
    ) -> HSEActionRecommendationDTO:
        """Update lifecycle state of an HSE action recommendation with deterministic validation."""
        action = await self.session.get(HSEActionRecommendation, action_id)
        if not action:
            raise ActionNotFoundException(f"HSE action recommendation '{action_id}' was not found.")

        # Valid transitions
        valid_transitions = {
            ActionStatus.OPEN: {ActionStatus.ACKNOWLEDGED, ActionStatus.IN_PROGRESS, ActionStatus.COMPLETED, ActionStatus.DISMISSED},
            ActionStatus.ACKNOWLEDGED: {ActionStatus.IN_PROGRESS, ActionStatus.COMPLETED, ActionStatus.DISMISSED},
            ActionStatus.IN_PROGRESS: {ActionStatus.COMPLETED, ActionStatus.DISMISSED},
            ActionStatus.COMPLETED: set(),  # Terminal state
            ActionStatus.DISMISSED: set(),  # Terminal state
        }

        if request.status not in valid_transitions.get(action.status, set()):
            raise InvalidStateTransitionException(
                f"Invalid action status transition from '{action.status.value}' to '{request.status.value}'."
            )

        if request.status in (ActionStatus.COMPLETED, ActionStatus.DISMISSED) and not request.status_rationale:
            raise InvalidStateTransitionException(
                f"Status rationale is mandatory when transitioning action to '{request.status.value}'."
            )

        now = datetime.now(timezone.utc)
        action.status = request.status
        action.actor_id = request.actor_id
        action.status_rationale = request.status_rationale
        if request.assigned_to:
            action.assigned_to = request.assigned_to
        action.updated_at = now

        if request.status == ActionStatus.COMPLETED:
            action.completed_at = now
        elif request.status == ActionStatus.DISMISSED:
            action.dismissed_at = now

        await self.session.flush()
        return self._to_dto(action)
