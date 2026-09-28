"""CSV parser implementation for batch safety report ingestion."""

import csv
import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.domain.batch.models import ParsedReportRow
from app.domain.batch.normalizer import BatchNormalizer
from app.domain.interfaces.batch import BatchParserInterface


class CsvSafetyReportParser(BatchParserInterface):
    """Parses safety observation CSV files into normalized ParsedReportRow DTOs."""

    # Column alias mappings to canonical field names
    COLUMN_ALIASES: Dict[str, List[str]] = {
        "source_report_id": [
            "source_report_id",
            "report_ref",
            "report_id",
            "id",
            "reference_id",
            "incident_id",
            "ref_no",
            "reference",
        ],
        "raw_text": [
            "raw_text",
            "description",
            "narrative",
            "report_text",
            "observation",
            "event_description",
            "details",
            "text",
            "incident_description",
        ],
        "source_type": [
            "source_type",
            "report_type",
            "observation_type",
            "type",
            "category",
            "event_type",
        ],
        "reported_location": [
            "reported_location",
            "location",
            "facility",
            "site",
            "area",
            "field",
            "rig",
            "plant",
            "operating_unit",
        ],
        "reported_department": [
            "reported_department",
            "department",
            "dept",
            "section",
            "division",
            "unit",
        ],
        "actual_severity": [
            "actual_severity",
            "severity",
            "actual_outcome",
            "outcome",
            "injury_severity",
            "impact",
        ],
        "actual_outcome_details": [
            "actual_outcome_details",
            "outcome_details",
            "injury_details",
            "damage_details",
        ],
        "event_timestamp": [
            "event_timestamp",
            "event_date",
            "report_date",
            "date",
            "timestamp",
            "incident_date",
            "date_time",
        ],
    }

    def supports_format(self, filename: str) -> bool:
        """Return True if filename has a .csv extension."""
        return Path(filename).suffix.lower() == ".csv"

    def _decode_content(self, file_content: bytes) -> str:
        """Attempt multi-encoding decode of raw file bytes."""
        encodings = ["utf-8-sig", "utf-8", "latin-1", "iso-8859-1", "cp1252"]
        for enc in encodings:
            try:
                return file_content.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        raise ValueError("Unsupported or corrupt file encoding. File could not be decoded as UTF-8 or Latin-1.")

    def _resolve_column_mapping(self, header_row: List[str]) -> Tuple[Dict[str, str], List[str]]:
        """Map raw CSV column headers to canonical domain field names.
        
        Returns:
            Tuple of (column_index_or_name_to_canonical_field, list_of_ignored_columns)
        """
        mapping: Dict[str, str] = {}
        ignored: List[str] = []

        # Build reverse lookup map
        alias_to_canonical: Dict[str, str] = {}
        for canonical, aliases in self.COLUMN_ALIASES.items():
            for alias in aliases:
                alias_to_canonical[alias.lower().replace(" ", "_").replace("-", "_")] = canonical

        for col in header_row:
            clean_col = col.strip().lower().replace(" ", "_").replace("-", "_")
            if clean_col in alias_to_canonical:
                canonical_name = alias_to_canonical[clean_col]
                # If canonical field not yet mapped, map this column
                if canonical_name not in mapping.values():
                    mapping[col] = canonical_name
                else:
                    ignored.append(col)
            else:
                ignored.append(col)

        return mapping, ignored

    def parse(
        self,
        file_content: bytes,
        filename: str,
    ) -> Tuple[List[ParsedReportRow], List[Tuple[int, str, str, str]]]:
        """Parse raw CSV bytes into ParsedReportRow items and syntax errors."""
        text_content = self._decode_content(file_content)
        
        # Check empty or whitespace only
        if not text_content.strip():
            raise ValueError("CSV file is empty.")

        # Read CSV lines
        stream = io.StringIO(text_content, newline=None)
        reader = csv.reader(stream)

        try:
            header_row = next(reader)
        except StopIteration:
            raise ValueError("CSV file contains no headers or records.")
        except csv.Error as e:
            raise ValueError(f"Malformed CSV header structure: {e}")

        if not header_row or not any(h.strip() for h in header_row):
            raise ValueError("CSV file header row is empty.")

        col_mapping, ignored_cols = self._resolve_column_mapping(header_row)

        # Check required narrative column is present
        if "raw_text" not in col_mapping.values():
            raise ValueError(
                "CSV header is missing a required narrative column (e.g. 'raw_text', 'description', 'narrative', 'observation')."
            )

        parsed_rows: List[ParsedReportRow] = []
        parse_errors: List[Tuple[int, str, str, str]] = []

        for row_idx, raw_cells in enumerate(reader, start=2):
            # Skip empty lines
            if not raw_cells or not any(c.strip() for c in raw_cells):
                continue

            # Row data dictionary
            row_dict: Dict[str, Any] = {}
            for col_idx, col_name in enumerate(header_row):
                if col_idx < len(raw_cells):
                    row_dict[col_name] = raw_cells[col_idx]
                else:
                    row_dict[col_name] = None

            # Map canonical fields
            canonical_values: Dict[str, Any] = {}
            for original_header, canonical_field in col_mapping.items():
                canonical_values[canonical_field] = row_dict.get(original_header)

            raw_narrative = BatchNormalizer.normalize_text(canonical_values.get("raw_text")) or ""
            source_id = BatchNormalizer.normalize_text(canonical_values.get("source_report_id"))
            loc = BatchNormalizer.normalize_text(canonical_values.get("reported_location"))
            dept = BatchNormalizer.normalize_text(canonical_values.get("reported_department"))
            src_type = BatchNormalizer.normalize_source_type(canonical_values.get("source_type"))
            act_sev = BatchNormalizer.normalize_actual_outcome(canonical_values.get("actual_severity"))
            outcome_details = BatchNormalizer.normalize_text(canonical_values.get("actual_outcome_details"))

            # Parse event date safely
            raw_date = canonical_values.get("event_timestamp")
            parsed_date = None
            if raw_date is not None and str(raw_date).strip():
                try:
                    parsed_date = BatchNormalizer.normalize_date(raw_date)
                except ValueError as ve:
                    parse_errors.append((
                        row_idx,
                        "event_timestamp",
                        "INVALID_DATE_FORMAT",
                        str(ve),
                    ))
                    # Row has date formatting failure -> skip adding to parsed_rows so it is recorded as rejected
                    continue

            parsed_row = ParsedReportRow(
                row_number=row_idx,
                raw_text=raw_narrative,
                source_report_id=source_id,
                source_type=src_type,
                reported_location=loc,
                reported_department=dept,
                actual_severity=act_sev,
                actual_outcome_details=outcome_details,
                event_timestamp=parsed_date,
                raw_data=row_dict,
                ignored_columns=ignored_cols,
            )
            parsed_rows.append(parsed_row)

        return parsed_rows, parse_errors
