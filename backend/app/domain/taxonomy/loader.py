"""Taxonomy loader and parser with validation."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TaxonomyRuleDefinition(BaseModel):
    """Pydantic model for a single Life-Saving Rule definition."""
    code: str
    name: str
    description: str
    guidance: Optional[str] = None
    detection_patterns: List[str] = Field(default_factory=list)
    active: bool = True


class TaxonomyDefinition(BaseModel):
    """Pydantic model for a complete versioned Life-Saving Rule taxonomy."""
    taxonomy_id: str
    authority: str
    version: str
    name: str
    description: str
    active: bool = True
    rules: List[TaxonomyRuleDefinition] = Field(default_factory=list)

    @property
    def rule_codes(self) -> List[str]:
        """Get all active rule codes in this taxonomy."""
        return [rule.code for rule in self.rules if rule.active]

    def get_rule_by_code(self, code: str) -> Optional[TaxonomyRuleDefinition]:
        """Find a rule definition by its code."""
        for rule in self.rules:
            if rule.code.upper() == code.upper():
                return rule
        return None


def load_taxonomy_from_file(file_path: Path) -> TaxonomyDefinition:
    """Load and validate a taxonomy definition from a JSON file."""
    if not file_path.exists():
        raise FileNotFoundError(f"Taxonomy definition file not found at: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return TaxonomyDefinition.model_validate(data)


@lru_cache()
def get_default_taxonomy() -> TaxonomyDefinition:
    """Load and cache the baseline default taxonomy (IOGP Report 459 - 2018)."""
    current_dir = Path(__file__).resolve().parent
    default_path = current_dir / "iogp_report_459.json"
    return load_taxonomy_from_file(default_path)
