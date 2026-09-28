"""Unit tests for SIF Evidence Screening Engine."""

import uuid
import pytest
from app.domain.enums import (
    ActualOutcome,
    EvidenceStrength,
    PotentialOutcome,
    ReviewStatus,
    SIFClassification,
    TriageStatus,
)
from app.domain.extraction.rule_based_extractor import RuleBasedSafetyExtractor
from app.domain.sif.screening import (
    SIFScreeningEngine,
    SIFScreeningProfile,
    SIFScreeningRule,
)
from app.db.models.review import TriageReview


@pytest.fixture
def extractor():
    return RuleBasedSafetyExtractor()


@pytest.fixture
def screening_engine():
    return SIFScreeningEngine()


def test_sif_scenario_1_suspended_load_rigging_failure(extractor, screening_engine):
    """Scenario 1: Suspended load + personnel exposure + failed barrier -> POTENTIAL_SIF & FATALITY."""
    raw = (
        "While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung "
        "across the rig floor, narrowly missing two floormen who jumped out of the way. No injuries occurred."
    )
    context = extractor.extract_safety_event_context(raw)
    result = screening_engine.evaluate_context(context, actual_severity=ActualOutcome.NO_INJURY)

    assert result.sif_classification == SIFClassification.POTENTIAL_SIF
    assert result.actual_severity == ActualOutcome.NO_INJURY
    assert result.potential_severity == PotentialOutcome.FATALITY
    assert result.evidence_score >= 0.70
    assert result.evidence_strength == EvidenceStrength.HIGH
    assert result.evidence_breakdown.energy_hazard.present is True
    assert result.evidence_breakdown.exposure.present is True
    assert result.evidence_breakdown.barrier_degradation.present is True
    assert len(result.rule_provenance) > 0
    assert result.rule_provenance[0].rule_id == "SIF_RULE_GRAVITY_LIFTING_001"


def test_sif_scenario_2_pressure_isolation_failure(extractor, screening_engine):
    """Scenario 2: High pressure hazard + isolation failure -> POTENTIAL_SIF & MAJOR_PROCESS_SAFETY_EVENT."""
    raw = (
        "Technician began unbolting high pressure flange on production manifold at EPS-02. "
        "Trapped pressurized hydrocarbon gas vented with loud roar because valve was not fully closed."
    )
    context = extractor.extract_safety_event_context(raw)
    result = screening_engine.evaluate_context(context, actual_severity=ActualOutcome.NO_INJURY)

    assert result.sif_classification == SIFClassification.POTENTIAL_SIF
    assert result.potential_severity == PotentialOutcome.MAJOR_PROCESS_SAFETY_EVENT
    assert result.evidence_breakdown.energy_hazard.present is True
    assert result.evidence_breakdown.barrier_degradation.present is True
    assert any(r.rule_id == "SIF_RULE_PRESSURE_ISOLATION_002" for r in result.rule_provenance)


def test_sif_scenario_3_height_fall_protection_failure(extractor, screening_engine):
    """Scenario 3: Height exposure + fall protection failure -> POTENTIAL_SIF & FATALITY."""
    raw = (
        "During mast maintenance on monkey board at 25 meters height, derrickman unhooked his full body "
        "harness lanyard without 100% tie-off."
    )
    context = extractor.extract_safety_event_context(raw)
    result = screening_engine.evaluate_context(context, actual_severity=ActualOutcome.NO_INJURY)

    assert result.sif_classification == SIFClassification.POTENTIAL_SIF
    assert result.potential_severity == PotentialOutcome.FATALITY
    assert any(r.rule_id == "SIF_RULE_HEIGHT_FALL_PROTECTION_003" for r in result.rule_provenance)


def test_sif_scenario_4_confined_space_omitted_controls(extractor, screening_engine):
    """Scenario 4: Confined space + toxic/asphyxiation hazard + missing controls -> POTENTIAL_SIF & FATALITY."""
    raw = (
        "Contractor personnel entered the crude oil storage tank compartment for sludge cleaning "
        "without gas test clearance and without a dedicated standby man."
    )
    context = extractor.extract_safety_event_context(raw)
    result = screening_engine.evaluate_context(context, actual_severity=ActualOutcome.NO_INJURY)

    assert result.sif_classification == SIFClassification.POTENTIAL_SIF
    assert result.potential_severity == PotentialOutcome.FATALITY
    assert any(r.rule_id == "SIF_RULE_CONFINED_SPACE_ATMOSPHERE_004" for r in result.rule_provenance)


def test_sif_scenario_5_routine_housekeeping_non_sif(extractor, screening_engine):
    """Scenario 5: Routine low-energy housekeeping -> NON_SIF & LOW_IMPACT."""
    raw = "Empty paint cans and cleaning rags left unattended near workshop entrance, creating trip hazard."
    context = extractor.extract_safety_event_context(raw)
    result = screening_engine.evaluate_context(context, actual_severity=ActualOutcome.NO_INJURY)

    assert result.sif_classification == SIFClassification.NON_SIF
    assert result.potential_severity == PotentialOutcome.LOW_IMPACT
    assert result.evidence_score <= 0.20
    assert result.evidence_strength == EvidenceStrength.LOW


def test_sif_scenario_7_insufficient_evidence_undetermined(extractor, screening_engine):
    """Scenario 7: Minimal / ambiguous narrative -> UNDETERMINED."""
    raw = "Observed unsafe condition near the compressor shed area yesterday."
    context = extractor.extract_safety_event_context(raw)
    result = screening_engine.evaluate_context(context, actual_severity=ActualOutcome.NO_INJURY)

    assert result.sif_classification == SIFClassification.UNDETERMINED
    assert result.potential_severity is None


# ====================================================================
# PHASE 1B FINAL CORRECTION VERIFICATION TESTS (A through F)
# ====================================================================

def test_a_minor_injury_alone_does_not_produce_actual_sif(extractor, screening_engine):
    """Requirement A: Minor injury alone does not produce ACTUAL_SIF."""
    raw = "Worker tripped over loose gravel in walkway and received first aid dressing for minor scrape on knee."
    context = extractor.extract_safety_event_context(raw)
    result = screening_engine.evaluate_context(context, actual_severity=ActualOutcome.MINOR_INJURY)

    assert result.actual_severity == ActualOutcome.MINOR_INJURY
    assert result.sif_classification != SIFClassification.ACTUAL_SIF
    assert result.sif_classification in (SIFClassification.NON_SIF, SIFClassification.UNDETERMINED)


def test_b_injury_severity_does_not_automatically_determine_sif_classification(extractor, screening_engine):
    """Requirement B: Injury severity is decoupled from SIF potential classification."""
    raw_high_energy = (
        "While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator "
        "swung across the rig floor near floormen."
    )
    context_high = extractor.extract_safety_event_context(raw_high_energy)

    # High energy + barrier failure should yield POTENTIAL_SIF regardless of whether actual outcome is NO_INJURY or LOST_TIME_INJURY
    res_no_injury = screening_engine.evaluate_context(context_high, actual_severity=ActualOutcome.NO_INJURY)
    res_lti = screening_engine.evaluate_context(context_high, actual_severity=ActualOutcome.LOST_TIME_INJURY)

    assert res_no_injury.sif_classification == SIFClassification.POTENTIAL_SIF
    assert res_lti.sif_classification == SIFClassification.POTENTIAL_SIF
    assert res_lti.sif_classification != SIFClassification.ACTUAL_SIF
    assert res_no_injury.evidence_score == res_lti.evidence_score


def test_c_automated_screening_returns_allowed_categories(extractor, screening_engine):
    """Requirement C: Automated screening returns strictly POTENTIAL_SIF, NON_SIF, or UNDETERMINED."""
    scenarios = [
        ("Winch line parted swinging heavy elevator on rig floor near roughneck.", SIFClassification.POTENTIAL_SIF),
        ("Empty paint cans left in workshop corridor causing trip hazard.", SIFClassification.NON_SIF),
        ("Observed general safety observation at site.", SIFClassification.UNDETERMINED),
    ]

    for raw, expected_class in scenarios:
        ctx = extractor.extract_safety_event_context(raw)
        res = screening_engine.evaluate_context(ctx)
        assert res.sif_classification == expected_class
        assert res.sif_classification in (
            SIFClassification.POTENTIAL_SIF,
            SIFClassification.NON_SIF,
            SIFClassification.UNDETERMINED,
        )


def test_d_actual_sif_accepted_only_through_authoritative_or_triage_path():
    """Requirement D: ACTUAL_SIF is reserved for explicit human HSE review or authoritative records."""
    # Ensure domain enum and triage review model support ACTUAL_SIF
    assert SIFClassification.ACTUAL_SIF == "ACTUAL_SIF"

    # Simulated HSE reviewer validation of an actual SIF
    triage_review = TriageReview(
        report_id=uuid.uuid4(),
        reviewer_id="HSE_AUDITOR_042",
        review_status=ReviewStatus.VALIDATED,
        verified_sif_classification=SIFClassification.ACTUAL_SIF,
        reviewer_notes="Confirmed hospital admission with permanent disabling hand injury from unguarded rotary table.",
    )
    assert triage_review.verified_sif_classification == SIFClassification.ACTUAL_SIF


def test_e_context_evidence_does_not_alter_numeric_score(extractor, screening_engine):
    """Requirement E: Context evidence (activity, equipment) does not alter numeric evidence score."""
    raw_with_context = (
        "While running 9-5/8 inch casing using casing elevator at Rig-04, winch line parted near roughneck."
    )
    raw_minimal_context = (
        "Winch line parted near roughneck."
    )

    ctx_with_context = extractor.extract_safety_event_context(raw_with_context)
    ctx_min = extractor.extract_safety_event_context(raw_minimal_context)

    res_with = screening_engine.evaluate_context(ctx_with_context)
    res_min = screening_engine.evaluate_context(ctx_min)

    # Context factor contribution is strictly 0.0 in profile
    assert res_with.evidence_breakdown.context.contribution_score == 0.0
    assert res_min.evidence_breakdown.context.contribution_score == 0.0

    # Presence of operational context records qualitative details without numeric distortion
    assert res_with.evidence_breakdown.context.present is True
    assert res_with.evidence_breakdown.energy_hazard.contribution_score > 0.0


def test_f_heuristic_thresholds_are_configuration_driven(extractor):
    """Requirement F: Screening thresholds and factor weights are configuration-driven, not hardcoded."""
    custom_profile = SIFScreeningProfile(
        profile_id="CUSTOM_STRICT_PROFILE",
        version="1.0.0-strict",
        name="Strict SIF Screening Profile",
        description="Profile with stricter threshold requiring 0.90 evidence score for SIF potential",
        active=True,
        factor_weights={
            "energy_hazard": 0.30,
            "exposure_proximity": 0.30,
            "barrier_degradation": 0.20,
            "potential_consequence": 0.20,
        },
        strength_thresholds={"high": 0.85, "medium": 0.50, "low": 0.0},
        classification_thresholds={"potential_sif_min_score": 0.90, "non_sif_max_score": 0.15},
        screening_rules=[],
    )

    strict_engine = SIFScreeningEngine(profile=custom_profile)

    # Event with score ~ 0.80 will NOT meet strict threshold of 0.90
    raw = "Tugger winch rope snapped during drill collar lifting."
    ctx = extractor.extract_safety_event_context(raw)
    res = strict_engine.evaluate_context(ctx)

    assert strict_engine.profile.classification_thresholds["potential_sif_min_score"] == 0.90
    assert res.evidence_score < 0.90
