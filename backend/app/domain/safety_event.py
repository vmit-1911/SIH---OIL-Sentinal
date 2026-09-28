"""Domain models for safety event context extraction and evidence tracking."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.domain.enums import DerivationType, EvidenceStrength


class EvidenceSpan(BaseModel):
    """Exact character offset span in the source narrative supporting an extraction."""
    text: str = Field(..., description="Exact substring from the source narrative")
    category: str = Field(..., description="Entity category (e.g. HAZARD, BARRIER_FAILURE, ACTIVITY)")
    start_char: int = Field(..., ge=0, description="0-indexed start character offset")
    end_char: int = Field(..., ge=0, description="0-indexed end character offset (exclusive)")

    def validate_against_text(self, source_text: str) -> bool:
        """Verify that the character offsets match the text exactly."""
        if self.start_char < 0 or self.end_char > len(source_text) or self.start_char >= self.end_char:
            return False
        return source_text[self.start_char:self.end_char] == self.text


class ExtractedItem(BaseModel):
    """An individual extracted safety event entity with canonical naming and provenance."""
    canonical_name: str = Field(..., description="Standardized domain entity name (e.g. 'Suspended Load')")
    category: str = Field(..., description="Category: HAZARD, ACTIVITY, EQUIPMENT, BARRIER_FAILURE, etc.")
    raw_match: str = Field(..., description="Raw text segment that triggered the match")
    evidence_spans: List[EvidenceSpan] = Field(
        default_factory=list,
        description="Character spans in source text where this entity appears",
    )
    evidence_strength: EvidenceStrength = Field(
        default=EvidenceStrength.MEDIUM,
        description="Confidence/strength of evidence for this extraction",
    )
    derivation_type: DerivationType = Field(
        default=DerivationType.DIRECT_MATCH,
        description="Provenance of the concept (DIRECT_MATCH, LEXICON_INFERENCE, RULE_INFERENCE)",
    )
    is_negated: bool = Field(
        default=False,
        description="Whether this entity is negated in context (e.g. 'no gas leak')",
    )
    provenance_rule: Optional[str] = Field(
        default=None,
        description="Lexicon rule or pattern key that extracted this item",
    )
    attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional domain attributes (e.g. energy_type, barrier_type)",
    )


class TextNormalizationResult(BaseModel):
    """Result of deterministic text normalization."""
    original_text: str
    normalized_text: str
    sentence_spans: List[tuple[int, int]] = Field(
        default_factory=list,
        description="Start and end character offsets for each sentence in normalized text",
    )


class SafetyEventContext(BaseModel):
    """Comprehensive structured domain representation of a safety report event."""
    original_text: str
    normalized_text: str
    
    # Core Extraction Dimensions
    activity: Optional[ExtractedItem] = Field(
        default=None,
        description="Primary operational task (e.g. Casing Running, Tank Cleaning)",
    )
    hazards: List[ExtractedItem] = Field(
        default_factory=list,
        description="Identified hazards present during the event",
    )
    energy_sources: List[ExtractedItem] = Field(
        default_factory=list,
        description="Specific high-energy sources (Gravity, High Pressure, Flammable Gas, etc.)",
    )
    equipment: List[ExtractedItem] = Field(
        default_factory=list,
        description="Machinery, tools, or physical assets involved",
    )
    exposure: List[ExtractedItem] = Field(
        default_factory=list,
        description="Worker exposure, position, proximity, or line-of-fire presence",
    )
    barrier_failures: List[ExtractedItem] = Field(
        default_factory=list,
        description="Defenses, interlocks, PPE, or procedures that failed, were missing, or bypassed",
    )
    unsafe_acts: List[ExtractedItem] = Field(
        default_factory=list,
        description="Behavioral safety violations or non-compliances observed",
    )
    unsafe_conditions: List[ExtractedItem] = Field(
        default_factory=list,
        description="Hazardous physical states or environmental conditions observed",
    )
    potential_consequences: List[ExtractedItem] = Field(
        default_factory=list,
        description="Plausible worst-case outcomes described in the narrative",
    )
    location: Optional[ExtractedItem] = Field(
        default=None,
        description="Specific physical location or operating area within the narrative",
    )
    department: Optional[ExtractedItem] = Field(
        default=None,
        description="Department or operating discipline mentioned",
    )
    people_roles: List[ExtractedItem] = Field(
        default_factory=list,
        description="Job roles or personnel involved (e.g. Derrickman, Floorman, Welder)",
    )
    event_mechanism: Optional[ExtractedItem] = Field(
        default=None,
        description="Underlying physical mechanism (e.g. Line Snapped, Flange Leaked, Fall From Height)",
    )
    all_evidence_spans: List[EvidenceSpan] = Field(
        default_factory=list,
        description="Consolidated list of all evidence spans across all extracted items",
    )
