"""Unit tests for Pydantic v2 schemas and validation contracts."""

import pytest
from pydantic import ValidationError
from uuid import uuid4

from app.domain.enums import (
    ActualOutcome,
    EvidenceStrength,
    PotentialOutcome,
    SIFClassification,
    SourceType,
)
from app.schemas.assessment import (
    ActualOutcomeDTO,
    ExplainabilityDTO,
    PotentialOutcomeDTO,
    ScoringBreakdownDTO,
)
from app.schemas.precursor import StructuredPrecursor
from app.schemas.report import (
    SingleReportAnalysisRequest,
    SingleReportAnalysisResponse,
)
from app.schemas.taxonomy import LSRMappingDTO


def test_structured_precursor_all_dimensions():
    """Verify 7-dimensional StructuredPrecursor initializes properly."""
    precursor = StructuredPrecursor(
        hazard="High Pressure Gas Release",
        activity="Flange Bolting on Wellhead",
        barrier_failure="Defective Gasket / Torque Spec Not Verified",
        exposure="Technician in Direct Trajectory",
        potential_consequence="High-Velocity Projectile Impact / Fire",
        life_saving_rule="LSR_04_ENERGY_ISOLATION",
        location="EPS Moran / Wellhead-14",
    )
    assert precursor.hazard == "High Pressure Gas Release"
    assert precursor.activity == "Flange Bolting on Wellhead"
    assert precursor.barrier_failure == "Defective Gasket / Torque Spec Not Verified"
    assert precursor.exposure == "Technician in Direct Trajectory"
    assert precursor.potential_consequence == "High-Velocity Projectile Impact / Fire"
    assert precursor.life_saving_rule == "LSR_04_ENERGY_ISOLATION"
    assert precursor.location == "EPS Moran / Wellhead-14"


def test_single_report_analysis_request_valid():
    """Verify valid request payload parses cleanly."""
    req = SingleReportAnalysisRequest(
        raw_text="Winch line snapped during casing running on rig floor. Two floormen narrowly avoided impact.",
        source_type=SourceType.NEAR_MISS,
        reported_location="Rig-04 / Moran Field",
        actual_severity=ActualOutcome.NO_INJURY,
    )
    assert req.source_type == SourceType.NEAR_MISS
    assert req.actual_severity == ActualOutcome.NO_INJURY


def test_single_report_analysis_request_too_short():
    """Verify raw_text under 10 chars triggers validation error."""
    with pytest.raises(ValidationError):
        SingleReportAnalysisRequest(
            raw_text="Short",
            source_type=SourceType.NEAR_MISS,
        )


def test_single_report_analysis_response_schema():
    """Verify complete response contract validation."""
    resp = SingleReportAnalysisResponse(
        report_id=uuid4(),
        sif_classification=SIFClassification.POTENTIAL_SIF,
        actual_outcome=ActualOutcomeDTO(
            severity=ActualOutcome.NO_INJURY,
            details="No injuries occurred",
        ),
        potential_outcome=PotentialOutcomeDTO(
            severity=PotentialOutcome.FATALITY,
            details="Catastrophic crush exposure",
        ),
        scoring=ScoringBreakdownDTO(
            evidence_score=0.94,
            evidence_strength=EvidenceStrength.HIGH,
            rule_based_screening_score=0.92,
        ),
        life_saving_rules=[
            LSRMappingDTO(
                taxonomy_id="IOGP_REPORT_459",
                rule_code="LSR_07_SAFE_MECHANICAL_LIFTING",
                rule_name="Safe Mechanical Lifting",
                confidence_score=0.96,
                is_primary=True,
            )
        ],
        structured_precursor=StructuredPrecursor(
            hazard="Suspended Load",
            activity="Casing Running",
            barrier_failure="Winch line parted",
            exposure="Floormen in swing radius",
            potential_consequence="Fatality",
            life_saving_rule="LSR_07_SAFE_MECHANICAL_LIFTING",
            location="Rig-04",
        ),
        explainability=ExplainabilityDTO(
            primary_reasoning="High energy lifting failure...",
            evidence_spans=[],
            rule_provenance=["RULE_MECHANICAL_LIFTING"],
        ),
    )
    assert resp.sif_classification == SIFClassification.POTENTIAL_SIF
    assert resp.scoring.evidence_strength == EvidenceStrength.HIGH
