"""Comprehensive unit tests covering Phase 2B test cases A through J."""

import json
from pathlib import Path
import uuid
from datetime import datetime, timezone
import pytest

from app.domain.pattern.grouping import PatternGroupingEngine
from app.domain.pattern.models import PatternRelationshipEvidence
from app.domain.pattern.synthesizer import PatternSynthesizer
from app.domain.precursor.model import StructuredSIFPrecursor
from app.domain.similarity.hybrid import HybridPrecursorSimilarity


@pytest.fixture
def fixtures():
    fixture_path = Path("data/synthetic/pattern_fixtures.json")
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)["test_cases"]


def test_case_a_qualifying_pattern(fixtures):
    """CASE A: 3 strongly related suspended-load reports -> qualifying pattern candidate."""
    case = fixtures["case_a_qualifying_pattern"]
    engine = PatternGroupingEngine(min_report_count=3, candidate_threshold=0.65)

    candidates = []
    for r in case["reports"]:
        candidates.append({
            "report_id": uuid.uuid4(),
            "location": r["location"],
            "event_timestamp": datetime.fromisoformat(r["timestamp"]),
            "precursor": r["precursor"],
            "embedding": None,
        })

    res = engine.group_candidates(candidates)
    assert res.qualifying_group_count == 1
    assert len(res.qualifying_groups) == 1
    group = res.qualifying_groups[0]
    assert len(group["member_records"]) == 3

    pattern = PatternSynthesizer.synthesize_pattern(group["member_records"], group["relationships"])
    assert pattern.supporting_report_count == 3
    assert pattern.hazard_category == "Suspended Load"
    assert pattern.lsr_code == "LSR_03_MECHANICAL_LIFTING"
    assert pattern.representative_precursor.location == "Rig-04 / Moran Field"


def test_case_b_two_related_reports_no_pattern(fixtures):
    """CASE B: 2 related reports only -> no pattern (fails minimum recurrence count of 3)."""
    case = fixtures["case_b_insufficient_member_count"]
    engine = PatternGroupingEngine(min_report_count=3, candidate_threshold=0.65)

    candidates = [
        {
            "report_id": uuid.uuid4(),
            "location": r["location"],
            "event_timestamp": datetime.fromisoformat(r["timestamp"]),
            "precursor": r["precursor"],
            "embedding": None,
        }
        for r in case["reports"]
    ]

    res = engine.group_candidates(candidates)
    assert res.qualifying_group_count == 0
    assert len(res.qualifying_groups) == 0
    assert len(res.unassigned_report_ids) == 2


def test_case_c_same_hazard_divergent_barrier_activity(fixtures):
    """CASE C: 3 reports with same hazard but substantially different barrier/activity -> no group above threshold."""
    case = fixtures["case_c_divergent_barriers"]
    engine = PatternGroupingEngine(min_report_count=3, candidate_threshold=0.65)

    candidates = [
        {
            "report_id": uuid.uuid4(),
            "location": r["location"],
            "precursor": r["precursor"],
            "embedding": None,
        }
        for r in case["reports"]
    ]

    res = engine.group_candidates(candidates)
    assert res.qualifying_group_count == 0


def test_case_d_multi_location_preserves_locations_null_rep_location(fixtures):
    """CASE D: 4 reports across different locations but same precursor -> 1 pattern with multiple supporting locations."""
    case = fixtures["case_d_multi_location"]
    engine = PatternGroupingEngine(min_report_count=3, candidate_threshold=0.65)

    candidates = [
        {
            "report_id": uuid.uuid4(),
            "location": r["location"],
            "precursor": r["precursor"],
            "embedding": None,
        }
        for r in case["reports"]
    ]

    res = engine.group_candidates(candidates)
    assert res.qualifying_group_count == 1
    group = res.qualifying_groups[0]
    assert len(group["member_records"]) == 4

    pattern = PatternSynthesizer.synthesize_pattern(group["member_records"], group["relationships"])
    assert pattern.supporting_report_count == 4
    assert pattern.representative_precursor.location is None
    assert len(pattern.supporting_locations) == 4
    assert "GGS-01 Nahorkatiya" in pattern.supporting_locations
    assert "EPS Moran" in pattern.supporting_locations


def test_case_e_completely_unrelated_reports(fixtures):
    """CASE E: 3 completely unrelated reports -> no common pattern."""
    case = fixtures["case_e_completely_unrelated"]
    engine = PatternGroupingEngine(min_report_count=3, candidate_threshold=0.65)

    candidates = [
        {
            "report_id": uuid.uuid4(),
            "location": r["location"],
            "precursor": r["precursor"],
            "embedding": None,
        }
        for r in case["reports"]
    ]

    res = engine.group_candidates(candidates)
    assert res.qualifying_group_count == 0
    assert len(res.unassigned_report_ids) == 3


def test_case_f_mixed_similarity_modes():
    """CASE F: 3 reports with mixed similarity modes -> verify mode-aware evidence."""
    engine = PatternGroupingEngine(min_report_count=3, candidate_threshold=0.65)

    # Precursors for 3 reports
    prec = {
        "hazard": "High Pressure Fluid",
        "activity": "Flange Maintenance",
        "barrier_failure": "Energy Isolation Failure",
        "exposure": "Line of Fire",
        "potential_consequence": "FATALITY",
        "life_saving_rule": "LSR_04_ENERGY_ISOLATION",
    }
    vec = [0.1] * 384

    id1 = uuid.uuid4()
    id2 = uuid.uuid4()
    id3 = uuid.uuid4()

    # Report 1 has struct + vector (FULL_HYBRID with Report 2)
    # Report 2 has struct + vector (FULL_HYBRID with Report 1)
    # Report 3 has ONLY struct (STRUCTURED_ONLY_FALLBACK with Reports 1 and 2)
    candidates = [
        {"report_id": id1, "precursor": prec, "embedding": vec},
        {"report_id": id2, "precursor": prec, "embedding": vec},
        {"report_id": id3, "precursor": prec, "embedding": None},
    ]

    res = engine.group_candidates(candidates)
    assert res.qualifying_group_count == 1
    group = res.qualifying_groups[0]
    relationships = group["relationships"]

    modes = [r.mode for r in relationships]
    assert "FULL_HYBRID" in modes
    assert "STRUCTURED_ONLY_FALLBACK" in modes

    pattern = PatternSynthesizer.synthesize_pattern(group["member_records"], relationships)
    mode_counts = pattern.similarity_summary["mode_counts"]
    assert mode_counts.get("FULL_HYBRID") == 1
    assert mode_counts.get("STRUCTURED_ONLY_FALLBACK") == 2


def test_case_g_duplicate_discovery_execution_idempotency():
    """CASE G: Duplicate discovery execution produces identical deterministic pattern key and evidence."""
    prec = {
        "hazard": "Suspended Load",
        "activity": "Crane Lifting",
        "barrier_failure": "Rigging Failure",
        "exposure": "Line of Fire",
        "potential_consequence": "FATALITY",
        "life_saving_rule": "LSR_03_MECHANICAL_LIFTING",
    }
    rids = [uuid.UUID("11111111-1111-1111-1111-111111111111"), uuid.UUID("22222222-2222-2222-2222-222222222222"), uuid.UUID("33333333-3333-3333-3333-333333333333")]
    records = [
        {"report_id": rids[0], "location": "Rig-01", "precursor": prec},
        {"report_id": rids[1], "location": "Rig-01", "precursor": prec},
        {"report_id": rids[2], "location": "Rig-01", "precursor": prec},
    ]
    rels = [
        PatternRelationshipEvidence(report_a=rids[0], report_b=rids[1], score=0.9, mode="STRUCTURED_ONLY_FALLBACK"),
        PatternRelationshipEvidence(report_a=rids[1], report_b=rids[2], score=0.9, mode="STRUCTURED_ONLY_FALLBACK"),
    ]

    pat1 = PatternSynthesizer.synthesize_pattern(records, rels)
    pat2 = PatternSynthesizer.synthesize_pattern(records, rels)

    assert pat1.pattern_key == pat2.pattern_key
    assert pat1.title == pat2.title
    assert pat1.description == pat2.description
    assert pat1.supporting_report_count == pat2.supporting_report_count


def test_case_h_missing_location_remains_null():
    """CASE H: Missing location on reports -> representative location remains null."""
    prec = {"hazard": "Electrical Arc", "life_saving_rule": "LSR_04_ENERGY_ISOLATION", "location": None}
    records = [
        {"report_id": uuid.uuid4(), "location": None, "precursor": prec},
        {"report_id": uuid.uuid4(), "location": None, "precursor": prec},
        {"report_id": uuid.uuid4(), "location": None, "precursor": prec},
    ]
    rels = []

    pattern = PatternSynthesizer.synthesize_pattern(records, rels)
    assert pattern.representative_precursor.location is None
    assert pattern.supporting_locations == []


def test_case_i_different_lsrs_preserved_without_inventing_combined_lsr():
    """CASE I: Different LSRs across reports -> all supporting LSRs preserved without inventing combined LSR."""
    prec1 = {"hazard": "High Pressure Fluid", "life_saving_rule": "LSR_04_ENERGY_ISOLATION"}
    prec2 = {"hazard": "High Pressure Fluid", "life_saving_rule": "LSR_01_BYPASSING_SAFETY_CONTROLS"}
    prec3 = {"hazard": "High Pressure Fluid", "life_saving_rule": "LSR_06_HOT_WORK"}

    records = [
        {"report_id": uuid.uuid4(), "precursor": prec1},
        {"report_id": uuid.uuid4(), "precursor": prec2},
        {"report_id": uuid.uuid4(), "precursor": prec3},
    ]
    rels = []

    pattern = PatternSynthesizer.synthesize_pattern(records, rels)
    # No single rule reached majority threshold (>=50%)
    assert pattern.representative_precursor.life_saving_rule is None
    # All supporting rules preserved cleanly
    assert set(pattern.supporting_lsr_codes) == {
        "LSR_01_BYPASSING_SAFETY_CONTROLS",
        "LSR_04_ENERGY_ISOLATION",
        "LSR_06_HOT_WORK",
    }


def test_case_j_single_report_pattern_like_no_recurrence():
    """CASE J: One report with pattern-like precursor but no minimum member count -> no pattern formed."""
    engine = PatternGroupingEngine(min_report_count=3, candidate_threshold=0.65)
    prec = {
        "hazard": "Suspended Load",
        "activity": "Crane Lifting",
        "barrier_failure": "Rigging Failure",
        "exposure": "Line of Fire",
        "potential_consequence": "FATALITY",
        "life_saving_rule": "LSR_03_MECHANICAL_LIFTING",
    }
    id1 = uuid.uuid4()
    candidates = [{"report_id": id1, "precursor": prec, "embedding": None}]

    res = engine.group_candidates(candidates)
    assert res.qualifying_group_count == 0
    assert res.unassigned_report_ids == [id1]
