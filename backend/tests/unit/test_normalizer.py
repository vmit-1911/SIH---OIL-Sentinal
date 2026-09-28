"""Unit tests for deterministic text normalizer."""

from app.domain.extraction.normalizer import TextNormalizer


def test_normalizer_empty_and_none():
    """Verify safe handling of empty and None inputs."""
    res1 = TextNormalizer.normalize(None)
    assert res1.original_text == ""
    assert res1.normalized_text == ""
    assert res1.sentence_spans == []

    res2 = TextNormalizer.normalize("   ")
    assert res2.original_text == "   "
    assert res2.normalized_text == ""


def test_normalizer_whitespace_and_unicode():
    """Verify whitespace reduction and unicode NFKC normalization."""
    raw = "While  running\t 9-5/8 inch \n\n casing at Rig-04...   Two floormen escaped."
    res = TextNormalizer.normalize(raw)
    assert "  " not in res.normalized_text
    assert "\t" not in res.normalized_text
    assert "\n" not in res.normalized_text
    assert res.normalized_text.startswith("While running 9-5/8 inch casing at Rig-04...")
    assert res.normalized_text.endswith("Two floormen escaped.")


def test_normalizer_sentence_segmentation():
    """Verify sentence boundary segmentation and character spans."""
    raw = "First sentence here. Second sentence here! Third sentence?"
    res = TextNormalizer.normalize(raw)
    assert len(res.sentence_spans) == 3

    for start, end in res.sentence_spans:
        sentence = res.normalized_text[start:end]
        assert len(sentence) > 0
        assert sentence in ["First sentence here.", "Second sentence here!", "Third sentence?"]
