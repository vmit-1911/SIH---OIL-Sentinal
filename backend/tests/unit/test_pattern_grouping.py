"""Unit tests for PatternGroupingEngine candidate clustering and threshold enforcement."""

import uuid
from app.domain.pattern.grouping import PatternGroupingEngine
from app.domain.similarity.hybrid import HybridPrecursorSimilarity


def test_grouping_below_min_report_count():
    """Verify 2 similar reports do not form a pattern when min_report_count=3."""
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
    id2 = uuid.uuid4()
    candidates = [
        {"report_id": id1, "precursor": prec, "embedding": None},
        {"report_id": id2, "precursor": prec, "embedding": None},
    ]

    res = engine.group_candidates(candidates)

    assert res.qualifying_group_count == 0
    assert len(res.qualifying_groups) == 0
    assert set(res.unassigned_report_ids) == {id1, id2}


def test_grouping_meets_min_report_count():
    """Verify 3 similar reports form 1 qualifying pattern candidate."""
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
    id2 = uuid.uuid4()
    id3 = uuid.uuid4()
    candidates = [
        {"report_id": id1, "precursor": prec, "embedding": None},
        {"report_id": id2, "precursor": prec, "embedding": None},
        {"report_id": id3, "precursor": prec, "embedding": None},
    ]

    res = engine.group_candidates(candidates)

    assert res.qualifying_group_count == 1
    assert len(res.qualifying_groups) == 1
    assert len(res.unassigned_report_ids) == 0
    group = res.qualifying_groups[0]
    assert len(group["member_records"]) == 3
    assert len(group["relationships"]) == 3  # (1,2), (1,3), (2,3)


def test_no_data_available_never_forms_relationship():
    """Verify candidates with no data available never create pattern relationships."""
    engine = PatternGroupingEngine(min_report_count=3, candidate_threshold=0.65)

    id1 = uuid.uuid4()
    id2 = uuid.uuid4()
    id3 = uuid.uuid4()
    candidates = [
        {"report_id": id1, "precursor": None, "embedding": None},
        {"report_id": id2, "precursor": None, "embedding": None},
        {"report_id": id3, "precursor": None, "embedding": None},
    ]

    res = engine.group_candidates(candidates)

    assert res.total_relationships == 0
    assert res.qualifying_group_count == 0
    assert set(res.unassigned_report_ids) == {id1, id2, id3}


def test_disjoint_components_partitioned():
    """Verify distinct clusters are correctly partitioned into separate groups."""
    engine = PatternGroupingEngine(min_report_count=3, candidate_threshold=0.65)

    prec_a = {
        "hazard": "Suspended Load",
        "activity": "Crane Lifting",
        "barrier_failure": "Rigging Failure",
        "exposure": "Line of Fire",
        "potential_consequence": "FATALITY",
        "life_saving_rule": "LSR_03_MECHANICAL_LIFTING",
    }

    prec_b = {
        "hazard": "Toxic Gas",
        "activity": "Confined Space Entry",
        "barrier_failure": "Atmospheric Gas Testing Failure",
        "exposure": "Asphyxiation Exposure",
        "potential_consequence": "FATALITY",
        "life_saving_rule": "LSR_05_CONFINED_SPACE",
    }

    # 3 of group A, 3 of group B
    ids_a = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    ids_b = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]

    candidates = [
        {"report_id": rid, "precursor": prec_a, "embedding": None}
        for rid in ids_a
    ] + [
        {"report_id": rid, "precursor": prec_b, "embedding": None}
        for rid in ids_b
    ]

    res = engine.group_candidates(candidates)

    assert res.qualifying_group_count == 2
    assert len(res.unassigned_report_ids) == 0

    group_member_sets = [set(g["member_report_ids"]) for g in res.qualifying_groups]
    assert set(ids_a) in group_member_sets
    assert set(ids_b) in group_member_sets


def test_chaining_rejection_single_linkage():
    """Verify single-linkage chaining (A-B=0.80, B-C=0.80, A-C=0.20) is strictly rejected from forming a pattern."""
    class MockHybridEngine:
        def compute_hybrid_similarity(self, precursor_a, precursor_b, vec_a, vec_b):
            from app.domain.similarity.hybrid import HybridSimilarityResult
            key = tuple(sorted([precursor_a["id"], precursor_b["id"]]))
            if key == ("A", "B"):
                score = 0.80
            elif key == ("B", "C"):
                score = 0.80
            else:  # ("A", "C")
                score = 0.20

            return HybridSimilarityResult(
                hybrid_score=score,
                mode="FULL_HYBRID",
                structured_score=score,
                semantic_score=score,
                dimension_scores={},
                explanation=f"Mock score {score}",
            )

    engine = PatternGroupingEngine(
        hybrid_engine=MockHybridEngine(),
        min_report_count=3,
        candidate_threshold=0.65,
        min_cohesion=0.65,
    )

    id_a = uuid.uuid4()
    id_b = uuid.uuid4()
    id_c = uuid.uuid4()

    candidates = [
        {"report_id": id_a, "precursor": {"id": "A"}, "embedding": None},
        {"report_id": id_b, "precursor": {"id": "B"}, "embedding": None},
        {"report_id": id_c, "precursor": {"id": "C"}, "embedding": None},
    ]

    res = engine.group_candidates(candidates)

    # Even though connected component (A-B-C) has size 3, group cohesion is (0.8+0.8+0.2)/3 = 0.60 < 0.65
    # and member A/C cohesion to group is (0.8+0.2)/2 = 0.50 < 0.65
    # Therefore it MUST be rejected!
    assert res.qualifying_group_count == 0
    assert len(res.qualifying_groups) == 0
    assert set(res.unassigned_report_ids) == {id_a, id_b, id_c}


def test_group_cohesion_satisfied_forms_pattern():
    """Verify cohesive candidate group (A-B=0.80, B-C=0.80, A-C=0.75) passes cohesion and forms pattern."""
    class MockHybridEngine:
        def compute_hybrid_similarity(self, precursor_a, precursor_b, vec_a, vec_b):
            from app.domain.similarity.hybrid import HybridSimilarityResult
            key = tuple(sorted([precursor_a["id"], precursor_b["id"]]))
            if key == ("A", "B"):
                score = 0.80
            elif key == ("B", "C"):
                score = 0.80
            else:  # ("A", "C")
                score = 0.75

            return HybridSimilarityResult(
                hybrid_score=score,
                mode="FULL_HYBRID",
                structured_score=score,
                semantic_score=score,
                dimension_scores={},
                explanation=f"Mock score {score}",
            )

    engine = PatternGroupingEngine(
        hybrid_engine=MockHybridEngine(),
        min_report_count=3,
        candidate_threshold=0.65,
        min_cohesion=0.65,
    )

    id_a = uuid.uuid4()
    id_b = uuid.uuid4()
    id_c = uuid.uuid4()

    candidates = [
        {"report_id": id_a, "precursor": {"id": "A"}, "embedding": None},
        {"report_id": id_b, "precursor": {"id": "B"}, "embedding": None},
        {"report_id": id_c, "precursor": {"id": "C"}, "embedding": None},
    ]

    res = engine.group_candidates(candidates)

    assert res.qualifying_group_count == 1
    assert len(res.unassigned_report_ids) == 0
    group = res.qualifying_groups[0]
    assert group["group_cohesion"] >= 0.65
    assert group["min_member_cohesion"] >= 0.65
    assert len(group["relationships"]) == 3
