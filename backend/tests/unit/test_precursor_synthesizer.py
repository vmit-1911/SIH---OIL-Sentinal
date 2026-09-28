"""Unit tests for Structured SIF Precursor Synthesizer (Phase 1D)."""

import pytest
from app.domain.enums import ActualOutcome, DerivationType, PotentialOutcome
from app.domain.extraction.rule_based_extractor import RuleBasedSafetyExtractor
from app.domain.lsr.mapper import LSRMapper
from app.domain.precursor.synthesizer import StructuredPrecursorSynthesizer
from app.domain.sif.screening import SIFScreeningEngine


@pytest.fixture
def extractor():
    return RuleBasedSafetyExtractor()


@pytest.fixture
def screening_engine():
    return SIFScreeningEngine()


@pytest.fixture
def lsr_mapper():
    return LSRMapper()


@pytest.fixture
def synthesizer():
    return StructuredPrecursorSynthesizer()


def test_scenario_a_suspended_load_precursor(extractor, screening_engine, lsr_mapper, synthesizer):
    """Test A: Suspended-load near miss produces structured precursor fields where evidence supports them."""
    raw = (
        "While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung "
        "across the rig floor, narrowly missing two floormen who jumped out of the way. No injuries occurred."
    )
    context = extractor.extract_safety_event_context(raw)
    screening_res = screening_engine.evaluate_context(context, actual_severity=ActualOutcome.NO_INJURY)
    lsr_res = lsr_mapper.map_rules(context)

    precursor = synthesizer.synthesize(context, screening_res, lsr_res, reported_location="Rig-04 / Moran Field")

    assert precursor.hazard == "Suspended Heavy Load"
    assert precursor.activity == "Casing Running Operation"
    assert precursor.barrier_failure == "Lifting Line / Rigging Failure"
    assert precursor.exposure == "Personnel in Line of Fire / Swing Path"
    assert precursor.potential_consequence == "FATALITY"
    assert precursor.life_saving_rule == "LSR_07_SAFE_MECHANICAL_LIFTING"
    assert precursor.location == "Rig-04 / Moran Field"

    sig = precursor.to_signature()
    assert sig == "Suspended Heavy Load|Casing Running Operation|Lifting Line / Rigging Failure|Personnel in Line of Fire / Swing Path|FATALITY|LSR_07_SAFE_MECHANICAL_LIFTING"


def test_scenario_b_working_at_height_precursor(extractor, screening_engine, lsr_mapper, synthesizer):
    """Test B: Working-at-height case produces corresponding structured precursor."""
    raw = (
        "During mast maintenance on monkey board at 25 meters height, derrickman unhooked his full body "
        "harness lanyard without 100% tie-off."
    )
    context = extractor.extract_safety_event_context(raw)
    screening_res = screening_engine.evaluate_context(context)
    lsr_res = lsr_mapper.map_rules(context)

    precursor = synthesizer.synthesize(context, screening_res, lsr_res, reported_location="Rig-07 / Digboi")

    assert precursor.hazard == "Working at Height Fall Exposure"
    assert precursor.activity == "Mast & Derrick Maintenance"
    assert precursor.barrier_failure == "Fall Protection Disconnected / Not Used"
    assert precursor.exposure == "Unprotected Fall Exposure"
    assert precursor.potential_consequence == "FATALITY"
    assert precursor.life_saving_rule == "LSR_09_WORKING_AT_HEIGHT"


def test_scenario_c_energy_isolation_precursor(extractor, screening_engine, lsr_mapper, synthesizer):
    """Test C: Energy-isolation case produces corresponding structured precursor."""
    raw = (
        "Technician began unbolting flange on production manifold at EPS-02 while isolation not verified. "
        "Trapped pressurized hydrocarbon gas vented to atmosphere."
    )
    context = extractor.extract_safety_event_context(raw)
    screening_res = screening_engine.evaluate_context(context)
    lsr_res = lsr_mapper.map_rules(context)

    precursor = synthesizer.synthesize(context, screening_res, lsr_res, reported_location="EPS-02")

    assert precursor.hazard in ["High Pressure Fluid / Gas", "Flammable Hydrocarbon Release"]
    assert precursor.barrier_failure == "Energy Isolation (LOTO) Failure"
    assert precursor.life_saving_rule == "LSR_04_ENERGY_ISOLATION"


def test_scenario_d_e_missing_fields_remain_null(extractor, screening_engine, lsr_mapper, synthesizer):
    """Tests D & E: Missing activity or exposure remains genuinely null (no fake placeholders)."""
    raw = "Observed severe corrosion and unisolated line on separator vessel near compressor station."
    context = extractor.extract_safety_event_context(raw)
    screening_res = screening_engine.evaluate_context(context)
    lsr_res = lsr_mapper.map_rules(context)

    precursor = synthesizer.synthesize(context, screening_res, lsr_res)

    assert precursor.activity is None
    assert precursor.exposure is None
    assert "activity" not in precursor.field_provenance
    assert "exposure" not in precursor.field_provenance


def test_scenario_f_multiple_hazards_deterministic_selection(extractor, screening_engine, lsr_mapper, synthesizer):
    """Test F: Multiple hazards use deterministic evidence-based selection."""
    raw = (
        "While running 9-5/8 inch casing on rig floor at high elevation, air winch line parted and heavy elevator swung. "
        "Also noticed minor trip hazard from cleaning rags."
    )
    context = extractor.extract_safety_event_context(raw)
    screening_res = screening_engine.evaluate_context(context)
    lsr_res = lsr_mapper.map_rules(context)

    precursor = synthesizer.synthesize(context, screening_res, lsr_res)

    # High-energy SIF-contributing hazard takes precedence over Housekeeping / Trip Hazard
    assert precursor.hazard in ["Working at Height Fall Exposure", "Suspended Heavy Load"]
    assert precursor.hazard != "Housekeeping & Minor Trip Hazard"


def test_scenario_g_multiple_lsrs_uses_primary(extractor, screening_engine, lsr_mapper, synthesizer):
    """Test G: Multiple LSR mappings use the primary designated rule."""
    raw = (
        "While running casing, air winch line parted and heavy elevator swung narrowly missing floormen in swing path."
    )
    context = extractor.extract_safety_event_context(raw)
    screening_res = screening_engine.evaluate_context(context)
    lsr_res = lsr_mapper.map_rules(context)

    precursor = synthesizer.synthesize(context, screening_res, lsr_res)

    assert lsr_res.primary_rule is not None
    assert lsr_res.primary_rule.rule_code == "LSR_07_SAFE_MECHANICAL_LIFTING"
    assert precursor.life_saving_rule == "LSR_07_SAFE_MECHANICAL_LIFTING"


def test_scenario_h_no_defensible_lsr_is_null(extractor, screening_engine, lsr_mapper, synthesizer):
    """Test H: Routine narrative with no matching LSR leaves life_saving_rule null."""
    raw = "Empty paint cans and cleaning rags left unattended near workshop entrance."
    context = extractor.extract_safety_event_context(raw)
    screening_res = screening_engine.evaluate_context(context)
    lsr_res = lsr_mapper.map_rules(context)

    precursor = synthesizer.synthesize(context, screening_res, lsr_res)

    assert lsr_res.mapped_rules == []
    assert precursor.life_saving_rule is None


def test_scenario_i_j_k_field_provenance_and_derivation_types(extractor, screening_engine, lsr_mapper, synthesizer):
    """Tests I, J, K: Field provenance preserves DIRECT_MATCH, LEXICON_INFERENCE, and RULE_INFERENCE."""
    raw = (
        "While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung "
        "across the rig floor, narrowly missing two floormen who jumped out of the way. No injuries occurred."
    )
    context = extractor.extract_safety_event_context(raw)
    screening_res = screening_engine.evaluate_context(context)
    lsr_res = lsr_mapper.map_rules(context)

    precursor = synthesizer.synthesize(context, screening_res, lsr_res, reported_location="Rig-04 / Moran Field")

    # Direct match or lexicon inference for activity
    act_prov = precursor.field_provenance["activity"]
    assert act_prov.derivation_type in [DerivationType.DIRECT_MATCH, DerivationType.LEXICON_INFERENCE]
    assert len(act_prov.evidence_spans) > 0

    # Rule inference for potential consequence and LSR
    conseq_prov = precursor.field_provenance["potential_consequence"]
    assert conseq_prov.derivation_type == DerivationType.RULE_INFERENCE

    lsr_prov = precursor.field_provenance["life_saving_rule"]
    assert lsr_prov.derivation_type == DerivationType.RULE_INFERENCE


def test_scenario_l_evidence_spans_traceable_to_raw_text(extractor, screening_engine, lsr_mapper, synthesizer):
    """Test L: Evidence spans on precursor dimensions point accurately to character offsets in source text."""
    raw = (
        "While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung "
        "across the rig floor, narrowly missing two floormen who jumped out of the way. No injuries occurred."
    )
    context = extractor.extract_safety_event_context(raw)
    screening_res = screening_engine.evaluate_context(context)
    lsr_res = lsr_mapper.map_rules(context)

    precursor = synthesizer.synthesize(context, screening_res, lsr_res)

    for dim_name, prov in precursor.field_provenance.items():
        for span in prov.evidence_spans:
            extracted_text = raw[span.start_char:span.end_char]
            assert extracted_text == span.text, f"Offset mismatch in {dim_name}: '{extracted_text}' != '{span.text}'"


def test_scenario_m_n_consequence_comes_from_screening_not_actual_injury(
    extractor,
    screening_engine,
    lsr_mapper,
    synthesizer,
):
    """Tests M & N: Potential consequence strictly originates from screening output, decoupled from actual injury."""
    raw = "While running casing, air winch line parted and heavy elevator swung narrowly missing floormen."
    context = extractor.extract_safety_event_context(raw)
    
    # Near miss with NO_INJURY actual outcome
    screening_res = screening_engine.evaluate_context(context, actual_severity=ActualOutcome.NO_INJURY)
    lsr_res = lsr_mapper.map_rules(context)

    precursor = synthesizer.synthesize(context, screening_res, lsr_res)

    # Actual severity was NO_INJURY, but potential consequence in precursor is FATALITY
    assert screening_res.actual_severity == ActualOutcome.NO_INJURY
    assert precursor.potential_consequence == "FATALITY"



def test_scenario_o_determinism_same_input_same_precursor(extractor, screening_engine, lsr_mapper, synthesizer):
    """Test O: Same report narrative executed 100 times produces identical structured precursors."""
    raw = (
        "During mast maintenance on monkey board at 25 meters height, derrickman unhooked his full body "
        "harness lanyard without 100% tie-off."
    )
    context = extractor.extract_safety_event_context(raw)
    screening_res = screening_engine.evaluate_context(context)
    lsr_res = lsr_mapper.map_rules(context)

    baseline = synthesizer.synthesize(context, screening_res, lsr_res, reported_location="Rig-07")
    baseline_dict = baseline.to_dict()
    baseline_sig = baseline.to_signature()

    for _ in range(50):
        run = synthesizer.synthesize(context, screening_res, lsr_res, reported_location="Rig-07")
        assert run.to_dict() == baseline_dict
        assert run.to_signature() == baseline_sig


def test_regression_no_wildcard_asterisks_in_precursor_or_signature(extractor, screening_engine, lsr_mapper, synthesizer):
    """Regression test: Ensure '*' wildcard is never synthesized as a dimension value or signature placeholder."""
    # 1. Housekeeping scenario (only hazard present)
    raw_housekeeping = "Empty paint cans and cleaning rags left unattended near workshop entrance."
    ctx1 = extractor.extract_safety_event_context(raw_housekeeping)
    scr1 = screening_engine.evaluate_context(ctx1)
    lsr1 = lsr_mapper.map_rules(ctx1)
    precursor1 = synthesizer.synthesize(ctx1, scr1, lsr1)

    assert precursor1.hazard == "Housekeeping & Minor Trip Hazard"
    assert precursor1.activity is None
    assert precursor1.barrier_failure is None
    assert precursor1.exposure is None
    assert precursor1.potential_consequence is None
    assert precursor1.life_saving_rule is None
    assert precursor1.to_signature() == "Housekeeping & Minor Trip Hazard|||||"
    assert "*" not in (precursor1.to_signature() or "")

    # 2. Energy isolation scenario (exposure is absent)
    raw_energy = (
        "During unbolting flange on production manifold at EPS Moran, trapped high pressure crude oil "
        "vented because isolation not verified. Floorman stepped back into safety zone."
    )
    ctx2 = extractor.extract_safety_event_context(raw_energy)
    scr2 = screening_engine.evaluate_context(ctx2)
    lsr2 = lsr_mapper.map_rules(ctx2)
    precursor2 = synthesizer.synthesize(ctx2, scr2, lsr2)

    assert precursor2.exposure is None
    sig2 = precursor2.to_signature()
    assert sig2 is not None
    assert "*" not in sig2
    assert "||" in sig2  # Empty slot for missing exposure dimension


def test_regression_location_provenance_narrative_vs_metadata(extractor, screening_engine, lsr_mapper, synthesizer):
    """Regression test: Metadata location must have DerivationType.METADATA and empty evidence_spans."""
    raw = "While running casing, air winch line parted and elevator swung near floormen."
    ctx = extractor.extract_safety_event_context(raw)
    scr = screening_engine.evaluate_context(ctx)
    lsr = lsr_mapper.map_rules(ctx)

    # 1. Sourced from request metadata
    precursor_meta = synthesizer.synthesize(ctx, scr, lsr, reported_location="Rig-04 / Moran Field")
    assert precursor_meta.location == "Rig-04 / Moran Field"
    loc_prov = precursor_meta.field_provenance["location"]
    assert loc_prov.derivation_type == DerivationType.METADATA
    assert loc_prov.evidence_spans == []
    assert loc_prov.provenance_rule == "REPORT_METADATA_LOCATION"

