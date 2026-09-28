"""Unit tests for BatchNormalizer."""

from datetime import datetime, timezone
import pytest
from app.domain.batch.normalizer import BatchNormalizer
from app.domain.enums import ActualOutcome, SourceType


def test_batch_normalizer_text():
    """Verify Unicode NFKC, whitespace collapsing, and control character stripping."""
    raw = "  Worker \t observed   standing \r\n under \u00a0 suspended pipe \x00 load.  "
    norm = BatchNormalizer.normalize_text(raw)
    assert norm == "Worker observed standing under suspended pipe load."

    assert BatchNormalizer.normalize_text(None) is None
    assert BatchNormalizer.normalize_text("   ") is None


def test_batch_normalizer_dates_valid():
    """Verify ISO, standard date, and datetime parsing to UTC."""
    # ISO-8601
    d1 = BatchNormalizer.normalize_date("2026-03-15T14:30:00Z")
    assert d1 == datetime(2026, 3, 15, 14, 30, 0, tzinfo=timezone.utc)

    # YYYY-MM-DD
    d2 = BatchNormalizer.normalize_date("2026-03-15")
    assert d2 == datetime(2026, 3, 15, 0, 0, 0, tzinfo=timezone.utc)

    # DD/MM/YYYY
    d3 = BatchNormalizer.normalize_date("15/03/2026 10:00:00")
    assert d3 == datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc)

    # MM/DD/YYYY
    d4 = BatchNormalizer.normalize_date("03/15/2026")
    assert d4 == datetime(2026, 3, 15, 0, 0, 0, tzinfo=timezone.utc)

    # None and empty
    assert BatchNormalizer.normalize_date(None) is None
    assert BatchNormalizer.normalize_date("") is None
    assert BatchNormalizer.normalize_date("N/A") is None


def test_batch_normalizer_dates_invalid_raises():
    """Verify unparseable date strings raise ValueError."""
    with pytest.raises(ValueError, match="Unrecognized date format"):
        BatchNormalizer.normalize_date("32-13-2026")

    with pytest.raises(ValueError, match="Unrecognized date format"):
        BatchNormalizer.normalize_date("yesterday afternoon")


def test_batch_normalizer_source_type():
    """Verify source type mapping from various string representations."""
    assert BatchNormalizer.normalize_source_type("Near Miss") == SourceType.NEAR_MISS
    assert BatchNormalizer.normalize_source_type("UA") == SourceType.UA
    assert BatchNormalizer.normalize_source_type("Unsafe Condition") == SourceType.UC
    assert BatchNormalizer.normalize_source_type("Incident") == SourceType.INCIDENT
    assert BatchNormalizer.normalize_source_type(None) == SourceType.NEAR_MISS


def test_batch_normalizer_actual_outcome():
    """Verify actual severity/outcome mapping."""
    assert BatchNormalizer.normalize_actual_outcome("No Injury") == ActualOutcome.NO_INJURY
    assert BatchNormalizer.normalize_actual_outcome("First Aid") == ActualOutcome.FIRST_AID
    assert BatchNormalizer.normalize_actual_outcome("LTI") == ActualOutcome.LOST_TIME_INJURY
    assert BatchNormalizer.normalize_actual_outcome("Equipment Damage") == ActualOutcome.EQUIPMENT_DAMAGE_ONLY
    assert BatchNormalizer.normalize_actual_outcome(None) == ActualOutcome.NO_INJURY
