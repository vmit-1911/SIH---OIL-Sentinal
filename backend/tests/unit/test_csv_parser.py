"""Unit tests for CsvSafetyReportParser."""

import pytest
from app.infrastructure.parsers.csv_parser import CsvSafetyReportParser


def test_csv_parser_valid_file_all_aliases():
    """Verify parsing a valid CSV with various supported column aliases."""
    csv_data = (
        "id,description,category,facility,severity,event_date\n"
        "INC-101,Worker standing in line of fire near high pressure manifold,NEAR_MISS,Rig-04 Moran,NO_INJURY,2026-03-10\n"
        "INC-102,Scaffolding plank unfastened at 15m elevation,UNSAFE_CONDITION,Platform-A,MINOR_INJURY,2026-03-11\n"
    ).encode("utf-8")

    parser = CsvSafetyReportParser()
    assert parser.supports_format("test.csv") is True
    assert parser.supports_format("test.xlsx") is False

    rows, errors = parser.parse(csv_data, "test.csv")
    assert len(errors) == 0
    assert len(rows) == 2

    assert rows[0].row_number == 2
    assert rows[0].source_report_id == "INC-101"
    assert "pressure manifold" in rows[0].raw_text
    assert rows[0].reported_location == "Rig-04 Moran"
    assert rows[0].event_timestamp is not None
    assert rows[0].event_timestamp.year == 2026
    assert rows[0].event_timestamp.month == 3
    assert rows[0].event_timestamp.day == 10

    assert rows[1].row_number == 3
    assert rows[1].source_report_id == "INC-102"
    assert "Scaffolding" in rows[1].raw_text


def test_csv_parser_utf8_bom_handling():
    """Verify parsing a UTF-8 file with BOM signature."""
    csv_text = "report_ref,raw_text,reported_location\nSR-BOM-1,Forklift operated near unprotected pedestrian aisle,Central Yard\n"
    csv_data = csv_text.encode("utf-8-sig")

    parser = CsvSafetyReportParser()
    rows, errors = parser.parse(csv_data, "bom.csv")
    assert len(errors) == 0
    assert len(rows) == 1
    assert rows[0].source_report_id == "SR-BOM-1"
    assert "Forklift" in rows[0].raw_text


def test_csv_parser_latin1_encoding():
    """Verify parsing a Latin-1 encoded CSV with accented characters."""
    csv_text = "report_ref,raw_text,location\nSR-LATIN-1,Rupture de tuyau sous pression à l'unité de forage,Bassin Pétrolier\n"
    csv_data = csv_text.encode("latin-1")

    parser = CsvSafetyReportParser()
    rows, errors = parser.parse(csv_data, "latin.csv")
    assert len(errors) == 0
    assert len(rows) == 1
    assert "tuyau sous pression" in rows[0].raw_text
    assert rows[0].reported_location == "Bassin Pétrolier"


def test_csv_parser_missing_narrative_header_raises_value_error():
    """Verify CSV missing required narrative column raises descriptive ValueError."""
    csv_data = "report_id,location,event_date\n101,Rig-04,2026-01-01\n".encode("utf-8")
    parser = CsvSafetyReportParser()
    with pytest.raises(ValueError, match="missing a required narrative column"):
        parser.parse(csv_data, "invalid.csv")


def test_csv_parser_empty_file_raises_value_error():
    """Verify completely empty CSV content raises ValueError."""
    parser = CsvSafetyReportParser()
    with pytest.raises(ValueError, match="CSV file is empty"):
        parser.parse(b"", "empty.csv")


def test_csv_parser_ignored_columns_recorded():
    """Verify unrecognized columns are preserved in ignored_columns without failing parse."""
    csv_data = (
        "report_ref,raw_text,custom_enterprise_id,internal_sap_code\n"
        "SR-1,Worker observed standing under suspended pipe load,CUSTOM-99,SAP-888\n"
    ).encode("utf-8")

    parser = CsvSafetyReportParser()
    rows, errors = parser.parse(csv_data, "ignored.csv")
    assert len(errors) == 0
    assert len(rows) == 1
    assert "custom_enterprise_id" in rows[0].ignored_columns
    assert "internal_sap_code" in rows[0].ignored_columns
    assert rows[0].raw_data["custom_enterprise_id"] == "CUSTOM-99"


def test_csv_parser_invalid_date_recorded_as_syntax_error():
    """Verify row with corrupt date format is returned in syntax errors and not parsed rows."""
    csv_data = (
        "report_ref,raw_text,event_date\n"
        "SR-OK,Worker observed standing under crane load on deck,2026-03-15\n"
        "SR-BAD,Pressure gauge valve leaking hydrogen sulfide gas,NOT_A_REAL_DATE\n"
    ).encode("utf-8")

    parser = CsvSafetyReportParser()
    rows, errors = parser.parse(csv_data, "dates.csv")
    assert len(rows) == 1
    assert rows[0].source_report_id == "SR-OK"
    assert len(errors) == 1
    assert errors[0][0] == 3  # row 3
    assert errors[0][1] == "event_timestamp"
    assert errors[0][2] == "INVALID_DATE_FORMAT"
