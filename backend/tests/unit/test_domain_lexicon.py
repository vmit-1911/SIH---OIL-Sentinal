"""Unit tests for domain lexicon loading and validation."""

from app.domain.lexicon.loader import get_default_safety_lexicon


def test_lexicon_schema_validation():
    """Verify that default safety lexicon loads and parses cleanly."""
    lexicon = get_default_safety_lexicon()
    assert lexicon.lexicon_id == "OIL_SAFETY_LEXICON_V1"
    assert lexicon.version == "1.0.0"
    assert len(lexicon.hazards) > 0
    assert len(lexicon.activities) > 0
    assert len(lexicon.equipment) > 0
    assert len(lexicon.barrier_failures) > 0
    assert len(lexicon.exposure) > 0
    assert len(lexicon.people_roles) > 0


def test_lexicon_patterns_not_empty():
    """Verify that all entries have non-empty patterns."""
    lexicon = get_default_safety_lexicon()
    for cat_name, entries in [
        ("hazards", lexicon.hazards),
        ("activities", lexicon.activities),
        ("equipment", lexicon.equipment),
        ("barrier_failures", lexicon.barrier_failures),
        ("exposure", lexicon.exposure),
    ]:
        for entry in entries:
            assert len(entry.patterns) > 0, f"Entry {entry.canonical_name} in {cat_name} has empty patterns"
            assert entry.canonical_name != ""
