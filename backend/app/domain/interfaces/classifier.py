"""Abstract interface for SIF classification providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class SIFClassifierInterface(ABC):
    """Port for SIF classification providers.
    
    Implementations (Rule-based heuristic, Scikit-learn, Transformer, or LLM)
    must adhere to this contract. Concrete ML implementation is deferred to Phase 1.
    """

    @abstractmethod
    async def classify(
        self,
        raw_text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Evaluate raw text narrative and return SIF classification attributes.
        
        Returns dictionary containing:
        - sif_classification
        - evidence_score
        - evidence_strength
        - rule_based_screening_score
        - potential_severity
        - primary_reasoning
        - evidence_spans
        """
        pass
