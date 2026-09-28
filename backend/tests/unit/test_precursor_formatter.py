"""Unit tests for PrecursorTextFormatter."""

import pytest
from app.domain.precursor.formatter import PrecursorTextFormatter
from app.domain.precursor.model import (
    PrecursorDimensionProvenance,
    StructuredSIFPrecursor,
)


def test_formatter_full_precursor():
    """Verify deterministic formatting with all 7 dimensions populated."""
    precursor = StructuredSIFPrecursor(
        hazard="Suspended Load / Rigging Failure",
        activity="Crane & Hoisting Operations",
        barrier_failure="Rigging Failure / Line Parted",
        exposure="Line of Fire Exposure",
        potential_consequence="FATALITY",
        life_saving_rule="LSR_03_MECHANICAL_LIFTING",
        location="Rig-04 / Moran Field",
    )
    text = PrecursorTextFormatter.format_to_text(precursor)
    assert text is not None
    lines = text.split("\n")
    assert len(lines) == 7
    assert lines[0] == "Hazard: Suspended Load / Rigging Failure"
    assert lines[1] == "Activity: Crane & Hoisting Operations"
    assert lines[2] == "Barrier Failure: Rigging Failure / Line Parted"
    assert lines[3] == "Exposure: Line of Fire Exposure"
    assert lines[4] == "Potential Consequence: FATALITY"
    assert lines[5] == "Life-Saving Rule: LSR_03_MECHANICAL_LIFTING"
    assert lines[6] == "Location: Rig-04 / Moran Field"


def test_formatter_sparse_precursor_omits_none_and_no_wildcards():
    """Verify missing dimensions are cleanly omitted and no wildcards appear."""
    precursor = StructuredSIFPrecursor(
        hazard="Housekeeping & Minor Trip Hazard",
        activity=None,
        barrier_failure=None,
        exposure=None,
        potential_consequence=None,
        life_saving_rule=None,
        location="Central Workshop",
    )
    text = PrecursorTextFormatter.format_to_text(precursor)
    assert text is not None
    assert "*" not in text
    assert "UNKNOWN" not in text
    assert "OTHER" not in text
    assert text == "Hazard: Housekeeping & Minor Trip Hazard\nLocation: Central Workshop"


def test_formatter_none_precursor_returns_none():
    """Verify None input returns None."""
    assert PrecursorTextFormatter.format_to_text(None) is None


def test_formatter_empty_precursor_returns_none():
    """Verify empty precursor returns None."""
    precursor = StructuredSIFPrecursor()
    assert PrecursorTextFormatter.format_to_text(precursor) is None
