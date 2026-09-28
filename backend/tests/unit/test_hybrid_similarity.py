"""Unit tests for HybridPrecursorSimilarity."""

import pytest
from app.domain.similarity.hybrid import HybridPrecursorSimilarity


def test_hybrid_similarity_dual_modality():
    """Verify dual modality weighted combination."""
    engine = HybridPrecursorSimilarity(structured_weight=0.6, semantic_weight=0.4)
    p1 = {
        "hazard": "Suspended Load",
        "potential_consequence": "FATALITY",
        "life_saving_rule": "LSR_03_MECHANICAL_LIFTING",
    }
    p2 = {
        "hazard": "Suspended Load",
        "potential_consequence": "FATALITY",
        "life_saving_rule": "LSR_03_MECHANICAL_LIFTING",
    }
    vec1 = [0.1] * 384
    vec2 = [0.1] * 384

    res = engine.compute_hybrid_similarity(p1, p2, vec1, vec2)
    assert res.hybrid_score == 1.0
    assert res.structured_score == 1.0
    assert res.semantic_score == 1.0
    assert res.mode == "FULL_HYBRID"
    assert res.structured_weight == 0.6
    assert res.semantic_weight == 0.4
    assert res.comparison_metadata["fusion_strategy"] == "DUAL_MODALITY_WEIGHTED"


def test_hybrid_similarity_structured_only_fallback():
    """Verify fallback to structured score when embeddings are missing."""
    engine = HybridPrecursorSimilarity()
    p1 = {"hazard": "Working at Height Fall Exposure", "life_saving_rule": "LSR_09_WORKING_AT_HEIGHT"}
    p2 = {"hazard": "Working at Height Fall Exposure", "life_saving_rule": "LSR_09_WORKING_AT_HEIGHT"}
    
    res = engine.compute_hybrid_similarity(p1, p2, vec_a=None, vec_b=None)
    assert res.hybrid_score == 1.0
    assert res.structured_score == 1.0
    assert res.semantic_score is None
    assert res.mode == "STRUCTURED_ONLY_FALLBACK"
    assert res.structured_weight == 1.0
    assert res.semantic_weight == 0.0
    assert res.comparison_metadata["fusion_strategy"] == "STRUCTURED_ONLY_FALLBACK"


def test_hybrid_similarity_semantic_only_fallback():
    """Verify fallback to semantic score when structured precursors are missing."""
    engine = HybridPrecursorSimilarity()
    vec1 = [1.0] + [0.0] * 383
    vec2 = [1.0] + [0.0] * 383

    res = engine.compute_hybrid_similarity(precursor_a=None, precursor_b=None, vec_a=vec1, vec_b=vec2)
    assert res.hybrid_score == 1.0
    assert res.structured_score is None
    assert res.semantic_score == 1.0
    assert res.mode == "SEMANTIC_ONLY_FALLBACK"
    assert res.structured_weight == 0.0
    assert res.semantic_weight == 1.0
    assert res.comparison_metadata["fusion_strategy"] == "SEMANTIC_ONLY_FALLBACK"


def test_hybrid_similarity_no_data_available():
    """Verify score is 0.0 when neither modality is available."""
    engine = HybridPrecursorSimilarity()
    res = engine.compute_hybrid_similarity(None, None, None, None)
    assert res.hybrid_score == 0.0
    assert res.mode == "NO_DATA_AVAILABLE"
    assert res.structured_weight == 0.0
    assert res.semantic_weight == 0.0
    assert res.comparison_metadata["fusion_strategy"] == "NO_DATA_AVAILABLE"


def test_hybrid_similarity_invalid_weights_raise_value_error():
    """Verify invalid weights raise ValueError."""
    with pytest.raises(ValueError, match="Similarity weights must be non-negative"):
        HybridPrecursorSimilarity(structured_weight=-0.5, semantic_weight=0.5)

    with pytest.raises(ValueError, match="At least one similarity weight must be greater than zero"):
        HybridPrecursorSimilarity(structured_weight=0.0, semantic_weight=0.0)
