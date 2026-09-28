"""Unit tests for IOGP Report 459 taxonomy loader."""

from app.domain.taxonomy.loader import get_default_taxonomy


def test_default_taxonomy_loaded(loaded_taxonomy):
    """Verify IOGP Report 459 (2018) taxonomy loads with exact 9 rules."""
    assert loaded_taxonomy.taxonomy_id == "IOGP_REPORT_459"
    assert loaded_taxonomy.authority == "IOGP"
    assert loaded_taxonomy.version == "2018"
    assert loaded_taxonomy.active is True
    assert len(loaded_taxonomy.rules) == 9


def test_all_9_iogp_rules_present(loaded_taxonomy):
    """Verify each of the 9 IOGP Life-Saving Rules is accurately represented."""
    expected_codes = {
        "LSR_01_BYPASS_SAFETY_CONTROLS",
        "LSR_02_CONFINED_SPACE",
        "LSR_03_DRIVING",
        "LSR_04_ENERGY_ISOLATION",
        "LSR_05_HOT_WORK",
        "LSR_06_LINE_OF_FIRE",
        "LSR_07_SAFE_MECHANICAL_LIFTING",
        "LSR_08_WORK_AUTHORIZATION",
        "LSR_09_WORKING_AT_HEIGHT",
    }
    actual_codes = set(loaded_taxonomy.rule_codes)
    assert expected_codes == actual_codes


def test_rule_detection_patterns(loaded_taxonomy):
    """Verify detection patterns exist for each rule."""
    for rule in loaded_taxonomy.rules:
        assert len(rule.detection_patterns) > 0
        assert rule.active is True
        assert rule.name != ""
        assert rule.description != ""
