"""Unit tests for PatternSynthesizer (representative precursor, pattern key, and explanation)."""

import uuid
from datetime import datetime, timezone
from app.domain.enums import DerivationType, PatternStatus
from app.domain.pattern.models import PatternRelationshipEvidence
from app.domain.pattern.synthesizer import PatternSynthesizer
from app.domain.precursor.model import (
    PrecursorDimensionProvenance,
    StructuredSIFPrecursor,
)
from app.domain.safety_event import EvidenceSpan


def test_representative_precursor_unanimous():
    """Verify representative precursor synthesis when all members share identical values."""
    p1 = StructuredSIFPrecursor(
        hazard="Suspended Load",
        activity="Crane Lifting",
        barrier_failure="Rigging Failure",
        exposure="Line of Fire",
        potential_consequence="FATALITY",
        life_saving_rule="LSR_03_MECHANICAL_LIFTING",
        location="Rig-04",
        field_provenance={
            "hazard": PrecursorDimensionProvenance(
                dimension="hazard",
                value="Suspended Load",
                derivation_type=DerivationType.DIRECT_MATCH,
                evidence_spans=[EvidenceSpan(text="suspended load", category="hazard", start_char=0, end_char=14)],
            )
        },
    )
    p2 = StructuredSIFPrecursor(
        hazard="Suspended Load",
        activity="Crane Lifting",
        barrier_failure="Rigging Failure",
        exposure="Line of Fire",
        potential_consequence="FATALITY",
        life_saving_rule="LSR_03_MECHANICAL_LIFTING",
        location="Rig-04",
    )
    p3 = StructuredSIFPrecursor(
        hazard="Suspended Load",
        activity="Crane Lifting",
        barrier_failure="Rigging Failure",
        exposure="Line of Fire",
        potential_consequence="FATALITY",
        life_saving_rule="LSR_03_MECHANICAL_LIFTING",
        location="Rig-04",
    )

    rep = PatternSynthesizer.synthesize_representative_precursor([p1, p2, p3])

    assert rep.hazard == "Suspended Load"
    assert rep.activity == "Crane Lifting"
    assert rep.barrier_failure == "Rigging Failure"
    assert rep.exposure == "Line of Fire"
    assert rep.potential_consequence == "FATALITY"
    assert rep.life_saving_rule == "LSR_03_MECHANICAL_LIFTING"
    assert rep.location == "Rig-04"

    # Verify provenance exists
    assert "hazard" in rep.field_provenance
    assert rep.field_provenance["hazard"].derivation_type == DerivationType.RULE_INFERENCE
    assert "3/3 member reports" in rep.field_provenance["hazard"].provenance_rule


def test_representative_precursor_differing_locations_sets_null():
    """Verify differing operational locations result in representative location=None."""
    p1 = {"hazard": "Hot Work", "location": "Rig-01"}
    p2 = {"hazard": "Hot Work", "location": "EPS Moran"}
    p3 = {"hazard": "Hot Work", "location": "OCS Dikom"}

    rep = PatternSynthesizer.synthesize_representative_precursor([p1, p2, p3])

    assert rep.hazard == "Hot Work"
    assert rep.location is None


def test_representative_precursor_majority_lsr():
    """Verify dominant LSR is selected when meeting consensus/majority criteria."""
    p1 = {"life_saving_rule": "LSR_06_HOT_WORK"}
    p2 = {"life_saving_rule": "LSR_06_HOT_WORK"}
    p3 = {"life_saving_rule": "LSR_04_ENERGY_ISOLATION"}

    rep = PatternSynthesizer.synthesize_representative_precursor([p1, p2, p3])
    assert rep.life_saving_rule == "LSR_06_HOT_WORK"


def test_representative_precursor_mixed_lsr_no_majority_sets_null():
    """Verify split LSR with no majority results in representative life_saving_rule=None."""
    p1 = {"life_saving_rule": "LSR_01_BYPASSING_SAFETY_CONTROLS"}
    p2 = {"life_saving_rule": "LSR_02_WORKING_AT_HEIGHT"}
    p3 = {"life_saving_rule": "LSR_03_MECHANICAL_LIFTING"}

    rep = PatternSynthesizer.synthesize_representative_precursor([p1, p2, p3])
    assert rep.life_saving_rule is None


def test_representative_precursor_filters_placeholders():
    """Verify placeholders like *, UNKNOWN, OTHER are never used."""
    p1 = {"hazard": "UNKNOWN", "activity": "*", "barrier_failure": "OTHER"}
    p2 = {"hazard": "None", "activity": "N/A", "barrier_failure": "NULL"}

    rep = PatternSynthesizer.synthesize_representative_precursor([p1, p2])
    assert rep.hazard is None
    assert rep.activity is None
    assert rep.barrier_failure is None


def test_pattern_key_generation():
    """Verify deterministic pattern key generation based on representative precursor."""
    rep = StructuredSIFPrecursor(
        hazard="Suspended Load",
        barrier_failure="Rigging Failure",
        life_saving_rule="LSR_03_MECHANICAL_LIFTING",
    )
    key = PatternSynthesizer.generate_pattern_key(rep)

    assert key.startswith("PAT_")
    assert "LSR_03" in key or "MECHANICAL" in key
    assert len(key) <= 100

    # Test stability
    key2 = PatternSynthesizer.generate_pattern_key(rep)
    assert key == key2


def test_stable_pattern_key_when_membership_grows():
    """Verify pattern key remains identical when membership expands from A,B,C to A,B,C,D."""
    prec = {
        "hazard": "Suspended Load",
        "activity": "Crane Lifting",
        "barrier_failure": "Rigging Failure",
        "exposure": "Line of Fire",
        "potential_consequence": "FATALITY",
        "life_saving_rule": "LSR_03_MECHANICAL_LIFTING",
    }

    id_a = uuid.uuid4()
    id_b = uuid.uuid4()
    id_c = uuid.uuid4()
    id_d = uuid.uuid4()

    records_3 = [
        {"report_id": id_a, "precursor": prec},
        {"report_id": id_b, "precursor": prec},
        {"report_id": id_c, "precursor": prec},
    ]

    records_4 = [
        {"report_id": id_a, "precursor": prec},
        {"report_id": id_b, "precursor": prec},
        {"report_id": id_c, "precursor": prec},
        {"report_id": id_d, "precursor": prec},
    ]

    pat_3 = PatternSynthesizer.synthesize_pattern(records_3, [])
    pat_4 = PatternSynthesizer.synthesize_pattern(records_4, [])

    # Pattern key must be completely identical
    assert pat_3.pattern_key == pat_4.pattern_key
    assert pat_3.title == pat_4.title
    assert pat_3.hazard_category == pat_4.hazard_category
    assert pat_3.lsr_code == pat_4.lsr_code
    # Member count reflects growth
    assert pat_3.supporting_report_count == 3
    assert pat_4.supporting_report_count == 4


def test_pattern_key_no_member_id_dependency():
    """Verify two groups with totally disjoint report IDs but same precursor receive identical pattern key."""
    prec = {
        "hazard": "Toxic Gas",
        "activity": "Confined Space Entry",
        "barrier_failure": "Gas Monitoring Failure",
        "exposure": "Asphyxiation",
        "potential_consequence": "FATALITY",
        "life_saving_rule": "LSR_05_CONFINED_SPACE",
    }

    group_1 = [
        {"report_id": uuid.uuid4(), "precursor": prec},
        {"report_id": uuid.uuid4(), "precursor": prec},
        {"report_id": uuid.uuid4(), "precursor": prec},
    ]

    group_2 = [
        {"report_id": uuid.uuid4(), "precursor": prec},
        {"report_id": uuid.uuid4(), "precursor": prec},
        {"report_id": uuid.uuid4(), "precursor": prec},
    ]

    pat_1 = PatternSynthesizer.synthesize_pattern(group_1, [])
    pat_2 = PatternSynthesizer.synthesize_pattern(group_2, [])

    assert pat_1.pattern_key == pat_2.pattern_key


def test_representative_provenance_is_rule_inference_not_direct_match():
    """Verify representative precursor dimensions are annotated as RULE_INFERENCE, never DIRECT_MATCH."""
    p1 = StructuredSIFPrecursor(
        hazard="Suspended Load",
        activity="Crane Lifting",
        barrier_failure="Rigging Failure",
        exposure="Line of Fire",
        potential_consequence="FATALITY",
        life_saving_rule="LSR_03_MECHANICAL_LIFTING",
    )
    p2 = StructuredSIFPrecursor(
        hazard="Suspended Load",
        activity="Crane Lifting",
        barrier_failure="Rigging Failure",
        exposure="Line of Fire",
        potential_consequence="FATALITY",
        life_saving_rule="LSR_03_MECHANICAL_LIFTING",
    )

    rep = PatternSynthesizer.synthesize_representative_precursor([p1, p2])

    for dim, prov in rep.field_provenance.items():
        assert prov.derivation_type == DerivationType.RULE_INFERENCE
        assert prov.derivation_type != DerivationType.DIRECT_MATCH
        assert "CONSENSUS" in prov.provenance_rule


def test_synthesize_pattern_complete():
    """Verify full pattern synthesis domain model."""
    id1 = uuid.uuid4()
    id2 = uuid.uuid4()
    id3 = uuid.uuid4()

    records = [
        {
            "report_id": id1,
            "location": "Rig-01",
            "event_timestamp": datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            "precursor": {"hazard": "Toxic Gas", "life_saving_rule": "LSR_05_CONFINED_SPACE"},
        },
        {
            "report_id": id2,
            "location": "Rig-02",
            "event_timestamp": datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
            "precursor": {"hazard": "Toxic Gas", "life_saving_rule": "LSR_05_CONFINED_SPACE"},
        },
        {
            "report_id": id3,
            "location": "Rig-03",
            "event_timestamp": datetime(2026, 1, 20, 15, 0, tzinfo=timezone.utc),
            "precursor": {"hazard": "Toxic Gas", "life_saving_rule": "LSR_05_CONFINED_SPACE"},
        },
    ]

    relationships = [
        PatternRelationshipEvidence(
            report_a=id1,
            report_b=id2,
            score=0.85,
            mode="FULL_HYBRID",
        ),
        PatternRelationshipEvidence(
            report_a=id2,
            report_b=id3,
            score=0.88,
            mode="FULL_HYBRID",
        ),
    ]

    pattern = PatternSynthesizer.synthesize_pattern(records, relationships)

    assert pattern.supporting_report_count == 3
    assert pattern.hazard_category == "Toxic Gas"
    assert pattern.lsr_code == "LSR_05_CONFINED_SPACE"
    assert pattern.status == PatternStatus.CANDIDATE
    assert set(pattern.supporting_locations) == {"Rig-01", "Rig-02", "Rig-03"}
    assert pattern.representative_precursor.location is None  # Different locations
    assert pattern.first_observed_at == datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    assert pattern.last_observed_at == datetime(2026, 1, 20, 15, 0, tzinfo=timezone.utc)
    assert pattern.similarity_summary["avg_score"] == 0.865
