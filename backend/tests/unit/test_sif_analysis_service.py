"""Unit tests for SIFAnalysisService."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.assessment import SIFAssessment
from app.domain.enums import ActualOutcome, PotentialOutcome, SIFClassification, SourceType
from app.schemas.report import SingleReportAnalysisRequest
from app.services.sif_analysis_service import SIFAnalysisService


@pytest.mark.asyncio
async def test_sif_analysis_service_execution(db_session: AsyncSession):
    """Test full analysis and persistence flow in SIFAnalysisService."""
    service = SIFAnalysisService(db_session)
    request = SingleReportAnalysisRequest(
        raw_text=(
            "While running 9-5/8 inch casing at Rig-04, the air winch line parted and the heavy elevator swung "
            "across the rig floor near floormen. No injuries occurred."
        ),
        source_type=SourceType.NEAR_MISS,
        reported_location="Rig-04 / Moran Field",
        reported_department="Drilling Operations",
        actual_severity=ActualOutcome.NO_INJURY,
    )

    result = await service.analyze_and_persist(request)

    assert result.report_id is not None
    assert result.report_ref.startswith("SR-")
    assert result.sif_classification == SIFClassification.POTENTIAL_SIF
    assert result.evidence_score >= 0.60
    assert result.potential_severity == PotentialOutcome.FATALITY
    assert result.primary_lsr is not None
    assert result.primary_lsr.rule_code == "LSR_07_SAFE_MECHANICAL_LIFTING"

    # Verify extracted entities are preserved in context
    assert result.safety_event_context.activity is not None
    assert result.safety_event_context.activity.canonical_name == "Casing Running Operation"
    assert any("Suspended" in h.canonical_name for h in result.safety_event_context.hazards)
    assert any("Lifting Line" in b.canonical_name for b in result.safety_event_context.barrier_failures)

    # Verify structured precursor is synthesized and populated on result
    assert result.structured_precursor is not None
    assert result.structured_precursor.hazard == "Suspended Heavy Load"
    assert result.structured_precursor.activity == "Casing Running Operation"
    assert result.structured_precursor.barrier_failure == "Lifting Line / Rigging Failure"
    assert result.precursor_signature is not None

    # Verify persisted assessment in database has structured_precursor populated and pattern_id/embedding as None
    stmt = select(SIFAssessment).where(SIFAssessment.report_id == result.report_id)
    ass_res = await db_session.execute(stmt)
    assessment = ass_res.scalar_one_or_none()
    assert assessment is not None
    assert assessment.structured_precursor is not None
    assert assessment.structured_precursor["hazard"] == "Suspended Heavy Load"
    assert assessment.structured_precursor["activity"] == "Casing Running Operation"
    assert "field_provenance" in assessment.structured_precursor
    assert assessment.precursor_signature == result.precursor_signature
    assert assessment.pattern_id is None
    assert assessment.text_embedding is not None
    assert len(assessment.text_embedding) == 384




@pytest.mark.asyncio
async def test_sif_analysis_service_empty_text_raises_value_error(db_session: AsyncSession):
    """Test that empty narrative input raises ValueError."""
    service = SIFAnalysisService(db_session)
    request = SingleReportAnalysisRequest.model_construct(
        raw_text="   ",
        source_type=SourceType.NEAR_MISS,
        actual_severity=ActualOutcome.NO_INJURY,
    )

    with pytest.raises(ValueError, match="narrative cannot be empty"):
        await service.analyze_and_persist(request)
