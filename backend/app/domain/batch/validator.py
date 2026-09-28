"""Validation layer for batch file uploads and individual safety report rows."""

from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

from app.domain.batch.models import ParsedReportRow


class BatchValidator:
    """Validates structural file properties and domain-level safety report row constraints."""

    @staticmethod
    def validate_file(
        file_content: bytes,
        filename: Optional[str],
        max_size_bytes: int = 10 * 1024 * 1024,
        allowed_extensions: Optional[List[str]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate file presence, size limits, and allowed file extensions.
        
        Returns (is_valid, error_message).
        """
        if not filename or not filename.strip():
            return False, "Filename must be provided and cannot be empty."

        # Extension check
        allowed = allowed_extensions or [".csv"]
        file_ext = Path(filename).suffix.lower()
        if file_ext not in [ext.lower() for ext in allowed]:
            return False, f"Unsupported file extension '{file_ext}'. Supported extensions are: {', '.join(allowed)}."

        # Non-empty check
        if not file_content or len(file_content.strip()) == 0:
            return False, "Uploaded file content is empty."

        # File size check
        if len(file_content) > max_size_bytes:
            return False, f"File size ({len(file_content)} bytes) exceeds the maximum allowed limit of {max_size_bytes} bytes."

        return True, None

    @staticmethod
    def validate_row(row: ParsedReportRow) -> List[Tuple[str, str, str]]:
        """Validate individual parsed row against structural and domain safety rules.
        
        Returns a list of (field_name, error_code, error_message) tuples.
        """
        errors: List[Tuple[str, str, str]] = []

        # 1. Required narrative check
        if not row.raw_text or len(row.raw_text.strip()) < 10:
            errors.append((
                "raw_text",
                "MISSING_REQUIRED_TEXT",
                f"Safety observation narrative is required and must contain at least 10 characters (got {len(row.raw_text.strip()) if row.raw_text else 0}).",
            ))

        # 2. Event timestamp sanity check
        if row.event_timestamp is not None:
            now = datetime.now(timezone.utc)
            # Allow 1 day future drift for timezone discrepancies
            if row.event_timestamp > now + timedelta(days=1):
                errors.append((
                    "event_timestamp",
                    "FUTURE_EVENT_DATE",
                    f"Event date cannot be in the future ({row.event_timestamp.isoformat()}).",
                ))

        # 3. String length constraints
        if row.source_report_id and len(row.source_report_id) > 100:
            errors.append((
                "source_report_id",
                "FIELD_TOO_LONG",
                f"Source report ID exceeds maximum allowed length of 100 characters ({len(row.source_report_id)} chars).",
            ))

        if row.reported_location and len(row.reported_location) > 255:
            errors.append((
                "reported_location",
                "FIELD_TOO_LONG",
                f"Reported location exceeds maximum allowed length of 255 characters ({len(row.reported_location)} chars).",
            ))

        if row.reported_department and len(row.reported_department) > 255:
            errors.append((
                "reported_department",
                "FIELD_TOO_LONG",
                f"Reported department exceeds maximum allowed length of 255 characters ({len(row.reported_department)} chars).",
            ))

        return errors
