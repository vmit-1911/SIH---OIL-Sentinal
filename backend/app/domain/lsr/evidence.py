"""Domain models for Life-Saving Rules evidence mappings and results."""

from typing import List, Optional
from pydantic import BaseModel, Field

from app.domain.enums import EvidenceStrength
from app.domain.safety_event import EvidenceSpan


class LSREvidenceMapping(BaseModel):
    """An individual Life-Saving Rule mapping supported by textual and domain evidence."""
    taxonomy_id: str = Field(default="IOGP_REPORT_459")
    taxonomy_version: str = Field(default="2018")
    rule_code: str = Field(..., description="Unique rule code (e.g. LSR_07_SAFE_MECHANICAL_LIFTING)")
    rule_name: str = Field(..., description="Canonical rule name")
    evidence_strength: EvidenceStrength = Field(default=EvidenceStrength.HIGH)
    trigger_evidence: List[str] = Field(default_factory=list, description="Specific terms or concepts that matched")
    evidence_spans: List[EvidenceSpan] = Field(default_factory=list, description="Source character offset spans")
    provenance_rule: str = Field(..., description="Rule ID explaining why this LSR was matched")
    is_primary: bool = Field(default=False, description="Whether this rule is the defensible primary focus")


class LSRMappingResult(BaseModel):
    """Complete outcome of the Life-Saving Rules mapping engine."""
    taxonomy_id: str = "IOGP_REPORT_459"
    taxonomy_version: str = "2018"
    mapped_rules: List[LSREvidenceMapping] = Field(default_factory=list)
    primary_rule: Optional[LSREvidenceMapping] = None
