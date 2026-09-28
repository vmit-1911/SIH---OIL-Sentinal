"""Unit tests for SentenceTransformerEmbedder."""

import pytest
from app.domain.interfaces.embedder import TextEmbedderInterface
from app.infrastructure.embeddings.sentence_transformer import SentenceTransformerEmbedder


def test_embedder_implements_interface():
    """Verify embedder inherits from TextEmbedderInterface."""
    embedder = SentenceTransformerEmbedder()
    assert isinstance(embedder, TextEmbedderInterface)
    assert embedder.dimension == 384
    assert embedder.model_name == "all-MiniLM-L6-v2"


def test_embedder_generates_384_dimensional_vector():
    """Verify real 384-dimensional dense vector generation."""
    embedder = SentenceTransformerEmbedder()
    text = "Hazard: Suspended Heavy Load\nActivity: Crane Operations"
    vector = embedder.embed_text(text)
    
    assert isinstance(vector, list)
    assert len(vector) == 384
    assert all(isinstance(v, float) for v in vector)
    # Check non-zero vector
    assert any(abs(v) > 1e-4 for v in vector)


def test_embedder_deterministic_output():
    """Verify same text produces identical embedding vector."""
    embedder = SentenceTransformerEmbedder()
    text = "Hazard: High Pressure Gas\nActivity: Flange Maintenance"
    vec1 = embedder.embed_text(text)
    vec2 = embedder.embed_text(text)
    
    assert vec1 == vec2


def test_embedder_batch_generation():
    """Verify batch embedding generation."""
    embedder = SentenceTransformerEmbedder()
    texts = [
        "Hazard: Working at Height\nActivity: Derrick Inspection",
        "Hazard: Confined Space Atmosphere\nActivity: Vessel Entry",
    ]
    vectors = embedder.embed_batch(texts)
    
    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    assert len(vectors[1]) == 384
    # Ensure distinct vectors for distinct inputs
    assert vectors[0] != vectors[1]


def test_embedder_empty_text_raises_value_error():
    """Verify empty input string raises ValueError."""
    embedder = SentenceTransformerEmbedder()
    with pytest.raises(ValueError, match="Input text for embedding generation cannot be empty"):
        embedder.embed_text("   ")


def test_embedder_batch_empty_text_raises_value_error():
    """Verify empty item in batch raises ValueError."""
    embedder = SentenceTransformerEmbedder()
    with pytest.raises(ValueError, match="Batch item at index 1 is empty"):
        embedder.embed_batch(["Hazard: Heavy Lifting", "  "])


def test_embedder_invalid_model_raises_explicit_runtime_error():
    """Verify nonexistent model raises explicit RuntimeError."""
    embedder = SentenceTransformerEmbedder(model_name="nonexistent_fake_model_xyz_9999")
    with pytest.raises(RuntimeError, match="could not be initialized"):
        embedder.embed_text("Test narrative")
