"""Precursor pattern and recurring cluster service."""

from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.pattern import PrecursorPattern
from app.domain.enums import PatternStatus
from app.schemas.pattern import PrecursorPatternDTO
from app.schemas.precursor import PrecursorFieldProvenanceDTO, StructuredPrecursor


class PatternService:
    """Service for querying identified recurring precursor clusters."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _model_to_dto(model: PrecursorPattern) -> PrecursorPatternDTO:
        """Convert PrecursorPattern ORM model to PrecursorPatternDTO."""
        rep_precursor: Optional[StructuredPrecursor] = None
        if model.representative_precursor:
            raw_prec = model.representative_precursor
            prov_dict = raw_prec.get("field_provenance", {})
            field_prov_dto = {}
            for dim, p in prov_dict.items():
                if isinstance(p, dict):
                    field_prov_dto[dim] = PrecursorFieldProvenanceDTO(**p)
            rep_precursor = StructuredPrecursor(
                hazard=raw_prec.get("hazard"),
                activity=raw_prec.get("activity"),
                barrier_failure=raw_prec.get("barrier_failure"),
                exposure=raw_prec.get("exposure"),
                potential_consequence=raw_prec.get("potential_consequence"),
                life_saving_rule=raw_prec.get("life_saving_rule"),
                location=raw_prec.get("location"),
                field_provenance=field_prov_dto,
            )

        supporting_report_uuids = [
            UUID(rid) if isinstance(rid, str) else rid
            for rid in (model.supporting_report_ids or [])
        ]

        return PrecursorPatternDTO(
            id=model.id,
            pattern_code=model.pattern_code,
            title=model.title,
            description=model.description,
            hazard_category=model.hazard_category,
            activity_type=model.activity_type,
            failed_barrier_type=model.failed_barrier_type,
            lsr_code=model.lsr_code,
            occurrence_count=model.occurrence_count,
            affected_locations=model.affected_locations or [],
            supporting_report_ids=supporting_report_uuids,
            supporting_lsr_codes=model.supporting_lsr_codes or [],
            representative_precursor=rep_precursor,
            similarity_summary=model.similarity_summary,
            evidence_summary=model.evidence_summary,
            similarity_weights=model.similarity_weights,
            discovery_method=model.discovery_method,
            status=model.status,
            first_detected_at=model.first_detected_at,
            last_detected_at=model.last_detected_at,
        )

    async def list_patterns(
        self,
        status: Optional[PatternStatus] = None,
        lsr_code: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[PrecursorPatternDTO], int]:
        """Fetch all identified precursor patterns with optional filtering and pagination."""
        stmt = select(PrecursorPattern)
        count_stmt = select(func.count(PrecursorPattern.id))

        if status is not None:
            stmt = stmt.where(PrecursorPattern.status == status)
            count_stmt = count_stmt.where(PrecursorPattern.status == status)

        if lsr_code is not None:
            stmt = stmt.where(PrecursorPattern.lsr_code == lsr_code)
            count_stmt = count_stmt.where(PrecursorPattern.lsr_code == lsr_code)

        stmt = stmt.order_by(PrecursorPattern.occurrence_count.desc(), PrecursorPattern.first_detected_at.desc()).limit(limit).offset(offset)

        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        result = await self.session.execute(stmt)
        models = list(result.scalars().all())

        dtos = [self._model_to_dto(m) for m in models]
        return dtos, total

    async def get_pattern_by_id(self, pattern_id: UUID) -> Optional[PrecursorPatternDTO]:
        """Fetch pattern details by ID."""
        stmt = select(PrecursorPattern).where(PrecursorPattern.id == pattern_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._model_to_dto(model)
