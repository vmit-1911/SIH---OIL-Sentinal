"""Domain models and DTOs for structured, semantic, and hybrid precursor similarity."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class StructuredSimilarityResult(BaseModel):
    """Result of comparing structured precursor dimensions."""
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized similarity score [0.0 - 1.0]")
    dimension_scores: Dict[str, Optional[float]] = Field(
        default_factory=dict,
        description="Dimension-level similarity scores; None if dimension was missing in either precursor",
    )
    compared_dimensions: int = Field(
        default=0,
        ge=0,
        description="Count of dimensions that were populated and compared in both precursors",
    )


class SemanticSimilarityResult(BaseModel):
    """Result of computing cosine similarity between semantic vector embeddings."""
    score: float = Field(..., ge=0.0, le=1.0, description="Bounded cosine similarity [0.0 - 1.0]")
    raw_cosine: float = Field(..., description="Raw unbounded cosine similarity [-1.0 - 1.0]")
    vector_dimension: int = Field(default=384, description="Dimensionality of vector embeddings")


class HybridSimilarityResult(BaseModel):
    """Result of fusing structured dimension similarity and semantic vector similarity."""
    hybrid_score: float = Field(..., ge=0.0, le=1.0, description="Overall weighted hybrid similarity score [0.0 - 1.0]")
    structured_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    semantic_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    structured_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    semantic_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    mode: str = Field(
        default="FULL_HYBRID",
        description="Scoring mode: FULL_HYBRID, STRUCTURED_ONLY_FALLBACK, SEMANTIC_ONLY_FALLBACK, or NO_DATA_AVAILABLE",
    )
    dimension_scores: Dict[str, Optional[float]] = Field(default_factory=dict)
    compared_dimensions: int = 0
    comparison_metadata: Dict[str, Any] = Field(default_factory=dict)

