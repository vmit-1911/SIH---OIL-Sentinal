"""Unit tests for StructuredPrecursorSimilarity."""

import pytest
from app.domain.precursor.model import StructuredSIFPrecursor
from app.domain.similarity.structured import StructuredPrecursorSimilarity


def test_structured_similarity_identical_precursor():
    """Verify identical precursors score 1.0."""
    engine = StructuredPrecursorSimilarity()
    p1 = StructuredSIFPrecursor(
        hazard="Suspended Load / Rigging Failure",
        activity="Crane & Hoisting Operations",
        barrier_failure="Rigging Failure / Line Parted",
        exposure="Line of Fire Exposure",
        potential_consequence="FATALITY",
        life_saving_rule="LSR_03_MECHANICAL_LIFTING",
        location="Rig-04 / Moran Field",
    )
    p2 = StructuredSIFPrecursor(
        hazard="Suspended Load / Rigging Failure",
        activity="Crane & Hoisting Operations",
        barrier_failure="Rigging Failure / Line Parted",
        exposure="Line of Fire Exposure",
        potential_consequence="FATALITY",
        life_saving_rule="LSR_03_MECHANICAL_LIFTING",
        location="Rig-04 / Moran Field",
    )
    res = engine.compute_similarity(p1, p2)
    assert res.score == 1.0
    assert res.compared_dimensions == 7
    assert all(score == 1.0 for score in res.dimension_scores.values())


def test_structured_similarity_same_hazard_different_wording():
    """Verify fuzzy token matching on different phrasing of the same hazard/activity."""
    engine = StructuredPrecursorSimilarity()
    p1 = {
        "hazard": "Suspended Load Rigging Failure",
        "activity": "Crane and Hoisting Operations",
        "barrier_failure": "Rigging Line Parted",
        "potential_consequence": "FATALITY",
        "life_saving_rule": "LSR_03_MECHANICAL_LIFTING",
    }
    p2 = {
        "hazard": "Suspended Load with Rigging Cable Breakdown",
        "activity": "Heavy Hoisting Operations on Rig",
        "barrier_failure": "Line Parted during Hoist",
        "potential_consequence": "FATALITY",
        "life_saving_rule": "LSR_03_MECHANICAL_LIFTING",
    }
    res = engine.compute_similarity(p1, p2)
    assert res.score >= 0.65
    assert res.compared_dimensions == 5

    assert res.dimension_scores["hazard"] > 0.50
    assert res.dimension_scores["activity"] > 0.35
    assert res.dimension_scores["potential_consequence"] == 1.0
    assert res.dimension_scores["life_saving_rule"] == 1.0



def test_structured_similarity_missing_dimensions_tolerated():
    """Verify missing dimensions on either side are ignored and not penalized as mismatches."""
    engine = StructuredPrecursorSimilarity()
    p1 = {
        "hazard": "High Pressure Fluid / Gas",
        "barrier_failure": "Energy Isolation (LOTO) Failure",
        "potential_consequence": "MAJOR_PROCESS_SAFETY_EVENT",
        "life_saving_rule": "LSR_04_ENERGY_ISOLATION",
    }
    p2 = {
        "hazard": "High Pressure Fluid / Gas",
        "activity": "Manifold Maintenance",
        "barrier_failure": "Energy Isolation (LOTO) Failure",
        "exposure": "Line of Fire Exposure",
        "potential_consequence": "MAJOR_PROCESS_SAFETY_EVENT",
        "life_saving_rule": "LSR_04_ENERGY_ISOLATION",
        "location": "EPS Moran",
    }
    res = engine.compute_similarity(p1, p2)
    # The 4 overlapping dimensions (hazard, barrier_failure, potential_consequence, life_saving_rule) match perfectly
    assert res.score == 1.0
    assert res.compared_dimensions == 4
    assert res.dimension_scores["activity"] is None
    assert res.dimension_scores["exposure"] is None
    assert res.dimension_scores["location"] is None


def test_structured_similarity_location_mismatch_and_partial_match():
    """Verify location matching behavior."""
    engine = StructuredPrecursorSimilarity()
    p1 = {"location": "Rig-04 / Moran Field"}
    p2 = {"location": "Rig-07 / Moran Field"}
    p3 = {"location": "Central Workshop"}

    res_partial = engine.compute_similarity(p1, p2)
    assert res_partial.score > 0.0  # partial match on 'moran field'

    res_mismatch = engine.compute_similarity(p1, p3)
    assert res_mismatch.score == 0.0


def test_structured_similarity_completely_unrelated():
    """Verify completely distinct precursors produce 0.0 or near-zero similarity."""
    engine = StructuredPrecursorSimilarity()
    p1 = {
        "hazard": "Suspended Heavy Load",
        "activity": "Crane Lifting",
        "barrier_failure": "Line Parted",
        "potential_consequence": "FATALITY",
        "life_saving_rule": "LSR_03_MECHANICAL_LIFTING",
    }
    p2 = {
        "hazard": "Housekeeping & Minor Trip Hazard",
        "activity": "Cleaning Operations",
        "barrier_failure": "Untidy Storage Area",
        "potential_consequence": "LOW_IMPACT",
        "life_saving_rule": "LSR_99_HOUSEKEEPING",
    }
    res = engine.compute_similarity(p1, p2)
    assert res.score < 0.20


def test_structured_similarity_both_none_or_empty():
    """Verify None/empty inputs return score 0.0."""
    engine = StructuredPrecursorSimilarity()
    res1 = engine.compute_similarity(None, None)
    assert res1.score == 0.0
    assert res1.compared_dimensions == 0

    res2 = engine.compute_similarity({}, {})
    assert res2.score == 0.0
    assert res2.compared_dimensions == 0
