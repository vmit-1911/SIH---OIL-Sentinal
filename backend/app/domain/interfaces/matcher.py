"""Abstract interface for weighted hybrid precursor similarity matching."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import UUID


class PrecursorMatcherInterface(ABC):
    """Port for weighted hybrid precursor matching and historical report retrieval.
    
    Supports multi-attribute structural similarity + semantic vector similarity.
    """

    @abstractmethod
    def compute_similarity(
        self,
        precursor_a: Optional[Dict[str, Any]],
        precursor_b: Optional[Dict[str, Any]],
        vec_a: Optional[List[float]] = None,
        vec_b: Optional[List[float]] = None,
    ) -> float:
        """Compute weighted hybrid similarity score between two precursor records."""
        pass

    @abstractmethod
    async def find_similar_reports(
        self,
        target_precursor: Optional[Dict[str, Any]],
        target_embedding: Optional[List[float]],
        exclude_report_id: Optional[UUID] = None,
        top_k: int = 5,
        threshold: float = 0.65,
    ) -> List[Dict[str, Any]]:
        """Find historical safety reports matching the target precursor using hybrid similarity."""
        pass

