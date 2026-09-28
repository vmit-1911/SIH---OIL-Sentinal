"""Integration test for the decoupled Phase 1B pipeline: Extractor -> SIF Engine & LSR Mapper."""

import json
from pathlib import Path
import pytest

from app.domain.enums import ActualOutcome, PotentialOutcome, SIFClassification
from app.domain.extraction.rule_based_extractor import RuleBasedSafetyExtractor
from app.domain.lsr.mapper import LSRMapper
from app.domain.sif.screening import SIFScreeningEngine


@pytest.fixture
def synthetic_reports():
    fixture_path = Path(__file__).resolve().parent.parent.parent / "data" / "synthetic" / "sample_safety_reports.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_decoupled_pipeline_execution(synthetic_reports):
    """Verify that SIF Screening Engine and LSR Mapper execute independently on SafetyEventContext."""
    extractor = RuleBasedSafetyExtractor()
    sif_engine = SIFScreeningEngine()
    lsr_mapper = LSRMapper()

    for report in synthetic_reports:
        raw_text = report["raw_text"]
        actual_severity = ActualOutcome(report["actual_severity"])

        # Stage 1: Extraction
        context = extractor.extract_safety_event_context(raw_text)
        assert context is not None

        # Stage 2A: SIF Screening (Independent)
        sif_result = sif_engine.evaluate_context(context, actual_severity=actual_severity)
        assert sif_result is not None
        assert sif_result.sif_classification in SIFClassification

        # Stage 2B: LSR Mapping (Independent)
        lsr_result = lsr_mapper.map_rules(context)
        assert lsr_result is not None
        assert isinstance(lsr_result.mapped_rules, list)

        # Scenario 1 validation: SIF Potential True + Safe Mechanical Lifting
        if report["scenario_id"] == "SYNTH_SCENARIO_01_CLEAR_SIF_PRECURSOR":
            assert sif_result.sif_classification == SIFClassification.POTENTIAL_SIF
            assert sif_result.potential_severity == PotentialOutcome.FATALITY
            mapped_codes = [m.rule_code for m in lsr_result.mapped_rules]
            assert "LSR_07_SAFE_MECHANICAL_LIFTING" in mapped_codes

        # Scenario 3 validation: Non-SIF + Zero LSRs
        elif report["scenario_id"] == "SYNTH_SCENARIO_03_ROUTINE_NON_SIF":
            assert sif_result.sif_classification == SIFClassification.NON_SIF
            assert len(lsr_result.mapped_rules) == 0

        # Scenario 8 validation: Minimal context -> Undetermined SIF
        elif report["scenario_id"] == "SYNTH_SCENARIO_08_MINIMAL_CONTEXT":
            assert sif_result.sif_classification == SIFClassification.UNDETERMINED
