"""Normalization layer for batch safety report ingestion."""

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Optional

from app.domain.enums import ActualOutcome, SourceType


class BatchNormalizer:
    """Normalizes raw input fields from batch files before validation."""

    @staticmethod
    def normalize_text(text: Optional[str]) -> Optional[str]:
        """Normalize string with Unicode NFKC, strip control characters and excessive whitespace."""
        if text is None:
            return None
        text_str = str(text)
        # Unicode normalization
        norm = unicodedata.normalize("NFKC", text_str)
        # Replace non-breaking spaces and line breaks with standard spaces
        norm = norm.replace("\r\n", " ").replace("\r", " ").replace("\n", " ").replace("\t", " ")
        # Strip control characters (except standard printable)
        norm = "".join(ch for ch in norm if unicodedata.category(ch)[0] != "C" or ch == " ")
        # Collapse multiple spaces
        norm = re.sub(r"\s+", " ", norm).strip()
        return norm if norm else None

    @staticmethod
    def normalize_date(date_val: Any) -> Optional[datetime]:
        """Parse date string into timezone-aware UTC datetime.
        
        Raises ValueError if a non-empty string cannot be parsed.
        """
        if date_val is None:
            return None
        if isinstance(date_val, datetime):
            if date_val.tzinfo is None:
                return date_val.replace(tzinfo=timezone.utc)
            return date_val.astimezone(timezone.utc)

        val_str = str(date_val).strip()
        if not val_str or val_str.lower() in ("null", "none", "nan", "n/a", ""):
            return None

        # Clean trailing 'Z' if needed for fromisoformat in older pythons
        cleaned_str = val_str.replace("Z", "+00:00") if val_str.endswith("Z") else val_str

        # 1. Try ISO-8601
        try:
            dt = datetime.fromisoformat(cleaned_str)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except (ValueError, TypeError):
            pass

        # 2. Try common date and datetime formats
        common_formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y",
            "%d-%m-%Y %H:%M:%S",
            "%d-%m-%Y",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M",
            "%m/%d/%Y",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d",
        ]
        for fmt in common_formats:
            try:
                dt = datetime.strptime(val_str, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

        raise ValueError(f"Unrecognized date format: '{date_val}'")

    @staticmethod
    def normalize_source_type(source_type_val: Optional[str]) -> SourceType:
        """Map raw source classification string to SourceType enum."""
        if not source_type_val:
            return SourceType.NEAR_MISS
        clean = source_type_val.strip().upper().replace(" ", "_").replace("-", "_")
        if clean in ("UA", "UNSAFE_ACT", "UNSAFE_ACTION"):
            return SourceType.UA
        elif clean in ("UC", "UNSAFE_CONDITION", "UNSAFE_COND"):
            return SourceType.UC
        elif clean in ("INCIDENT", "ACCIDENT", "OCCURRENCE"):
            return SourceType.INCIDENT
        elif clean in ("NEAR_MISS", "NEARMISS", "NM"):
            return SourceType.NEAR_MISS
        return SourceType.NEAR_MISS

    @staticmethod
    def normalize_actual_outcome(severity_val: Optional[str]) -> ActualOutcome:
        """Map raw severity/outcome string to ActualOutcome enum."""
        if not severity_val:
            return ActualOutcome.NO_INJURY
        clean = severity_val.strip().upper().replace(" ", "_").replace("-", "_")
        if clean in ("NO_INJURY", "NONE", "NO_HARM", "NIL", "UNHARMED"):
            return ActualOutcome.NO_INJURY
        elif clean in ("FIRST_AID", "FA", "FIRSTAID", "FIRST_AID_CASE"):
            return ActualOutcome.FIRST_AID
        elif clean in ("MINOR_INJURY", "MINOR", "MEDICAL_TREATMENT", "MTC", "RESTRICTED_WORK", "RWC"):
            return ActualOutcome.MINOR_INJURY
        elif clean in ("LOST_TIME_INJURY", "LTI", "LOST_TIME", "MAJOR_INJURY", "FATALITY"):
            return ActualOutcome.LOST_TIME_INJURY
        elif clean in ("EQUIPMENT_DAMAGE_ONLY", "EQUIPMENT_DAMAGE", "PROPERTY_DAMAGE", "DAMAGE_ONLY", "MATERIAL_DAMAGE"):
            return ActualOutcome.EQUIPMENT_DAMAGE_ONLY
        return ActualOutcome.NO_INJURY
