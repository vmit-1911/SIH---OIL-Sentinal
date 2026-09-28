"""Application service orchestrating recurring SIF precursor pattern discovery and assessment linking."""

import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.logging import get_logger
from app.db.models.assessment import SIFAssessment
from app.db.models.pattern import PrecursorPattern
from app.db.models.report import SafetyReport
from app.domain.enums import PatternStatus
from app.domain.pattern.grouping import PatternGroupingEngine
from app.domain.pattern.synthesizer import PatternSynthesizer
from app.domain.similarity.hybrid import HybridPrecursorSimilarity
from app.schemas.pattern import PatternDiscoveryResponse, PrecursorPatternDTO
from app.schemas.precursor import StructuredPrecursor

logger = get_logger(__name__)


class PatternDiscoveryService:
    """Service discovering multi-report recurring precursor patterns and managing pattern membership."""

    def __init__(
        self,
        session: AsyncSession,
        grouping_engine: Optional[PatternGroupingEngine] = None,
        hybrid_engine: Optional[HybridPrecursorSimilarity] = None,
    ):
        self.session = session
        self.settings = get_settings()
        self.hybrid_engine = hybrid_engine or HybridPrecursorSimilarity(
            structured_weight=self.settings.SIMILARITY_STRUCTURED_WEIGHT,
            semantic_weight=self.settings.SIMILARITY_SEMANTIC_WEIGHT,
        )
        self.grouping_engine = grouping_engine or PatternGroupingEngine(
            hybrid_engine=self.hybrid_engine,
            min_report_count=self.settings.MIN_PATTERN_REPORT_COUNT,
            candidate_threshold=self.settings.PRECURSOR_SIMILARITY_CANDIDATE_THRESHOLD,
            min_cohesion=self.settings.PATTERN_MIN_GROUP_COHESION,
        )

    async def discover_patterns(
        self,
        min_report_count: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> PatternDiscoveryResponse:
        """Execute deterministic pattern discovery across SIF-eligible assessments."""
        run_id = uuid.uuid4()
        eff_min_count = min_report_count or self.settings.MIN_PATTERN_REPORT_COUNT
        eff_threshold = threshold or self.settings.PRECURSOR_SIMILARITY_CANDIDATE_THRESHOLD
        eligible_classifications = self.settings.PATTERN_ELIGIBLE_SIF_CLASSIFICATIONS

        logger.info(
            f"Starting pattern discovery run_id={run_id} "
            f"(min_report_count={eff_min_count}, threshold={eff_threshold}, eligible={eligible_classifications}, method={self.settings.PATTERN_DISCOVERY_METHOD})"
        )

        # 1. Retrieve candidate SIF-eligible assessments and reports
        # SIF precursor pattern discovery strictly excludes NON_SIF and UNDETERMINED assessments
        stmt = (
            select(SIFAssessment, SafetyReport)
            .join(SafetyReport, SIFAssessment.report_id == SafetyReport.id)
            .where(
                SIFAssessment.sif_classification.in_(eligible_classifications),
                (SIFAssessment.structured_precursor.isnot(None))
                | (SIFAssessment.text_embedding.isnot(None)),
            )
        )
        res = await self.session.execute(stmt)
        rows = res.all()

        candidates: List[Dict[str, Any]] = [
            {
                "report_id": report.id,
                "assessment_id": assessment.id,
                "sif_classification": assessment.sif_classification,
                "precursor": assessment.structured_precursor,
                "embedding": assessment.text_embedding,
                "location": report.reported_location,
                "raw_text": report.raw_text,
                "event_timestamp": report.event_timestamp,
                "created_at": report.created_at,
                "assessed_at": assessment.assessed_at,
            }
            for assessment, report in rows
        ]

        logger.info(f"Retrieved {len(candidates)} SIF-eligible candidate assessments for pattern grouping")

        # 2. Group candidate reports into cohesive recurring patterns
        group_result = self.grouping_engine.group_candidates(
            candidates=candidates,
            threshold=eff_threshold,
            min_count=eff_min_count,
            min_cohesion=self.settings.PATTERN_MIN_GROUP_COHESION,
        )

        patterns_created = 0
        patterns_updated = 0
        assessments_assigned = 0
        discovered_pattern_dtos: List[PrecursorPatternDTO] = []

        # 3. Synthesize and persist qualifying patterns
        for group in group_result.qualifying_groups:
            member_records = group["member_records"]
            relationships = group["relationships"]

            # Synthesize domain pattern
            synthesized = PatternSynthesizer.synthesize_pattern(
                member_records=member_records,
                relationships=relationships,
                discovery_method=self.settings.PATTERN_DISCOVERY_METHOD,
            )

            # Idempotency check by pattern_code
            stmt_pat = select(PrecursorPattern).where(
                PrecursorPattern.pattern_code == synthesized.pattern_key
            )
            res_pat = await self.session.execute(stmt_pat)
            existing_pat = res_pat.scalar_one_or_none()

            str_member_ids = [str(rid) for rid in synthesized.supporting_report_ids]
            rep_precursor_dict = synthesized.representative_precursor.to_dict()

            if existing_pat:
                # Update existing pattern
                existing_pat.title = synthesized.title
                existing_pat.description = synthesized.description
                existing_pat.hazard_category = synthesized.hazard_category
                existing_pat.activity_type = synthesized.activity_type
                existing_pat.failed_barrier_type = synthesized.failed_barrier_type
                existing_pat.lsr_code = synthesized.lsr_code
                existing_pat.occurrence_count = synthesized.supporting_report_count
                existing_pat.affected_locations = synthesized.supporting_locations
                existing_pat.supporting_report_ids = str_member_ids
                existing_pat.supporting_lsr_codes = synthesized.supporting_lsr_codes
                existing_pat.representative_precursor = rep_precursor_dict
                existing_pat.similarity_summary = synthesized.similarity_summary
                existing_pat.evidence_summary = synthesized.evidence_summary
                existing_pat.first_detected_at = synthesized.first_observed_at
                existing_pat.last_detected_at = synthesized.last_observed_at
                pattern_db = existing_pat
                patterns_updated += 1
            else:
                # Create new pattern
                pattern_db = PrecursorPattern(
                    id=synthesized.id,
                    pattern_code=synthesized.pattern_key,
                    title=synthesized.title,
                    description=synthesized.description,
                    hazard_category=synthesized.hazard_category,
                    activity_type=synthesized.activity_type,
                    failed_barrier_type=synthesized.failed_barrier_type,
                    lsr_code=synthesized.lsr_code,
                    occurrence_count=synthesized.supporting_report_count,
                    affected_locations=synthesized.supporting_locations,
                    supporting_report_ids=str_member_ids,
                    supporting_lsr_codes=synthesized.supporting_lsr_codes,
                    representative_precursor=rep_precursor_dict,
                    similarity_summary=synthesized.similarity_summary,
                    evidence_summary=synthesized.evidence_summary,
                    discovery_method=synthesized.discovery_method,
                    status=synthesized.status,
                    first_detected_at=synthesized.first_observed_at,
                    last_detected_at=synthesized.last_observed_at,
                )
                self.session.add(pattern_db)
                patterns_created += 1

            await self.session.flush()

            # Link member assessments to the pattern
            member_report_uuids = [r["report_id"] for r in member_records]
            stmt_update = (
                update(SIFAssessment)
                .where(SIFAssessment.report_id.in_(member_report_uuids))
                .values(pattern_id=pattern_db.id)
            )
            await self.session.execute(stmt_update)
            assessments_assigned += len(member_report_uuids)

            # Build response DTO
            rep_schema = synthesized.representative_precursor.to_schema() if synthesized.representative_precursor else None
            dto = PrecursorPatternDTO(
                id=pattern_db.id,
                pattern_code=pattern_db.pattern_code,
                title=pattern_db.title,
                description=pattern_db.description,
                hazard_category=pattern_db.hazard_category,
                activity_type=pattern_db.activity_type,
                failed_barrier_type=pattern_db.failed_barrier_type,
                lsr_code=pattern_db.lsr_code,
                occurrence_count=pattern_db.occurrence_count,
                affected_locations=pattern_db.affected_locations,
                supporting_report_ids=[uuid.UUID(rid) for rid in pattern_db.supporting_report_ids],
                supporting_lsr_codes=pattern_db.supporting_lsr_codes,
                representative_precursor=rep_schema,
                similarity_summary=pattern_db.similarity_summary,
                evidence_summary=pattern_db.evidence_summary,
                similarity_weights=pattern_db.similarity_weights,
                discovery_method=pattern_db.discovery_method,
                status=pattern_db.status,
                first_detected_at=pattern_db.first_detected_at,
                last_detected_at=pattern_db.last_detected_at,
            )
            discovered_pattern_dtos.append(dto)

        # 4. For unassigned reports, ensure pattern_id is not falsely pointing to deleted/stale patterns
        # If reports were unassigned in this run, keep or set their pattern_id to None if needed
        # (We only touch candidate reports evaluated in this run)

        await self.session.flush()

        logger.info(
            f"Pattern discovery completed: run_id={run_id}, candidates={len(candidates)}, "
            f"relationships={group_result.total_relationships}, qualifying_groups={group_result.qualifying_group_count}, "
            f"created={patterns_created}, updated={patterns_updated}, reports_assigned={assessments_assigned}"
        )

        return PatternDiscoveryResponse(
            run_id=run_id,
            discovery_method=self.settings.PATTERN_DISCOVERY_METHOD,
            candidates_evaluated=len(candidates),
            relationships_identified=group_result.total_relationships,
            qualifying_groups_found=group_result.qualifying_group_count,
            patterns_created=patterns_created,
            patterns_updated=patterns_updated,
            assessments_assigned=assessments_assigned,
            discovered_patterns=discovered_pattern_dtos,
        )
