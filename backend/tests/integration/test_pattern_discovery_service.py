"""Integration tests for PatternDiscoveryService database operations and idempotency."""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.assessment import SIFAssessment
from app.db.models.pattern import PrecursorPattern
from app.db.models.report import SafetyReport
from app.domain.enums import ActualOutcome, EvidenceStrength, PatternStatus, PotentialOutcome, SIFClassification, SourceType, TriageStatus
from app.services.pattern_discovery_service import PatternDiscoveryService


@pytest.mark.asyncio
async def test_pattern_discovery_creates_pattern_and_links_assessments(db_session: AsyncSession):
    """Verify discovery service creates a pattern and links assessment.pattern_id for 3 qualifying reports."""
    prec = {
        "hazard": "Suspended Load",
        "activity": "Crane Lifting & Hoisting",
        "barrier_failure": "Rigging Failure / Line Parted",
        "exposure": "Line of Fire Exposure",
        "potential_consequence": "FATALITY",
        "life_saving_rule": "LSR_03_MECHANICAL_LIFTING",
        "location": "Rig-04 / Moran",
    }

    # Insert 3 similar reports and assessments
    assessment_ids = []
    report_ids = []
    for i in range(3):
        rep = SafetyReport(
            report_ref=f"SR-TEST-{i}-{uuid.uuid4().hex[:6]}",
            source_type=SourceType.NEAR_MISS,
            raw_text=f"Crane hoist line failure event number {i} with suspended casing.",
            reported_location="Rig-04 / Moran",
            actual_severity=ActualOutcome.NO_INJURY,
            event_timestamp=datetime(2026, 1, 10 + i, 10, 0, tzinfo=timezone.utc),
        )
        db_session.add(rep)
        await db_session.flush()
        report_ids.append(rep.id)

        ass = SIFAssessment(
            report_id=rep.id,
            sif_classification=SIFClassification.POTENTIAL_SIF,
            evidence_score=0.9,
            evidence_strength=EvidenceStrength.HIGH,
            rule_based_screening_score=0.9,
            potential_severity=PotentialOutcome.FATALITY,
            evidence_spans=[],
            structured_precursor=prec,
            text_embedding=None,
            pattern_id=None,
            triage_status=TriageStatus.AUTO_SCREENED,
        )
        db_session.add(ass)
        await db_session.flush()
        assessment_ids.append(ass.id)

    # Also insert 1 unrelated report
    rep_unrelated = SafetyReport(
        report_ref=f"SR-UNRELATED-{uuid.uuid4().hex[:6]}",
        source_type=SourceType.NEAR_MISS,
        raw_text="Driver speeding on access road.",
        reported_location="Moran Access Road",
        actual_severity=ActualOutcome.NO_INJURY,
        event_timestamp=datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc),
    )
    db_session.add(rep_unrelated)
    await db_session.flush()

    ass_unrelated = SIFAssessment(
        report_id=rep_unrelated.id,
        sif_classification=SIFClassification.NON_SIF,
        evidence_score=0.1,
        evidence_strength=EvidenceStrength.LOW,
        rule_based_screening_score=0.1,
        potential_severity=PotentialOutcome.LOW_IMPACT,
        evidence_spans=[],
        structured_precursor={"hazard": "Moving Vehicle", "life_saving_rule": "LSR_09_DRIVING_SAFETY"},
        text_embedding=None,
        pattern_id=None,
        triage_status=TriageStatus.AUTO_SCREENED,
    )
    db_session.add(ass_unrelated)
    await db_session.flush()

    # Execute discovery service
    service = PatternDiscoveryService(session=db_session)
    response = await service.discover_patterns(min_report_count=3, threshold=0.65)

    assert response.qualifying_groups_found >= 1
    assert response.patterns_created >= 1
    assert response.assessments_assigned >= 3

    # Check database: pattern created for our suspended load cluster
    stmt_pat = select(PrecursorPattern).where(PrecursorPattern.hazard_category.ilike("%Suspended%"))
    pat_res = await db_session.execute(stmt_pat)
    patterns = pat_res.scalars().all()
    assert len(patterns) >= 1
    created_pat = patterns[0]
    assert created_pat.occurrence_count >= 3
    assert created_pat.status == PatternStatus.CANDIDATE

    # Verify assessment.pattern_id linked for the 3 reports
    stmt_ass = select(SIFAssessment).where(SIFAssessment.id.in_(assessment_ids))
    ass_res = await db_session.execute(stmt_ass)
    linked_assessments = ass_res.scalars().all()
    for la in linked_assessments:
        assert la.pattern_id is not None
        assert la.pattern_id == created_pat.id

    # Verify unrelated report assessment pattern_id remains NULL
    stmt_unrel = select(SIFAssessment).where(SIFAssessment.id == ass_unrelated.id)
    res_unrel = await db_session.execute(stmt_unrel)
    unrel_assessment = res_unrel.scalar_one()
    assert unrel_assessment.pattern_id is None

    # Test idempotency: run discovery a second time
    count_before_res = await db_session.execute(select(PrecursorPattern))
    total_patterns_before = len(count_before_res.scalars().all())

    response2 = await service.discover_patterns(min_report_count=3, threshold=0.65)
    assert response2.qualifying_groups_found >= 1
    assert response2.patterns_created == 0  # 0 new patterns created
    assert response2.patterns_updated >= 1  # Updated in place

    # Total patterns in DB should be unchanged
    count_after_res = await db_session.execute(select(PrecursorPattern))
    total_patterns_after = len(count_after_res.scalars().all())
    assert total_patterns_after == total_patterns_before


@pytest.mark.asyncio
async def test_non_sif_and_undetermined_strictly_excluded_from_patterns(db_session: AsyncSession):
    """Verify 3 NON_SIF and 3 UNDETERMINED reports never participate in SIF precursor patterns."""
    prec_nonsif = {
        "hazard": "Trip Hazard",
        "activity": "Office Walkway",
        "barrier_failure": "Housekeeping Failure",
        "potential_consequence": "FIRST_AID",
        "life_saving_rule": None,
    }

    prec_undetermined = {
        "hazard": "Unspecified Odor",
        "activity": "Field Walk",
        "potential_consequence": "MEDICAL_TREATMENT",
    }

    # 3 NON_SIF reports
    for i in range(3):
        rep = SafetyReport(
            report_ref=f"SR-NONSIF-{i}-{uuid.uuid4().hex[:6]}",
            source_type=SourceType.NEAR_MISS,
            raw_text=f"Loose electrical cord in office hallway number {i}.",
            reported_location="Admin Moran",
            actual_severity=ActualOutcome.NO_INJURY,
            event_timestamp=datetime(2026, 2, 1 + i, 10, 0, tzinfo=timezone.utc),
        )
        db_session.add(rep)
        await db_session.flush()

        ass = SIFAssessment(
            report_id=rep.id,
            sif_classification=SIFClassification.NON_SIF,
            evidence_score=0.05,
            evidence_strength=EvidenceStrength.LOW,
            rule_based_screening_score=0.05,
            potential_severity=PotentialOutcome.LOW_IMPACT,
            evidence_spans=[],
            structured_precursor=prec_nonsif,
            text_embedding=None,
            pattern_id=None,
            triage_status=TriageStatus.AUTO_SCREENED,
        )
        db_session.add(ass)

    # 3 UNDETERMINED reports
    for i in range(3):
        rep = SafetyReport(
            report_ref=f"SR-UNDET-{i}-{uuid.uuid4().hex[:6]}",
            source_type=SourceType.NEAR_MISS,
            raw_text=f"Faint smell observed near perimeter fence number {i}.",
            reported_location="Dikom Perimeter",
            actual_severity=ActualOutcome.NO_INJURY,
            event_timestamp=datetime(2026, 2, 10 + i, 10, 0, tzinfo=timezone.utc),
        )
        db_session.add(rep)
        await db_session.flush()

        ass = SIFAssessment(
            report_id=rep.id,
            sif_classification=SIFClassification.UNDETERMINED,
            evidence_score=0.3,
            evidence_strength=EvidenceStrength.LOW,
            rule_based_screening_score=0.3,
            potential_severity=PotentialOutcome.LOW_IMPACT,
            evidence_spans=[],
            structured_precursor=prec_undetermined,
            text_embedding=None,
            pattern_id=None,
            triage_status=TriageStatus.AUTO_SCREENED,
        )
        db_session.add(ass)

    await db_session.flush()

    service = PatternDiscoveryService(session=db_session)
    response = await service.discover_patterns(min_report_count=3, threshold=0.65)

    assert response.candidates_evaluated == 0  # Neither NON_SIF nor UNDETERMINED are evaluated
    assert response.qualifying_groups_found == 0
    assert response.patterns_created == 0
    assert response.assessments_assigned == 0


@pytest.mark.asyncio
async def test_mixed_potential_sif_and_non_sif_only_eligible_participate(db_session: AsyncSession):
    """Verify in a mixed dataset, only SIF-eligible assessments form patterns and receive pattern_id."""
    prec = {
        "hazard": "High Pressure Fluid",
        "activity": "Wellhead Testing",
        "barrier_failure": "Isolation Valve Leak",
        "exposure": "Line of Fire",
        "potential_consequence": "FATALITY",
        "life_saving_rule": "LSR_04_ENERGY_ISOLATION",
    }

    # 2 POTENTIAL_SIF reports + 2 NON_SIF reports with identical precursor content
    potential_sif_ids = []
    non_sif_ids = []

    for i in range(2):
        rep = SafetyReport(
            report_ref=f"SR-POT-{i}-{uuid.uuid4().hex[:6]}",
            source_type=SourceType.NEAR_MISS,
            raw_text=f"High pressure gas release during wellhead test {i}.",
            reported_location="Well-01",
            actual_severity=ActualOutcome.NO_INJURY,
            event_timestamp=datetime(2026, 3, 1 + i, 10, 0, tzinfo=timezone.utc),
        )
        db_session.add(rep)
        await db_session.flush()
        potential_sif_ids.append(rep.id)

        ass = SIFAssessment(
            report_id=rep.id,
            sif_classification=SIFClassification.POTENTIAL_SIF,
            evidence_score=0.9,
            evidence_strength=EvidenceStrength.HIGH,
            rule_based_screening_score=0.9,
            potential_severity=PotentialOutcome.FATALITY,
            evidence_spans=[],
            structured_precursor=prec,
            text_embedding=None,
            pattern_id=None,
            triage_status=TriageStatus.AUTO_SCREENED,
        )
        db_session.add(ass)

    for i in range(2):
        rep = SafetyReport(
            report_ref=f"SR-NON-{i}-{uuid.uuid4().hex[:6]}",
            source_type=SourceType.UC,
            raw_text=f"Valve label faded near wellhead {i}.",
            reported_location="Well-01",
            actual_severity=ActualOutcome.NO_INJURY,
            event_timestamp=datetime(2026, 3, 5 + i, 10, 0, tzinfo=timezone.utc),
        )
        db_session.add(rep)
        await db_session.flush()
        non_sif_ids.append(rep.id)

        ass = SIFAssessment(
            report_id=rep.id,
            sif_classification=SIFClassification.NON_SIF,
            evidence_score=0.1,
            evidence_strength=EvidenceStrength.LOW,
            rule_based_screening_score=0.1,
            potential_severity=PotentialOutcome.LOW_IMPACT,
            evidence_spans=[],
            structured_precursor=prec,
            text_embedding=None,
            pattern_id=None,
            triage_status=TriageStatus.AUTO_SCREENED,
        )
        db_session.add(ass)

    await db_session.flush()

    service = PatternDiscoveryService(session=db_session)
    # With min_report_count=3, only 2 POTENTIAL_SIF candidates exist -> no pattern formed yet
    resp1 = await service.discover_patterns(min_report_count=3, threshold=0.65)
    assert resp1.candidates_evaluated == 2
    assert resp1.qualifying_groups_found == 0

    # Add 3rd POTENTIAL_SIF report
    rep3 = SafetyReport(
        report_ref=f"SR-POT-3-{uuid.uuid4().hex[:6]}",
        source_type=SourceType.NEAR_MISS,
        raw_text="Third high pressure release during wellhead test.",
        reported_location="Well-01",
        actual_severity=ActualOutcome.NO_INJURY,
        event_timestamp=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc),
    )
    db_session.add(rep3)
    await db_session.flush()
    potential_sif_ids.append(rep3.id)

    ass3 = SIFAssessment(
        report_id=rep3.id,
        sif_classification=SIFClassification.POTENTIAL_SIF,
        evidence_score=0.9,
        evidence_strength=EvidenceStrength.HIGH,
        rule_based_screening_score=0.9,
        potential_severity=PotentialOutcome.FATALITY,
        evidence_spans=[],
        structured_precursor=prec,
        text_embedding=None,
        pattern_id=None,
        triage_status=TriageStatus.AUTO_SCREENED,
    )
    db_session.add(ass3)
    await db_session.flush()

    # Discover again
    resp2 = await service.discover_patterns(min_report_count=3, threshold=0.65)
    assert resp2.candidates_evaluated == 3
    assert resp2.qualifying_groups_found == 1
    assert resp2.patterns_created == 1

    # Verify only the 3 POTENTIAL_SIF assessments were assigned pattern_id
    stmt_pot = select(SIFAssessment).where(SIFAssessment.report_id.in_(potential_sif_ids))
    res_pot = await db_session.execute(stmt_pot)
    for row in res_pot.scalars().all():
        assert row.pattern_id is not None

    stmt_non = select(SIFAssessment).where(SIFAssessment.report_id.in_(non_sif_ids))
    res_non = await db_session.execute(stmt_non)
    for row in res_non.scalars().all():
        assert row.pattern_id is None


@pytest.mark.asyncio
async def test_pattern_key_and_record_stable_when_membership_grows_in_db(db_session: AsyncSession):
    """Verify discovery 1 (A,B,C) -> discovery 2 (A,B,C,D) updates occurrence_count with same pattern_key and no duplicate."""
    prec = {
        "hazard": "Toxic Gas Exposure",
        "activity": "Confined Tank Inspection",
        "barrier_failure": "Gas Detector Calibration Failure",
        "exposure": "Toxic Atmosphere",
        "potential_consequence": "FATALITY",
        "life_saving_rule": "LSR_05_CONFINED_SPACE",
    }

    # Step 1: Insert 3 reports (A, B, C)
    report_ids_initial = []
    for i in range(3):
        rep = SafetyReport(
            report_ref=f"SR-CONF-{i}-{uuid.uuid4().hex[:6]}",
            source_type=SourceType.NEAR_MISS,
            raw_text=f"H2S gas alarm triggered in tank {i}.",
            reported_location="Tank Farm Moran",
            actual_severity=ActualOutcome.NO_INJURY,
            event_timestamp=datetime(2026, 4, 1 + i, 10, 0, tzinfo=timezone.utc),
        )
        db_session.add(rep)
        await db_session.flush()
        report_ids_initial.append(rep.id)

        ass = SIFAssessment(
            report_id=rep.id,
            sif_classification=SIFClassification.POTENTIAL_SIF,
            evidence_score=0.9,
            evidence_strength=EvidenceStrength.HIGH,
            rule_based_screening_score=0.9,
            potential_severity=PotentialOutcome.FATALITY,
            evidence_spans=[],
            structured_precursor=prec,
            text_embedding=None,
            pattern_id=None,
            triage_status=TriageStatus.AUTO_SCREENED,
        )
        db_session.add(ass)

    await db_session.flush()

    service = PatternDiscoveryService(session=db_session)
    resp1 = await service.discover_patterns(min_report_count=3, threshold=0.65)
    assert resp1.patterns_created == 1
    assert resp1.patterns_updated == 0

    pat1_dto = resp1.discovered_patterns[0]
    initial_pattern_key = pat1_dto.pattern_code
    assert pat1_dto.occurrence_count == 3

    # Step 2: Add 4th report (D) with same precursor
    rep4 = SafetyReport(
        report_ref=f"SR-CONF-4-{uuid.uuid4().hex[:6]}",
        source_type=SourceType.NEAR_MISS,
        raw_text="H2S gas alarm triggered in tank 4 during inspection.",
        reported_location="Tank Farm Moran",
        actual_severity=ActualOutcome.NO_INJURY,
        event_timestamp=datetime(2026, 4, 15, 10, 0, tzinfo=timezone.utc),
    )
    db_session.add(rep4)
    await db_session.flush()

    ass4 = SIFAssessment(
        report_id=rep4.id,
        sif_classification=SIFClassification.POTENTIAL_SIF,
        evidence_score=0.9,
        evidence_strength=EvidenceStrength.HIGH,
        rule_based_screening_score=0.9,
        potential_severity=PotentialOutcome.FATALITY,
        evidence_spans=[],
        structured_precursor=prec,
        text_embedding=None,
        pattern_id=None,
        triage_status=TriageStatus.AUTO_SCREENED,
    )
    db_session.add(ass4)
    await db_session.flush()

    # Step 3: Run discovery 2
    resp2 = await service.discover_patterns(min_report_count=3, threshold=0.65)
    assert resp2.patterns_created == 0  # NO duplicate pattern created
    assert resp2.patterns_updated == 1  # Pattern updated in place

    # Check pattern in DB
    stmt_pat = select(PrecursorPattern).where(PrecursorPattern.pattern_code == initial_pattern_key)
    res_pat = await db_session.execute(stmt_pat)
    pattern_in_db = res_pat.scalar_one()

    # Pattern key, ID, and occurrence count verified
    assert pattern_in_db.pattern_code == initial_pattern_key
    assert pattern_in_db.id == pat1_dto.id
    assert pattern_in_db.occurrence_count == 4
    assert str(rep4.id) in pattern_in_db.supporting_report_ids

    # Verify all 4 assessments have pattern_id set
    all_4_ids = report_ids_initial + [rep4.id]
    stmt_all = select(SIFAssessment).where(SIFAssessment.report_id.in_(all_4_ids))
    res_all = await db_session.execute(stmt_all)
    for ass_row in res_all.scalars().all():
        assert ass_row.pattern_id == pattern_in_db.id

