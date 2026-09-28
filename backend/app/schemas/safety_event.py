"""Pydantic schemas for Safety Event Context DTO serialization."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.domain.enums import DerivationType, EvidenceStrength
from app.domain.safety_event import ExtractedItem, SafetyEventContext
from app.schemas.assessment import EvidenceSpanDTO


class ExtractedItemDTO(BaseModel):
    """Data transfer model for an extracted domain entity."""
    canonical_name: str
    category: str
    raw_match: str
    evidence_spans: List[EvidenceSpanDTO] = Field(default_factory=list)
    evidence_strength: EvidenceStrength = EvidenceStrength.MEDIUM
    derivation_type: DerivationType = DerivationType.DIRECT_MATCH
    is_negated: bool = False
    provenance_rule: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, item: ExtractedItem) -> "ExtractedItemDTO":
        """Convert domain ExtractedItem to DTO."""
        return cls(
            canonical_name=item.canonical_name,
            category=item.category,
            raw_match=item.raw_match,
            evidence_spans=[
                EvidenceSpanDTO(
                    text=span.text,
                    category=span.category,
                    start_char=span.start_char,
                    end_char=span.end_char,
                )
                for span in item.evidence_spans
            ],
            evidence_strength=item.evidence_strength,
            derivation_type=item.derivation_type,
            is_negated=item.is_negated,
            provenance_rule=item.provenance_rule,
            attributes=item.attributes,
        )


class SafetyEventContextDTO(BaseModel):
    """Data transfer representation of structured safety event context."""
    original_text: str
    normalized_text: str
    activity: Optional[ExtractedItemDTO] = None
    hazards: List[ExtractedItemDTO] = Field(default_factory=list)
    energy_sources: List[ExtractedItemDTO] = Field(default_factory=list)
    equipment: List[ExtractedItemDTO] = Field(default_factory=list)
    exposure: List[ExtractedItemDTO] = Field(default_factory=list)
    barrier_failures: List[ExtractedItemDTO] = Field(default_factory=list)
    unsafe_acts: List[ExtractedItemDTO] = Field(default_factory=list)
    unsafe_conditions: List[ExtractedItemDTO] = Field(default_factory=list)
    potential_consequences: List[ExtractedItemDTO] = Field(default_factory=list)
    location: Optional[ExtractedItemDTO] = None
    department: Optional[ExtractedItemDTO] = None
    people_roles: List[ExtractedItemDTO] = Field(default_factory=list)
    event_mechanism: Optional[ExtractedItemDTO] = None
    all_evidence_spans: List[EvidenceSpanDTO] = Field(default_factory=list)

    @classmethod
    def from_domain(cls, ctx: SafetyEventContext) -> "SafetyEventContextDTO":
        """Convert domain SafetyEventContext to DTO."""
        return cls(
            original_text=ctx.original_text,
            normalized_text=ctx.normalized_text,
            activity=ExtractedItemDTO.from_domain(ctx.activity) if ctx.activity else None,
            hazards=[ExtractedItemDTO.from_domain(h) for h in ctx.hazards],
            energy_sources=[ExtractedItemDTO.from_domain(e) for e in ctx.energy_sources],
            equipment=[ExtractedItemDTO.from_domain(eq) for eq in ctx.equipment],
            exposure=[ExtractedItemDTO.from_domain(ex) for ex in ctx.exposure],
            barrier_failures=[ExtractedItemDTO.from_domain(b) for b in ctx.barrier_failures],
            unsafe_acts=[ExtractedItemDTO.from_domain(u) for u in ctx.unsafe_acts],
            unsafe_conditions=[ExtractedItemDTO.from_domain(u) for u in ctx.unsafe_conditions],
            potential_consequences=[ExtractedItemDTO.from_domain(p) for p in ctx.potential_consequences],
            location=ExtractedItemDTO.from_domain(ctx.location) if ctx.location else None,
            department=ExtractedItemDTO.from_domain(ctx.department) if ctx.department else None,
            people_roles=[ExtractedItemDTO.from_domain(r) for r in ctx.people_roles],
            event_mechanism=ExtractedItemDTO.from_domain(ctx.event_mechanism) if ctx.event_mechanism else None,
            all_evidence_spans=[
                EvidenceSpanDTO(
                    text=s.text,
                    category=s.category,
                    start_char=s.start_char,
                    end_char=s.end_char,
                )
                for s in ctx.all_evidence_spans
            ],
        )
