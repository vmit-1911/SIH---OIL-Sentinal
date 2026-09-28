"""Unit tests evaluating synthetic precursor pairs from data/synthetic/similarity_fixtures.json."""

import json
from pathlib import Path
import pytest
from app.domain.precursor.formatter import PrecursorTextFormatter
from app.domain.precursor.model import StructuredSIFPrecursor
from app.domain.similarity.hybrid import HybridPrecursorSimilarity
from app.infrastructure.embeddings.sentence_transformer import SentenceTransformerEmbedder


@pytest.fixture(scope="module")
def embedder():
    return SentenceTransformerEmbedder()


@pytest.fixture(scope="module")
def hybrid_engine():
    return HybridPrecursorSimilarity(structured_weight=0.5, semantic_weight=0.5)


def test_synthetic_similarity_fixtures(embedder, hybrid_engine):
    """Verify all synthetic precursor test pairs score within their expected similarity ranges."""
    fixture_path = Path("data/synthetic/similarity_fixtures.json")
    assert fixture_path.exists(), "Synthetic fixtures file must exist"

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    pairs = data["synthetic_pairs"]
    assert len(pairs) >= 8

    for item in pairs:
        pair_id = item["pair_id"]
        rep1 = item["report_1"]
        rep2 = item["report_2"]
        min_expected, max_expected = item["expected_similarity_range"]

        # Build precursor domain objects
        p1 = StructuredSIFPrecursor(**rep1["precursor"]) if rep1["precursor"] else None
        p2 = StructuredSIFPrecursor(**rep2["precursor"]) if rep2["precursor"] else None

        # Build text embeddings
        text1 = PrecursorTextFormatter.format_to_text(p1)
        text2 = PrecursorTextFormatter.format_to_text(p2)

        vec1 = embedder.embed_text(text1) if text1 else None
        vec2 = embedder.embed_text(text2) if text2 else None

        # Compute hybrid similarity
        res = hybrid_engine.compute_hybrid_similarity(
            precursor_a=p1,
            precursor_b=p2,
            vec_a=vec1,
            vec_b=vec2,
        )

        score = res.hybrid_score
        assert min_expected <= score <= max_expected, (
            f"Pair {pair_id} score {score} is outside expected range [{min_expected}, {max_expected}]. "
            f"Structured: {res.structured_score}, Semantic: {res.semantic_score}"
        )
