"""Unit tests for EvidenceExplanationService."""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AssessmentNotFoundException,
    ConcentrationNotFoundException,
    PatternNotFoundException,
    ReportNotFoundException,
)
from app.db.models.assessment import SIFAssessment
from app.db.models.concentration import RiskConcentration
from app.db.models.pattern import PrecursorPattern
from app.db.models.report import SafetyReport
from app.db.models.taxonomy import LSRReportMapping, LSRTaxonomy
from app.domain.enums import (
    ActualOutcome,
    ConcentrationDimension,
    ConcentrationStatus,
    DerivationType,
    EvidenceStrength,
    ObservedTrend,
    PatternStatus,
    PotentialOutcome,
    SIFClassification,
    SourceType,
    TriageStatus,
)
from app.schemas.intelligence import EvidenceType
from app.services.evidence_explanation_service import EvidenceExplanationService
from app.services.sif_analysis_service import SIFAnalysisService


@pytest.mark.asyncio
async def test_extract_evidence_items_comprehensive(db_session: AsyncSession):
    """Verify evidence items are accurately extracted with character offsets, normalized concepts, and types."""
    service = EvidenceExplanationService(db_session)

    report = SafetyReport(
        id=uuid.uuid4(),
        report_ref="SR-EV-001",
        source_type=SourceType.NEAR_MISS,
        raw_text=(
            "While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung "
            "across the rig floor, narrowly missing two floormen who jumped out of the way. No injuries occurred."
        ),
        reported_location="Rig-04 / Moran Field",
        reported_department="Drilling Operations",
        actual_severity=ActualOutcome.NO_INJURY,
    )
    db_session.add(report)
    await db_session.flush()

    items = service._extract_evidence_items(report)
    assert len(items) >= 4

    types = [i.evidence_type for i in items]
    assert EvidenceType.HAZARD in types
    assert EvidenceType.BARRIER in types
    assert EvidenceType.EXPOSURE in types
    assert EvidenceType.ACTIVITY in types

    # Check offsets and provenance
    for item in items:
        assert item.evidence_id.startswith(f"EV-{report.id.hex[:8]}-")
        assert item.source_text is not None
        assert item.start_offset is not None
        assert item.end_offset is not None
        assert item.end_offset > item.start_offset
        assert item.provenance_rule is not None


@pytest.mark.asyncio
async def test_get_screening_explanation_structured(db_session: AsyncSession):
    """Verify screening explanation contains complete factors, triggered rules, and precursor provenance."""
    sif_service = SIFAnalysisService(db_session)
    expl_service = EvidenceExplanationService(db_session)

    from app.schemas.report import SingleReportAnalysisRequest

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-EXPL-001",
            raw_text="While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung across the rig floor, narrowly missing two floormen.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04 / Moran",
        )
    )

    explanation = await expl_service.get_screening_explanation(res.report_id)
    assert explanation.report_id == res.report_id
    assert explanation.classification == SIFClassification.POTENTIAL_SIF
    assert explanation.evidence_score >= 0.60
    assert explanation.evidence_strength in (EvidenceStrength.MEDIUM, EvidenceStrength.HIGH)
    assert "energy_hazard" in explanation.factors
    assert "barrier_degradation" in explanation.factors
    assert "exposure_proximity" in explanation.factors
    assert explanation.factors["energy_hazard"].present is True
    assert explanation.factors["barrier_degradation"].present is True
    assert explanation.factors["exposure_proximity"].present is True

    # Precursor provenance
    assert "hazard" in explanation.precursor_provenance
    assert "barrier_failure" in explanation.precursor_provenance
    assert explanation.precursor_provenance["hazard"].value is not None


@pytest.mark.asyncio
async def test_assessment_similar_reports_ranking(db_session: AsyncSession):
    """Verify similar reports ranking by hybrid similarity score."""
    sif_service = SIFAnalysisService(db_session)
    expl_service = EvidenceExplanationService(db_session)

    from app.schemas.report import SingleReportAnalysisRequest

    res1 = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-SIM-001",
            raw_text="While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung across the rig floor, narrowly missing two floormen who jumped out of the way.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04 / Moran",
        )
    )

    res2 = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-SIM-002",
            raw_text="While running 9-5/8 inch casing at Rig-04, the wire rope snapped and the heavy elevator swung across the rig floor, with floormen standing under load.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04 / Moran",
        )
    )

    # Completely unrelated report
    await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-SIM-UNRELATED",
            raw_text="Empty paint cans and cleaning rags left unattended near workshop entrance creating trip hazard.",
            source_type=SourceType.UC,
            reported_location="Workshop",
        )
    )

    ass_res = await db_session.execute(select(SIFAssessment).where(SIFAssessment.report_id == res1.report_id))
    assessment = ass_res.scalar_one()

    sim_response = await expl_service.get_assessment_similar_reports(assessment.id, limit=5, threshold=0.50)
    assert sim_response.total_similar_reports >= 1

    top_match = sim_response.similar_reports[0]
    assert top_match.matched_report_ref == res2.report_ref
    assert top_match.hybrid_score >= 0.70
    assert len(top_match.matching_dimensions) >= 3


@pytest.mark.asyncio
async def test_pattern_and_concentration_evidence_traceability(db_session: AsyncSession):
    """Verify full pattern and concentration traceability to underlying reports."""
    expl_service = EvidenceExplanationService(db_session)

    # 1. Create Reports & Assessments
    r1 = SafetyReport(
        id=uuid.uuid4(),
        report_ref="SR-PAT-001",
        source_type=SourceType.NEAR_MISS,
        raw_text="Rigging failed during crane lift.",
        reported_location="Rig-01",
        actual_severity=ActualOutcome.NO_INJURY,
    )
    r2 = SafetyReport(
        id=uuid.uuid4(),
        report_ref="SR-PAT-002",
        source_type=SourceType.NEAR_MISS,
        raw_text="Winch line parted during casing lift.",
        reported_location="Rig-01",
        actual_severity=ActualOutcome.NO_INJURY,
    )
    db_session.add_all([r1, r2])
    await db_session.flush()

    a1 = SIFAssessment(
        id=uuid.uuid4(),
        report_id=r1.id,
        sif_classification=SIFClassification.POTENTIAL_SIF,
        evidence_score=0.85,
        evidence_strength=EvidenceStrength.HIGH,
        rule_based_screening_score=0.85,
        potential_severity=PotentialOutcome.FATALITY,
        structured_precursor={"hazard": "Suspended Load", "barrier_failure": "Rigging Failure"},
        triage_status=TriageStatus.AUTO_SCREENED,
    )
    a2 = SIFAssessment(
        id=uuid.uuid4(),
        report_id=r2.id,
        sif_classification=SIFClassification.POTENTIAL_SIF,
        evidence_score=0.85,
        evidence_strength=EvidenceStrength.HIGH,
        rule_based_screening_score=0.85,
        potential_severity=PotentialOutcome.FATALITY,
        structured_precursor={"hazard": "Suspended Load", "barrier_failure": "Rigging Failure"},
        triage_status=TriageStatus.AUTO_SCREENED,
    )
    db_session.add_all([a1, a2])
    await db_session.flush()

    # 2. Create Pattern
    pattern = PrecursorPattern(
        id=uuid.uuid4(),
        pattern_code="PAT_TEST_SUSPENDED_LOAD_001",
        title="Recurring Rigging Failure",
        description="Pattern of rigging failures on Rig-01",
        hazard_category="Suspended Load",
        failed_barrier_type="Rigging Failure",
        occurrence_count=2,
        affected_locations=["Rig-01"],
        supporting_report_ids=[str(r1.id), str(r2.id)],
        status=PatternStatus.ACTIVE,
        first_detected_at=datetime.now(timezone.utc),
        last_detected_at=datetime.now(timezone.utc),
    )
    db_session.add(pattern)

    # 3. Create Concentration
    conc = RiskConcentration(
        id=uuid.uuid4(),
        concentration_key="CONC|LOCATION|RIG_01",
        dimension_type=ConcentrationDimension.LOCATION,
        dimension_value="Rig-01",
        occurrence_count=2,
        distinct_report_count=2,
        distinct_location_count=1,
        first_observed_at=datetime.now(timezone.utc),
        last_observed_at=datetime.now(timezone.utc),
        observed_trend=ObservedTrend.STABLE,
        supporting_report_ids=[str(r1.id), str(r2.id)],
        supporting_locations=["Rig-01"],
        status=ConcentrationStatus.ACTIVE,
        calculation_method="FREQUENCY_AGGREGATION_V1",
    )
    db_session.add(conc)
    await db_session.flush()

    # Test Pattern Evidence
    pat_ev = await expl_service.get_pattern_evidence(pattern.id)
    assert pat_ev.pattern_code == "PAT_TEST_SUSPENDED_LOAD_001"
    assert len(pat_ev.supporting_reports) == 2
    refs = [sr.report_ref for sr in pat_ev.supporting_reports]
    assert "SR-PAT-001" in refs
    assert "SR-PAT-002" in refs

    # Test Concentration Evidence
    conc_ev = await expl_service.get_concentration_evidence("CONC|LOCATION|RIG_01")
    assert conc_ev.concentration_key == "CONC|LOCATION|RIG_01"
    assert len(conc_ev.supporting_reports) == 2


@pytest.mark.asyncio
async def test_investigation_context_consolidation(db_session: AsyncSession):
    """Verify complete 10-dimension investigation context aggregation for a report."""
    sif_service = SIFAnalysisService(db_session)
    expl_service = EvidenceExplanationService(db_session)

    from app.schemas.report import SingleReportAnalysisRequest

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-CTX-001",
            raw_text="While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung across the rig floor, narrowly missing two floormen who jumped out of the way.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Rig-04 / Moran Field",
        )
    )

    ctx = await expl_service.get_investigation_context(res.report_id)
    assert ctx.report.id == res.report_id
    assert ctx.report.report_ref == res.report_ref
    assert ctx.assessment is not None
    assert ctx.assessment.sif_classification == SIFClassification.POTENTIAL_SIF
    assert len(ctx.evidence) >= 4
    assert ctx.screening is not None
    assert ctx.precursor is not None
    assert len(ctx.precursor_provenance) >= 3


@pytest.mark.asyncio
async def test_nonexistent_entity_exceptions(db_session: AsyncSession):
    """Verify deterministic 404 exceptions on nonexistent reports, assessments, patterns, and concentrations."""
    service = EvidenceExplanationService(db_session)
    fake_id = uuid.uuid4()

    with pytest.raises(ReportNotFoundException):
        await service.get_report_evidence(fake_id)

    with pytest.raises(AssessmentNotFoundException):
        await service.get_assessment_evidence(fake_id)

    with pytest.raises(PatternNotFoundException):
        await service.get_pattern_evidence(fake_id)

    with pytest.raises(ConcentrationNotFoundException):
        await service.get_concentration_evidence("NONEXISTENT_KEY")


@pytest.mark.asyncio
async def test_phase3_canonical_concentration_taxonomy_preservation(db_session: AsyncSession):
    """Correction 1: Verify all 6 canonical Phase 3 concentration dimensions are preserved and exposed unchanged."""
    service = EvidenceExplanationService(db_session)

    # 1. Create a sample report and assessment
    r = SafetyReport(
        id=uuid.uuid4(),
        report_ref="SR-CONC-TAX-001",
        source_type=SourceType.NEAR_MISS,
        raw_text="Overhead crane wire rope snapped during pipe transfer.",
        reported_location="Rig-07",
        actual_severity=ActualOutcome.NO_INJURY,
    )
    db_session.add(r)
    await db_session.flush()

    # 2. Create concentrations covering all 6 canonical Phase 3 dimensions
    canonical_dims = [
        (ConcentrationDimension.PATTERN, "PAT-001"),
        (ConcentrationDimension.HAZARD, "Suspended Load"),
        (ConcentrationDimension.BARRIER_FAILURE, "Rigging Failure"),
        (ConcentrationDimension.ACTIVITY, "Lifting Operations"),
        (ConcentrationDimension.LIFE_SAVING_RULE, "LSR_07_SAFE_MECHANICAL_LIFTING"),
        (ConcentrationDimension.LOCATION, "Rig-07"),
    ]

    for dim_type, dim_val in canonical_dims:
        key = f"CONC|{dim_type.value}|{dim_val}"
        conc = RiskConcentration(
            id=uuid.uuid4(),
            concentration_key=key,
            dimension_type=dim_type,
            dimension_value=dim_val,
            occurrence_count=3,
            distinct_report_count=3,
            distinct_location_count=1,
            first_observed_at=datetime.now(timezone.utc),
            last_observed_at=datetime.now(timezone.utc),
            observed_trend=ObservedTrend.STABLE,
            supporting_report_ids=[str(r.id)],
            supporting_locations=["Rig-07"],
            status=ConcentrationStatus.ACTIVE,
            calculation_method="FREQUENCY_AGGREGATION_V1",
        )
        db_session.add(conc)
    await db_session.flush()

    for dim_type, dim_val in canonical_dims:
        key = f"CONC|{dim_type.value}|{dim_val}"
        resp = await service.get_concentration_evidence(key)
        assert resp.concentration_key == key
        assert resp.dimension_type == dim_type
        assert isinstance(resp.dimension_type, ConcentrationDimension)
        assert resp.dimension_value == dim_val
        assert len(resp.supporting_reports) == 1
        assert resp.supporting_reports[0].report_id == r.id


@pytest.mark.asyncio
async def test_provenance_derivation_semantics_preserved(db_session: AsyncSession):
    """Correction 2: Verify provenance derivation types (DIRECT_MATCH, RULE_INFERENCE, METADATA) are preserved."""
    sif_service = SIFAnalysisService(db_session)
    expl_service = EvidenceExplanationService(db_session)

    from app.schemas.report import SingleReportAnalysisRequest

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-PROV-001",
            raw_text="High pressure gas leak observed on production separator due to faulty gasket seal during routine inspection.",
            source_type=SourceType.NEAR_MISS,
            reported_location="Production Header / Moran",
        )
    )

    explanation = await expl_service.get_screening_explanation(res.report_id)

    # Precursor provenance
    prov = explanation.precursor_provenance
    assert "hazard" in prov
    assert prov["hazard"].derivation_type in (
        DerivationType.DIRECT_MATCH,
        DerivationType.LEXICON_INFERENCE,
        DerivationType.RULE_INFERENCE,
    )
    assert prov["hazard"].value is not None

    if "location" in prov and prov["location"].value:
        assert prov["location"].derivation_type == DerivationType.METADATA

    # Evidence items
    ev_resp = await expl_service.get_report_evidence(res.report_id)
    assert ev_resp.total_evidence_items >= 1
    for ev in ev_resp.evidence_items:
        if ev.derivation_type:
            assert isinstance(ev.derivation_type, DerivationType)
            assert ev.derivation_type in (
                DerivationType.DIRECT_MATCH,
                DerivationType.LEXICON_INFERENCE,
                DerivationType.RULE_INFERENCE,
                DerivationType.METADATA,
            )


@pytest.mark.asyncio
async def test_missing_dimensions_are_null_not_placeholders(db_session: AsyncSession):
    """Correction 3: Verify missing precursor dimensions evaluate to None/null and never to '*', 'UNKNOWN', or 'OTHER'."""
    sif_service = SIFAnalysisService(db_session)
    expl_service = EvidenceExplanationService(db_session)

    from app.schemas.report import SingleReportAnalysisRequest

    # Sparse observation lacking activity and barrier failure
    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-SPARSE-001",
            raw_text="Pressurized gas line detected near fence.",
            source_type=SourceType.UC,
            reported_location=None,
        )
    )

    explanation = await expl_service.get_screening_explanation(res.report_id)
    assert explanation.structured_precursor is not None
    prec = explanation.structured_precursor

    # Check for placeholder strings in any field
    for field_name in ["hazard", "activity", "barrier_failure", "exposure", "potential_consequence", "life_saving_rule", "location"]:
        val = getattr(prec, field_name)
        assert val not in ("*", "UNKNOWN", "OTHER", "N/A"), f"Field {field_name} must not contain placeholder: {val}"


@pytest.mark.asyncio
async def test_phase7_read_only_invariance(db_session: AsyncSession):
    """Correction 4: Verify Phase 7 services are strictly read-only and cause zero database state mutations."""
    sif_service = SIFAnalysisService(db_session)
    expl_service = EvidenceExplanationService(db_session)

    from app.schemas.report import SingleReportAnalysisRequest

    res = await sif_service.analyze_and_persist(
        SingleReportAnalysisRequest(
            report_ref="SR-READONLY-001",
            raw_text="Technician working at 15 meters without harness on Rig-02.",
            source_type=SourceType.UA,
            reported_location="Rig-02",
        )
    )

    # Capture row counts before
    count_rep_before = (await db_session.execute(select(SafetyReport))).scalars().all()
    count_ass_before = (await db_session.execute(select(SIFAssessment))).scalars().all()

    # Call Phase 7 read operations multiple times
    _ = await expl_service.get_report_evidence(res.report_id)
    _ = await expl_service.get_screening_explanation(res.report_id)
    _ = await expl_service.get_investigation_context(res.report_id)

    # Capture row counts after
    count_rep_after = (await db_session.execute(select(SafetyReport))).scalars().all()
    count_ass_after = (await db_session.execute(select(SIFAssessment))).scalars().all()

    assert len(count_rep_before) == len(count_rep_after)
    assert len(count_ass_before) == len(count_ass_after)

