"""Domain similarity package for structured, semantic, and hybrid precursor matching."""

from app.domain.similarity.hybrid import HybridPrecursorSimilarity
from app.domain.similarity.models import (
    HybridSimilarityResult,
    SemanticSimilarityResult,
    StructuredSimilarityResult,
)
from app.domain.similarity.semantic import CosineSemanticSimilarity
from app.domain.similarity.structured import StructuredPrecursorSimilarity

__all__ = [
    "StructuredSimilarityResult",
    "SemanticSimilarityResult",
    "HybridSimilarityResult",
    "StructuredPrecursorSimilarity",
    "CosineSemanticSimilarity",
    "HybridPrecursorSimilarity",
]
