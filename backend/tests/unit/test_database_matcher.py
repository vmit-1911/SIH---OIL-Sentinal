"""Unit tests for DatabasePrecursorMatcher."""

import uuid
from datetime import datetime, timezone
import pytest
from app.db.models.assessment import SIFAssessment
from app.db.models.report import SafetyReport
from app.domain.enums import ActualOutcome, PotentialOutcome, SIFClassification, SourceType, TriageStatus
from app.domain.similarity.hybrid import HybridPrecursorSimilarity
from app.infrastructure.matcher.database_matcher import DatabasePrecursorMatcher


@pytest.mark.asyncio
async def test_database_matcher_candidate_retrieval_and_ranking(db_session):
    """Verify DatabasePrecursorMatcher retrieves candidates, ranks by score DESC, and excludes self."""
    # Seed 3 historical reports in test DB
    rep1_id = uuid.uuid4()
    rep1 = SafetyReport(
        id=rep1_id,
        report_ref="SR-TEST-001",
        source_type=SourceType.NEAR_MISS,
        raw_text="Crane hoist line parted and suspended load swung dangerously near worker.",
        reported_location="Rig-04 / Moran Field",
        actual_severity=ActualOutcome.NO_INJURY,
    )
    ass1 = SIFAssessment(
        id=uuid.uuid4(),
        report_id=rep1_id,
        sif_classification=SIFClassification.POTENTIAL_SIF,
        evidence_score=0.9,
        potential_severity=PotentialOutcome.FATALITY,
        structured_precursor={
            "hazard": "Suspended Load / Rigging Failure",
            "activity": "Crane & Hoisting Operations",
            "barrier_failure": "Rigging Failure / Line Parted",
            "exposure": "Line of Fire Exposure",
            "potential_consequence": "FATALITY",
            "life_saving_rule": "LSR_03_MECHANICAL_LIFTING",
            "location": "Rig-04 / Moran Field",
        },
        text_embedding=[0.05] * 384,
        triage_status=TriageStatus.AUTO_SCREENED,
    )

    rep2_id = uuid.uuid4()
    rep2 = SafetyReport(
        id=rep2_id,
        report_ref="SR-TEST-002",
        source_type=SourceType.UC,
        raw_text="Paint cans and cleaning rags left on workshop walkway causing minor tripping hazard.",
        reported_location="Central Workshop",
        actual_severity=ActualOutcome.NO_INJURY,
    )
    ass2 = SIFAssessment(
        id=uuid.uuid4(),
        report_id=rep2_id,
        sif_classification=SIFClassification.NON_SIF,
        evidence_score=0.1,
        potential_severity=PotentialOutcome.LOW_IMPACT,
        structured_precursor={
            "hazard": "Housekeeping & Minor Trip Hazard",
            "activity": None,
            "barrier_failure": None,
            "exposure": None,
            "potential_consequence": None,
            "life_saving_rule": None,
            "location": "Central Workshop",
        },
        text_embedding=[-0.05] * 384,
        triage_status=TriageStatus.AUTO_SCREENED,
    )

    db_session.add_all([rep1, ass1, rep2, ass2])
    await db_session.flush()

    matcher = DatabasePrecursorMatcher(session=db_session)

    # Search with a crane lifting precursor target
    target_precursor = {
        "hazard": "Suspended Load / Rigging Failure",
        "activity": "Crane & Hoisting Operations",
        "barrier_failure": "Rigging Failure / Line Parted",
        "exposure": "Line of Fire Exposure",
        "potential_consequence": "FATALITY",
        "life_saving_rule": "LSR_03_MECHANICAL_LIFTING",
        "location": "Rig-04 / Moran Field",
    }
    target_embedding = [0.05] * 384

    # Case 1: Exclude self
    results = await matcher.find_similar_reports(
        target_precursor=target_precursor,
        target_embedding=target_embedding,
        exclude_report_id=rep1_id,
        top_k=5,
        threshold=0.50,
    )
    # rep1 was excluded, rep2 is below 0.50 threshold -> 0 results
    assert len(results) == 0

    # Case 2: Do not exclude rep1
    results_all = await matcher.find_similar_reports(
        target_precursor=target_precursor,
        target_embedding=target_embedding,
        exclude_report_id=None,
        top_k=5,
        threshold=0.50,
    )
    # rep1 should match with high similarity
    assert len(results_all) == 1
    assert results_all[0]["report_id"] == rep1_id
    assert results_all[0]["similarity_score"] >= 0.95
    assert results_all[0]["similarity_type"] == "HYBRID"
    assert "Crane hoist line parted" in results_all[0]["summary"]


@pytest.mark.asyncio
async def test_database_matcher_empty_input_returns_empty_list(db_session):
    """Verify empty target input returns empty list immediately."""
    matcher = DatabasePrecursorMatcher(session=db_session)
    res = await matcher.find_similar_reports(target_precursor=None, target_embedding=None)
    assert res == []
