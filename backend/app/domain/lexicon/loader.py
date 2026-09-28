"""Lexicon loader and parser for safety entity matching."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LexiconEntry(BaseModel):
    """An individual entry in the safety lexicon."""
    canonical_name: str
    category: str
    energy_type: Optional[str] = None
    patterns: List[str] = Field(default_factory=list)


class NegationConfig(BaseModel):
    """Triggers distinguishing hazard negation from barrier absence."""
    hazard_negation_triggers: List[str] = Field(default_factory=list)
    barrier_absence_triggers: List[str] = Field(default_factory=list)


class SafetyLexicon(BaseModel):
    """Complete domain lexicon definition."""
    lexicon_id: str
    version: str
    description: str
    hazards: List[LexiconEntry] = Field(default_factory=list)
    activities: List[LexiconEntry] = Field(default_factory=list)
    equipment: List[LexiconEntry] = Field(default_factory=list)
    barrier_failures: List[LexiconEntry] = Field(default_factory=list)
    exposure: List[LexiconEntry] = Field(default_factory=list)
    unsafe_acts: List[LexiconEntry] = Field(default_factory=list)
    unsafe_conditions: List[LexiconEntry] = Field(default_factory=list)
    potential_consequences: List[LexiconEntry] = Field(default_factory=list)
    people_roles: List[LexiconEntry] = Field(default_factory=list)
    negation_config: NegationConfig = Field(default_factory=NegationConfig)


def load_safety_lexicon_from_file(file_path: Path) -> SafetyLexicon:
    """Load safety lexicon from JSON file."""
    if not file_path.exists():
        raise FileNotFoundError(f"Safety lexicon file not found at: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return SafetyLexicon.model_validate(data)


@lru_cache()
def get_default_safety_lexicon() -> SafetyLexicon:
    """Get the cached default safety lexicon."""
    current_dir = Path(__file__).resolve().parent
    default_path = current_dir / "safety_lexicon.json"
    return load_safety_lexicon_from_file(default_path)
