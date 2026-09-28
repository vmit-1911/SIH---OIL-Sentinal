"""Application service orchestrating Phase 7 HSE intelligence, evidence graph, explainability, and investigation context."""

import uuid
from typing import Any, Dict, List, Optional, Set
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    AssessmentNotFoundException,
    ConcentrationNotFoundException,
    PatternNotFoundException,
    ReportNotFoundException,
)
from app.core.logging import get_logger
from app.db.models.assessment import SIFAssessment
from app.db.models.concentration import RiskConcentration
from app.db.models.pattern import PrecursorPattern
from app.db.models.report import SafetyReport
from app.db.models.review import ReviewAuditEvent, TriageReview
from app.db.models.taxonomy import LSRReportMapping, LSRTaxonomy
from app.domain.enums import (
    ConcentrationDimension,
    DerivationType,
    EvidenceStrength,
    PatternStatus,
    PotentialOutcome,
    SIFClassification,
)
from app.domain.extraction.rule_based_extractor import RuleBasedSafetyExtractor
from app.domain.safety_event import SafetyEventContext
from app.domain.sif.screening import SIFScreeningEngine
from app.domain.similarity.hybrid import HybridPrecursorSimilarity
from app.schemas.analytics import RiskConcentrationDTO
from app.schemas.assessment import EvidenceSpanDTO, PotentialOutcomeDTO
from app.schemas.intelligence import (
    AssessmentPatternResponse,
    AssessmentSimilarReportDTO,
    AssessmentSimilarityResponse,
    ConcentrationEvidenceResponse,
    ConcentrationSupportingReportDTO,
    EvidenceItemDTO,
    EvidenceType,
    FactorExplanationDTO,
    PatternEvidenceResponse,
    PatternSupportingReportEvidenceDTO,
    ReportEvidenceListResponse,
    ScreeningExplanationDTO,
    SIFInvestigationContextAssessmentDTO,
    SIFInvestigationContextReportDTO,
    SIFInvestigationContextResponse,
    TriggeredRuleDTO,
)
from app.schemas.pattern import PrecursorPatternDTO
from app.schemas.precursor import PrecursorFieldProvenanceDTO, StructuredPrecursor
from app.schemas.review import (
    ReviewAuditEventResponse,
    ReviewDetailResponse,
    ReviewFeedbackResponse,
)
from app.schemas.taxonomy import LSRMappingDTO

logger = get_logger(__name__)


class EvidenceExplanationService:
    """Service producing deterministic evidence, explainability, and investigation context."""

    def __init__(
        self,
        session: AsyncSession,
        extractor: Optional[RuleBasedSafetyExtractor] = None,
        screener: Optional[SIFScreeningEngine] = None,
        similarity_engine: Optional[HybridPrecursorSimilarity] = None,
    ):
        self.session = session
        self.extractor = extractor or RuleBasedSafetyExtractor()
        self.screener = screener or SIFScreeningEngine()
        self.similarity_engine = similarity_engine or HybridPrecursorSimilarity()

    @staticmethod
    def _map_category_to_evidence_type(cat: str) -> EvidenceType:
        """Map extraction category to normalized EvidenceType enum."""
        c = cat.upper().strip()
        if c in ("HAZARD", "ENERGY_SOURCE"):
            return EvidenceType.HAZARD
        elif c == "ACTIVITY":
            return EvidenceType.ACTIVITY
        elif c == "BARRIER_FAILURE":
            return EvidenceType.BARRIER
        elif c == "EXPOSURE":
            return EvidenceType.EXPOSURE
        elif c == "POTENTIAL_CONSEQUENCE":
            return EvidenceType.CONSEQUENCE
        elif c == "LOCATION":
            return EvidenceType.LOCATION
        elif c == "PEOPLE_ROLE":
            return EvidenceType.PEOPLE_ROLE
        elif c == "UNSAFE_ACT":
            return EvidenceType.UNSAFE_ACT
        elif c == "UNSAFE_CONDITION":
            return EvidenceType.UNSAFE_CONDITION
        elif "LSR" in c:
            return EvidenceType.LSR
        else:
            return EvidenceType.OTHER

    def _extract_evidence_items(
        self,
        report: SafetyReport,
        assessment: Optional[SIFAssessment] = None,
        context: Optional[SafetyEventContext] = None,
    ) -> List[EvidenceItemDTO]:
        """Extract deterministic, auditable evidence items from raw narrative context."""
        ctx = context or self.extractor.extract_safety_event_context(report.raw_text)
        evidence_items: List[EvidenceItemDTO] = []
        seen_spans: Set[tuple] = set()

        assessment_id = assessment.id if assessment else None

        # Helper to append extracted item evidence
        def _add_items(items, default_dim=None):
            for item in items:
                for span in item.evidence_spans:
                    span_key = (span.start_char, span.end_char, span.category)
                    if span_key in seen_spans:
                        continue
                    seen_spans.add(span_key)

                    ev_type = self._map_category_to_evidence_type(span.category or item.category)
                    start_char = span.start_char if span.start_char is not None else 0
                    ev_id = f"EV-{report.id.hex[:8]}-{ev_type.value}-{start_char}"

                    evidence_items.append(
                        EvidenceItemDTO(
                            evidence_id=ev_id,
                            assessment_id=assessment_id,
                            report_id=report.id,
                            evidence_type=ev_type,
                            source_text=span.text,
                            start_offset=span.start_char,
                            end_offset=span.end_char,
                            normalized_concept=item.canonical_name,
                            dimension=default_dim or span.category.lower(),
                            derivation_type=item.derivation_type,
                            provenance_rule=item.provenance_rule,
                            strength=item.evidence_strength,
                            is_negated=item.is_negated,
                            attributes=item.attributes or {},
                        )
                    )

        _add_items(ctx.hazards, default_dim="hazard")
        _add_items(ctx.energy_sources, default_dim="hazard")
        _add_items(ctx.barrier_failures, default_dim="barrier_failure")
        _add_items(ctx.exposure, default_dim="exposure")
        if ctx.activity:
            _add_items([ctx.activity], default_dim="activity")
        _add_items(ctx.potential_consequences, default_dim="potential_consequence")
        _add_items(ctx.equipment, default_dim="equipment")
        _add_items(ctx.unsafe_acts, default_dim="unsafe_act")
        _add_items(ctx.unsafe_conditions, default_dim="unsafe_condition")
        _add_items(ctx.people_roles, default_dim="people_role")
        if ctx.location:
            _add_items([ctx.location], default_dim="location")

        # Sort deterministically by start_offset
        evidence_items.sort(key=lambda x: (x.start_offset if x.start_offset is not None else 999999, x.evidence_id))
        return evidence_items

    async def get_report_evidence(self, report_id: uuid.UUID) -> ReportEvidenceListResponse:
        """Retrieve full factual evidence items for a safety report."""
        report = await self.session.get(SafetyReport, report_id)
        if not report:
            raise ReportNotFoundException(f"Safety report '{report_id}' was not found.")

        stmt_ass = select(SIFAssessment).where(SIFAssessment.report_id == report_id)
        res_ass = await self.session.execute(stmt_ass)
        assessment = res_ass.scalar_one_or_none()

        items = self._extract_evidence_items(report, assessment)
        return ReportEvidenceListResponse(
            report_id=report.id,
            assessment_id=assessment.id if assessment else None,
            total_evidence_items=len(items),
            evidence_items=items,
        )

    async def get_assessment_evidence(self, assessment_id: uuid.UUID) -> ReportEvidenceListResponse:
        """Retrieve factual evidence items for a SIF assessment."""
        assessment = await self.session.get(SIFAssessment, assessment_id)
        if not assessment:
            raise AssessmentNotFoundException(f"SIF assessment '{assessment_id}' was not found.")

        report = await self.session.get(SafetyReport, assessment.report_id)
        if not report:
            raise ReportNotFoundException(f"Safety report '{assessment.report_id}' was not found.")

        items = self._extract_evidence_items(report, assessment)
        return ReportEvidenceListResponse(
            report_id=report.id,
            assessment_id=assessment.id,
            total_evidence_items=len(items),
            evidence_items=items,
        )

    async def get_screening_explanation(self, report_id: uuid.UUID) -> ScreeningExplanationDTO:
        """Construct structured, deterministic screening explanation for a report."""
        report = await self.session.get(SafetyReport, report_id)
        if not report:
            raise ReportNotFoundException(f"Safety report '{report_id}' was not found.")

        stmt_ass = select(SIFAssessment).where(SIFAssessment.report_id == report_id)
        res_ass = await self.session.execute(stmt_ass)
        assessment = res_ass.scalar_one_or_none()
        if not assessment:
            raise AssessmentNotFoundException(f"No SIF assessment found for report '{report_id}'.")

        # Fetch Primary LSR mapping if available
        stmt_lsr = (
            select(LSRReportMapping)
            .where(LSRReportMapping.report_id == report_id, LSRReportMapping.is_primary == True)
        )
        res_lsr = await self.session.execute(stmt_lsr)
        mapping = res_lsr.scalar_one_or_none()

        primary_lsr_dto: Optional[LSRMappingDTO] = None
        if mapping:
            primary_lsr_dto = LSRMappingDTO(
                taxonomy_id="IOGP_REPORT_459",
                rule_code=mapping.rule_code,
                rule_name=mapping.rule_name,
                confidence_score=mapping.confidence_score or 1.0,
                is_primary=mapping.is_primary,
                trigger_evidence=mapping.trigger_evidence or [],
            )

        # Run extraction & screening to reconstruct structured factor breakdown
        ctx = self.extractor.extract_safety_event_context(report.raw_text)
        screening_res = self.screener.evaluate_context(ctx, actual_severity=report.actual_severity)
        breakdown = screening_res.evidence_breakdown

        factors: Dict[str, FactorExplanationDTO] = {
            "energy_hazard": FactorExplanationDTO(
                factor_name="ENERGY_HAZARD",
                present=breakdown.energy_hazard.present,
                evidence_strength=breakdown.energy_hazard.evidence_strength,
                contribution_score=breakdown.energy_hazard.contribution_score,
                evidence_items=breakdown.energy_hazard.evidence_items,
                evidence_spans=[
                    EvidenceSpanDTO(text=s.text, category=s.category, start_char=s.start_char, end_char=s.end_char)
                    for s in breakdown.energy_hazard.evidence_spans
                ],
            ),
            "exposure_proximity": FactorExplanationDTO(
                factor_name="EXPOSURE",
                present=breakdown.exposure.present,
                evidence_strength=breakdown.exposure.evidence_strength,
                contribution_score=breakdown.exposure.contribution_score,
                evidence_items=breakdown.exposure.evidence_items,
                evidence_spans=[
                    EvidenceSpanDTO(text=s.text, category=s.category, start_char=s.start_char, end_char=s.end_char)
                    for s in breakdown.exposure.evidence_spans
                ],
            ),
            "barrier_degradation": FactorExplanationDTO(
                factor_name="BARRIER_DEGRADATION",
                present=breakdown.barrier_degradation.present,
                evidence_strength=breakdown.barrier_degradation.evidence_strength,
                contribution_score=breakdown.barrier_degradation.contribution_score,
                evidence_items=breakdown.barrier_degradation.evidence_items,
                evidence_spans=[
                    EvidenceSpanDTO(text=s.text, category=s.category, start_char=s.start_char, end_char=s.end_char)
                    for s in breakdown.barrier_degradation.evidence_spans
                ],
            ),
            "potential_consequence": FactorExplanationDTO(
                factor_name="POTENTIAL_CONSEQUENCE",
                present=breakdown.potential_consequence.present,
                evidence_strength=breakdown.potential_consequence.evidence_strength,
                contribution_score=breakdown.potential_consequence.contribution_score,
                evidence_items=breakdown.potential_consequence.evidence_items,
                evidence_spans=[
                    EvidenceSpanDTO(text=s.text, category=s.category, start_char=s.start_char, end_char=s.end_char)
                    for s in breakdown.potential_consequence.evidence_spans
                ],
            ),
            "operational_context": FactorExplanationDTO(
                factor_name="OPERATIONAL_CONTEXT",
                present=breakdown.context.present,
                evidence_strength=breakdown.context.evidence_strength,
                contribution_score=breakdown.context.contribution_score,
                evidence_items=breakdown.context.evidence_items,
                evidence_spans=[
                    EvidenceSpanDTO(text=s.text, category=s.category, start_char=s.start_char, end_char=s.end_char)
                    for s in breakdown.context.evidence_spans
                ],
            ),
        }

        triggered_rules = [
            TriggeredRuleDTO(
                rule_id=r.rule_id,
                description=r.description,
                evidence_spans=[
                    EvidenceSpanDTO(text=s.text, category=s.category, start_char=s.start_char, end_char=s.end_char)
                    for s in r.evidence_spans
                ],
                derivation_type=r.derivation_type,
            )
            for r in screening_res.rule_provenance
        ]

        evidence_spans = [
            EvidenceSpanDTO(
                text=s.get("text", ""),
                category=s.get("category", "EVIDENCE"),
                start_char=s.get("start_char"),
                end_char=s.get("end_char"),
            )
            for s in (assessment.evidence_spans or [])
        ]

        # Structured Precursor and Provenance
        structured_prec: Optional[StructuredPrecursor] = None
        provenance_dict: Dict[str, PrecursorFieldProvenanceDTO] = {}
        if assessment.structured_precursor:
            raw_prec = assessment.structured_precursor
            raw_prov = raw_prec.get("field_provenance", {})
            for dim, prov in raw_prov.items():
                spans = [
                    EvidenceSpanDTO(
                        text=s.get("text", ""),
                        category=s.get("category", dim.upper()),
                        start_char=s.get("start_char"),
                        end_char=s.get("end_char"),
                    )
                    for s in prov.get("evidence_spans", [])
                ]
                provenance_dict[dim] = PrecursorFieldProvenanceDTO(
                    dimension=dim,
                    value=prov.get("value"),
                    derivation_type=prov.get("derivation_type"),
                    evidence_spans=spans,
                    provenance_rule=prov.get("provenance_rule"),
                )

            structured_prec = StructuredPrecursor(
                hazard=raw_prec.get("hazard"),
                activity=raw_prec.get("activity"),
                barrier_failure=raw_prec.get("barrier_failure"),
                exposure=raw_prec.get("exposure"),
                potential_consequence=raw_prec.get("potential_consequence"),
                life_saving_rule=raw_prec.get("life_saving_rule"),
                location=raw_prec.get("location"),
                field_provenance=provenance_dict,
            )

        potential_consequence_dto = None
        if assessment.potential_severity:
            potential_consequence_dto = PotentialOutcomeDTO(
                severity=assessment.potential_severity,
                details=screening_res.potential_outcome_details,
            )

        return ScreeningExplanationDTO(
            report_id=report.id,
            assessment_id=assessment.id,
            classification=assessment.sif_classification,
            evidence_score=assessment.evidence_score,
            evidence_strength=assessment.evidence_strength,
            rule_based_screening_score=assessment.rule_based_screening_score,
            primary_reasoning=screening_res.primary_reasoning,
            factors=factors,
            triggered_rules=triggered_rules,
            evidence_spans=evidence_spans,
            potential_consequence=potential_consequence_dto,
            primary_lsr=primary_lsr_dto,
            structured_precursor=structured_prec,
            precursor_provenance=provenance_dict,
        )

    async def get_assessment_similar_reports(
        self,
        assessment_id: uuid.UUID,
        limit: int = 10,
        threshold: float = 0.50,
    ) -> AssessmentSimilarityResponse:
        """Retrieve historically similar safety reports evaluated via weighted hybrid similarity."""
        target_ass = await self.session.get(SIFAssessment, assessment_id)
        if not target_ass:
            raise AssessmentNotFoundException(f"SIF assessment '{assessment_id}' was not found.")

        target_rep = await self.session.get(SafetyReport, target_ass.report_id)
        if not target_rep:
            raise ReportNotFoundException(f"Safety report '{target_ass.report_id}' was not found.")

        # Query other assessments with reports
        stmt = (
            select(SIFAssessment, SafetyReport)
            .join(SafetyReport, SIFAssessment.report_id == SafetyReport.id)
            .where(SIFAssessment.id != target_ass.id)
        )
        res = await self.session.execute(stmt)
        other_rows = res.all()

        similar_items: List[AssessmentSimilarReportDTO] = []

        for other_ass, other_rep in other_rows:
            sim_res = self.similarity_engine.compute_hybrid_similarity(
                precursor_a=target_ass.structured_precursor,
                precursor_b=other_ass.structured_precursor,
                vec_a=target_ass.text_embedding,
                vec_b=other_ass.text_embedding,
            )

            score = sim_res.hybrid_score
            if score >= threshold:
                matching_dims = [
                    dim for dim, dscore in sim_res.dimension_scores.items()
                    if dscore is not None and dscore >= 0.70
                ]
                missing_dims = [
                    dim for dim, dscore in sim_res.dimension_scores.items()
                    if dscore is None
                ]

                similar_items.append(
                    AssessmentSimilarReportDTO(
                        target_assessment_id=target_ass.id,
                        matched_assessment_id=other_ass.id,
                        matched_report_id=other_rep.id,
                        matched_report_ref=other_rep.report_ref,
                        matched_narrative=other_rep.raw_text,
                        matched_location=other_rep.reported_location,
                        matched_sif_classification=other_ass.sif_classification,
                        hybrid_score=score,
                        structured_score=sim_res.structured_score,
                        semantic_score=sim_res.semantic_score,
                        similarity_mode=sim_res.mode,
                        dimension_scores=sim_res.dimension_scores,
                        matching_dimensions=matching_dims,
                        missing_dimensions=missing_dims,
                    )
                )

        similar_items.sort(key=lambda x: x.hybrid_score, reverse=True)
        top_items = similar_items[:limit]

        return AssessmentSimilarityResponse(
            assessment_id=target_ass.id,
            report_id=target_rep.id,
            total_similar_reports=len(top_items),
            similar_reports=top_items,
        )

    async def get_assessment_pattern(self, assessment_id: uuid.UUID) -> AssessmentPatternResponse:
        """Retrieve recurring precursor pattern and co-membership for an assessment."""
        ass = await self.session.get(SIFAssessment, assessment_id)
        if not ass:
            raise AssessmentNotFoundException(f"SIF assessment '{assessment_id}' was not found.")

        if not ass.pattern_id:
            return AssessmentPatternResponse(
                assessment_id=ass.id,
                report_id=ass.report_id,
                has_pattern=False,
                pattern=None,
                co_members_count=0,
                co_member_report_ids=[],
                message="No recurring precursor pattern associated with this assessment.",
            )

        pattern = await self.session.get(PrecursorPattern, ass.pattern_id)
        if not pattern:
            return AssessmentPatternResponse(
                assessment_id=ass.id,
                report_id=ass.report_id,
                has_pattern=False,
                pattern=None,
                co_members_count=0,
                co_member_report_ids=[],
                message="Associated precursor pattern record not found.",
            )

        co_members = [
            uuid.UUID(rid) for rid in (pattern.supporting_report_ids or [])
            if rid and uuid.UUID(rid) != ass.report_id
        ]

        rep_schema = StructuredPrecursor.model_validate(pattern.representative_precursor) if pattern.representative_precursor else None

        pattern_dto = PrecursorPatternDTO(
            id=pattern.id,
            pattern_code=pattern.pattern_code,
            title=pattern.title,
            description=pattern.description,
            hazard_category=pattern.hazard_category,
            activity_type=pattern.activity_type,
            failed_barrier_type=pattern.failed_barrier_type,
            lsr_code=pattern.lsr_code,
            occurrence_count=pattern.occurrence_count,
            affected_locations=pattern.affected_locations,
            supporting_report_ids=[uuid.UUID(rid) for rid in pattern.supporting_report_ids if rid],
            supporting_lsr_codes=pattern.supporting_lsr_codes,
            representative_precursor=rep_schema,
            similarity_summary=pattern.similarity_summary,
            evidence_summary=pattern.evidence_summary,
            similarity_weights=pattern.similarity_weights,
            discovery_method=pattern.discovery_method,
            status=pattern.status,
            first_detected_at=pattern.first_detected_at,
            last_detected_at=pattern.last_detected_at,
        )

        return AssessmentPatternResponse(
            assessment_id=ass.id,
            report_id=ass.report_id,
            has_pattern=True,
            pattern=pattern_dto,
            co_members_count=len(co_members),
            co_member_report_ids=co_members,
        )

    async def get_pattern_evidence(self, pattern_id: uuid.UUID) -> PatternEvidenceResponse:
        """Retrieve full evidence and underlying reports contributing to a recurring pattern."""
        pattern = await self.session.get(PrecursorPattern, pattern_id)
        if not pattern:
            raise PatternNotFoundException(f"Precursor pattern '{pattern_id}' was not found.")

        str_rids = pattern.supporting_report_ids or []
        report_uuids = [uuid.UUID(rid) for rid in str_rids if rid]

        supporting_reports: List[PatternSupportingReportEvidenceDTO] = []
        if report_uuids:
            stmt = (
                select(SafetyReport, SIFAssessment)
                .join(SIFAssessment, SafetyReport.id == SIFAssessment.report_id)
                .where(SafetyReport.id.in_(report_uuids))
            )
            res = await self.session.execute(stmt)
            for rep, ass in res.all():
                prec = StructuredPrecursor.model_validate(ass.structured_precursor) if ass.structured_precursor else None
                supporting_reports.append(
                    PatternSupportingReportEvidenceDTO(
                        report_id=rep.id,
                        report_ref=rep.report_ref,
                        location=rep.reported_location,
                        department=rep.reported_department,
                        narrative=rep.raw_text,
                        event_timestamp=rep.event_timestamp,
                        assessment_id=ass.id,
                        sif_classification=ass.sif_classification,
                        evidence_score=ass.evidence_score,
                        structured_precursor=prec,
                    )
                )

        rep_schema = StructuredPrecursor.model_validate(pattern.representative_precursor) if pattern.representative_precursor else None

        temporal_range = {
            "first_detected_at": pattern.first_detected_at,
            "last_detected_at": pattern.last_detected_at,
        }

        cohesion_evidence = {
            "group_cohesion": (pattern.similarity_summary or {}).get("avg_score", 1.0),
            "member_count": pattern.occurrence_count,
            "mode_counts": (pattern.similarity_summary or {}).get("mode_counts", {}),
        }

        return PatternEvidenceResponse(
            pattern_id=pattern.id,
            pattern_code=pattern.pattern_code,
            title=pattern.title,
            description=pattern.description,
            hazard_category=pattern.hazard_category,
            activity_type=pattern.activity_type,
            failed_barrier_type=pattern.failed_barrier_type,
            lsr_code=pattern.lsr_code,
            occurrence_count=pattern.occurrence_count,
            affected_locations=pattern.affected_locations,
            supporting_report_ids=report_uuids,
            supporting_lsr_codes=pattern.supporting_lsr_codes,
            representative_precursor=rep_schema,
            temporal_range=temporal_range,
            similarity_summary=pattern.similarity_summary,
            cohesion_evidence=cohesion_evidence,
            discovery_method=pattern.discovery_method,
            status=pattern.status.value,
            supporting_reports=supporting_reports,
        )

    async def get_concentration_evidence(self, concentration_key: str) -> ConcentrationEvidenceResponse:
        """Retrieve full explainable evidence and underlying reports for a risk concentration."""
        stmt = select(RiskConcentration).where(RiskConcentration.concentration_key == concentration_key)
        res = await self.session.execute(stmt)
        conc = res.scalar_one_or_none()
        if not conc:
            raise ConcentrationNotFoundException(f"Risk concentration '{concentration_key}' was not found.")

        str_rids = conc.supporting_report_ids or []
        report_uuids = [uuid.UUID(rid) for rid in str_rids if rid]

        supporting_reports: List[ConcentrationSupportingReportDTO] = []
        if report_uuids:
            stmt_rep = (
                select(SafetyReport, SIFAssessment)
                .outerjoin(SIFAssessment, SafetyReport.id == SIFAssessment.report_id)
                .where(SafetyReport.id.in_(report_uuids))
            )
            res_rep = await self.session.execute(stmt_rep)
            for rep, ass in res_rep.all():
                prec = StructuredPrecursor.model_validate(ass.structured_precursor) if ass and ass.structured_precursor else None
                supporting_reports.append(
                    ConcentrationSupportingReportDTO(
                        report_id=rep.id,
                        report_ref=rep.report_ref,
                        location=rep.reported_location,
                        department=rep.reported_department,
                        narrative=rep.raw_text,
                        event_timestamp=rep.event_timestamp,
                        sif_classification=ass.sif_classification if ass else None,
                        structured_precursor=prec,
                    )
                )

        return ConcentrationEvidenceResponse(
            concentration_key=conc.concentration_key,
            dimension_type=conc.dimension_type,
            dimension_value=conc.dimension_value,
            pattern_id=conc.pattern_id,
            occurrence_count=conc.occurrence_count,
            distinct_report_count=conc.distinct_report_count,
            distinct_location_count=conc.distinct_location_count,
            first_observed_at=conc.first_observed_at,
            last_observed_at=conc.last_observed_at,
            observed_trend=conc.observed_trend,
            temporal_distribution=conc.temporal_distribution or {},
            supporting_report_ids=report_uuids,
            supporting_pattern_ids=[uuid.UUID(pid) for pid in (conc.supporting_pattern_ids or []) if pid],
            supporting_locations=conc.supporting_locations or [],
            supporting_lsr_codes=conc.supporting_lsr_codes or [],
            evidence_summary=conc.evidence_summary or {},
            calculation_method=conc.calculation_method,
            status=conc.status,
            supporting_reports=supporting_reports,
        )

    async def get_investigation_context(self, report_id: uuid.UUID) -> SIFInvestigationContextResponse:
        """Consolidate the complete 10-dimension HSE investigation context for a report."""
        report = await self.session.get(SafetyReport, report_id)
        if not report:
            raise ReportNotFoundException(f"Safety report '{report_id}' was not found.")

        # Eager load Assessment
        stmt_ass = select(SIFAssessment).where(SIFAssessment.report_id == report_id)
        res_ass = await self.session.execute(stmt_ass)
        assessment = res_ass.scalar_one_or_none()

        # Eager load Review and Audit Events
        stmt_rev = select(TriageReview).where(TriageReview.report_id == report_id)
        res_rev = await self.session.execute(stmt_rev)
        review = res_rev.scalar_one_or_none()

        audit_history: List[ReviewAuditEventResponse] = []
        review_dto: Optional[ReviewDetailResponse] = None
        if review:
            stmt_events = (
                select(ReviewAuditEvent)
                .where(ReviewAuditEvent.review_id == review.id)
                .order_by(ReviewAuditEvent.created_at.asc())
            )
            res_events = await self.session.execute(stmt_events)
            audit_events = res_events.scalars().all()

            audit_history = [
                ReviewAuditEventResponse(
                    id=e.id,
                    review_id=e.review_id,
                    actor_id=e.actor_id,
                    actor_role=e.actor_role,
                    event_type=e.event_type,
                    before_state=e.before_state,
                    after_state=e.after_state,
                    changed_fields=e.changed_fields,
                    rationale=e.rationale,
                    created_at=e.created_at,
                )
                for e in audit_events
            ]

            fb = None
            if review.feedback_category:
                fb_notes = None
                fb_details = None
                if isinstance(review.feedback_details, dict):
                    fb_notes = review.feedback_details.get("notes")
                    fb_details = review.feedback_details.get("specific_error_details")
                fb = ReviewFeedbackResponse(
                    category=review.feedback_category,
                    notes=fb_notes,
                    specific_error_details=fb_details,
                )

            review_dto = ReviewDetailResponse(
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
                feedback=fb,
                version=review.version,
                created_at=review.created_at,
                updated_at=review.updated_at,
                report_narrative=report.raw_text,
                reported_location=report.reported_location,
                source_type=report.source_type.value,
                event_timestamp=report.event_timestamp,
                recent_audit_events=audit_history,
            )

        # 1. Report Baseline DTO
        report_dto = SIFInvestigationContextReportDTO(
            id=report.id,
            report_ref=report.report_ref,
            source_type=report.source_type,
            reported_location=report.reported_location,
            reported_department=report.reported_department,
            actual_severity=report.actual_severity,
            raw_text=report.raw_text,
            event_timestamp=report.event_timestamp,
            created_at=report.created_at,
        )

        # 2. Assessment Baseline DTO
        assessment_dto = None
        if assessment:
            assessment_dto = SIFInvestigationContextAssessmentDTO(
                id=assessment.id,
                report_id=assessment.report_id,
                sif_classification=assessment.sif_classification,
                evidence_score=assessment.evidence_score,
                evidence_strength=assessment.evidence_strength,
                rule_based_screening_score=assessment.rule_based_screening_score,
                potential_severity=assessment.potential_severity,
                triage_status=assessment.triage_status,
                pattern_id=assessment.pattern_id,
                assessed_at=assessment.assessed_at,
            )

        # 3. Evidence Items
        evidence_items = self._extract_evidence_items(report, assessment)

        # 4. Screening Explanation
        screening_dto = None
        if assessment:
            screening_dto = await self.get_screening_explanation(report.id)

        # 5. Precursor and Provenance
        structured_prec = None
        precursor_provenance = {}
        if assessment and assessment.structured_precursor:
            raw_prec = assessment.structured_precursor
            raw_prov = raw_prec.get("field_provenance", {})
            for dim, prov in raw_prov.items():
                spans = [
                    EvidenceSpanDTO(
                        text=s.get("text", ""),
                        category=s.get("category", dim.upper()),
                        start_char=s.get("start_char"),
                        end_char=s.get("end_char"),
                    )
                    for s in prov.get("evidence_spans", [])
                ]
                precursor_provenance[dim] = PrecursorFieldProvenanceDTO(
                    dimension=dim,
                    value=prov.get("value"),
                    derivation_type=prov.get("derivation_type"),
                    evidence_spans=spans,
                    provenance_rule=prov.get("provenance_rule"),
                )

            structured_prec = StructuredPrecursor(
                hazard=raw_prec.get("hazard"),
                activity=raw_prec.get("activity"),
                barrier_failure=raw_prec.get("barrier_failure"),
                exposure=raw_prec.get("exposure"),
                potential_consequence=raw_prec.get("potential_consequence"),
                life_saving_rule=raw_prec.get("life_saving_rule"),
                location=raw_prec.get("location"),
                field_provenance=precursor_provenance,
            )

        # 6. Similar Reports
        similar_reports: List[AssessmentSimilarReportDTO] = []
        if assessment:
            sim_resp = await self.get_assessment_similar_reports(assessment.id, limit=5, threshold=0.50)
            similar_reports = sim_resp.similar_reports

        # 7. Pattern
        pattern_dto = None
        if assessment and assessment.pattern_id:
            pat_resp = await self.get_assessment_pattern(assessment.id)
            pattern_dto = pat_resp.pattern

        # 8. Concentrations associated with this report
        str_rid = str(report.id)
        stmt_conc = select(RiskConcentration)
        res_conc = await self.session.execute(stmt_conc)
        all_conc = res_conc.scalars().all()
        conc_rows = [
            c for c in all_conc
            if (str_rid in (c.supporting_report_ids or []))
            or (report.reported_location and c.dimension_value == report.reported_location)
            or (assessment and assessment.pattern_id and c.pattern_id == assessment.pattern_id)
        ]
        concentration_dtos = [
            RiskConcentrationDTO(
                id=c.id,
                concentration_key=c.concentration_key,
                dimension_type=c.dimension_type,
                dimension_value=c.dimension_value,
                pattern_id=c.pattern_id,
                occurrence_count=c.occurrence_count,
                distinct_report_count=c.distinct_report_count,
                distinct_location_count=c.distinct_location_count,
                first_observed_at=c.first_observed_at,
                last_observed_at=c.last_observed_at,
                observed_trend=c.observed_trend,
                temporal_distribution=c.temporal_distribution or {},
                supporting_report_ids=[uuid.UUID(rid) for rid in c.supporting_report_ids if rid],
                supporting_pattern_ids=[uuid.UUID(pid) for pid in c.supporting_pattern_ids if pid],
                supporting_locations=c.supporting_locations or [],
                supporting_lsr_codes=c.supporting_lsr_codes or [],
                evidence_summary=c.evidence_summary or {},
                calculation_method=c.calculation_method,
                status=c.status,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in conc_rows
        ]

        return SIFInvestigationContextResponse(
            report=report_dto,
            assessment=assessment_dto,
            evidence=evidence_items,
            screening=screening_dto,
            precursor=structured_prec,
            precursor_provenance=precursor_provenance,
            similar_reports=similar_reports,
            pattern=pattern_dto,
            concentrations=concentration_dtos,
            review=review_dto,
            audit_history=audit_history,
        )
