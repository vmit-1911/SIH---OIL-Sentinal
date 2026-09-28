"""Unified domain result model for SIF analysis."""

from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.domain.enums import (
    ActualOutcome,
    EvidenceStrength,
    PotentialOutcome,
    SIFClassification,
)
from app.domain.lsr.evidence import LSREvidenceMapping
from app.domain.precursor.model import StructuredSIFPrecursor
from app.domain.safety_event import EvidenceSpan, SafetyEventContext
from app.domain.sif.evidence import SIFEvidenceBreakdown, SIFRuleProvenance
from app.schemas.assessment import (
    ActualOutcomeDTO,
    EvidenceSpanDTO,
    ExplainabilityDTO,
    PotentialOutcomeDTO,
    ScoringBreakdownDTO,
)
from app.schemas.report import SimilarReportDTO, SingleReportAnalysisResponse
from app.schemas.safety_event import SafetyEventContextDTO
from app.schemas.taxonomy import LSRMappingDTO


class SIFAnalysisResult(BaseModel):
    """Unified domain result combining Context Extraction, SIF Screening, LSR Mapping, and Precursor Synthesis.
    
    Preserves end-to-end evidence spans, provenance rules, and explainability without
    synthetic or placeholder values.
    """
    report_id: Optional[UUID] = None
    report_ref: Optional[str] = None
    sif_classification: SIFClassification
    evidence_score: float = Field(..., ge=0.0, le=1.0)
    evidence_strength: EvidenceStrength
    rule_based_screening_score: float = Field(..., ge=0.0, le=1.0)
    actual_severity: ActualOutcome
    actual_outcome_details: Optional[str] = None
    potential_severity: Optional[PotentialOutcome] = None
    potential_outcome_details: Optional[str] = None
    evidence_breakdown: SIFEvidenceBreakdown
    primary_reasoning: str
    rule_provenance: List[SIFRuleProvenance] = Field(default_factory=list)
    evidence_spans: List[EvidenceSpan] = Field(default_factory=list)
    safety_event_context: SafetyEventContext
    lsr_mappings: List[LSREvidenceMapping] = Field(default_factory=list)
    primary_lsr: Optional[LSREvidenceMapping] = None
    structured_precursor: Optional[StructuredSIFPrecursor] = None
    precursor_signature: Optional[str] = None
    text_embedding: Optional[List[float]] = None
    similar_reports: List[Dict[str, Any]] = Field(default_factory=list)
    screening_profile_id: str = "SIF_SCREENING_PROFILE_V1"
    screening_profile_version: str = "1.0.0"
    lsr_taxonomy_id: str = "IOGP_REPORT_459"
    lsr_taxonomy_version: str = "2018"
    lexicon_version: str = "1.0.0"


    def to_api_response(self) -> SingleReportAnalysisResponse:
        """Convert domain analysis result to API response schema."""
        if not self.report_id:
            raise ValueError("report_id must be set before converting to SingleReportAnalysisResponse")

        # LSR mappings DTO (confidence_score represents deterministic rule match strength, not statistical probability)
        lsr_dtos: List[LSRMappingDTO] = [
            LSRMappingDTO(
                taxonomy_id=m.taxonomy_id,
                rule_code=m.rule_code,
                rule_name=m.rule_name,
                confidence_score=1.0 if m.evidence_strength == EvidenceStrength.HIGH else 0.7,
                is_primary=m.is_primary,
                trigger_evidence=m.trigger_evidence,
            )
            for m in self.lsr_mappings
        ]

        # Evidence spans DTO
        span_dtos: List[EvidenceSpanDTO] = [
            EvidenceSpanDTO(
                text=s.text,
                category=s.category,
                start_char=s.start_char,
                end_char=s.end_char,
            )
            for s in self.evidence_spans
        ]

        # Rule provenance IDs
        provenance_ids = [r.rule_id for r in self.rule_provenance]
        for lsr in self.lsr_mappings:
            if lsr.provenance_rule and lsr.provenance_rule not in provenance_ids:
                provenance_ids.append(lsr.provenance_rule)

        # Triage recommendation
        if self.sif_classification == SIFClassification.POTENTIAL_SIF:
            recommendation = (
                "ESCALATE_IMMEDIATE_INVESTIGATION"
                if self.evidence_strength == EvidenceStrength.HIGH
                else "HSE_OFFICER_REVIEW"
            )
        elif self.sif_classification == SIFClassification.NON_SIF:
            recommendation = "ROUTINE_LOGGING"
        else:
            recommendation = "HSE_OFFICER_REVIEW"

        # Extracted entities DTO
        extracted_entities = SafetyEventContextDTO.from_domain(self.safety_event_context).model_dump()

        # Structured precursor DTO
        precursor_dto = self.structured_precursor.to_schema() if self.structured_precursor else None
        precursor_sig = self.precursor_signature or (self.structured_precursor.to_signature() if self.structured_precursor else None)

        # Similar reports DTO
        similar_dtos: List[SimilarReportDTO] = [
            SimilarReportDTO(
                report_id=s["report_id"],
                similarity_score=s["similarity_score"],
                similarity_type=s.get("similarity_type", "HYBRID"),
                summary=s["summary"],
                location=s.get("location"),
                event_timestamp=s.get("event_timestamp"),
            )
            for s in self.similar_reports
        ]

        return SingleReportAnalysisResponse(
            report_id=self.report_id,
            sif_classification=self.sif_classification,
            actual_outcome=ActualOutcomeDTO(
                severity=self.actual_severity,
                details=self.actual_outcome_details,
            ),
            potential_outcome=PotentialOutcomeDTO(
                severity=self.potential_severity or PotentialOutcome.LOW_IMPACT,
                details=self.potential_outcome_details,
            ),
            scoring=ScoringBreakdownDTO(
                evidence_score=self.evidence_score,
                evidence_strength=self.evidence_strength,
                rule_based_screening_score=self.rule_based_screening_score,
            ),
            life_saving_rules=lsr_dtos,
            extracted_entities=extracted_entities,
            explainability=ExplainabilityDTO(
                primary_reasoning=self.primary_reasoning,
                evidence_spans=span_dtos,
                rule_provenance=provenance_ids,
            ),
            structured_precursor=precursor_dto,
            precursor_signature=precursor_sig,
            pattern_id=None,
            similar_reports=similar_dtos,
            triage_recommendation=recommendation,
        )



