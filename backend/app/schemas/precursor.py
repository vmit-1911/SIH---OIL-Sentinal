"""Pydantic schema for the 7-dimensional structured precursor and field-level provenance."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.domain.enums import DerivationType
from app.schemas.assessment import EvidenceSpanDTO


class PrecursorFieldProvenanceDTO(BaseModel):
    """Auditable provenance details for an individual precursor dimension."""
    dimension: str = Field(..., description="Dimension name (e.g. hazard, activity, barrier_failure)")
    value: Optional[str] = Field(default=None, description="Extracted or derived canonical concept value")
    derivation_type: Optional[DerivationType] = Field(
        default=None,
        description="Origin of the value: DIRECT_MATCH, LEXICON_INFERENCE, RULE_INFERENCE",
    )
    evidence_spans: List[EvidenceSpanDTO] = Field(
        default_factory=list,
        description="Source character spans supporting this field",
    )
    provenance_rule: Optional[str] = Field(
        default=None,
        description="Rule ID, pattern, or metadata source that established this field",
    )


class StructuredPrecursor(BaseModel):
    """The 7-dimensional structured SIF precursor representation.
    
    Stored as queryable JSONB in PostgreSQL to enable both structured matching
    and cross-site systemic failure pattern discovery. Every populated dimension
    preserves auditable field-level provenance back to original narrative text.
    """
    hazard: Optional[str] = Field(
        default=None,
        description="Identified high-energy hazard or hazardous condition (e.g., High Pressure Gas, Suspended Load)",
    )
    activity: Optional[str] = Field(
        default=None,
        description="Operational task being performed (e.g., Casing Running, Tank Cleaning, Flange Bolting)",
    )
    barrier_failure: Optional[str] = Field(
        default=None,
        description="Degraded, missing, or bypassed safety barrier (e.g., Winch Line Parted, Gas Testing Omitted)",
    )
    exposure: Optional[str] = Field(
        default=None,
        description="Worker exposure, position, or proximity relative to the hazard (e.g., Floormen in swing path)",
    )
    potential_consequence: Optional[str] = Field(
        default=None,
        description="Plausible worst-case consequence (e.g., Fatality from impact, Toxic asphyxiation)",
    )
    life_saving_rule: Optional[str] = Field(
        default=None,
        description="Associated Life-Saving Rule code (e.g., LSR_07_SAFE_MECHANICAL_LIFTING)",
    )
    location: Optional[str] = Field(
        default=None,
        description="Physical operating location, rig, or plant unit (e.g., Rig-04 / Moran Field)",
    )
    field_provenance: Dict[str, PrecursorFieldProvenanceDTO] = Field(
        default_factory=dict,
        description="Field-level provenance and evidence spans for each populated dimension",
    )

