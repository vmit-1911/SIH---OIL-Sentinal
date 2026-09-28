"""Integration tests for RiskConcentrationService covering Scenarios A through T."""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.assessment import SIFAssessment
from app.db.models.concentration import RiskConcentration
from app.db.models.pattern import PrecursorPattern
from app.db.models.report import SafetyReport
from app.domain.enums import (
    ActualOutcome,
    ConcentrationDimension,
    ConcentrationStatus,
    EvidenceStrength,
    ObservedTrend,
    PotentialOutcome,
    SIFClassification,
    SourceType,
    TriageStatus,
)
from app.services.risk_concentration_service import RiskConcentrationService


@pytest.mark.asyncio
async def test_scenarios_a_i_q_three_recurring_precursors_form_multi_dimensional_concentrations(db_session: AsyncSession):
    """SCENARIO A, I, Q: 3 recurring reports form concentrations across Pattern, Hazard, Barrier, Activity, LSR, Location with correct monthly temporal distribution."""
    prec = {
        "hazard": "Suspended Load",
        "activity": "Crane Lifting Operation",
        "barrier_failure": "Rigging Failure",
        "exposure": "Line of Fire",
        "potential_consequence": "FATALITY",
        "life_saving_rule": "LSR_03_MECHANICAL_LIFTING",
    }

    # 3 reports spanning 2026-01, 2026-02, 2026-03
    report_ids = []
    months = [1, 2, 3]
    for i in range(3):
        rep = SafetyReport(
            report_ref=f"SR-CONC-{i}-{uuid.uuid4().hex[:6]}",
            source_type=SourceType.NEAR_MISS,
            raw_text=f"Casing lift line parted during crane operations event {i}.",
            reported_location="Rig-04 / Moran",
            actual_severity=ActualOutcome.NO_INJURY,
            event_timestamp=datetime(2026, months[i], 15, 10, 0, tzinfo=timezone.utc),
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
            triage_status=TriageStatus.AUTO_SCREENED,
        )
        db_session.add(ass)

    # Insert 1 PrecursorPattern grouping these 3 reports
    pat = PrecursorPattern(
        id=uuid.uuid4(),
        pattern_code="PAT_LSR_03_SUSPENDED_LOAD_A1B2C3D4",
        title="Recurring Suspended Load with Rigging Failure",
        description="3 reports grouped as recurring precursor",
        hazard_category="Suspended Load",
        activity_type="Crane Lifting Operation",
        failed_barrier_type="Rigging Failure",
        lsr_code="LSR_03_MECHANICAL_LIFTING",
        occurrence_count=3,
        affected_locations=["Rig-04 / Moran"],
        supporting_report_ids=[str(rid) for rid in report_ids],
        supporting_lsr_codes=["LSR_03_MECHANICAL_LIFTING"],
    )
    db_session.add(pat)
    await db_session.flush()

    service = RiskConcentrationService(session=db_session)
    response = await service.refresh_concentrations()

    assert response.assessments_evaluated == 3
    assert response.concentrations_created >= 5  # PATTERN, HAZARD, BARRIER_FAILURE, ACTIVITY, LIFE_SAVING_RULE, LOCATION
    assert response.total_active_concentrations >= 5

    # Check Hazard concentration
    res_haz = await service.get_concentrations(dimension=ConcentrationDimension.HAZARD)
    assert len(res_haz.concentrations) == 1
    haz_dto = res_haz.concentrations[0]
    assert haz_dto.dimension_value == "Suspended Load"
    assert haz_dto.occurrence_count == 3
    assert haz_dto.distinct_report_count == 3
    assert haz_dto.distinct_location_count == 1
    # Temporal distribution across 3 months
    assert haz_dto.temporal_distribution == {"2026-01": 1, "2026-02": 1, "2026-03": 1}
    assert haz_dto.observed_trend == ObservedTrend.STABLE

    # Check Location concentration
    res_loc = await service.get_concentrations(dimension=ConcentrationDimension.LOCATION)
    assert len(res_loc.concentrations) == 1
    loc_dto = res_loc.concentrations[0]
    assert loc_dto.dimension_value == "Rig-04 / Moran"
    assert loc_dto.occurrence_count == 3

    # Check Pattern concentration
    res_pat = await service.get_concentrations(dimension=ConcentrationDimension.PATTERN)
    assert len(res_pat.concentrations) == 1
    pat_dto = res_pat.concentrations[0]
    assert pat_dto.pattern_id == pat.id
    assert pat_dto.occurrence_count == 3


@pytest.mark.asyncio
async def test_scenario_b_two_reports_aggregates_without_false_recurrence(db_session: AsyncSession):
    """SCENARIO B: 2 reports only aggregate correctly without artificial recurrence claims."""
    prec = {"hazard": "High Pressure Gas", "life_saving_rule": "LSR_04_ENERGY_ISOLATION"}

    for i in range(2):
        rep = SafetyReport(
            report_ref=f"SR-TWO-{i}-{uuid.uuid4().hex[:6]}",
            source_type=SourceType.NEAR_MISS,
            raw_text=f"Pressure release incident {i}.",
            reported_location="EPS Moran",
            actual_severity=ActualOutcome.NO_INJURY,
            event_timestamp=datetime(2026, 1, 10 + i, 10, 0, tzinfo=timezone.utc),
        )
        db_session.add(rep)
        await db_session.flush()

        ass = SIFAssessment(
            report_id=rep.id,
            sif_classification=SIFClassification.POTENTIAL_SIF,
            evidence_score=0.85,
            evidence_strength=EvidenceStrength.HIGH,
            rule_based_screening_score=0.85,
            potential_severity=PotentialOutcome.FATALITY,
            evidence_spans=[],
            structured_precursor=prec,
            triage_status=TriageStatus.AUTO_SCREENED,
        )
        db_session.add(ass)

    await db_session.flush()

    service = RiskConcentrationService(session=db_session)
    response = await service.refresh_concentrations()

    assert response.assessments_evaluated == 2
    res_haz = await service.get_concentrations(dimension=ConcentrationDimension.HAZARD)
    assert len(res_haz.concentrations) == 1
    assert res_haz.concentrations[0].occurrence_count == 2
    assert res_haz.concentrations[0].distinct_report_count == 2


@pytest.mark.asyncio
async def test_scenarios_c_d_e_non_sif_and_undetermined_excluded(db_session: AsyncSession):
    """SCENARIOS C, D, E: NON_SIF and UNDETERMINED excluded, only POTENTIAL_SIF participate in mixed dataset."""
    prec_pot = {"hazard": "Toxic Gas Exposure", "life_saving_rule": "LSR_05_CONFINED_SPACE"}
    prec_non = {"hazard": "Trip Hazard"}
    prec_undet = {"hazard": "Odor"}

    # 2 POTENTIAL_SIF
    for i in range(2):
        rep = SafetyReport(
            report_ref=f"SR-POT-{i}-{uuid.uuid4().hex[:6]}",
            source_type=SourceType.NEAR_MISS,
            raw_text="H2S alarm.",
            reported_location="GGS Dikom",
            actual_severity=ActualOutcome.NO_INJURY,
            event_timestamp=datetime(2026, 1, 5 + i, 10, 0, tzinfo=timezone.utc),
        )
        db_session.add(rep)
        await db_session.flush()
        ass = SIFAssessment(
            report_id=rep.id,
            sif_classification=SIFClassification.POTENTIAL_SIF,
            evidence_score=0.9,
            evidence_strength=EvidenceStrength.HIGH,
            rule_based_screening_score=0.9,
            potential_severity=PotentialOutcome.FATALITY,
            evidence_spans=[],
            structured_precursor=prec_pot,
            triage_status=TriageStatus.AUTO_SCREENED,
        )
        db_session.add(ass)

    # 2 NON_SIF
    for i in range(2):
        rep = SafetyReport(
            report_ref=f"SR-NON-{i}-{uuid.uuid4().hex[:6]}",
            source_type=SourceType.UC,
            raw_text="Loose wire.",
            reported_location="Admin Moran",
            actual_severity=ActualOutcome.NO_INJURY,
            event_timestamp=datetime(2026, 1, 10 + i, 10, 0, tzinfo=timezone.utc),
        )
        db_session.add(rep)
        await db_session.flush()
        ass = SIFAssessment(
            report_id=rep.id,
            sif_classification=SIFClassification.NON_SIF,
            evidence_score=0.1,
            evidence_strength=EvidenceStrength.LOW,
            rule_based_screening_score=0.1,
            potential_severity=PotentialOutcome.LOW_IMPACT,
            evidence_spans=[],
            structured_precursor=prec_non,
            triage_status=TriageStatus.AUTO_SCREENED,
        )
        db_session.add(ass)

    # 2 UNDETERMINED
    for i in range(2):
        rep = SafetyReport(
            report_ref=f"SR-UNDET-{i}-{uuid.uuid4().hex[:6]}",
            source_type=SourceType.UA,
            raw_text="Unclear observation.",
            reported_location="Moran Field",
            actual_severity=ActualOutcome.NO_INJURY,
            event_timestamp=datetime(2026, 1, 15 + i, 10, 0, tzinfo=timezone.utc),
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
            structured_precursor=prec_undet,
            triage_status=TriageStatus.AUTO_SCREENED,
        )
        db_session.add(ass)

    await db_session.flush()

    service = RiskConcentrationService(session=db_session)
    response = await service.refresh_concentrations()

    # Evaluated only the 2 POTENTIAL_SIF assessments
    assert response.assessments_evaluated == 2

    # Verify only Toxic Gas hazard concentration exists, Trip Hazard / Odor do NOT exist
    res_haz = await service.get_concentrations(dimension=ConcentrationDimension.HAZARD)
    assert len(res_haz.concentrations) == 1
    assert res_haz.concentrations[0].dimension_value == "Toxic Gas Exposure"


@pytest.mark.asyncio
async def test_scenarios_f_g_h_r_multi_location_missing_location_and_multiple_lsrs(db_session: AsyncSession):
    """SCENARIOS F, G, H, R: Multi-location preservation, missing location does not fabricate UNKNOWN, and multiple LSRs tracked."""
    # Report 1: Rig-01, LSR 03
    rep1 = SafetyReport(
        report_ref="SR-FGH-1",
        source_type=SourceType.NEAR_MISS,
        raw_text="Casing sling failure.",
        reported_location="Rig-01 Nahorkatiya",
        actual_severity=ActualOutcome.NO_INJURY,
        event_timestamp=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
    )
    db_session.add(rep1)
    await db_session.flush()
    db_session.add(SIFAssessment(
        report_id=rep1.id,
        sif_classification=SIFClassification.POTENTIAL_SIF,
        evidence_score=0.9,
        evidence_strength=EvidenceStrength.HIGH,
        rule_based_screening_score=0.9,
        potential_severity=PotentialOutcome.FATALITY,
        evidence_spans=[],
        structured_precursor={"hazard": "Suspended Load", "life_saving_rule": "LSR_03_MECHANICAL_LIFTING"},
        triage_status=TriageStatus.AUTO_SCREENED,
    ))

    # Report 2: Rig-02, LSR 01
    rep2 = SafetyReport(
        report_ref="SR-FGH-2",
        source_type=SourceType.NEAR_MISS,
        raw_text="Casing sling failure bypassing interlock.",
        reported_location="Rig-02 Moran",
        actual_severity=ActualOutcome.NO_INJURY,
        event_timestamp=datetime(2026, 1, 5, 10, 0, tzinfo=timezone.utc),
    )
    db_session.add(rep2)
    await db_session.flush()
    db_session.add(SIFAssessment(
        report_id=rep2.id,
        sif_classification=SIFClassification.POTENTIAL_SIF,
        evidence_score=0.9,
        evidence_strength=EvidenceStrength.HIGH,
        rule_based_screening_score=0.9,
        potential_severity=PotentialOutcome.FATALITY,
        evidence_spans=[],
        structured_precursor={"hazard": "Suspended Load", "life_saving_rule": "LSR_01_BYPASSING_SAFETY_CONTROLS"},
        triage_status=TriageStatus.AUTO_SCREENED,
    ))

    # Report 3: Missing location (None), LSR 03
    rep3 = SafetyReport(
        report_ref="SR-FGH-3",
        source_type=SourceType.NEAR_MISS,
        raw_text="Casing sling failure unspecified location.",
        reported_location=None,
        actual_severity=ActualOutcome.NO_INJURY,
        event_timestamp=datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc),
    )
    db_session.add(rep3)
    await db_session.flush()
    db_session.add(SIFAssessment(
        report_id=rep3.id,
        sif_classification=SIFClassification.POTENTIAL_SIF,
        evidence_score=0.9,
        evidence_strength=EvidenceStrength.HIGH,
        rule_based_screening_score=0.9,
        potential_severity=PotentialOutcome.FATALITY,
        evidence_spans=[],
        structured_precursor={"hazard": "Suspended Load", "life_saving_rule": "LSR_03_MECHANICAL_LIFTING"},
        triage_status=TriageStatus.AUTO_SCREENED,
    ))

    await db_session.flush()

    service = RiskConcentrationService(session=db_session)
    await service.refresh_concentrations()

    # Check Hazard concentration
    res_haz = await service.get_concentrations(dimension=ConcentrationDimension.HAZARD)
    haz_dto = res_haz.concentrations[0]
    assert haz_dto.occurrence_count == 3
    # Locations tracked: Rig-01, Rig-02 (no "UNKNOWN" fabricated for report 3)
    assert set(haz_dto.supporting_locations) == {"Rig-01 Nahorkatiya", "Rig-02 Moran"}
    assert haz_dto.distinct_location_count == 2
    # LSRs tracked: both LSR_01 and LSR_03
    assert set(haz_dto.supporting_lsr_codes) == {"LSR_01_BYPASSING_SAFETY_CONTROLS", "LSR_03_MECHANICAL_LIFTING"}

    # Check Location concentrations: only 2 location concentrations created (Rig-01, Rig-02), none for None/UNKNOWN
    res_loc = await service.get_concentrations(dimension=ConcentrationDimension.LOCATION)
    assert len(res_loc.concentrations) == 2
    loc_names = {l.dimension_value for l in res_loc.concentrations}
    assert loc_names == {"Rig-01 Nahorkatiya", "Rig-02 Moran"}
    assert "UNKNOWN" not in loc_names


@pytest.mark.asyncio
async def test_scenarios_j_k_l_m_trends_increasing_decreasing_stable_insufficient(db_session: AsyncSession):
    """SCENARIOS J, K, L, M: Verify trend classification on INCREASING, DECREASING, STABLE, and INSUFFICIENT_DATA."""
    service = RiskConcentrationService(session=db_session)

    # 1. Increasing Hazard: 1 in Jan, 2 in Feb, 4 in March
    hazard_inc = "High Pressure Wellhead"
    counts_inc = [1, 2, 4]
    for m_idx, count in enumerate(counts_inc):
        for c_idx in range(count):
            rep = SafetyReport(
                report_ref=f"SR-INC-{m_idx}-{c_idx}",
                source_type=SourceType.NEAR_MISS,
                raw_text="Pressure leak.",
                reported_location="Well-01",
                actual_severity=ActualOutcome.NO_INJURY,
                event_timestamp=datetime(2026, m_idx + 1, 10 + c_idx, 10, 0, tzinfo=timezone.utc),
            )
            db_session.add(rep)
            await db_session.flush()
            db_session.add(SIFAssessment(
                report_id=rep.id,
                sif_classification=SIFClassification.POTENTIAL_SIF,
                evidence_score=0.9,
                evidence_strength=EvidenceStrength.HIGH,
                rule_based_screening_score=0.9,
                potential_severity=PotentialOutcome.FATALITY,
                evidence_spans=[],
                structured_precursor={"hazard": hazard_inc},
                triage_status=TriageStatus.AUTO_SCREENED,
            ))

    # 2. Decreasing Hazard: 4 in Jan, 2 in Feb, 1 in March
    hazard_dec = "Electrical Arc"
    counts_dec = [4, 2, 1]
    for m_idx, count in enumerate(counts_dec):
        for c_idx in range(count):
            rep = SafetyReport(
                report_ref=f"SR-DEC-{m_idx}-{c_idx}",
                source_type=SourceType.NEAR_MISS,
                raw_text="Arc flash.",
                reported_location="Substation-01",
                actual_severity=ActualOutcome.NO_INJURY,
                event_timestamp=datetime(2026, m_idx + 1, 10 + c_idx, 10, 0, tzinfo=timezone.utc),
            )
            db_session.add(rep)
            await db_session.flush()
            db_session.add(SIFAssessment(
                report_id=rep.id,
                sif_classification=SIFClassification.POTENTIAL_SIF,
                evidence_score=0.9,
                evidence_strength=EvidenceStrength.HIGH,
                rule_based_screening_score=0.9,
                potential_severity=PotentialOutcome.FATALITY,
                evidence_spans=[],
                structured_precursor={"hazard": hazard_dec},
                triage_status=TriageStatus.AUTO_SCREENED,
            ))

    # 3. Insufficient data: only in 1 month (Jan)
    hazard_insuf = "Dropped Tubular"
    rep_ins = SafetyReport(
        report_ref="SR-INS-1",
        source_type=SourceType.NEAR_MISS,
        raw_text="Dropped pipe.",
        reported_location="Rig-04",
        actual_severity=ActualOutcome.NO_INJURY,
        event_timestamp=datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc),
    )
    db_session.add(rep_ins)
    await db_session.flush()
    db_session.add(SIFAssessment(
        report_id=rep_ins.id,
        sif_classification=SIFClassification.POTENTIAL_SIF,
        evidence_score=0.9,
        evidence_strength=EvidenceStrength.HIGH,
        rule_based_screening_score=0.9,
        potential_severity=PotentialOutcome.FATALITY,
        evidence_spans=[],
        structured_precursor={"hazard": hazard_insuf},
        triage_status=TriageStatus.AUTO_SCREENED,
    ))

    await db_session.flush()

    await service.refresh_concentrations()

    # Query trends
    trends_res = await service.get_trends(dimension=ConcentrationDimension.HAZARD)
    trends_by_val = {t.dimension_value: t for t in trends_res.trends}

    assert trends_by_val[hazard_inc].observed_trend == ObservedTrend.INCREASING
    assert trends_by_val[hazard_dec].observed_trend == ObservedTrend.DECREASING
    assert trends_by_val[hazard_insuf].observed_trend == ObservedTrend.INSUFFICIENT_DATA


@pytest.mark.asyncio
async def test_scenarios_n_o_membership_growth_and_idempotent_refresh(db_session: AsyncSession):
    """SCENARIOS N, O: Membership growth updates existing concentration; duplicate refresh is 100% idempotent."""
    service = RiskConcentrationService(session=db_session)
    hazard = "Confined Space Toxic Gas"

    # Step 1: 3 reports
    rids = []
    for i in range(3):
        rep = SafetyReport(
            report_ref=f"SR-IDEM-{i}",
            source_type=SourceType.NEAR_MISS,
            raw_text="Gas alarm in tank.",
            reported_location="Tank Farm",
            actual_severity=ActualOutcome.NO_INJURY,
            event_timestamp=datetime(2026, 1, 10 + i, 10, 0, tzinfo=timezone.utc),
        )
        db_session.add(rep)
        await db_session.flush()
        rids.append(rep.id)
        db_session.add(SIFAssessment(
            report_id=rep.id,
            sif_classification=SIFClassification.POTENTIAL_SIF,
            evidence_score=0.9,
            evidence_strength=EvidenceStrength.HIGH,
            rule_based_screening_score=0.9,
            potential_severity=PotentialOutcome.FATALITY,
            evidence_spans=[],
            structured_precursor={"hazard": hazard},
            triage_status=TriageStatus.AUTO_SCREENED,
        ))

    await db_session.flush()

    # Run 1: created=1
    resp1 = await service.refresh_concentrations()
    assert resp1.concentrations_created >= 1
    assert resp1.concentrations_updated == 0

    res_haz1 = await service.get_concentrations(dimension=ConcentrationDimension.HAZARD)
    dto1 = res_haz1.concentrations[0]
    initial_id = dto1.id
    initial_key = dto1.concentration_key
    assert dto1.occurrence_count == 3

    # Run 2 (no new data): created=0, updated >= 1 (Idempotent!)
    resp2 = await service.refresh_concentrations()
    assert resp2.concentrations_created == 0
    assert resp2.concentrations_updated >= 1

    count_res = await db_session.execute(select(RiskConcentration))
    total_in_db = len(count_res.scalars().all())

    # Run 3: Add 4th report (membership growth)
    rep4 = SafetyReport(
        report_ref="SR-IDEM-4",
        source_type=SourceType.NEAR_MISS,
        raw_text="Gas alarm in tank 4.",
        reported_location="Tank Farm",
        actual_severity=ActualOutcome.NO_INJURY,
        event_timestamp=datetime(2026, 1, 20, 10, 0, tzinfo=timezone.utc),
    )
    db_session.add(rep4)
    await db_session.flush()
    db_session.add(SIFAssessment(
        report_id=rep4.id,
        sif_classification=SIFClassification.POTENTIAL_SIF,
        evidence_score=0.9,
        evidence_strength=EvidenceStrength.HIGH,
        rule_based_screening_score=0.9,
        potential_severity=PotentialOutcome.FATALITY,
        evidence_spans=[],
        structured_precursor={"hazard": hazard},
        triage_status=TriageStatus.AUTO_SCREENED,
    ))
    await db_session.flush()

    resp3 = await service.refresh_concentrations()
    assert resp3.concentrations_created == 0  # NO duplicate created!
    assert resp3.concentrations_updated >= 1

    res_haz3 = await service.get_concentrations(dimension=ConcentrationDimension.HAZARD)
    dto3 = res_haz3.concentrations[0]
    assert dto3.id == initial_id
    assert dto3.concentration_key == initial_key
    assert dto3.occurrence_count == 4
    assert dto3.distinct_report_count == 4


@pytest.mark.asyncio
async def test_scenario_p_empty_dataset_returns_clean_empty_response(db_session: AsyncSession):
    """SCENARIO P: Empty dataset produces zero concentrations without fabricating placeholder analytics."""
    service = RiskConcentrationService(session=db_session)
    response = await service.refresh_concentrations()

    assert response.assessments_evaluated == 0
    assert response.concentrations_created == 0
    assert response.concentrations_updated == 0
    assert response.total_active_concentrations == 0

    list_res = await service.get_concentrations()
    assert list_res.total_concentrations == 0
    assert list_res.concentrations == []

    summary = await service.get_analytics_summary()
    assert summary.total_reports_analyzed == 0
    assert summary.sif_potential_percentage == 0.0


@pytest.mark.asyncio
async def test_scenarios_s_t_date_filtering_and_boundaries(db_session: AsyncSession):
    """SCENARIOS S, T: Date range filtering and boundary timestamps."""
    service = RiskConcentrationService(session=db_session)
    hazard = "Drilling Wellhead Kicks"

    # Insert 3 reports on Jan 10, Feb 10, Mar 10
    dates = [
        datetime(2026, 1, 10, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 2, 10, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 10, 0, 0, tzinfo=timezone.utc),
    ]
    for i, d in enumerate(dates):
        rep = SafetyReport(
            report_ref=f"SR-DATE-{i}",
            source_type=SourceType.NEAR_MISS,
            raw_text="Well kick.",
            reported_location="Rig-01",
            actual_severity=ActualOutcome.NO_INJURY,
            event_timestamp=d,
        )
        db_session.add(rep)
        await db_session.flush()
        db_session.add(SIFAssessment(
            report_id=rep.id,
            sif_classification=SIFClassification.POTENTIAL_SIF,
            evidence_score=0.9,
            evidence_strength=EvidenceStrength.HIGH,
            rule_based_screening_score=0.9,
            potential_severity=PotentialOutcome.FATALITY,
            evidence_spans=[],
            structured_precursor={"hazard": hazard},
            triage_status=TriageStatus.AUTO_SCREENED,
        ))

    await db_session.flush()

    # Filter with start_date=Feb 1, end_date=Feb 28
    start_f = datetime(2026, 2, 1, 0, 0, tzinfo=timezone.utc)
    end_f = datetime(2026, 2, 28, 23, 59, tzinfo=timezone.utc)

    resp = await service.refresh_concentrations(start_date=start_f, end_date=end_f)
    assert resp.assessments_evaluated == 1

    res_haz = await service.get_concentrations(dimension=ConcentrationDimension.HAZARD)
    assert res_haz.concentrations[0].occurrence_count == 1
    assert res_haz.concentrations[0].temporal_distribution == {"2026-02": 1}
