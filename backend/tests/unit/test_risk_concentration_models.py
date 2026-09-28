"""Unit tests for risk concentration domain models and key generation."""

import uuid
from datetime import datetime, timezone
from app.domain.concentration.models import (
    ConcentrationEvidence,
    ConcentrationFinding,
    generate_concentration_key,
    normalize_dimension_identity,
)
from app.domain.enums import ConcentrationDimension, ConcentrationStatus, ObservedTrend


def test_normalize_dimension_identity():
    """Verify deterministic string normalization for concentration keys."""
    assert normalize_dimension_identity("Suspended Load") == "SUSPENDED_LOAD"
    assert normalize_dimension_identity("LSR_03_MECHANICAL_LIFTING") == "LSR_03_MECHANICAL_LIFTING"
    assert normalize_dimension_identity("Rig-04 / Moran Field") == "RIG_04_MORAN_FIELD"
    assert normalize_dimension_identity("  Multiple   Spaces  ") == "MULTIPLE_SPACES"
    assert normalize_dimension_identity("") == "UNSPECIFIED"
    assert normalize_dimension_identity(None) == "UNSPECIFIED"


def test_generate_concentration_key_all_dimensions():
    """Verify concentration key generation for all supported dimensions."""
    k_haz = generate_concentration_key(ConcentrationDimension.HAZARD, "Suspended Load")
    assert k_haz == "CONC|HAZARD|SUSPENDED_LOAD"

    k_bar = generate_concentration_key(ConcentrationDimension.BARRIER_FAILURE, "Rigging Failure")
    assert k_bar == "CONC|BARRIER_FAILURE|RIGGING_FAILURE"

    k_act = generate_concentration_key(ConcentrationDimension.ACTIVITY, "Crane Lifting")
    assert k_act == "CONC|ACTIVITY|CRANE_LIFTING"

    k_lsr = generate_concentration_key(ConcentrationDimension.LIFE_SAVING_RULE, "LSR_03_MECHANICAL_LIFTING")
    assert k_lsr == "CONC|LIFE_SAVING_RULE|LSR_03_MECHANICAL_LIFTING"

    k_loc = generate_concentration_key(ConcentrationDimension.LOCATION, "Rig-04 / Moran")
    assert k_loc == "CONC|LOCATION|RIG_04_MORAN"

    k_pat = generate_concentration_key(ConcentrationDimension.PATTERN, "PAT_LSR_03_CRANE_LIFTING_A1B2C3D4")
    assert k_pat == "CONC|PATTERN|PAT_LSR_03_CRANE_LIFTING_A1B2C3D4"


def test_concentration_finding_domain_model():
    """Verify ConcentrationFinding domain model structure and defaults."""
    now = datetime.now(timezone.utc)
    id1 = uuid.uuid4()
    finding = ConcentrationFinding(
        concentration_key="CONC|HAZARD|TOXIC_GAS",
        dimension_type=ConcentrationDimension.HAZARD,
        dimension_value="Toxic Gas",
        occurrence_count=3,
        distinct_report_count=3,
        distinct_location_count=2,
        first_observed_at=now,
        last_observed_at=now,
        observed_trend=ObservedTrend.STABLE,
        temporal_distribution={"2026-01": 2, "2026-02": 1},
        supporting_report_ids=[id1],
        supporting_locations=["Rig-01", "Rig-02"],
    )

    assert finding.concentration_key == "CONC|HAZARD|TOXIC_GAS"
    assert finding.dimension_type == ConcentrationDimension.HAZARD
    assert finding.occurrence_count == 3
    assert finding.distinct_location_count == 2
    assert finding.status == ConcentrationStatus.ACTIVE
    assert finding.supporting_locations == ["Rig-01", "Rig-02"]
