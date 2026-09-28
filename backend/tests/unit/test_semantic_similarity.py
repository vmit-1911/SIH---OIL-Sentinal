"""Unit tests for CosineSemanticSimilarity."""

import pytest
from app.domain.similarity.semantic import CosineSemanticSimilarity


def test_semantic_similarity_identical_vectors():
    """Verify identical vectors produce score 1.0."""
    engine = CosineSemanticSimilarity(expected_dimension=4)
    vec = [0.5, 0.5, 0.5, 0.5]
    res = engine.compute_similarity(vec, vec)
    assert res.score == 1.0
    assert res.raw_cosine == 1.0
    assert res.vector_dimension == 4


def test_semantic_similarity_orthogonal_vectors():
    """Verify orthogonal vectors produce cosine 0.0."""
    engine = CosineSemanticSimilarity(expected_dimension=4)
    vec1 = [1.0, 0.0, 0.0, 0.0]
    vec2 = [0.0, 1.0, 0.0, 0.0]
    res = engine.compute_similarity(vec1, vec2)
    assert res.score == 0.0
    assert res.raw_cosine == 0.0


def test_semantic_similarity_similar_vectors():
    """Verify vectors with high angle produce proportional score."""
    engine = CosineSemanticSimilarity(expected_dimension=3)
    vec1 = [1.0, 2.0, 3.0]
    vec2 = [1.1, 1.9, 3.1]
    res = engine.compute_similarity(vec1, vec2)
    assert res.score > 0.95
    assert res.raw_cosine > 0.95


def test_semantic_similarity_zero_vector():
    """Verify zero vector is handled safely and produces 0.0."""
    engine = CosineSemanticSimilarity(expected_dimension=3)
    vec1 = [0.0, 0.0, 0.0]
    vec2 = [1.0, 1.0, 1.0]
    res = engine.compute_similarity(vec1, vec2)
    assert res.score == 0.0
    assert res.raw_cosine == 0.0


def test_semantic_similarity_dimension_mismatch_raises_value_error():
    """Verify dimension mismatch raises ValueError."""
    engine = CosineSemanticSimilarity(expected_dimension=384)
    with pytest.raises(ValueError, match="Vector dimensionality mismatch"):
        engine.compute_similarity([0.1] * 384, [0.1] * 100)


def test_semantic_similarity_none_vectors_raise_value_error():
    """Verify None input raises ValueError."""
    engine = CosineSemanticSimilarity(expected_dimension=384)
    with pytest.raises(ValueError, match="Vector embeddings cannot be None"):
        engine.compute_similarity(None, [0.1] * 384)
