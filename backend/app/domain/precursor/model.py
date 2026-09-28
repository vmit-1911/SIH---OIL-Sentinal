"""Domain models for Structured SIF Precursors and field-level provenance."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.domain.enums import DerivationType
from app.domain.safety_event import EvidenceSpan
from app.schemas.assessment import EvidenceSpanDTO
from app.schemas.precursor import PrecursorFieldProvenanceDTO, StructuredPrecursor


class PrecursorDimensionProvenance(BaseModel):
    """Auditable provenance and evidence justification for an individual precursor dimension."""
    dimension: str = Field(..., description="Name of the canonical precursor dimension")
    value: Optional[str] = Field(default=None, description="Standardized concept value")
    derivation_type: DerivationType = Field(
        default=DerivationType.DIRECT_MATCH,
        description="Origin of concept: DIRECT_MATCH, LEXICON_INFERENCE, RULE_INFERENCE",
    )
    evidence_spans: List[EvidenceSpan] = Field(
        default_factory=list,
        description="Character spans from source text directly supporting this extraction",
    )
    provenance_rule: Optional[str] = Field(
        default=None,
        description="Lexicon pattern, domain screening rule, or metadata rule identifier",
    )

    def to_dto(self) -> PrecursorFieldProvenanceDTO:
        """Convert domain dimension provenance to Pydantic API DTO."""
        return PrecursorFieldProvenanceDTO(
            dimension=self.dimension,
            value=self.value,
            derivation_type=self.derivation_type,
            evidence_spans=[
                EvidenceSpanDTO(
                    text=s.text,
                    category=s.category,
                    start_char=s.start_char,
                    end_char=s.end_char,
                )
                for s in self.evidence_spans
            ],
            provenance_rule=self.provenance_rule,
        )


class StructuredSIFPrecursor(BaseModel):
    """Canonical 7-dimensional Structured SIF Precursor representation.
    
    Synthesized deterministically from SafetyEventContext, SIFScreeningResult,
    and LSRMappingResult. Every populated dimension preserves auditable field-level
    provenance and source text spans.
    """
    hazard: Optional[str] = Field(default=None, description="Identified high-energy hazard")
    activity: Optional[str] = Field(default=None, description="Operational task being performed")
    barrier_failure: Optional[str] = Field(default=None, description="Degraded, missing, or bypassed safety barrier")
    exposure: Optional[str] = Field(default=None, description="Worker exposure or proximity to hazard")
    potential_consequence: Optional[str] = Field(default=None, description="Plausible worst-case consequence")
    life_saving_rule: Optional[str] = Field(default=None, description="Primary IOGP Life-Saving Rule code")
    location: Optional[str] = Field(default=None, description="Operating location or rig facility")
    
    field_provenance: Dict[str, PrecursorDimensionProvenance] = Field(
        default_factory=dict,
        description="Auditable provenance mapping for each populated dimension",
    )

    def to_signature(self) -> Optional[str]:
        """Generate a stable, deterministic canonical precursor signature.
        
        Format: hazard|activity|barrier_failure|exposure|potential_consequence|life_saving_rule
        Returns None if all 6 core dimensions are absent.
        """
        core_dims = [
            self.hazard or "",
            self.activity or "",
            self.barrier_failure or "",
            self.exposure or "",
            self.potential_consequence or "",
            self.life_saving_rule or "",
        ]
        if not any(core_dims):
            return None
        return "|".join(core_dims)


    def to_dict(self) -> Dict[str, Any]:
        """Convert precursor to JSON-serializable dictionary for PostgreSQL JSONB storage."""
        return {
            "hazard": self.hazard,
            "activity": self.activity,
            "barrier_failure": self.barrier_failure,
            "exposure": self.exposure,
            "potential_consequence": self.potential_consequence,
            "life_saving_rule": self.life_saving_rule,
            "location": self.location,
            "field_provenance": {
                dim: {
                    "dimension": prov.dimension,
                    "value": prov.value,
                    "derivation_type": prov.derivation_type.value,
                    "evidence_spans": [s.model_dump() for s in prov.evidence_spans],
                    "provenance_rule": prov.provenance_rule,
                }
                for dim, prov in self.field_provenance.items()
            },
        }

    def to_schema(self) -> StructuredPrecursor:
        """Convert domain precursor model to API response schema."""
        return StructuredPrecursor(
            hazard=self.hazard,
            activity=self.activity,
            barrier_failure=self.barrier_failure,
            exposure=self.exposure,
            potential_consequence=self.potential_consequence,
            life_saving_rule=self.life_saving_rule,
            location=self.location,
            field_provenance={
                dim: prov.to_dto()
                for dim, prov in self.field_provenance.items()
            },
        )
