"""Semantic vector cosine similarity engine."""

import math
from typing import List, Optional
from app.domain.similarity.models import SemanticSimilarityResult


class CosineSemanticSimilarity:
    """Calculates deterministic cosine similarity between dense vector embeddings."""

    def __init__(self, expected_dimension: int = 384):
        self.expected_dimension = expected_dimension

    def compute_similarity(
        self,
        vec_a: Optional[List[float]],
        vec_b: Optional[List[float]],
    ) -> SemanticSimilarityResult:
        """Compute cosine similarity between two vector embeddings.
        
        Raises ValueError on dimension mismatch or empty inputs.
        Handles identical, orthogonal, and zero vectors deterministically.
        """
        if vec_a is None or vec_b is None:
            raise ValueError("Vector embeddings cannot be None for semantic similarity calculation")

        if len(vec_a) != self.expected_dimension or len(vec_b) != self.expected_dimension:
            raise ValueError(
                f"Vector dimensionality mismatch: expected {self.expected_dimension}, "
                f"got len(vec_a)={len(vec_a)}, len(vec_b)={len(vec_b)}"
            )

        dot_product = 0.0
        norm_a_sq = 0.0
        norm_b_sq = 0.0

        for a, b in zip(vec_a, vec_b):
            dot_product += a * b
            norm_a_sq += a * a
            norm_b_sq += b * b

        norm_a = math.sqrt(norm_a_sq)
        norm_b = math.sqrt(norm_b_sq)

        # Handle zero vector
        if norm_a == 0.0 or norm_b == 0.0:
            return SemanticSimilarityResult(
                score=0.0,
                raw_cosine=0.0,
                vector_dimension=self.expected_dimension,
            )

        raw_cosine = dot_product / (norm_a * norm_b)
        # Numerical stability clamp [-1.0, 1.0]
        raw_cosine = max(-1.0, min(1.0, raw_cosine))

        # Normalized bounded similarity in [0.0, 1.0] for non-negative similarity ranking
        # Cosine for normalized text embeddings in sentence-transformers is typically in [0.0, 1.0]
        bounded_score = round(max(0.0, min(1.0, raw_cosine)), 4)

        return SemanticSimilarityResult(
            score=bounded_score,
            raw_cosine=round(raw_cosine, 6),
            vector_dimension=self.expected_dimension,
        )
