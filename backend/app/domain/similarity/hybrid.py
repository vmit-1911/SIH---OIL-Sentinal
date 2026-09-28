"""Weighted hybrid precursor similarity engine."""

from typing import Any, Dict, List, Optional
from app.domain.similarity.models import (
    HybridSimilarityResult,
    SemanticSimilarityResult,
    StructuredSimilarityResult,
)
from app.domain.similarity.semantic import CosineSemanticSimilarity
from app.domain.similarity.structured import StructuredPrecursorSimilarity


class HybridPrecursorSimilarity:
    """Combines structured dimension similarity with semantic vector similarity.
    
    Baseline Formulation:
        hybrid_score = (w_struct * struct_score) + (w_sem * sem_score)
        where w_struct + w_sem == 1.0 (normalized)
        
    Engineering Defaults:
        - structured_weight: 0.5 (structural dimension alignment)
        - semantic_weight: 0.5 (dense semantic embedding proximity)
        These defaults are baseline heuristics requiring calibration on OIL operational data.
        
    Missing Data Behavior:
        - If semantic embedding is unavailable on either side:
          hybrid_score relies 100% on structured similarity (if compared_dimensions > 0).
        - If structured precursor is unavailable on either side:
          hybrid_score relies 100% on semantic vector similarity (if vectors are valid).
        - If neither is available: hybrid_score = 0.0 with explanatory metadata.
    """

    def __init__(
        self,
        structured_weight: float = 0.5,
        semantic_weight: float = 0.5,
        structured_engine: Optional[StructuredPrecursorSimilarity] = None,
        semantic_engine: Optional[CosineSemanticSimilarity] = None,
    ):
        if structured_weight < 0 or semantic_weight < 0:
            raise ValueError("Similarity weights must be non-negative")
        if structured_weight == 0 and semantic_weight == 0:
            raise ValueError("At least one similarity weight must be greater than zero")

        # Normalize weights so they sum to 1.0
        total_w = structured_weight + semantic_weight
        self.structured_weight = structured_weight / total_w
        self.semantic_weight = semantic_weight / total_w

        self.structured_engine = structured_engine or StructuredPrecursorSimilarity()
        self.semantic_engine = semantic_engine or CosineSemanticSimilarity()

    def compute_hybrid_similarity(
        self,
        precursor_a: Optional[Any],
        precursor_b: Optional[Any],
        vec_a: Optional[List[float]],
        vec_b: Optional[List[float]],
    ) -> HybridSimilarityResult:
        """Compute comprehensive hybrid similarity between two precursor records."""
        # 1. Structured similarity
        struct_res: Optional[StructuredSimilarityResult] = None
        has_struct = precursor_a is not None and precursor_b is not None
        if has_struct:
            struct_res = self.structured_engine.compute_similarity(precursor_a, precursor_b)

        # 2. Semantic vector similarity
        sem_res: Optional[SemanticSimilarityResult] = None
        has_semantic = vec_a is not None and vec_b is not None
        if has_semantic:
            try:
                sem_res = self.semantic_engine.compute_similarity(vec_a, vec_b)
            except ValueError:
                sem_res = None

        # 3. Weighted hybrid fusion
        dimension_scores: Dict[str, Optional[float]] = struct_res.dimension_scores if struct_res else {}
        compared_dims = struct_res.compared_dimensions if struct_res else 0

        struct_score = struct_res.score if (struct_res and compared_dims > 0) else None
        sem_score = sem_res.score if sem_res else None

        metadata: Dict[str, Any] = {
            "has_structured_data": has_struct and compared_dims > 0,
            "has_semantic_data": sem_res is not None,
            "raw_cosine": sem_res.raw_cosine if sem_res else None,
        }

        # Determine explicit scoring mode and modality weights
        if struct_score is not None and sem_score is not None:
            # Both modalities available: FULL_HYBRID
            mode = "FULL_HYBRID"
            effective_struct_weight = self.structured_weight
            effective_sem_weight = self.semantic_weight
            hybrid_score = round(
                (effective_struct_weight * struct_score) + (effective_sem_weight * sem_score),
                4,
            )
            metadata["fusion_strategy"] = "DUAL_MODALITY_WEIGHTED"
        elif struct_score is not None:
            # Only structured available: STRUCTURED_ONLY_FALLBACK
            mode = "STRUCTURED_ONLY_FALLBACK"
            effective_struct_weight = 1.0
            effective_sem_weight = 0.0
            hybrid_score = struct_score
            metadata["fusion_strategy"] = "STRUCTURED_ONLY_FALLBACK"
        elif sem_score is not None:
            # Only semantic available: SEMANTIC_ONLY_FALLBACK
            mode = "SEMANTIC_ONLY_FALLBACK"
            effective_struct_weight = 0.0
            effective_sem_weight = 1.0
            hybrid_score = sem_score
            metadata["fusion_strategy"] = "SEMANTIC_ONLY_FALLBACK"
        else:
            # Neither available: NO_DATA_AVAILABLE
            mode = "NO_DATA_AVAILABLE"
            effective_struct_weight = 0.0
            effective_sem_weight = 0.0
            hybrid_score = 0.0
            metadata["fusion_strategy"] = "NO_DATA_AVAILABLE"

        metadata["mode"] = mode

        return HybridSimilarityResult(
            hybrid_score=min(1.0, max(0.0, hybrid_score)),
            structured_score=struct_score,
            semantic_score=sem_score,
            structured_weight=effective_struct_weight,
            semantic_weight=effective_sem_weight,
            mode=mode,
            dimension_scores=dimension_scores,
            compared_dimensions=compared_dims,
            comparison_metadata=metadata,
        )

