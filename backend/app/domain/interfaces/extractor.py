"""Abstract interface for NLP entity and structured precursor extraction."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class NLPExtractorInterface(ABC):
    """Port for NLP entity extraction providers."""

    @abstractmethod
    async def extract_entities(self, raw_text: str) -> Dict[str, Any]:
        """Extract domain entities (activity, hazard, barrier failure, equipment, etc.)."""
        pass

