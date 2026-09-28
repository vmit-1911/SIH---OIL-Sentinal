"""Unit tests for SafetyEventContextDTO schemas."""

from app.domain.enums import EvidenceStrength
from app.schemas.assessment import EvidenceSpanDTO
from app.schemas.safety_event import ExtractedItemDTO, SafetyEventContextDTO


def test_safety_event_context_dto_validation():
    """Verify SafetyEventContextDTO serializes cleanly."""
    dto = SafetyEventContextDTO(
        original_text="Raw text here",
        normalized_text="Raw text here",
        activity=ExtractedItemDTO(
            canonical_name="Casing Running Operation",
            category="ACTIVITY",
            raw_match="running casing",
            evidence_spans=[
                EvidenceSpanDTO(
                    text="running casing",
                    category="ACTIVITY",
                    start_char=0,
                    end_char=14,
                )
            ],
            evidence_strength=EvidenceStrength.HIGH,
        ),
        hazards=[
            ExtractedItemDTO(
                canonical_name="Suspended Heavy Load",
                category="HAZARD",
                raw_match="heavy elevator",
                evidence_spans=[],
                evidence_strength=EvidenceStrength.HIGH,
            )
        ],
    )
    assert dto.original_text == "Raw text here"
    assert dto.activity.canonical_name == "Casing Running Operation"
    assert len(dto.hazards) == 1
