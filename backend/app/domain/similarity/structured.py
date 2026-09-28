"""Dimension-aware structured precursor similarity engine."""

import re
from typing import Any, Dict, List, Optional, Set
from app.domain.precursor.model import StructuredSIFPrecursor
from app.domain.similarity.models import StructuredSimilarityResult


class StructuredPrecursorSimilarity:
    """Calculates deterministic dimension-aware similarity between structured SIF precursors.
    
    Examines the 7 precursor dimensions (hazard, activity, barrier_failure, exposure,
    potential_consequence, life_saving_rule, location). Dimensions missing in either
    precursor are ignored rather than penalized as mismatches.
    """

    DIMENSIONS = [
        "hazard",
        "activity",
        "barrier_failure",
        "exposure",
        "potential_consequence",
        "life_saving_rule",
        "location",
    ]

    # Default relative importance weights for dimensions when present
    DEFAULT_WEIGHTS: Dict[str, float] = {
        "hazard": 2.0,
        "activity": 1.0,
        "barrier_failure": 1.5,
        "exposure": 1.0,
        "potential_consequence": 1.0,
        "life_saving_rule": 1.5,
        "location": 0.5,
    }

    def __init__(self, dimension_weights: Optional[Dict[str, float]] = None):
        self.weights = dimension_weights or self.DEFAULT_WEIGHTS

    @staticmethod
    def _tokenize(text: str) -> Set[str]:
        """Extract lowercase alphanumeric word tokens."""
        return set(re.findall(r"\b[a-z0-9]+\b", text.lower()))

    @classmethod
    def _compute_text_similarity(cls, text_a: str, text_b: str) -> float:
        """Compute normalized deterministic token similarity between two strings."""
        norm_a = text_a.strip().lower()
        norm_b = text_b.strip().lower()

        if norm_a == norm_b:
            return 1.0

        tokens_a = cls._tokenize(norm_a)
        tokens_b = cls._tokenize(norm_b)

        if not tokens_a or not tokens_b:
            return 0.0

        intersection = tokens_a.intersection(tokens_b)
        union = tokens_a.union(tokens_b)

        if not union:
            return 0.0

        # Jaccard index
        jaccard = len(intersection) / len(union)
        # Token overlap ratio relative to the shorter text
        overlap_min = len(intersection) / min(len(tokens_a), len(tokens_b))

        # Balanced token similarity
        return round(0.5 * jaccard + 0.5 * overlap_min, 4)

    @classmethod
    def _compute_consequence_similarity(cls, c_a: str, c_b: str) -> float:
        """Compute similarity between potential consequence categories."""
        norm_a = c_a.strip().upper()
        norm_b = c_b.strip().upper()

        if norm_a == norm_b:
            return 1.0

        # Severity rank map
        severity_rank = {
            "FATALITY": 5,
            "PERMANENT_DISABLING_INJURY": 4,
            "MAJOR_PROCESS_SAFETY_EVENT": 4,
            "LOST_TIME_INJURY": 3,
            "MEDICAL_TREATMENT": 2,
            "FIRST_AID": 1,
            "LOW_IMPACT": 0,
        }

        rank_a = severity_rank.get(norm_a, 2)
        rank_b = severity_rank.get(norm_b, 2)

        diff = abs(rank_a - rank_b)
        if diff == 0:
            return 1.0
        elif diff == 1:
            return 0.75
        elif diff == 2:
            return 0.50
        elif diff == 3:
            return 0.25
        else:
            return 0.0

    @classmethod
    def _compute_lsr_similarity(cls, lsr_a: str, lsr_b: str) -> float:
        """Compute similarity between IOGP Life-Saving Rules."""
        norm_a = lsr_a.strip().upper()
        norm_b = lsr_b.strip().upper()

        if norm_a == norm_b:
            return 1.0

        # Compare rule codes if prefixed (e.g. LSR_03)
        code_a = norm_a.split("_")[1] if norm_a.startswith("LSR_") and len(norm_a.split("_")) > 1 else norm_a
        code_b = norm_b.split("_")[1] if norm_b.startswith("LSR_") and len(norm_b.split("_")) > 1 else norm_b

        if code_a == code_b:
            return 1.0

        # Otherwise compare token similarity of rule description
        return cls._compute_text_similarity(norm_a, norm_b)

    def _get_dimension_value(self, obj: Any, dim: str) -> Optional[str]:
        """Extract dimension string from StructuredSIFPrecursor or Dict."""
        if isinstance(obj, StructuredSIFPrecursor):
            val = getattr(obj, dim, None)
        elif isinstance(obj, dict):
            val = obj.get(dim)
        else:
            return None

        if val is None:
            return None
        val_str = str(val).strip()
        if not val_str or val_str in ("*", "UNKNOWN", "OTHER"):
            return None
        return val_str

    def compute_similarity(
        self,
        precursor_a: Optional[Any],
        precursor_b: Optional[Any],
    ) -> StructuredSimilarityResult:
        """Compute dimension-level similarity between two precursor objects."""
        dimension_scores: Dict[str, Optional[float]] = {}
        weighted_sum = 0.0
        total_weight = 0.0
        compared_count = 0

        for dim in self.DIMENSIONS:
            val_a = self._get_dimension_value(precursor_a, dim)
            val_b = self._get_dimension_value(precursor_b, dim)

            # If either precursor lacks this dimension, ignore it (do not penalize as mismatch)
            if val_a is None or val_b is None:
                dimension_scores[dim] = None
                continue

            # Both precursors have this dimension -> compare
            if dim == "potential_consequence":
                dim_score = self._compute_consequence_similarity(val_a, val_b)
            elif dim == "life_saving_rule":
                dim_score = self._compute_lsr_similarity(val_a, val_b)
            else:
                dim_score = self._compute_text_similarity(val_a, val_b)

            dimension_scores[dim] = dim_score
            w = self.weights.get(dim, 1.0)
            weighted_sum += dim_score * w
            total_weight += w
            compared_count += 1

        if total_weight > 0 and compared_count > 0:
            final_score = round(min(1.0, max(0.0, weighted_sum / total_weight)), 4)
        else:
            final_score = 0.0

        return StructuredSimilarityResult(
            score=final_score,
            dimension_scores=dimension_scores,
            compared_dimensions=compared_count,
        )
