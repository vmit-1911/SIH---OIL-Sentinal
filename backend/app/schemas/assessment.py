"""Pydantic schemas for SIF assessment, scoring, and explainability."""

from typing import List, Optional
from pydantic import BaseModel, Field

from app.domain.enums import (
    ActualOutcome,
    EvidenceStrength,
    PotentialOutcome,
    SIFClassification,
    TriageStatus,
)


class EvidenceSpanDTO(BaseModel):
    """Specific substring span in the raw narrative that justified the evaluation."""
    text: str = Field(..., description="Extracted text span from original report")
    category: str = Field(..., description="Category: HAZARD, BARRIER_FAILURE, EXPOSURE, UNSAFE_ACT, etc.")
    start_char: Optional[int] = Field(default=None, description="Starting character index")
    end_char: Optional[int] = Field(default=None, description="Ending character index")


class ScoringBreakdownDTO(BaseModel):
    """Evidence-based scoring metrics (not calibrated probabilities)."""
    evidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Aggregate strength score of textual and situational evidence [0.0 - 1.0]",
    )
    evidence_strength: EvidenceStrength = Field(
        ...,
        description="Categorical evidence strength level (LOW, MEDIUM, HIGH)",
    )
    rule_based_screening_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Deterministic screening match score against active domain rules [0.0 - 1.0]",
    )


class ActualOutcomeDTO(BaseModel):
    """Details of what physically occurred."""
    severity: ActualOutcome = Field(..., description="Reported actual injury severity")
    details: Optional[str] = Field(default=None, description="Narrative description of actual outcome")


class PotentialOutcomeDTO(BaseModel):
    """Details of plausible worst-case outcome."""
    severity: PotentialOutcome = Field(..., description="Potential worst-case severity")
    details: Optional[str] = Field(default=None, description="Narrative description of plausible outcome")


class ExplainabilityDTO(BaseModel):
    """Explainability payload detailing reasoning, evidence, and rule provenance."""
    primary_reasoning: str = Field(..., description="Summary explanation of the SIF evaluation")
    evidence_spans: List[EvidenceSpanDTO] = Field(
        default_factory=list,
        description="Specific highlighted text spans supporting classification",
    )
    rule_provenance: List[str] = Field(
        default_factory=list,
        description="List of domain rule IDs or heuristics triggered",
    )
