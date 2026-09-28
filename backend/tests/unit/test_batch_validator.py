"""Unit tests for BatchValidator."""

from datetime import datetime, timedelta, timezone
from app.domain.batch.models import ParsedReportRow
from app.domain.batch.validator import BatchValidator
from app.domain.enums import ActualOutcome, SourceType


def test_batch_validator_file_valid():
    """Verify validate_file accepts valid CSV within size constraints."""
    valid, err = BatchValidator.validate_file(b"col1,col2\nval1,val2", "safety_reports.csv", 1024)
    assert valid is True
    assert err is None

    valid_caps, err_caps = BatchValidator.validate_file(b"data", "INCIDENTS_2026.CSV", 50000)
    assert valid_caps is True
    assert err_caps is None


def test_batch_validator_file_invalid_extension():
    """Verify validate_file rejects non-csv file extensions."""
    valid, err = BatchValidator.validate_file(b"data", "safety_reports.xlsx", 1024)
    assert valid is False
    assert "Unsupported file extension '.xlsx'" in err

    valid, err = BatchValidator.validate_file(b"data", "data.pdf", 1024)
    assert valid is False
    assert "Unsupported file extension '.pdf'" in err


def test_batch_validator_file_empty():
    """Verify validate_file rejects 0-byte or whitespace-only files."""
    valid, err = BatchValidator.validate_file(b"", "empty.csv", 1024)
    assert valid is False
    assert "empty" in err.lower()

    valid, err = BatchValidator.validate_file(b"   \n\r\n  ", "whitespace.csv", 1024)
    assert valid is False
    assert "empty" in err.lower()


def test_batch_validator_file_size_exceeded():
    """Verify validate_file rejects files exceeding maximum size limit."""
    content = b"x" * 2000
    valid, err = BatchValidator.validate_file(content, "huge.csv", max_size_bytes=1000)
    assert valid is False
    assert "exceeds the maximum allowed limit" in err


def test_batch_validator_row_valid():
    """Verify validate_row approves a compliant row with valid fields."""
    row = ParsedReportRow(
        row_number=2,
        source_report_id="INC-001",
        raw_text="Worker observed standing under suspended pipe bundle on drilling rig floor.",
        source_type=SourceType.NEAR_MISS,
        reported_location="Rig-04 Moran",
        reported_department="Drilling",
        actual_severity=ActualOutcome.NO_INJURY,
        event_timestamp=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
    )
    errors = BatchValidator.validate_row(row)
    assert len(errors) == 0


def test_batch_validator_row_missing_text():
    """Verify validate_row rejects rows with empty or whitespace-only narrative."""
    row = ParsedReportRow(
        row_number=2,
        source_report_id="INC-002",
        raw_text="    ",
        source_type=SourceType.NEAR_MISS,
    )
    errors = BatchValidator.validate_row(row)
    assert len(errors) == 1
    field_name, error_code, msg = errors[0]
    assert field_name == "raw_text"
    assert error_code == "MISSING_REQUIRED_TEXT"


def test_batch_validator_row_narrative_too_short():
    """Verify validate_row rejects narratives shorter than minimum required length."""
    row = ParsedReportRow(
        row_number=3,
        source_report_id="INC-003",
        raw_text="Short",
        source_type=SourceType.NEAR_MISS,
    )
    errors = BatchValidator.validate_row(row)
    assert len(errors) == 1
    assert errors[0][1] == "MISSING_REQUIRED_TEXT"


def test_batch_validator_row_future_timestamp():
    """Verify validate_row rejects event timestamps in the future."""
    future_time = datetime.now(timezone.utc) + timedelta(days=365)
    row = ParsedReportRow(
        row_number=4,
        source_report_id="INC-004",
        raw_text="Worker slipped on wet deck plating near generator house.",
        event_timestamp=future_time,
    )
    errors = BatchValidator.validate_row(row)
    assert len(errors) == 1
    assert errors[0][1] == "FUTURE_EVENT_DATE"


def test_batch_validator_field_length_limits():
    """Verify validate_row rejects string fields exceeding maximum column lengths."""
    row = ParsedReportRow(
        row_number=5,
        source_report_id="X" * 105,
        raw_text="Worker observed improper rigging technique during crane lift.",
        reported_location="L" * 300,
        reported_department="D" * 300,
    )
    errors = BatchValidator.validate_row(row)
    assert len(errors) == 3
    assert all(err[1] == "FIELD_TOO_LONG" for err in errors)
