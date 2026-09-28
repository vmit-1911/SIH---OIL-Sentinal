"""Unit tests for RuleBasedSafetyExtractor."""

import pytest
from app.domain.enums import EvidenceStrength
from app.domain.extraction.rule_based_extractor import RuleBasedSafetyExtractor


@pytest.fixture
def extractor():
    """Create RuleBasedSafetyExtractor instance."""
    return RuleBasedSafetyExtractor()


def test_extractor_clear_sif_precursor(extractor):
    """Verify extraction of mechanical lifting SIF precursor with exact spans."""
    raw = (
        "While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung "
        "across the rig floor, narrowly missing two floormen who jumped out of the way. No injuries occurred."
    )
    context = extractor.extract_safety_event_context(raw)

    # 1. Activity
    assert context.activity is not None
    assert context.activity.canonical_name == "Casing Running Operation"

    # 2. Hazard & Energy Sources
    hazard_names = [h.canonical_name for h in context.hazards]
    assert "Suspended Heavy Load" in hazard_names
    energy_names = [e.canonical_name for e in context.energy_sources]
    assert any("GRAVITY" in e for e in energy_names)

    # 3. Equipment
    equip_names = [eq.canonical_name for eq in context.equipment]
    assert "Air Winch & Elevator" in equip_names

    # 4. Barrier Failure
    barrier_names = [b.canonical_name for b in context.barrier_failures]
    assert "Lifting Line / Rigging Failure" in barrier_names

    # 5. Exposure
    exposure_names = [ex.canonical_name for ex in context.exposure]
    assert "Personnel in Line of Fire / Swing Path" in exposure_names

    # 6. People Roles
    role_names = [p.canonical_name for p in context.people_roles]
    assert "Floorman / Roughneck" in role_names

    # 7. Verify all evidence spans match normalized text perfectly
    assert len(context.all_evidence_spans) > 0
    for span in context.all_evidence_spans:
        extracted_substring = context.normalized_text[span.start_char:span.end_char]
        assert extracted_substring == span.text, f"Span mismatch: '{extracted_substring}' != '{span.text}'"


def test_extractor_negated_hazard(extractor):
    """Verify that a negated hazard is correctly marked is_negated=True."""
    raw = "Routine inspection was conducted on mud pump discharge line. No gas leak occurred during the shift."
    context = extractor.extract_safety_event_context(raw)

    gas_leak_hazard = next((h for h in context.hazards if "Hydrocarbon" in h.canonical_name), None)
    assert gas_leak_hazard is not None
    assert gas_leak_hazard.is_negated is True

    # Energy source should NOT include the negated gas leak
    assert not any("CHEMICAL_FLAMMABLE" in e.canonical_name for e in context.energy_sources)


def test_extractor_entities_dict(extractor):
    """Verify extract_entities produces valid dictionary representation of SafetyEventContext."""
    import asyncio
    raw = (
        "During mast maintenance on the monkey board at 25 meters height, a derrickman unhooked his full body "
        "harness lanyard from the inertia reel without 100% tie-off."
    )
    entities = asyncio.run(extractor.extract_entities(raw))

    assert "hazards" in entities
    assert "activity" in entities
    assert "barrier_failures" in entities
    assert "exposure" in entities
    assert any(h["canonical_name"] == "Working at Height Fall Exposure" for h in entities["hazards"])



def test_extractor_minimal_text(extractor):
    """Verify safe handling of short, ambiguous, or empty text."""
    context_empty = extractor.extract_safety_event_context("")
    assert context_empty.activity is None
    assert context_empty.hazards == []
    assert context_empty.all_evidence_spans == []

    context_minimal = extractor.extract_safety_event_context("Observed unsafe condition near compressor area.")
    assert context_minimal.normalized_text == "Observed unsafe condition near compressor area."
    assert context_minimal.activity is None
