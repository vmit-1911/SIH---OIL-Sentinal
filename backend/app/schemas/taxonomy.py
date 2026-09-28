"""Pydantic schemas for Life-Saving Rules and taxonomy endpoints."""

from typing import List, Optional
from pydantic import BaseModel, Field


class LSRMappingDTO(BaseModel):
    """Life-Saving Rule mapping associated with a safety report."""
    taxonomy_id: str = Field(..., description="Taxonomy identifier (e.g. IOGP_REPORT_459)")
    rule_code: str = Field(..., description="Rule code (e.g. LSR_07_SAFE_MECHANICAL_LIFTING)")
    rule_name: str = Field(..., description="Human-readable rule title")
    confidence_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Deterministic rule match strength [0.0 - 1.0] (e.g. 1.0 for primary match, 0.7 for secondary; not a statistical probability)",
    )
    is_primary: bool = Field(default=True, description="Whether this is the primary violated rule")
    trigger_evidence: List[str] = Field(
        default_factory=list,
        description="Keywords or phrases in text that matched this rule",
    )


class TaxonomyRuleItemDTO(BaseModel):
    """Individual rule definition item."""
    code: str
    name: str
    description: str
    guidance: Optional[str] = None
    detection_patterns: List[str] = Field(default_factory=list)
    active: bool = True


class TaxonomyDetailResponse(BaseModel):
    """Complete taxonomy definition returned by API."""
    taxonomy_id: str
    authority: str
    version: str
    name: str
    description: str
    active: bool
    rules: List[TaxonomyRuleItemDTO]


class TaxonomyListResponse(BaseModel):
    """List of available taxonomies."""
    taxonomies: List[TaxonomyDetailResponse]
