"""Domain models for SIF evidence breakdown, scoring, and rule provenance."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.domain.enums import (
    ActualOutcome,
    DerivationType,
    EvidenceStrength,
    PotentialOutcome,
    SIFClassification,
)
from app.domain.safety_event import EvidenceSpan


class SIFFactorEvidence(BaseModel):
    """Detailed evidence for an individual SIF evaluation factor."""
    factor_name: str = Field(..., description="Factor: ENERGY_HAZARD, EXPOSURE, BARRIER_DEGRADATION, etc.")
    present: bool = Field(default=False, description="Whether active evidence was identified for this factor")
    evidence_strength: EvidenceStrength = Field(default=EvidenceStrength.LOW)
    evidence_items: List[str] = Field(default_factory=list, description="Canonical terms or evidence items")
    evidence_spans: List[EvidenceSpan] = Field(default_factory=list, description="Source character spans")
    contribution_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Factor contribution to screening score")


class SIFEvidenceBreakdown(BaseModel):
    """Machine-readable breakdown of all 5 SIF screening evidence factors."""
    energy_hazard: SIFFactorEvidence
    exposure: SIFFactorEvidence
    barrier_degradation: SIFFactorEvidence
    potential_consequence: SIFFactorEvidence
    context: SIFFactorEvidence


class SIFRuleProvenance(BaseModel):
    """Auditable citation of a domain screening rule that fired."""
    rule_id: str = Field(..., description="Unique rule identifier (e.g. SIF_RULE_GRAVITY_LIFTING_001)")
    description: str = Field(..., description="Explanation of the safety rule heuristic")
    evidence_spans: List[EvidenceSpan] = Field(default_factory=list)
    derivation_type: DerivationType = Field(
        default=DerivationType.RULE_INFERENCE,
        description="Origin of the screening conclusion",
    )


class SIFScreeningResult(BaseModel):
    """Complete output of the SIF Evidence Screening Engine."""
    sif_classification: SIFClassification
    evidence_score: float = Field(..., ge=0.0, le=1.0, description="Multi-factor evidence score [0.0 - 1.0]")
    evidence_strength: EvidenceStrength
    rule_based_screening_score: float = Field(..., ge=0.0, le=1.0)
    actual_severity: ActualOutcome
    potential_severity: Optional[PotentialOutcome] = None
    potential_outcome_details: Optional[str] = None
    evidence_breakdown: SIFEvidenceBreakdown
    primary_reasoning: str
    rule_provenance: List[SIFRuleProvenance] = Field(default_factory=list)
    all_evidence_spans: List[EvidenceSpan] = Field(default_factory=list)
