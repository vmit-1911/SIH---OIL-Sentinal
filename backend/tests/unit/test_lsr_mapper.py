"""Unit tests for IOGP Report 459 Life-Saving Rules Mapping Engine."""

import pytest
from app.domain.extraction.rule_based_extractor import RuleBasedSafetyExtractor
from app.domain.lsr.mapper import LSRMapper


@pytest.fixture
def extractor():
    return RuleBasedSafetyExtractor()


@pytest.fixture
def lsr_mapper():
    return LSRMapper()


def test_lsr_mechanical_lifting_and_line_of_fire(extractor, lsr_mapper):
    """Verify mapping of Mechanical Lifting (Primary) + Line of Fire (Secondary)."""
    raw = (
        "While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung "
        "across the rig floor, narrowly missing two floormen who jumped out of the way."
    )
    context = extractor.extract_safety_event_context(raw)
    result = lsr_mapper.map_rules(context)

    rule_codes = [m.rule_code for m in result.mapped_rules]
    assert "LSR_07_SAFE_MECHANICAL_LIFTING" in rule_codes
    assert "LSR_06_LINE_OF_FIRE" in rule_codes

    # Primary should be Safe Mechanical Lifting due to root rigging failure
    assert result.primary_rule is not None
    assert result.primary_rule.rule_code == "LSR_07_SAFE_MECHANICAL_LIFTING"


def test_lsr_working_at_height(extractor, lsr_mapper):
    """Verify Working at Height mapping."""
    raw = (
        "During mast maintenance on the monkey board at 25 meters height, a derrickman unhooked his full body "
        "harness lanyard without 100% tie-off."
    )
    context = extractor.extract_safety_event_context(raw)
    result = lsr_mapper.map_rules(context)

    rule_codes = [m.rule_code for m in result.mapped_rules]
    assert "LSR_09_WORKING_AT_HEIGHT" in rule_codes
    assert result.primary_rule is not None
    assert result.primary_rule.rule_code == "LSR_09_WORKING_AT_HEIGHT"


def test_lsr_energy_isolation(extractor, lsr_mapper):
    """Verify Energy Isolation mapping."""
    raw = (
        "Technician began unbolting high pressure flange on production manifold. "
        "Pressurized gas vented because double-block-and-bleed valve was not fully closed."
    )
    context = extractor.extract_safety_event_context(raw)
    result = lsr_mapper.map_rules(context)

    rule_codes = [m.rule_code for m in result.mapped_rules]
    assert "LSR_04_ENERGY_ISOLATION" in rule_codes


def test_lsr_confined_space(extractor, lsr_mapper):
    """Verify Confined Space mapping."""
    raw = (
        "Contractor entered crude oil storage tank compartment for sludge cleaning "
        "without gas test clearance certificate and without a dedicated standby man."
    )
    context = extractor.extract_safety_event_context(raw)
    result = lsr_mapper.map_rules(context)

    rule_codes = [m.rule_code for m in result.mapped_rules]
    assert "LSR_02_CONFINED_SPACE" in rule_codes


def test_lsr_hot_work(extractor, lsr_mapper):
    """Verify Hot Work mapping."""
    raw = "Contractor was welding a pipe support bracket near flammable gas area."
    context = extractor.extract_safety_event_context(raw)
    result = lsr_mapper.map_rules(context)

    rule_codes = [m.rule_code for m in result.mapped_rules]
    assert "LSR_05_HOT_WORK" in rule_codes


def test_lsr_driving(extractor, lsr_mapper):
    """Verify Driving mapping."""
    raw = "Bowser truck overspeeding on access road with driver not wearing seatbelt."
    context = extractor.extract_safety_event_context(raw)
    result = lsr_mapper.map_rules(context)

    rule_codes = [m.rule_code for m in result.mapped_rules]
    assert "LSR_03_DRIVING" in rule_codes


def test_lsr_bypassing_safety_controls(extractor, lsr_mapper):
    """Verify Bypassing Safety Controls mapping."""
    raw = "Safety switch interlock bypassed on compressor unit."
    context = extractor.extract_safety_event_context(raw)
    result = lsr_mapper.map_rules(context)

    rule_codes = [m.rule_code for m in result.mapped_rules]
    assert "LSR_01_BYPASS_SAFETY_CONTROLS" in rule_codes


def test_lsr_work_authorization(extractor, lsr_mapper):
    """Verify Work Authorization mapping."""
    raw = "Work started on manifold without permit to work."
    context = extractor.extract_safety_event_context(raw)
    result = lsr_mapper.map_rules(context)

    rule_codes = [m.rule_code for m in result.mapped_rules]
    assert "LSR_08_WORK_AUTHORIZATION" in rule_codes


def test_lsr_no_matching_rules_housekeeping(extractor, lsr_mapper):
    """Verify that routine housekeeping yields zero LSR mappings."""
    raw = "Empty paint cans and cleaning rags left unattended near workshop entrance."
    context = extractor.extract_safety_event_context(raw)
    result = lsr_mapper.map_rules(context)

    assert len(result.mapped_rules) == 0
    assert result.primary_rule is None
