"""Unit tests for contextual negation and barrier absence analyzer."""

from app.domain.extraction.negation import NegationAnalyzer
from app.domain.lexicon.loader import get_default_safety_lexicon


def test_hazard_negation_detection():
    """Verify hazard negation detection in preceding context window."""
    lexicon = get_default_safety_lexicon()
    analyzer = NegationAnalyzer(lexicon.negation_config)

    text = "Inspection was conducted and no gas leak occurred during the test."
    match_start = text.find("gas leak")
    match_end = match_start + len("gas leak")

    is_neg, trigger = analyzer.is_hazard_negated(text, match_start, match_end)
    assert is_neg is True
    assert trigger.lower() == "no"


def test_hazard_not_negated():
    """Verify that an active hazard is not falsely marked as negated."""
    lexicon = get_default_safety_lexicon()
    analyzer = NegationAnalyzer(lexicon.negation_config)

    text = "Severe pressurized gas vented from the manifold valve."
    match_start = text.find("pressurized gas")
    match_end = match_start + len("pressurized gas")

    is_neg, trigger = analyzer.is_hazard_negated(text, match_start, match_end)
    assert is_neg is False
    assert trigger is None


def test_barrier_absence_trigger():
    """Verify that safety control terms with absence triggers indicate barrier failure."""
    lexicon = get_default_safety_lexicon()
    analyzer = NegationAnalyzer(lexicon.negation_config)

    text = "Derrickman was working at height without 100% tie-off on monkey board."
    match_start = text.find("100% tie-off")
    match_end = match_start + len("100% tie-off")

    is_absence, trigger = analyzer.is_barrier_absence_triggered(text, match_start, match_end)
    assert is_absence is True
    assert trigger.lower() == "without"


def test_negation_respects_sentence_boundary():
    """Verify negation does not cross preceding sentence boundaries."""
    lexicon = get_default_safety_lexicon()
    analyzer = NegationAnalyzer(lexicon.negation_config)

    text = "No tools were damaged. Severe gas leak occurred in separator."
    match_start = text.find("gas leak")
    match_end = match_start + len("gas leak")

    is_neg, trigger = analyzer.is_hazard_negated(text, match_start, match_end)
    assert is_neg is False
