"""Application service orchestrating Context Extraction, SIF Screening, LSR Mapping, and Persistence."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.logging import get_logger
from app.db.models.assessment import SIFAssessment
from app.db.models.report import SafetyReport
from app.db.models.taxonomy import LSRReportMapping, LSRTaxonomy
from app.domain.enums import (
    ActualOutcome,
    EvidenceStrength,
    PotentialOutcome,
    SourceType,
    TriageStatus,
)
from app.domain.extraction.rule_based_extractor import RuleBasedSafetyExtractor
from app.domain.interfaces.embedder import TextEmbedderInterface
from app.domain.interfaces.matcher import PrecursorMatcherInterface
from app.domain.lsr.mapper import LSRMapper
from app.domain.precursor.formatter import PrecursorTextFormatter
from app.domain.precursor.synthesizer import StructuredPrecursorSynthesizer
from app.domain.sif.analysis import SIFAnalysisResult
from app.domain.sif.screening import SIFScreeningEngine
from app.domain.taxonomy.loader import get_default_taxonomy
from app.infrastructure.embeddings.sentence_transformer import SentenceTransformerEmbedder
from app.infrastructure.matcher.database_matcher import DatabasePrecursorMatcher
from app.schemas.report import SingleReportAnalysisRequest

logger = get_logger(__name__)


class SIFAnalysisService:
    """Orchestrates the end-to-end deterministic inference pipeline, embedding generation, matching, and database persistence."""

    def __init__(
        self,
        session: AsyncSession,
        extractor: Optional[RuleBasedSafetyExtractor] = None,
        screening_engine: Optional[SIFScreeningEngine] = None,
        lsr_mapper: Optional[LSRMapper] = None,
        precursor_synthesizer: Optional[StructuredPrecursorSynthesizer] = None,
        embedder: Optional[TextEmbedderInterface] = None,
        matcher: Optional[PrecursorMatcherInterface] = None,
    ):
        self.session = session
        self.settings = get_settings()
        self.extractor = extractor or RuleBasedSafetyExtractor()
        self.screening_engine = screening_engine or SIFScreeningEngine()
        self.lsr_mapper = lsr_mapper or LSRMapper()
        self.precursor_synthesizer = precursor_synthesizer or StructuredPrecursorSynthesizer()
        self.embedder = embedder or SentenceTransformerEmbedder(
            model_name=self.settings.EMBEDDING_MODEL_NAME,
            expected_dimension=self.settings.EMBEDDING_DIMENSION,
        )
        self.matcher = matcher or DatabasePrecursorMatcher(
            session=self.session,
        )


    async def _get_or_create_default_taxonomy(self) -> LSRTaxonomy:
        """Ensure the baseline IOGP Report 459 taxonomy record exists in the database."""
        stmt = select(LSRTaxonomy).where(LSRTaxonomy.taxonomy_id == "IOGP_REPORT_459")
        res = await self.session.execute(stmt)
        taxonomy_record = res.scalar_one_or_none()
        if not taxonomy_record:
            default_tax = get_default_taxonomy()
            taxonomy_record = LSRTaxonomy(
                taxonomy_id=default_tax.taxonomy_id,
                authority=default_tax.authority,
                version=default_tax.version,
                name=default_tax.name,
                description=default_tax.description,
                rules=[r.model_dump() for r in default_tax.rules],
                active=default_tax.active,
            )
            self.session.add(taxonomy_record)
            await self.session.flush()
        return taxonomy_record

    async def analyze_existing_report(
        self,
        report: SafetyReport,
    ) -> SIFAnalysisResult:
        """Execute deterministic inference pipeline for an existing persisted SafetyReport."""
        raw_text = report.raw_text.strip()
        if not raw_text:
            raise ValueError("Safety observation narrative cannot be empty")

        # 1. Context Extraction (Phase 1A)
        logger.info(f"Executing safety event context extraction for report_id={report.id}")
        context = self.extractor.extract_safety_event_context(raw_text)

        # 2. SIF Evidence Screening (Phase 1B)
        logger.info(f"Executing multi-factor SIF evidence screening for report_id={report.id}")
        screening_result = self.screening_engine.evaluate_context(
            context,
            actual_severity=report.actual_severity,
        )

        # 3. IOGP Life-Saving Rules Mapping (Phase 1B)
        logger.info(f"Executing IOGP Report 459 Life-Saving Rules mapping for report_id={report.id}")
        lsr_result = self.lsr_mapper.map_rules(context)

        # 4. Structured Precursor Synthesis (Phase 1D)
        logger.info(f"Executing structured SIF precursor synthesis for report_id={report.id}")
        precursor = self.precursor_synthesizer.synthesize(
            context=context,
            screening_result=screening_result,
            lsr_result=lsr_result,
            reported_location=report.reported_location,
        )
        precursor_sig = precursor.to_signature()

        # 5. Precursor Text Representation & Semantic Embedding (Phase 2A)
        precursor_text = PrecursorTextFormatter.format_to_text(precursor)
        embedding: Optional[List[float]] = None
        if precursor_text and self.embedder:
            try:
                logger.info(f"Generating 384-dimensional dense embedding for precursor of report_id={report.id}")
                embedding = self.embedder.embed_text(precursor_text)
            except Exception as e:
                logger.error(f"Embedding generation failed: {e}")
                embedding = None

        # 6. Database Assessment Persistence (Idempotent Check with Graceful Offline Resilience)
        try:
            stmt_ass = select(SIFAssessment).where(SIFAssessment.report_id == report.id)
            res_ass = await self.session.execute(stmt_ass)
            existing_assessment = res_ass.scalar_one_or_none()

            spans_json = [
                {
                    "text": s.text,
                    "category": s.category,
                    "start_char": s.start_char,
                    "end_char": s.end_char,
                }
                for s in screening_result.all_evidence_spans
            ]

            if existing_assessment:
                # Update existing assessment in-place
                existing_assessment.sif_classification = screening_result.sif_classification
                existing_assessment.evidence_score = screening_result.evidence_score
                existing_assessment.evidence_strength = screening_result.evidence_strength
                existing_assessment.rule_based_screening_score = screening_result.rule_based_screening_score
                existing_assessment.potential_severity = screening_result.potential_severity or PotentialOutcome.LOW_IMPACT
                existing_assessment.potential_outcome_details = screening_result.potential_outcome_details
                existing_assessment.primary_reasoning = screening_result.primary_reasoning
                existing_assessment.evidence_spans = spans_json
                existing_assessment.structured_precursor = precursor.to_dict()
                existing_assessment.text_embedding = embedding
                existing_assessment.precursor_signature = precursor_sig
                assessment = existing_assessment
            else:
                assessment = SIFAssessment(
                    report_id=report.id,
                    sif_classification=screening_result.sif_classification,
                    evidence_score=screening_result.evidence_score,
                    evidence_strength=screening_result.evidence_strength,
                    rule_based_screening_score=screening_result.rule_based_screening_score,
                    potential_severity=screening_result.potential_severity or PotentialOutcome.LOW_IMPACT,
                    potential_outcome_details=screening_result.potential_outcome_details,
                    primary_reasoning=screening_result.primary_reasoning,
                    evidence_spans=spans_json,
                    structured_precursor=precursor.to_dict(),
                    text_embedding=embedding,
                    precursor_signature=precursor_sig,
                    pattern_id=None,
                    triage_status=TriageStatus.AUTO_SCREENED,
                )
                self.session.add(assessment)

            # Persist LSR Mappings if present (avoid duplicates)
            if lsr_result.mapped_rules:
                taxonomy_record = await self._get_or_create_default_taxonomy()
                if existing_assessment:
                    stmt_del = select(LSRReportMapping).where(LSRReportMapping.report_id == report.id)
                    res_mappings = await self.session.execute(stmt_del)
                    for old_m in res_mappings.scalars().all():
                        await self.session.delete(old_m)

                for mapping in lsr_result.mapped_rules:
                    db_mapping = LSRReportMapping(
                        report_id=report.id,
                        taxonomy_id=taxonomy_record.id,
                        rule_code=mapping.rule_code,
                        rule_name=mapping.rule_name,
                        confidence_score=1.0 if mapping.evidence_strength == EvidenceStrength.HIGH else 0.7,
                        trigger_evidence=mapping.trigger_evidence,
                        is_primary=mapping.is_primary,
                    )
                    self.session.add(db_mapping)

            await self.session.flush()
        except Exception as db_exc:
            logger.warning(f"Database persistence unavailable; proceeding with ephemeral analysis: {db_exc}")

        # 7. Hybrid Precursor Matching against Previous Reports (Phase 2A)
        similar_reports = []
        if self.matcher:
            try:
                logger.info(f"Executing hybrid precursor similarity matching for report_id={report.id}")
                similar_reports = await self.matcher.find_similar_reports(
                    target_precursor=precursor.to_dict() if precursor else None,
                    target_embedding=embedding,
                    exclude_report_id=report.id,
                    top_k=self.settings.SIMILARITY_TOP_K,
                    threshold=self.settings.PRECURSOR_SIMILARITY_CANDIDATE_THRESHOLD,
                )
            except Exception as e:
                logger.error(f"Precursor similarity matching failed: {e}")
                similar_reports = []

        # 8. Assemble Unified Domain Result
        analysis_result = SIFAnalysisResult(
            report_id=report.id,
            report_ref=report.report_ref,
            sif_classification=screening_result.sif_classification,
            evidence_score=screening_result.evidence_score,
            evidence_strength=screening_result.evidence_strength,
            rule_based_screening_score=screening_result.rule_based_screening_score,
            actual_severity=report.actual_severity,
            actual_outcome_details=report.actual_outcome_details,
            potential_severity=screening_result.potential_severity,
            potential_outcome_details=screening_result.potential_outcome_details,
            evidence_breakdown=screening_result.evidence_breakdown,
            primary_reasoning=screening_result.primary_reasoning,
            rule_provenance=screening_result.rule_provenance,
            evidence_spans=screening_result.all_evidence_spans,
            safety_event_context=context,
            lsr_mappings=lsr_result.mapped_rules,
            primary_lsr=lsr_result.primary_rule,
            structured_precursor=precursor,
            precursor_signature=precursor_sig,
            text_embedding=embedding,
            similar_reports=similar_reports,
            screening_profile_id=self.screening_engine.profile.profile_id,
            screening_profile_version=self.screening_engine.profile.version,
            lsr_taxonomy_id=lsr_result.taxonomy_id,
            lsr_taxonomy_version=lsr_result.taxonomy_version,
            lexicon_version="1.0.0",
        )

        logger.info(
            f"Completed SIF analysis for report_id={report.id}: "
            f"classification={analysis_result.sif_classification.value}, score={analysis_result.evidence_score}, "
            f"similar_reports={len(analysis_result.similar_reports)}"
        )

        return analysis_result

    async def analyze_and_persist(
        self,
        request: SingleReportAnalysisRequest,
    ) -> SIFAnalysisResult:
        """Execute deterministic inference pipeline and persist report and assessment."""
        raw_text = request.raw_text.strip()
        if not raw_text:
            raise ValueError("Safety observation narrative cannot be empty")

        report_ref = f"SR-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        report = SafetyReport(
            id=uuid.uuid4(),
            report_ref=report_ref,
            source_type=request.source_type,
            raw_text=raw_text,
            reported_location=request.reported_location,
            reported_department=request.reported_department,
            actual_severity=request.actual_severity,
            actual_outcome_details=None,
            event_timestamp=request.event_timestamp,
        )
        try:
            self.session.add(report)
            await self.session.flush()
        except Exception as add_exc:
            logger.warning(f"Database unavailable for report insertion; continuing with in-memory report instance: {add_exc}")

        return await self.analyze_existing_report(report)



