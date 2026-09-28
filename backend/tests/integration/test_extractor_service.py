"""Integration test verifying RuleBasedSafetyExtractor across all 10 synthetic benchmark scenarios."""

import json
from pathlib import Path
import pytest

from app.domain.extraction.rule_based_extractor import RuleBasedSafetyExtractor


@pytest.fixture
def synthetic_reports():
    """Load all 10 synthetic safety reports from test data fixture."""
    fixture_path = Path(__file__).resolve().parent.parent.parent / "data" / "synthetic" / "sample_safety_reports.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_extractor_on_all_synthetic_scenarios(synthetic_reports):
    """Run extractor across all 10 synthetic scenarios and verify consistency."""
    extractor = RuleBasedSafetyExtractor()

    assert len(synthetic_reports) == 10

    for idx, report in enumerate(synthetic_reports):
        raw_text = report["raw_text"]
        context = extractor.extract_safety_event_context(raw_text)

        # 1. Text preservation check
        assert context.original_text == raw_text
        assert len(context.normalized_text) > 0

        # 2. Evidence span validity check (every single extracted span must match normalized text)
        for span in context.all_evidence_spans:
            match_in_text = context.normalized_text[span.start_char:span.end_char]
            assert match_in_text == span.text, (
                f"Scenario {idx+1} ({report['scenario_id']}) span mismatch: '{match_in_text}' != '{span.text}'"
            )

        # 3. Scenario-specific checks
        scenario_id = report["scenario_id"]

        if scenario_id == "SYNTH_SCENARIO_01_CLEAR_SIF_PRECURSOR":
            assert context.activity.canonical_name == "Casing Running Operation"
            assert any("Suspended" in h.canonical_name for h in context.hazards)
            assert any("Lifting Line" in b.canonical_name for b in context.barrier_failures)

        elif scenario_id == "SYNTH_SCENARIO_02_HIGH_PRESSURE_NEAR_MISS":
            assert any("High Pressure" in h.canonical_name for h in context.hazards)
            assert any("Energy Isolation" in b.canonical_name for b in context.barrier_failures)

        elif scenario_id == "SYNTH_SCENARIO_04_BARRIER_FAILURE_HEIGHT":
            assert any("Height" in h.canonical_name for h in context.hazards)
            assert any("Fall Protection" in b.canonical_name for b in context.barrier_failures)
            assert any("Derrickman" in p.canonical_name for p in context.people_roles)

        elif scenario_id == "SYNTH_SCENARIO_06_MULTIPLE_LSR_SIGNALS":
            assert any("Confined Space" in h.canonical_name for h in context.hazards)
            assert any("Confined Space Control" in b.canonical_name for b in context.barrier_failures)

        elif scenario_id == "SYNTH_SCENARIO_07_NEGATED_HAZARD":
            # Both gas leak and pressure buildup should be detected as negated
            assert any(h.is_negated for h in context.hazards)
            # Active energy sources should be empty
            assert len(context.energy_sources) == 0

        elif scenario_id == "SYNTH_SCENARIO_10_SHORT_OBSERVATION":
            assert any("Height" in h.canonical_name for h in context.hazards)
            assert any("Fall Protection" in b.canonical_name for b in context.barrier_failures)
